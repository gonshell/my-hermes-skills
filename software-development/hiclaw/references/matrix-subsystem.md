# HiClaw Matrix Subsystem — Deep Reference

## 1. Design Motivation: Why Matrix

HiClaw's core scenario is "Manager orchestrates Workers, Admin observes and intervenes via IM." This demands a protocol that is simultaneously machine-programmable and human-readable.

| Requirement | gRPC | NATS | Redis Pub/Sub | Matrix |
|---|---|---|---|---|
| Agent↔Agent async messages | ✅ | ✅ | ✅ | ✅ |
| Human-in-the-loop (native IM UI) | ❌ needs extra UI | ❌ | ❌ | ✅ Element Web |
| Room-level permission isolation | app-layer only | ❌ | ❌ | ✅ PowerLevel |
| Offline message replay | app-layer only | ❌ | ❌ | ✅ /sync |
| Multi-client simultaneous (Element + Agent) | ❌ | ❌ | ❌ | ✅ |
| E2EE | ❌ | ❌ | ❌ | ✅ Megolm |
| Add participants without protocol change | ❌ schema change | ❌ | ❌ | ✅ invite/join |

Matrix is the only protocol where Agents are first-class chat room citizens alongside humans.

**Why Tuwunel (not Synapse)?** Tuwunel is a conduwuit fork (Rust). Single binary, embedded SQLite, ~30MB RAM. Synapse (Python) needs PostgreSQL, orders of magnitude heavier. HiClaw's "one-click install" constraint rules out Synapse.

**Why not a custom protocol?** Human-in-the-Loop requires a production-grade Web IM client. Building one from scratch is a separate product. Element Web exists, is mature, and renders Matrix rooms natively.

## 2. Core Concepts

### 2.1 Participant Identities

| Identity | MXID Format | Power Level | Role |
|----------|-------------|-------------|------|
| Admin | `@admin:<domain>` | 100 (all rooms) | System administrator |
| Manager | `@manager:<domain>` | 100 (all rooms) | Orchestration Agent |
| Worker | `@<name>:<domain>` | 0 | Task execution Agent |
| Human | `@<name>:<domain>` | varies | Human participant |

### 2.2 Room Types

| Type | Alias Format | Participants | Purpose |
|------|-------------|--------------|---------|
| Worker Room | `#hiclaw-worker-<name>:<domain>` | Admin(100) + Authority(100) + Worker(0) | Single Agent workspace |
| Admin DM Room | (no alias) | Admin + Manager | Admin↔Manager direct conversation |
| Team Room | `#hiclaw-team-<name>:<domain>` | TeamAdmin(100)+Leader(100)+AllWorkers(0)+AllHumans(0) | Team collaboration |
| Leader DM Room | `#hiclaw-leader-dm-<name>:<domain>` | TeamAdmin + Leader | Private command channel |
| #admins Room | (no alias) | Admin + Tuwunel admin bot | Controller→Tuwunel admin commands |

**Authority resolution for Worker Room:**
- Team Worker → Team Leader
- Standalone Worker with Manager → Manager
- Standalone Worker without Manager → Admin

### 2.3 Tuwunel Configuration

| Config | Value | Design Intent |
|--------|-------|---------------|
| `ALLOW_REGISTRATION` | true | Controller dynamically registers Agent users |
| `REGISTRATION_TOKEN` | random | Prevent unauthorized registration |
| `DELETE_ROOMS_AFTER_LEAVE` | true | Agent deletion auto-cleans rooms |
| `FORGET_FORCED_UPON_LEAVE` | true | Complete room state purge |
| `SERVER_NAME` | `matrix-local.hiclaw.io:8080` | Internal only, no public exposure |
| `PORT` | 6167 | Internal, proxied via Nginx/Higress to 8080 |
| `CACHE_CAPACITY_MODIFIER` | 2.0 | Prevent RocksDB thrashing |

Start script: `manager/scripts/init/start-tuwunel.sh`

## 3. Architecture Layers

```
Control Plane:  Controller (Go) → REST API → Tuwunel
Data Plane:     Agent containers → Matrix SDK (nio/mautrix/js-sdk) → Tuwunel
Human Plane:    Element Web (Nginx :8088) → Tuwunel
Transport:      Tuwunel (Matrix protocol, message routing, persistence)
```

Controller holds admin token. Agent containers hold normal user tokens. Admin accesses via Element Web with `@admin` credentials. Clean separation.

## 4. Controller Matrix Client

Interface: `hiclaw-controller/internal/matrix/client.go` — `Client` (18 methods):

- **User mgmt**: `EnsureUser`, `Login`, `SetDisplayName`, `UserID`
- **Room mgmt**: `CreateRoom` (idempotent via alias), `ResolveRoomAlias`, `DeleteRoomAlias`, `JoinRoom`, `LeaveRoom`
- **Membership**: `InviteToRoom`, `InviteToRoomWithToken`, `KickFromRoom`, `KickFromRoomWithToken`, `ListRoomMembers`, `ListRoomMembersWithToken`, `ListJoinedRooms`
- **Messaging**: `SendMessage`, `SendMessageAsAdmin`
- **Admin**: `AdminCommand` (fires `!admin ...` to Tuwunel admin bot room)

`TuwunelClient` implements this via REST API with cached admin token (`atomic.Value`).

### 4.1 Orphan Recovery in EnsureUser

Tuwunel cannot hard-delete users — only deactivate. Re-registering the same username hits `M_USER_IN_USE`. If the stored password no longer works (password rotated or user deactivated), `EnsureUser` performs orphan recovery:

```
register → M_USER_IN_USE → login with stored password → fail
  → password rotated or user deactivated
    → AdminCommand("!admin users reset-password @user new-pass")
      → exponential backoff (500ms × attempt, max 5)
        → re-login with new password → success
```

This is critical for K8s environments where Workers are deleted and recreated with the same name.

## 5. Credential Delivery Chain (End-to-End)

### Step 1: Controller Provisioner

`ProvisionWorker()` in `provisioner.go`:
```
1. loadWorkerCredentials()    → generate or load passwords/keys
2. matrix.EnsureUser()        → register Matrix user
   Returns: UserCredentials{AccessToken, Password}
3. ossAdmin.EnsureUser()      → create MinIO user (embedded mode)
4. matrix.CreateRoom()        → create Worker Room
5. matrix.JoinRoom()          → join worker into room (runtimes that don't auto-join)
6. gateway.EnsureConsumer()   → create Higress consumer + authorize AI routes

Returns: WorkerProvisionResult{
  MatrixToken:    "syt_xxx...",     ← Matrix access token
  MatrixPassword: "auto-gen-16-char", ← for E2EE re-login
  GatewayKey:     "hex-32-chars",   ← Higress AI Gateway key
  MinIOPassword:  "auto-gen",       ← MinIO user password
  RoomID:         "!xxx:domain",    ← Worker Room ID
}
```

### Step 2: WorkerEnvBuilder

`worker_env.go` converts `WorkerProvisionResult` → container environment variables:
```
HICLAW_WORKER_NAME:         "alice"
HICLAW_WORKER_GATEWAY_KEY:  "hex..."
HICLAW_WORKER_MATRIX_TOKEN: "syt_xxx..."
HICLAW_FS_ACCESS_KEY:       "alice"
HICLAW_FS_SECRET_KEY:       "minio-password"
+ cluster defaults: HICLAW_MATRIX_URL, HICLAW_MATRIX_DOMAIN, etc.
```

### Step 3: Deployer → openclaw.json → MinIO

`deployer.go:DeployWorkerConfig()` generates `openclaw.json` and pushes to MinIO:
```json
{
  "channels": {
    "matrix": {
      "homeserver": "http://matrix-local.hiclaw.io:8080",
      "accessToken": "syt_xxx...",
      "userId": "@alice:matrix-local.hiclaw.io:8080",
      "autoJoin": "always",
      "dm": {"policy": "allowlist", "allowFrom": ["@manager:...", "@admin:..."]},
      "groupPolicy": "allowlist",
      "groupAllowFrom": ["@manager:...", "@admin:..."]
    }
  },
  "gateway": { "auth": { "token": "hex..." } },
  "models": { "providers": { "hiclaw-gateway": {...} } }
}
```

Also writes:
- `agents/{name}/credentials/matrix/password` → for E2EE re-login
- `agents/{name}/SOUL.md`, `AGENTS.md`, `skills/`

### Step 4: Worker Container Startup

`worker/scripts/worker-entrypoint.sh`:
1. **Pull config from MinIO**: `mc mirror` pulls openclaw.json, SOUL.md, AGENTS.md (retries up to 6×5s=30s)
2. **Clean crypto storage**: `rm -rf ~/.openclaw/matrix` — prevents stale E2EE sessions
3. **Re-login**: Read password from MinIO → `POST /_matrix/client/v3/login` → new token + device_id → `jq` updates openclaw.json
   - Why: crypto store is clean, old token's device_id has stale identity keys → E2EE fails
4. **Start OpenClaw**: `exec openclaw gateway run --verbose --force`
   - Reads openclaw.json, connects to Matrix with fresh token
   - First /sync → auto-join invited rooms → receive messages

**Security design:**
- Matrix **password** stored in MinIO (not env vars)
- Matrix **access token** delivered via two paths: (1) env var `HICLAW_WORKER_MATRIX_TOKEN` (CoPaw) (2) openclaw.json `channels.matrix.accessToken` (OpenClaw)
- Worker re-logins with password to get fresh token at startup (E2EE needs clean device_id)
- Gateway key via env var `HICLAW_WORKER_GATEWAY_KEY`

## 6. End-to-End Message Flow

### 6.1 Admin Assigns Task to Manager

```
Admin (Element Web)          Tuwunel          Manager Agent
     │                          │                   │
     │── m.room.message ──────→│                   │
     │   (Admin DM Room)       │── /sync ────────→│
     │                         │                   │─ parse task intent
     │                         │                   │─ select target Worker
```

### 6.2 Manager Dispatches Task to Worker

```
Manager Agent              MinIO              Worker Room         Worker Agent
     │                       │                     │                   │
     │─ mkdir + spec.md ──→│                     │                   │
     │─ mc cp → MinIO ────→│                     │                   │
     │                       │                     │                   │
     │── @worker:domain ─────────────────────────→│── /sync ────────→│
     │   "New task [task-id]│                     │                   │─ file-sync pull
     │    pull spec.md"     │←── mc mirror ──────│←──────────────────│
     │                       │                     │                   │─ execute task
```

**CRITICAL ORDERING**: Manager MUST push spec to MinIO BEFORE @mentioning Worker. If reversed, Worker file-sync gets empty files.

**Mention format**: Full MXID `@worker-name:matrix-local.hiclaw.io:8080` — missing domain prevents Worker's message filter from triggering.

**Send to Worker Room, NOT Admin DM**: Worker channel policy only accepts messages from its own Room.

Manager sends via runtime-specific method:
- **OpenClaw Manager**: `message` tool with `channel=matrix` and `target=room:<ROOM_ID>`
- **CoPaw Manager**: `copaw channels send --channel matrix --target-session "<ROOM_ID>" ...`

### 6.3 Worker Reports Completion

```
Worker Agent          Worker Room           Manager Agent          Admin DM
     │                     │                      │                     │
     │── @manager:domain ─→│── /sync ────────────→│                     │
     │   "task completed"  │                      │─ file-sync pull    │
     │                     │                      │─ read result.md    │
     │                     │                      │─ update state.json │
     │                     │                      │── [Task Completed]─→│
```

### 6.4 Task Directory Layout

```
shared/tasks/{task-id}/
├── meta.json     # Manager-maintained (type: finite/infinite, status, timestamps)
├── spec.md       # Manager-written requirements + acceptance criteria
├── base/         # Manager reference files (Workers must not overwrite)
├── plan.md       # Worker-written execution plan
├── result.md     # Worker-written final result
└── *             # Intermediate artifacts
```

## 7. Manager's Matrix Role (Deep)

### 7.1 Manager Startup & Registration (Docker Embedded Mode)

`manager/scripts/init/start-manager-agent.sh`:
1. Wait for Tuwunel ready (poll `/_matrix/client/versions`)
2. Register `admin` user via `m.login.registration_token`
3. Register `manager` user via `m.login.registration_token`
4. Login Manager with `m.login.password` → access token
5. Create Admin DM Room (`@admin + @manager`)
6. Background process: wait for OpenClaw ready, then send welcome message

### 7.2 K8s Welcome: Three-Gate Protocol

K8s mode: Controller handles welcome via `SendManagerWelcomeMessage`. Three sequential gates prevent silent message loss:

```
Gate 1: Manager joined DM?
  Controller polls ListRoomMembers until manager status = join
  (If not joined, message goes to timeline history → OpenClaw catch-up drops it)

Gate 2: LLM auth ready?
  Controller POSTs /v1/chat/completions with Bearer gatewayKey
  (Higress WASM key-auth propagation takes ~40-45s. If welcome arrives
   before auth propagates, Manager tries to respond, LLM call 401s,
   onboarding silently fails)

Gate 3: CLAIM WelcomeSent=true
  Prevents duplicate welcome from concurrent reconciles

After all gates clear → send welcome message
```

**Why active probes instead of sleep**: Docker mode uses `sleep 45` (fragile). K8s mode uses precise active probes — faster when conditions are met, reliable when they're slow.

### 7.3 Manager Task Dispatch Protocol

From `manager/agent/skills/task-management/references/finite-tasks.md`:

1. Generate task ID: `task-YYYYMMDD-HHMMSS`
2. Create task dir + `meta.json` (type: "finite", status: "assigned") + `spec.md`
3. **Push to MinIO immediately** (Worker can't file-sync until files are in MinIO)
4. Notify Worker in their Room (never Admin DM):
   ```
   @{worker}:{domain} New task [{task-id}]: {title}.
   Use your file-sync skill to pull the spec: shared/tasks/{task-id}/spec.md.
   @mention me when complete.
   ```
5. **MANDATORY**: Register in `state.json` via `manage-state.sh --action add-finite`
   - Skipping this → Worker auto-stopped by idle timeout while still working

### 7.4 Channel Policy Security Model

Three layers of defense (all enforced simultaneously):

| Layer | Mechanism | Scope |
|-------|-----------|-------|
| Matrix PowerLevel | PL:100 for admin/manager, PL:0 for workers | Room-level: who can modify settings, kick, etc. |
| OpenClaw Channel Policy | DM allowlist + group allowlist | Client-level: which messages the Agent processes |
| Tuwunel Invite ACL | Only room members can invite | Server-level: who can add people to rooms |

`openclaw.json` policy example:
```json
{
  "dm": {"policy": "allowlist", "allowFrom": ["@manager:domain", "@admin:domain"]},
  "groupPolicy": "allowlist",
  "groupAllowFrom": ["@manager:domain", "@admin:domain"],
  "groups": {"*": {"allow": true, "requireMention": true}}
}
```
- Worker only accepts DMs from Manager and Admin
- Worker in groups only responds to @mention
- Team Worker's allowlist replaces Manager with Team Leader

## 8. Three-Runtime Matrix Integration Comparison

| Dimension | OpenClaw (Node.js) | CoPaw (Python) | Hermes (Python) |
|-----------|-------------------|----------------|-----------------|
| Matrix SDK | Custom TS (matrix-js-sdk wrapper) | matrix-nio (Python async) | mautrix (Go bridge, Python overlay) |
| Config source | `openclaw.json` → channels.matrix | `openclaw.json` → bridge.py → `config.json` | Env vars + overlay inheritance |
| Login | Startup re-login (password → new token) | Startup re-login (same) | Inherits upstream bridge auth |
| Message receive | /sync long-poll (built into OpenClaw gateway) | /sync long-poll (nio AsyncClient, 30s timeout) | Bridge's sync loop |
| Auto-join rooms | `autoJoin: "always"` config | `_on_invite` callback auto-accept | Overlay inherits |
| E2EE | Supported (needs re-login for clean device_id) | Supported (libolm, crypto store) | Depends on upstream bridge |
| History buffer | OpenClaw session management | `HistoryBuffer` (per-room, configurable size/strategy) | Upstream bridge manages |
| Message format | m.text + HTML render | m.text + markdown→HTML | Upstream bridge format |
| File sync trigger | `file-sync` skill + 5m periodic pull | `FileSync` class (push/pull/propagate 3-layer) | Upstream bridge mechanism |
| Worker Room join | Auto (autoJoin) or Controller JoinRoom | Auto (_on_invite) | Controller JoinRoom on behalf |
| Debounce key | N/A | `matrix:<room_id>` | N/A |

## 9. Provisioning Flows

### 9.1 Worker Provisioning (`Provisioner.ProvisionWorker`)

```
1. loadWorkerCredentials()        → generate or load passwords/keys
2. matrix.EnsureUser()            → register Matrix user (or orphan recovery)
3. ossAdmin.EnsureUser()          → create MinIO user (embedded mode only)
4. matrix.CreateRoom()            → create Worker Room (idempotent via alias)
   - PowerLevels: admin=100, manager=100, authority=100, worker=0
   - Invite: admin, authority, worker
4a. ReconcileRoomMembership()     → fix membership diffs for existing rooms
4b. matrix.JoinRoom()             → join worker into room (runtimes that don't auto-join)
5. gateway.EnsureConsumer()       → create AI Gateway consumer + authorize AI routes
   + 2s sleep (Higress WASM key-auth sync delay)
```

### 9.2 Team Provisioning (`Provisioner.ProvisionTeamRooms`)

```
1. Resolve all participant MXIDs
2. Create Team Room (all members, PL: manager=100, leader=100, teamAdmin=100)
3. Create Leader DM Room (TeamAdmin + Leader only)
4. Reconcile membership for both rooms
```

### 9.3 Agent Lifecycle & Room Cleanup

```
Worker deletion:
  DeprovisionWorker()
    → gateway.DeauthorizeAIRoutes + DeleteConsumer
    → ossAdmin.DeleteUser
    → (async) LeaveAllWorkerRooms → Tuwunel DELETE_ROOMS_AFTER_LEAVE auto-cleanup
```

## 10. Runtime Matrix Clients (Detailed)

### 10.1 CoPaw (matrix-nio)

File: `copaw/src/matrix/channel.py` — `MatrixChannel(BaseChannel)`, ~2574 lines

Key features:
- **E2EE**: via matrix-nio + libolm, auto-trust all devices (bot use case)
- **History Buffer**: per-room buffer of unmentioned messages, injected as context on next mention
- **Typing Indicator**: auto-renewal (25s interval, 120s max)
- **Thread Support**: via `matrix_thread_root_event_id` metadata
- **Media**: image/audio/video/file upload and download
- **DM Detection**: cached DM room membership for reliable DM vs group distinction
- **Debounce**: serialized per room_id (`get_debounce_key` returns `matrix:<room_id>`)
- **from_env()**: reads `HICLAW_MATRIX_SERVER` + `HICLAW_MATRIX_TOKEN` from environment

History buffer markers (shared with OpenClaw for consistency):
```
[Chat messages since your last reply - for context]
sender: message body
...

[Current message - respond to this]
sender: @mention message
```

### 10.2 Hermes (mautrix overlay)

File: `hermes/src/hermes_matrix/overlay_adapter.py` — `MatrixAdapter(_NativeMatrixAdapter)`

**Not a reimplementation** — subclasses hermes-agent's native mautrix adapter, injects HiClaw-specific policy:
- `DualAllowList` — separate DM/group allow-lists (from env vars)
- `HistoryBuffer` — CoPaw-compatible history buffering
- `apply_outbound_mentions` — auto-fills `m.mentions.user_ids` from body text
- Image downgrade — non-vision models get `[sent an image: ...]` text placeholder

Policy helpers: `hermes/src/hermes_matrix/policies.py`

### 10.3 Mention Mechanism

OpenClaw's mention detection requires **both**:
1. `m.mentions.user_ids` contains the agent's MXID
2. Visible mention in body (matrix.to link) or regex match on agent identity

Missing either → silently dropped with `reason: "no-mention"`.

Test helper: `tests/lib/matrix-client.sh::matrix_send_mention_message` always includes both.

## 11. Element Web Integration

Deployed inside Manager container (port 8088). Config: `manager/scripts/init/start-element-web.sh`

```
config.json → points to local Tuwunel
Nginx (:8088) → static file serving + browser compat bypass
Manager Console (:18888) → reverse proxy to OpenClaw Gateway (:18799)
  OpenClaw: auto-injects gateway token via inline script for auto-login
  CoPaw: plain reverse proxy (no token injection needed)
WASM Plugin Server (:8002) → serves WASM modules to Envoy
```

Admin logs into Element Web with `@admin` credentials, sees:
- Admin DM Room (direct conversation with Manager)
- All Worker Rooms (observe task execution)
- Can @mention specific Workers to intervene

## 12. Key Environment Variables

| Variable | Used By | Purpose |
|----------|---------|---------|
| `HICLAW_MATRIX_DOMAIN` | Tuwunel, Controller | Server name for MXID construction |
| `HICLAW_REGISTRATION_TOKEN` | Tuwunel | Token for user registration API |
| `HICLAW_MATRIX_SERVER` | CoPaw | Homeserver URL for matrix-nio |
| `HICLAW_MATRIX_TOKEN` | CoPaw | Access token for Worker login |
| `HICLAW_WORKER_MATRIX_TOKEN` | OpenClaw | Worker Matrix token (env var path) |
| `HICLAW_WORKER_GATEWAY_KEY` | Worker | Higress AI Gateway auth key |
| `HICLAW_FS_ACCESS_KEY` | Worker | MinIO access key (= worker name) |
| `HICLAW_FS_SECRET_KEY` | Worker | MinIO secret key |
| `MATRIX_VISION_ENABLED` | Hermes | Whether active model supports image input |
| `MATRIX_DM_POLICY` | Hermes | DM allow-list mode (open/allowlist) |
| `MATRIX_GROUP_POLICY` | Hermes | Group allow-list mode |
| `MATRIX_ALLOWED_USERS` | Hermes | Comma-separated DM allow-list |
| `MATRIX_GROUP_ALLOW_FROM` | Hermes | Comma-separated group allow-list |
| `MATRIX_HISTORY_LIMIT` | Hermes | Max unmentioned messages to buffer per room |
| `COPAW_REACT_MAX_ITERS` | CoPaw | Max ReAct loop iterations (default 200) |

## 13. Test Infrastructure

`tests/lib/matrix-client.sh` provides Shell wrappers for Matrix API:
- `matrix_register`, `matrix_login` — user management
- `matrix_send_message`, `matrix_send_mention_message` — messaging (mention includes both m.mentions + matrix.to link)
- `matrix_wait_for_reply`, `matrix_wait_for_reply_matching` — polling with baseline snapshot
- `matrix_send_and_wait_for_reply` — at-least-once delivery with periodic resend (handles runtime readiness gaps)
- `matrix_wait_for_user_joined` — membership readiness check

**At-least-once is critical**: "membership=join" is NOT sufficient for readiness:
- CoPaw: suppresses callbacks during first-boot catch-up sync
- Hermes: controller pre-joins on behalf, room shows "join" before container boots
- OpenClaw: smaller but non-zero window for handler registration

## 14. Design Trade-offs

**Strengths:**
1. Room model naturally fits multi-Agent collaboration — permission isolation, message history, multi-party
2. Human-in-the-Loop needs zero extra UI — Element Web out of the box
3. Three-layer permission control (Matrix PL + Channel Policy + Invite ACL) is defense-in-depth
4. Credential chain is clear: Controller → MinIO → Container pull → re-login
5. Three-gate welcome protocol precisely solves distributed race conditions

**Costs:**
1. **Latency**: Matrix /sync long-poll (30s timeout) + message propagation + Agent processing → seconds, not milliseconds
2. **Tuwunel limitations**: Cannot hard-delete users, cannot delete rooms via API — admin bot workarounds needed
3. **Long config chain**: Controller → MinIO → Container pull → openclaw.json → Runtime parse. Any break → Agent won't start
4. **E2EE tax**: Every restart clears crypto store + re-login, increasing startup time
