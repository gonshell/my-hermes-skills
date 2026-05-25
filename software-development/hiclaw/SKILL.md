---
name: hiclaw
description: "Understanding, reading, and modifying the HiClaw multi-agent collaboration platform. Covers architecture, Matrix communication subsystem, Controller CRD/reconciler, Worker runtimes (OpenClaw/CoPaw/Hermes), deployment, and testing."
triggers:
  - HiClaw
  - hiclaw-controller
  - hiclaw
  - Tuwunel
  - Matrix Agent
  - 多Agent协作
  - Worker CRD
  - Manager CRD
  - Team CRD
---

# HiClaw Platform

## What It Is

HiClaw is an open-source multi-Agent collaboration runtime platform by Alibaba Higress team. It is **not** an Agent framework — it is an orchestration and lifecycle management platform that runs Agent containers and wires them together via Matrix protocol rooms.

GitHub: `agentscope-ai/HiClaw`

## Source Tree (at `/Users/xiesg/dev/HiClaw`)

```
hiclaw-controller/        # Go K8s Operator (CRD + reconciler + CLI + REST API)
  api/v1beta1/             # CRD types: Worker, Manager, Team, Human
  internal/
    controller/            # Reconcilers: WorkerReconciler, TeamReconciler, ManagerReconciler
    service/               # Provisioner (Matrix + Gateway + MinIO + K8s SA orchestration)
    matrix/                # Matrix homeserver REST client (TuwunelClient)
    gateway/               # Higress AI Gateway REST client
    oss/                   # MinIO admin client
    auth/                  # K8s ServiceAccount + token management
copaw/                     # Python Worker runtime package
  src/matrix/              # Matrix channel (matrix-nio), shared by Manager and Worker
  src/copaw_worker/        # bridge.py (openclaw.json → CoPaw config), sync.py (MinIO sync)
hermes/                    # Hermes Worker runtime package
  src/hermes_matrix/       # Shim + overlay_adapter.py (subclasses hermes-agent's native mautrix adapter)
  src/hermes_worker/       # worker.py (lifecycle), bridge.py (openclaw→hermes config), sync.py (MinIO), cli.py
worker/                    # OpenClaw Worker image (Node.js)
manager/                   # Manager image + agent content
  agent/                   # Built-in skills, SOUL.md, AGENTS.md
openclaw-base/             # Base Docker image
install/                   # Docker Compose local install scripts
helm/                      # Kubernetes Helm Chart
tests/                     # Integration tests (21 tests, Shell-based)
shared/lib/                # Shared shell library functions
docs/                      # Architecture and design docs
```

## Key Subsystems

| Subsystem | Location | Language | Purpose |
|-----------|----------|----------|---------|
| Controller | `hiclaw-controller/` | Go | K8s Operator: CRD reconciliation, provisioning |
| Matrix Client | `hiclaw-controller/internal/matrix/` | Go | REST client for Tuwunel homeserver |
| Provisioner | `hiclaw-controller/internal/service/` | Go | Orchestrates Matrix + Gateway + MinIO + K8s |
| CoPaw Runtime | `copaw/` | Python | Worker/Manager runtime with matrix-nio |
| Hermes Runtime | `hermes/` | Python | Worker runtime with mautrix overlay |
| OpenClaw Runtime | `worker/` | Node.js | Worker runtime (TypeScript) |
| Tuwunel | Container image | Rust | Matrix homeserver (conduwuit fork) |
| Tests | `tests/` | Shell | Integration tests with Matrix API helpers |

## Reading Strategy

When exploring a subsystem for the first time:

1. **Start with AGENTS.md** — every subsystem has one explaining its scope and structure
2. **Types/interfaces first** — CRD types (`api/v1beta1/types.go`), client interfaces (`matrix/client.go`)
3. **Reconciler logic** — understand what triggers actions and what the desired state looks like
4. **Provisioner flow** — understand the infrastructure setup sequence (Matrix → Gateway → MinIO → K8s)
5. **Credential delivery chain** — trace from `ProvisionWorker` → `WorkerEnvBuilder` → `DeployWorkerConfig` → `worker-entrypoint.sh` to understand how Matrix tokens reach the container
6. **Runtime channel** — how the Agent container connects to Matrix (different per runtime)
7. **Manager skills** — `manager/agent/skills/` contains the task dispatch protocol, channel policy, and state management

## Completeness Audit Technique

When asked to find unread files in a subsystem:

1. **System-wide grep**: `grep -rn "matrix\|Matrix\|MATRIX\|tuwunel\|Tuwunel" <path> --include="*.go" --include="*.py" --include="*.sh" -l` to enumerate ALL files referencing the subsystem
2. **Cross-reference against reading log** — maintain a checklist of read/unread per module
3. **Prioritize gaps by layer**: P0 (core logic), P1 (completeness), P2 (deployment/tests)
4. **Key areas commonly missed**: reconciler sub-files (`*_reconcile_*.go`), bridge configs, test helpers (`tests/lib/`), CRD scope structs

## Three Runtimes, One Protocol

All three runtimes connect to the same Matrix homeserver but use different SDKs:

| Runtime | Matrix SDK | Key File |
|---------|-----------|----------|
| CoPaw | matrix-nio (Python) | `copaw/src/matrix/channel.py` |
| Hermes | mautrix (Python, via hermes-agent) | `hermes/src/hermes_matrix/overlay_adapter.py` |
| OpenClaw | matrix-js-sdk (Node.js) | External repo |

HiClaw-specific policy overlay is consistent across runtimes: dual allow-lists, history buffering, outbound m.mentions enrichment.

### Hermes Runtime: Shim + Subclass Architecture

Hermes does NOT reimplement Matrix transport. It uses a **build-time shim** to hijack hermes-agent's native mautrix adapter and overlay HiClaw policy.

**Build-time injection** (`hermes/Dockerfile:132-140`):
```
1. mv gateway/platforms/matrix.py → _matrix_native.py   # rename original
2. cp hermes_matrix/_shim.py → gateway/platforms/matrix.py  # install shim
```
Shim (`_shim.py`, 23 lines) re-exports all native symbols + replaces `MatrixAdapter` with HiClaw's subclass. When hermes-agent does `import gateway.platforms.matrix`, it loads the shim transparently.

**Overlay adapter** (`overlay_adapter.py`, 239 lines) subclasses `_NativeMatrixAdapter` and overrides exactly 4 methods:

| Method | Lines | What it does |
|--------|-------|-------------|
| `__init__` | 97-101 | Init `DualAllowList`, `HistoryBuffer`, `_vision_enabled` from env |
| `connect` | 103-107 | After native connect, call `_wrap_send_message_event()` to monkey-patch outbound mentions |
| `_resolve_message_context` | 134-177 | Allow-list gate → super call → history buffer inject/passthrough |
| `_handle_media_message` | 179-239 | Image→text downgrade for non-vision models; strip transport filenames from image body |

**Outbound mention injection** (`_wrap_send_message_event`):
- Monkey-patches `self._client.send_message_event` at runtime
- Every outgoing event auto-calls `apply_outbound_mentions(content, self_user_id)`
- Extracts `@user:domain` MXIDs from body text via regex, merges into `m.mentions.user_ids` (MSC3952)

**Message flow through `_resolve_message_context`**:
```
inbound → DualAllowList.permits(sender, is_dm)?
  ├── No → HistoryBuffer.record (group) / drop → None
  └── Yes → super()._resolve_message_context
       ├── None (native mention gate rejected) → HistoryBuffer.record
       └── ctx returned →
            DM: pass through unchanged
            Command (starts with / or !): clear HistoryBuffer, pass through
            Group normal: prefix = history.drain(); body = prefix + "sender: body"
```

**Runtime env knobs** (`hermes-worker-entrypoint.sh`):
- `HERMES_YOLO_MODE=1` — bypass dangerous-command approval gate (container IS the security boundary)
- `MATRIX_HOME_CHANNEL=disabled` — suppress per-session "no home channel" reminder (workers have no home channel)

## Deployment Modes

- **Local**: Docker Compose (`install/`) — single machine, all-in-one
- **Kubernetes**: Helm Chart (`helm/`) — production, HA-capable

## Reference Files

- `references/matrix-subsystem.md` — Matrix subsystem complete reference: design motivation (why Matrix), end-to-end message flow diagrams, credential delivery chain (Controller→MinIO→Container), Manager welcome 3-gate protocol, three-runtime comparison, Channel Policy security model, Element Web integration, orphan recovery, Tuwunel config with design intent, provisioning flows, and design trade-offs
- `references/crd-runtime-lifecycle.md` — CRD reconciliation internals (Human/Team/Manager phases, ChannelPolicy merging rules, spec hashing), Hermes Worker bridge lifecycle (openclaw.json→config.yaml mapping, MinIO sync, Matrix relogin), CoPaw standard↔runtime space bridge, service interface layer
- `references/hermes-matrix-internals.md` — Hermes Matrix implementation deep dive: build-time shim injection mechanism (Dockerfile rename + _shim.py), overlay adapter 4 method overrides with line-level flow, policies.py component details, bridge.py complete openclaw.json→.env/config.yaml field mapping tables, worker.py 11-step startup sequence, runtime env knobs, Dockerfile layer caching strategy, test coverage
- `references/hermes-agent-native-matrix.md` — Upstream hermes-agent Matrix adapter internals (2872-line `gateway/platforms/matrix.py`): 7-phase connect() including full E2EE setup chain, sync loop, 8-layer inbound message filter chain, outbound mention system (3-layer detection + code-region protection), reactions lifecycle (processing + approval), text batch aggregation (split detection), media upload with encryption, helper functions, config/env var mapping
- `references/copaw-worker-runtime.md` — CoPaw Worker runtime deep dive: bridge.py config translation (openclaw→CoPaw format mapping, monkey-patching paths), sync.py bidirectional MinIO sync (local-first merge, credential paths), task.py DAG/Loop state machine (status symbols, FileSystemTaskStore), worker.py 6-stage startup, hooks/tools native agent tools, Manager 24-step startup script, OpenClaw Worker entrypoint with PULL_MARKER mechanism
