# CoPaw Worker Runtime

> Source files in `copaw/src/copaw_worker/`. Generated from complete source reading session (2025-05).

## Architecture

CoPaw Worker is the Python-based runtime for HiClaw Worker containers. It bridges the OpenClaw configuration format to CoPaw (AgentScope ecosystem) native format, manages bidirectional MinIO file sync, and provides a local task state machine.

**Entry chain**: `copaw-worker-entrypoint.sh` → `copaw-worker` CLI (`cli.py`) → `Worker` class (`worker.py`) → CoPaw FastAPI app (`copaw.app._app:app` via uvicorn)

## Core Modules

### bridge.py (906 lines) — Configuration Translation

Converts OpenClaw standard config (`openclaw.json`) → CoPaw native config (`config.json` + `providers.json` + `agent.json`).

| Input | Output |
|-------|--------|
| `openclaw.json` | `config.json` + `providers.json` + `agent.json` |
| `SOUL.md` / `AGENTS.md` / `HEARTBEAT.md` | Copied to CoPaw working dir |
| `skills/` directory | Symlinked to CoPaw workspace |
| mcporter config | Synced to CoPaw |

Key functions:
- `bridge_standard_to_runtime()` — Main entry: sync prompts → convert config → credential guard → sync mcporter → sync skills
- `bridge_openclaw_to_copaw()` — Core conversion: writes 3 config files
- `_patch_copaw_paths()` — Monkey-patches CoPaw module-level path constants (WORKING_DIR, SECRET_DIR) + sets `COPAW_WORKING_DIR` env var
- `_port_remap()` — Container port 8080 → host port mapping
- `sync_skills_to_runtime()` — Symlink MinIO-synced skills into CoPaw workspace
- `dedup_customized_skills()` — Dedup customized vs builtin skills
- `enable_workspace_skills_by_default()` — Write skill.json manifest for HiClaw skill activation

⚠️ **Not a pure function** — mutates `os.environ`, monkey-patches module constants, copies `providers.json` to `.copaw.secret/`.

### sync.py (923 lines) — MinIO File Sync

`FileSync` class: bidirectional sync between Worker and MinIO.

**Sync modes**:
- `mirror_all()` — Startup full pull (excludes `credentials/`) + `shared/` sync + Team Leader's `global-shared/`
- `sync_loop()` — Periodic pull of controller-managed files (openclaw.json, config/, skills/)
- `push_loop()` — Periodic push of local changes back to MinIO

**Config merge strategy** (`_merge_openclaw_config`): Local-first merge — local config as base, remote overlays models/gateway/channels/plugins. Local `accessToken` takes priority (Worker re-login token).

**Credential paths** (`_ensure_alias`):
- K8s: skip (mc-wrapper handles)
- Cloud: STS temporary credential refresh
- Local: static MinIO alias

### task.py (1061 lines) — Task State Machine

Local task flow state machine supporting two execution models:

**DAG mode** (Directed Acyclic Graph):
- Data: `DagTask` (node with dependencies)
- Operations: `create_project()` → `add_tasks()` → `plan_dag()` → `ready_nodes()`
- Validation: `validate_dag()` detects circular deps + self-references

**Loop mode** (Iterative):
- Data: `LoopPlan` (iterations + conditions)
- Operations: `plan_loop()` → `ready_loop_nodes()` → `record_loop_iteration()`

**Task status** (Markdown checkbox symbols):
- ` ` (space) = pending
- `~` = delegated
- `x` = completed
- `!` = blocked
- `→` = revision

Storage: `FileSystemTaskStore` — `shared/projects/` + `shared/tasks/`

### worker.py (974 lines) — Startup Orchestration

`Worker` class with async lifecycle: `start()` / `run()` / `stop()` / `_run_copaw()`.

**Startup sequence** (6 stages):
1. Ensure mc (MinIO Client) available
2. Init FileSync + `mirror_all()` from MinIO
3. Parse openclaw.json + Matrix re-login (E2EE compatible)
4. Create CoPaw working directory
5. `bridge_standard_to_runtime()` config bridging (infers HICLAW_PORT_GATEWAY)
6. Start pull/push sync loops + WorkerAPIServer

`_run_copaw()`: Launches CoPaw FastAPI app via uvicorn.
`_on_files_pulled()`: Triggers re-bridge or skill sync on controller-managed file changes.
`build_worker_readiness()`: Health check (copaw service + model service + matrix service).

Worker is **stateless** — all persistent state in MinIO. WorkerAPIServer on `console_port+1` provides readiness/liveness probes.

### hooks/tools/ — Native Agent Tools

CoPaw provides HiClaw-compatible tools for the Agent:

| Tool | Lines | Purpose |
|------|-------|---------|
| `taskflow.py` | 277 | Wraps task.py state machine ops as AgentScope ToolResponse |
| `message.py` | 463 | OpenClaw-compatible Matrix message tool (parse Matrix targets, validate policy, send) |
| `filesync.py` | 206 | Wraps FileSync push/pull as AgentScope ToolResponse |

All tools return `ToolResponse(content=[TextBlock(text=json.dumps(payload))])` format.

## Manager Startup (start-manager-agent.sh)

File: `manager/scripts/init/start-manager-agent.sh` (1281 lines, ~68KB)

The most complex shell script in the project. Handles 3 deployment modes (local/aliyun/k8s) with a 24-step initialization:

1. Runtime selection (HICLAW_MANAGER_RUNTIME → openclaw/copaw)
2. Timezone setup
3. YOLO mode promotion (marker file → env var)
4. Cloud/K8s: validate env vars + sync workspace from MinIO/OSS
5. Local: host symlinks + /etc/hosts + wait for local services (Higress 8080, Tuwunel 6167, MinIO 9000)
6. Secret auto-generation + persistence (`/data/hiclaw-secrets.env`, survives restarts)
7. Cloud/K8s workspace sync (mc mirror)
8. Workspace init/upgrade (compare image version → upgrade-builtins.sh)
9. Wait for MinIO init
10. Matrix user registration (admin + manager accounts; K8s skips, controller handles)
11. Get Manager Matrix token
12. Higress Console init (login + K8s lightweight config or Docker full setup)
13. Create Admin DM room (search/create + persist to state.json + welcome message on first boot)
14. Generate/update openclaw.json (template or jq merge; model params, E2EE, tools.exec)
15. CMS observability plugin (optional)
16. Container runtime detection
17. Upgrade existing Workers' openclaw.json
18. Worker Matrix password file fix (E2EE re-login)
19. Worker container rebuild (Manager restart recovers stopped Workers)
20. Notify Workers of builtin updates (with cooldown to prevent loops)
21. Render agent doc templates (render-skills.sh replaces `${VAR}`)
22. Cloud/K8s bidirectional file sync
23. mcporter auto-config (GitHub MCP)
24. Final launch: copaw → exec start-copaw-manager.sh; openclaw → exec openclaw gateway run

Model parameters are hardcoded via case statements mapping model names to context window / max tokens / reasoning / vision flags.

## OpenClaw Worker Startup (worker-entrypoint.sh)

File: `worker/scripts/worker-entrypoint.sh` (358 lines)

5-step startup:
1. Timezone setup
2. MinIO config (cloud RRSA / local MinIO)
3. Config pull — mc mirror from MinIO (retry until openclaw.json/SOUL.md/AGENTS.md exist) + create symlinks
4. Bidirectional file sync:
   - Local→Remote: 5s interval `find -newer` → mc mirror (exclude controller-managed files) + per-file push for SOUL.md/AGENTS.md/HEARTBEAT.md
   - Remote→Local: 5min safety-net pull (merge_openclaw_config local-first + skills + shared)
5. Matrix re-login (E2EE compatible) + cleanup session locks + cleanup crypto storage + background readiness reporter

Final: `exec openclaw gateway run --verbose --force`

**PULL_MARKER mechanism**: Prevents pushing just-pulled files (sets marker after pull, skips push for marked files).

## Key Design Patterns

1. **Bridge pattern**: Each runtime (copaw/hermes) has its own bridge that translates OpenClaw config to native format. The bridge is the integration seam.
2. **Monkey-patching for path alignment**: CoPaw bridge patches module-level constants to redirect the upstream library to HiClaw's directory layout.
3. **Local-first config merge**: Workers own their local config (especially accessToken from Matrix re-login). MinIO overlays only model/gateway/channel fields.
4. **Stateless workers**: All persistent state in MinIO. Containers can be destroyed and rebuilt at any time.
5. **Task state in shared filesystem**: Projects and tasks stored as files in `shared/`, enabling cross-Worker visibility via MinIO sync.
