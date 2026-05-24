# HiClaw CRD & Runtime Lifecycle Reference

Supplements `references/matrix-subsystem.md` with CRD reconciliation internals
and runtime bridge/lifecycle details discovered through source reading.

## 1. Human CRD Lifecycle

### 1.1 Reconciler Structure

File: `hiclaw-controller/internal/controller/human_controller.go`

`HumanReconciler` — no container, no gateway consumer. Entire job: keep a
Matrix user + room memberships in sync with `Spec.AccessibleWorkers/Teams`.

Three phases in order (only infrastructure is fatal):

```
reconcileHumanNormal:
  1. reconcileHumanInfra  → Matrix account registration (fatal)
  2. reconcileHumanRooms  → invite/join/kick rooms (non-fatal)
  3. reconcileHumanLegacy → humans-registry.json (non-fatal)
```

### 1.2 Infrastructure Phase

File: `human_reconcile_infra.go`

**First provisioning** (`Status.MatrixUserID == ""`):
- `EnsureHumanUser(username)` → registers account → gets `creds.{UserID, Password, AccessToken}`
- Persists `Status.MatrixUserID` + `Status.InitialPassword`
- Seeds `scope.userToken` for subsequent rooms phase

**Steady state** (`Status.MatrixUserID != ""`):
- **Does nothing** — intentionally avoids Login on every reconcile tick.
- Rationale: `POST /_matrix/client/v3/login` without a `device_id` creates a
  fresh device session every time. A Human has no credential store (unlike
  Worker's `WorkerCredentials.MatrixToken` path), so we avoid the call
  altogether unless rooms phase actually needs a token.

**DisplayName sync**: on first provisioning + when `Generation` changes,
calls `SetDisplayName`. If no token available, does a one-time LoginAsHuman
with the stored InitialPassword.

**Design decision**: never falls back to `EnsureHumanUser` after first
provisioning because its orphan-recovery branch issues
`!admin users reset-password`, which would silently overwrite a password
the user may have rotated via Element.

### 1.3 Rooms Phase

File: `human_reconcile_rooms.go`

Declarative reconciliation of Human's room memberships against desired state
derived from `Spec.AccessibleWorkers` and `Spec.AccessibleTeams`.

For each accessible Worker:
- Resolve Worker's room via `ResolveRoomAlias`
- `ensureJoinedRoom`: uses `ensureUserToken()` (lazy LoginAsHuman) to get a
  token, then `JoinRoomWithToken` + `InviteToRoomWithToken`

For each accessible Team:
- Resolve Team room
- Same join/invite flow

Rooms no longer in spec → `KickFromRoom` (graceful, logs errors)

**ensureUserToken laziness**: only logs in when there's actually a new room
to join. Prevents device bloat from 5-minute periodic requeues.

### 1.4 Provisioner Methods for Human

File: `internal/service/provisioner_human.go`

```
EnsureHumanUser(username) → UserCredentials
  1. Register (M_USER_IN_USE → orphan recovery via admin reset-password)
  2. Login with generated password → access_token

LoginAsHuman(username, password) → access_token
  - POST /_matrix/client/v3/login m.login.password

InviteToRoom(roomID, userID)
  - Uses admin token

JoinRoomAs(roomID, userID) → uses admin command to force-join
KickFromRoom(roomID, userID)
ForceLeaveRoom(roomID, userID)
SetDisplayName(userID, token, name)
```

### 1.5 Deletion

File: `human_reconcile_delete.go`

1. For each room the Human is known to be in: `ForceLeaveRoom`
2. Remove finalizer
3. **Does NOT delete the Matrix user** — only removes room memberships

## 2. Team CRD Reconciliation

File: `hiclaw-controller/internal/controller/team_controller.go` (~1183 lines)

### 2.1 reconcileTeamNormal — Six Steps

```
1. buildDesiredMembers(t) → []MemberContext
2. ReconcileTeamRooms → create/join Team Room + Leader DM Room
3. For each member: ReconcileMemberInfra → ProvisionWorker + Matrix account
4. For each member: ReconcileMemberConfig → openclaw.json → MinIO
5. For each member: ReconcileMemberContainer → create/update K8s container
6. For each member: ReconcileMemberExpose → ports, ingress
```

### 2.2 buildDesiredMembers

Constructs `[]MemberContext` from Team spec:
- **Leader**: mapped via `leaderWorkerSpec()` with merged ChannelPolicy
- **Each Worker**: mapped via `teamWorkerSpecToWorkerSpec()` with merged ChannelPolicy

Each `MemberContext` carries: Name, RuntimeName, Namespace, Role, Spec,
Generation, SpecChanged (hash comparison), IsUpdate, TeamName,
TeamLeaderName, TeamAdminMatrixID, TeamCoordinatorIDs, PodLabels, Owner.

### 2.3 ChannelPolicy Merging Rules

**Leader policy**:
```
base = merge(teamPolicy, leaderPolicy)
leader gets groupAllow: all worker names + coordinator IDs
leader gets dmAllow: teamAdmin ID
```

**Worker policy**:
```
base = merge(teamPolicy, workerPolicy)
worker gets groupAllow: leader name + coordinator IDs
if PeerMentions (default true): worker gets groupAllow: all peer worker names
```

This means: Leader can @mention all workers. Workers can @mention leader
(and optionally each other). TeamAdmin and Coordinators can @mention everyone.

### 2.4 Spec Hashing (SpecChanged)

`hashMemberSourceSpec` computes FNV-1a-64 of JSON payload:
- Leader: `{Leader: LeaderSpec, TeamPolicy}`
- Worker: `{Worker: TeamWorkerSpec, TeamPolicy, PeerMentions}`

Only user-authored fields are hashed (not derived values like groupAllowExtra).
`SpecChanged` is `false` when stored hash is empty (new member) — initial
creation handled by StatusNotFound branch in ReconcileMemberContainer.

**Stability contract**: every new field on `LeaderSpec`/`TeamWorkerSpec` MUST
have `json:",omitempty"` and zero-value semantics matching pre-field behavior.
Otherwise all Teams get recreated on upgrade.

## 3. Shared Member Reconciliation

File: `internal/controller/member_reconcile.go` (~487 lines)

Shared by Team controller (for leader + workers). Four phases:

### 3.1 ReconcileMemberInfra
- If member not provisioned: `ProvisionWorker()` (Matrix + Gateway + MinIO + SA)
- If member provisioned but spec changed: `DeprovisionWorker()` then `ProvisionWorker()`

### 3.2 ReconcileMemberConfig
- Generate openclaw.json via `agentconfig.Generator`
- Push to MinIO via `FileSync`
- Inject coordination context (SOUL.md templates, heartbeat config)

### 3.3 ReconcileMemberContainer
- Check K8s container status (Starting/Running/Stopped)
- Create or update container as needed
- Handle spec changes with graceful shutdown

### 3.4 ReconcileMemberExpose
- Port forwarding for exposed services
- Ingress configuration

## 4. Hermes Worker Runtime

### 4.1 Worker Lifecycle

File: `hermes/src/hermes_worker/worker.py`

```
Worker.run():
  1. start()
     a. _ensure_mc() — auto-download MinIO Client
     b. FileSync(endpoint, key, secret, bucket, worker_name)
     c. sync.mirror_all() — full MinIO pull (excl. credentials/)
     d. sync.get_config() — read openclaw.json
     e. _matrix_relogin(openclaw_cfg) — fresh token + device_id for E2EE
     f. bridge_openclaw_to_hermes(cfg, hermes_home, soul, agents_md)
     g. _load_env_file(hermes_home/.env) — source into os.environ
     h. _sync_skills() — MinIO skills/ → hermes_home/skills/
     i. _copy_mcporter_config()
     j. sync_loop (background, periodic pull)
     k. push_loop (background, 5s interval)
  2. _run_hermes_gateway() — start_gateway(gw_config)
```

### 4.2 Matrix Re-login

File: `hermes/src/hermes_worker/worker.py:_matrix_relogin`

```
1. Read password from MinIO: agents/{name}/credentials/matrix/password
2. POST /_matrix/client/v3/login m.login.password
3. Extract new access_token + device_id
4. Update openclaw.json channels.matrix.accessToken/deviceId
5. Persist back to disk for subsequent re-bridge
```

Fails gracefully: if no password in MinIO or login fails, uses existing token
(E2EE may not work, but agent still runs).

### 4.3 Bridge: openclaw.json → Hermes Config

File: `hermes/src/hermes_worker/bridge.py`

**Bridge-owned env keys** (rewritten every time):
- `MATRIX_*` prefix: HOMESERVER, ACCESS_TOKEN, USER_ID, DEVICE_ID, ENCRYPTION,
  DM_POLICY, ALLOW_USERS, GROUP_POLICY, GROUP_ALLOW_FROM, REQUIRE_MENTION,
  FREE_RESPONSE_ROOMS, AUTO_THREAD, DM_MENTION_THREADS, HOME_ROOM,
  VISION_ENABLED, FILTER_TOOL_MESSAGES, FILTER_THINKING, HISTORY_LIMIT
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `HERMES_DEFAULT_MODEL`

**Bridge-owned YAML blocks**:
- `model: {default, provider, base_url, context_length}`
- `auxiliary.vision: {provider, model, base_url, api_key}` (if model supports image)
- `matrix: {require_mention, auto_thread, dm_mention_threads, free_response_rooms}`
- `platforms.matrix: {enabled: true, reply_to_mode: "first"}`
- `logging.level: DEBUG` (when `HICLAW_MATRIX_DEBUG=1`)

**Non-bridge keys preserved**: user-added env vars (TAVILY_API_KEY, etc.),
terminal backend, memory limits, MCP servers, skills paths.

**Port remapping**: container-internal `:8080` → host-exposed gateway port
(18080 by default) when worker runs on host (dev mode).

### 4.4 File Sync (MinIO)

File: `hermes/src/hermes_worker/sync.py`

**Manager-managed (Worker pull-only)**: openclaw.json, mcporter-servers.json, skills/

**Worker-managed (Worker push)**: AGENTS.md, SOUL.md, sessions/, memory/

**openclaw.json merge** (not blind overwrite):
- Base: local (Worker)
- Remote overlays: `models`, `gateway` (replace), `channels` (deep merge, local token wins)
- `plugins.entries`: deep merge, local wins shared keys; `load.paths`: union

**Shared files**:
- Team member: pulls from `teams/{team_id}/shared/`
- Team leader: also pulls from global `shared/`

### 4.5 Shim: Module Replacement

File: `hermes/src/hermes_matrix/_shim.py`

Replaces hermes-agent's native Matrix platform module with HiClaw's overlay
subclass at import time. The overlay adapter (`overlay_adapter.py`) inherits
from the native adapter and adds HiClaw-specific policy and history buffering.

## 5. CoPaw Worker Runtime

### 5.1 Standard Space → Runtime Space Bridge

File: `copaw/src/copaw_worker/bridge.py` (~906 lines)

Two distinct "spaces":
- **Standard space**: `/root/.hiclaw-worker/<name>/` — durable, runtime-agnostic
  (openclaw.json, SOUL.md, skills/, config/)
- **Runtime space**: `/root/.hiclaw-worker/<name>/.copaw/` — CoPaw-native layout
  (config.json, providers.json, workspaces/default/agent.json)

`bridge_standard_to_runtime()`:
1. Copy prompt files (SOUL.md, AGENTS.md) → workspaces/default/
2. Convert openclaw.json → config.json + providers.json + agent.json
3. Copy providers.json to secret dir
4. Sync mcporter config
5. Symlink skills/ directory

### 5.2 Matrix Field Derivation (openclaw → CoPaw config.json)

```
channels.matrix.enabled     ← matrix.enabled (default true)
channels.matrix.homeserver  ← matrix.homeserver (port-remapped)
channels.matrix.access_token ← matrix.accessToken
channels.matrix.user_id     ← matrix.userId OR derived from env
channels.matrix.encryption  ← matrix.encryption (default false)
channels.matrix.dm_policy   ← matrix.dm.policy (default "allowlist")
channels.matrix.group_policy ← matrix.groupPolicy (default "allowlist")
channels.matrix.filter_tool_messages ← matrix.filterToolMessages
channels.matrix.filter_thinking     ← matrix.filterThinking (default true)
channels.matrix.vision_enabled      ← derived from model input modalities
channels.matrix.history_limit       ← matrix.historyLimit
channels.matrix.allow_from   ← matrix.dm.allowFrom (union merge)
channels.matrix.group_allow_from ← matrix.groupAllowFrom (union merge)
channels.matrix.groups       ← matrix.groups (deep merge)
```

## 6. Manager Reconciler

File: `hiclaw-controller/internal/controller/manager_controller.go`

```
reconcileManagerNormal:
  1. reconcileManagerInfra  → ProvisionManager (Matrix + Gateway + MinIO + SA)
  2. reconcileManagerSA     → K8s ServiceAccount + RBAC
  3. reconcileManagerConfig → openclaw.json → MinIO
  4. reconcileManagerContainer → K8s Deployment
  5. reconcileManagerWelcome → 3-gate welcome protocol
```

`reconcileManagerInfra` (`manager_reconcile_infra.go`):
- `ProvisionManager()` on first run (or when credentials missing)
- `RefreshManagerCredentials()` on subsequent runs (re-issue gateway key)

## 7. Service Interfaces

File: `hiclaw-controller/internal/service/interfaces.go`

Key Matrix-relevant interfaces:

```
WorkerProvisioner:
  ProvisionWorker / DeprovisionWorker
  ProvisionManager / DeprovisionManager
  ProvisionTeamRooms / DeprovisionTeamRooms

HumanProvisioner:
  EnsureHumanUser / LoginAsHuman
  InviteToRoom / JoinRoomAs / KickFromRoom / ForceLeaveRoom
  SetDisplayName
```

These are consumed by the reconcilers. The Provisioner implementation
(`provisioner.go`) orchestrates Matrix + Gateway + MinIO + K8s calls.
