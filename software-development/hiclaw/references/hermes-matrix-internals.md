# Hermes Matrix Implementation Internals

Deep code-level reference for how HiClaw's Hermes Worker runtime interacts
with Matrix protocol. Supplements the class-level description in SKILL.md
and the lifecycle details in `references/crd-runtime-lifecycle.md`.

## 1. Package Structure

```
hermes/src/hermes_matrix/
  __init__.py           (17 lines)  — module docstring explaining shim strategy
  _shim.py              (23 lines)  — installed as gateway/platforms/matrix.py at build time
  adapter.py             (4 lines)  — re-exports MatrixAdapter from overlay_adapter
  overlay_adapter.py    (239 lines) — MatrixAdapter subclass (4 method overrides)
  policies.py           (222 lines) — DualAllowList, HistoryBuffer, apply_outbound_mentions

hermes/src/hermes_worker/
  __init__.py            (3 lines)
  bridge.py             (537 lines) — openclaw.json → hermes config.yaml + .env translation
  worker.py             (462 lines) — Worker lifecycle (7-step startup → gateway handoff)
  sync.py               (621 lines) — MinIO FileSync, push_loop, sync_loop
  config.py              (39 lines) — WorkerConfig dataclass
  cli.py                 (71 lines) — typer CLI entry point (hermes-worker command)
```

## 2. Build-Time Shim Injection (Dockerfile:132-140)

```dockerfile
# Step 1: Rename hermes-agent's native module
RUN SITE=/opt/venv/hermes/lib/python3.11/site-packages \
    && mv "$SITE/gateway/platforms/matrix.py" \
          "$SITE/gateway/platforms/_matrix_native.py"

# Step 2: Install HiClaw's shim at the original import path
    && cp "$SITE/hermes_matrix/_shim.py" \
          "$SITE/gateway/platforms/matrix.py"
```

### `_shim.py` Mechanism (23 lines)

```python
from gateway.platforms import _matrix_native as _native
from gateway.platforms._matrix_native import *  # re-export all native symbols

from hermes_matrix.adapter import MatrixAdapter  # HiClaw's subclass

check_matrix_requirements = _native.check_matrix_requirements

def __getattr__(name):
    return getattr(_native, name)

def __dir__():
    return sorted(set(globals()) | set(dir(_native)))
```

Result: `import gateway.platforms.matrix` loads the shim, which transparently
provides all native symbols but swaps `MatrixAdapter` with HiClaw's overlay.

**Upgrade path**: Change `HERMES_GIT_REF` build arg in Dockerfile. No fork needed.

## 3. Overlay Adapter: 4 Method Overrides

### 3.1 `__init__` (L97-101)

```python
def __init__(self, config):
    super().__init__(config)
    self._dual_allow = DualAllowList.from_env()
    self._history = HistoryBuffer.from_env()
    self._vision_enabled = _truthy_env("MATRIX_VISION_ENABLED", default=False)
```

Reads all policy from env vars (set by bridge.py from openclaw.json).

### 3.2 `connect` (L103-107)

```python
async def connect(self) -> bool:
    ok = await super().connect()
    if ok and self._client is not None:
        self._wrap_send_message_event()  # inject outbound m.mentions
    return ok
```

After native mautrix connection succeeds, monkey-patches `send_message_event`
to auto-inject MSC3952 `m.mentions.user_ids` on every outgoing event.

### 3.3 `_resolve_message_context` (L134-177)

This is the core policy gate. Called for every inbound message.

```python
async def _resolve_message_context(self, room_id, sender, event_id,
                                     body, source_content, relates_to):
    # Gate 1: Allow-list check
    is_dm = await self._is_dm_room(room_id)
    if not self._dual_allow.permits(sender, is_dm=is_dm):
        return None  # silently drop

    # Gate 2: Native mention gating (from upstream hermes-agent)
    ctx = await super()._resolve_message_context(...)
    if ctx is None:
        # Not mentioned → buffer for group rooms, drop for DM
        if not is_dm:
            display = await self._get_display_name(room_id, sender)
            history_body = _describe_dropped_media(source_content, body)
            self._history.record(room_id, display, history_body)
        return None

    body, is_dm, chat_type, thread_id, display_name, source = ctx

    # DM → pass through unchanged
    if is_dm:
        return ctx

    # Command (/ or ! prefix) → clear history, pass through
    if _is_commandish(body):
        self._history.clear(room_id)
        return ctx

    # Group normal → inject history prefix + prepend sender
    body = f"{display_name}: {body}"
    history_prefix = self._history.drain(room_id)
    if history_prefix:
        body = history_prefix + body
    return body, is_dm, chat_type, thread_id, display_name, source
```

### 3.4 `_handle_media_message` (L179-239)

Two behaviors:

1. **Image downgrade** (when `MATRIX_VISION_ENABLED=false`):
   - Converts `m.image` → `m.text` with placeholder body:
     `[User sent an image (current model does not support image input): <filename>]`
   - Prevents hermes-agent from trying vision_analyze on unsupported models

2. **Transport filename stripping** (`_normalize_image_body`):
   - Matrix image events set `body` to the upload filename even without caption
   - Feeding "foo.png" to hermes causes it to do `search_files("foo.png")` instead of vision
   - Strips single-word filenames with image extensions; preserves multi-line captions

## 4. policies.py: Three Policy Components

### 4.1 `extract_mentions_from_text(text, self_user_id=None) → List[str]`

Regex: `@[a-zA-Z0-9._=+/\-]:[a-zA-Z0-9.\-]+(?::\d+)?`

Extracts MXIDs from body text, deduplicates (case-insensitive), excludes self.
Used by `apply_outbound_mentions` and tested in `test_policies.py`.

### 4.2 `DualAllowList`

```python
@dataclass(frozen=True)
class DualAllowList:
    dm_policy: str        # "open" | "allowlist" | "disabled"
    group_policy: str     # "open" | "allowlist" | "disabled"
    dm_allow: frozenset   # from MATRIX_ALLOWED_USERS
    group_allow: frozenset  # from MATRIX_GROUP_ALLOW_FROM

    @property
    def group_combined_allow(self) -> frozenset:
        return self.dm_allow | self.group_allow

    def permits(self, sender: str, is_dm: bool) -> bool:
        # DM: check dm_allow; Group: check dm_allow | group_allow
```

Env var mapping:
- `MATRIX_DM_POLICY` → dm_policy
- `MATRIX_ALLOWED_USERS` → dm_allow (CSV)
- `MATRIX_GROUP_POLICY` → group_policy
- `MATRIX_GROUP_ALLOW_FROM` → group_allow (CSV)

### 4.3 `HistoryBuffer`

```python
@dataclass
class HistoryBuffer:
    limit: int = 50  # from MATRIX_HISTORY_LIMIT
    _entries: Dict[str, List[_HistoryEntry]]  # per-room

    def record(self, room_id, sender, body) → None
    def drain(self, room_id) → str  # pops and formats
    def clear(self, room_id) → None
```

Drain format (matches CoPaw convention):
```
[Chat messages since your last reply - for context]
alice: msg1
bob: msg2

[Current message - respond to this]
```

## 5. bridge.py: Complete Field Mapping

### 5.1 openclaw.json → .env

| Env Var | openclaw.json Path | Notes |
|---------|-------------------|-------|
| `MATRIX_HOMESERVER` | `channels.matrix.homeserver` | Port-remapped if !container |
| `MATRIX_ACCESS_TOKEN` | `channels.matrix.accessToken` | Refreshed by _matrix_relogin |
| `MATRIX_USER_ID` | `channels.matrix.userId` | |
| `MATRIX_DEVICE_ID` | `channels.matrix.deviceId` | Refreshed by _matrix_relogin |
| `MATRIX_ENCRYPTION` | `channels.matrix.encryption` | "true"/"false" |
| `MATRIX_DM_POLICY` | `channels.matrix.dm.policy` | |
| `MATRIX_ALLOWED_USERS` | `channels.matrix.dm.allowFrom` | CSV |
| `MATRIX_GROUP_POLICY` | `channels.matrix.groupPolicy` | |
| `MATRIX_GROUP_ALLOW_FROM` | `channels.matrix.groupAllowFrom` | CSV |
| `MATRIX_REQUIRE_MENTION` | `channels.matrix.requireMention` | "true"/"false" |
| `MATRIX_FREE_RESPONSE_ROOMS` | `channels.matrix.freeResponseRooms` | CSV |
| `MATRIX_AUTO_THREAD` | `channels.matrix.autoThread` | |
| `MATRIX_DM_MENTION_THREADS` | `channels.matrix.dmMentionThreads` | |
| `MATRIX_HOME_ROOM` | `channels.matrix.homeRoomId` | |
| `MATRIX_VISION_ENABLED` | Derived from model `input` modalities | "true" if "image" in input |
| `MATRIX_FILTER_TOOL_MESSAGES` | Always "true" | |
| `MATRIX_FILTER_THINKING` | Always "true" | |
| `MATRIX_HISTORY_LIMIT` | `channels.matrix.historyLimit` OR `messages.groupChat.historyLimit` | |
| `OPENAI_BASE_URL` | Active provider `baseUrl` | Port-remapped |
| `OPENAI_API_KEY` | Active provider `apiKey` | |
| `HERMES_DEFAULT_MODEL` | Active model `id` | |

**Bridge ownership model**: Only `MATRIX_*` prefix + `OPENAI_*` exact keys are
owned. User-added keys (TAVILY_API_KEY, etc.) survive re-bridge.

### 5.2 openclaw.json → config.yaml

| YAML Block | Source |
|-----------|--------|
| `model.default` | Active model `id` |
| `model.provider` | Always `"custom"` (use OPENAI_BASE_URL) |
| `model.base_url` | Provider `baseUrl` |
| `model.context_length` | Model `contextWindow` |
| `matrix.require_mention` | `channels.matrix.requireMention` |
| `matrix.auto_thread` | `channels.matrix.autoThread` |
| `matrix.dm_mention_threads` | `channels.matrix.dmMentionThreads` |
| `matrix.free_response_rooms` | `channels.matrix.freeResponseRooms` |
| `auxiliary.vision.*` | Same endpoint as main model (only if vision enabled) |
| `platforms.matrix.enabled` | Always `true` |
| `platforms.matrix.reply_to_mode` | Always `"first"` |
| `logging.level` | `"DEBUG"` when `HICLAW_MATRIX_DEBUG=1` |

### 5.3 Worker Defaults (always set)

```yaml
memory:
  memory_enabled: true
group_sessions_per_user: true
terminal:
  backend: local
  cwd: <hermes_home>
```

## 6. Worker Startup Sequence (worker.py)

```
Worker.run()
  └─ start()
       1. _ensure_mc()           — auto-download MinIO Client to ~/.local/bin
       2. FileSync(...)           — create sync object
       3. sync.mirror_all()       — full MinIO pull (openclaw.json, SOUL.md, skills, etc.)
       4. sync.get_config()       — read openclaw.json
       5. _matrix_relogin()       — POST /_matrix/client/v3/login → fresh token + device_id
       6. bridge_openclaw_to_hermes() — write .env + config.yaml + SOUL.md + AGENTS.md
       7. _load_env_file()        — source .env into os.environ for this process
       8. _sync_skills()          — copy MinIO skills/ → ${HERMES_HOME}/skills/
       9. _copy_mcporter_config()
      10. sync_loop (background)  — periodic MinIO pull, triggers re-bridge on openclaw.json change
      11. push_loop (background)  — 5s interval MinIO push
  └─ _run_hermes_gateway()
       from gateway.run import start_gateway
       start_gateway(gw_config, replace=False, verbosity=0)
         → loads config.yaml → creates MatrixAdapter (shim ensures it's HiClaw's version)
         → mautrix SDK connects → agent loop runs until cancelled
```

### _matrix_relogin Detail

```
1. Read password: MinIO agents/{name}/credentials/matrix/password
2. POST /_matrix/client/v3/login {type: "m.login.password", identifier: {type: "m.id.user", user: name}}
3. Extract access_token + device_id from response
4. Update openclaw.json channels.matrix.{accessToken, deviceId}
5. Persist to disk
```

Purpose: each restart gets new device_id → new Olm identity → E2EE key rotation
invisible to other Matrix clients (Element Web).

Fails gracefully: if no password or login fails, uses existing token.

## 7. Runtime Env Knobs (entrypoint)

```bash
HERMES_YOLO_MODE=1           # bypass dangerous-command approval gate
                              # (container IS the security boundary)
MATRIX_HOME_CHANNEL=disabled  # suppress "no home channel" reminder
                              # (workers don't have home channels)

HICLAW_MATRIX_DEBUG=1         # bridge.py sets logging.level=DEBUG in config.yaml
                              # (hermes-agent has no native Matrix debug env var)
```

## 8. Dockerfile Key Details

```dockerfile
# Base: python:3.11-slim
# Installs: libolm-dev (E2EE), jemalloc (memory), ffmpeg, ripgrep, jq
# Node.js 22: for mcporter, skills CLI compatibility
# hermes-agent: git clone --depth 1 --branch v2026.4.16
# Matrix deps: mautrix[encryption], matrix-nio[e2e]>=0.24.0
# HiClaw packages: installed from local src/ via pip install /tmp/hermes-worker/

# Layer caching strategy:
# 1. Heavy install layer (hermes-agent + deps) — cached unless git ref or pyproject.toml change
# 2. Overlay source layer (src/ copy) — rebuilt on every src/ change but doesn't invalidate #1
# 3. Shim injection layer — just renames + copies 1 file
```

## 9. Tests

- `tests/test_bridge.py` (109 lines): tests bridge config translation
  - vision model → auxiliary.vision block written
  - text-only model → no auxiliary.vision
  - HICLAW_MATRIX_DEBUG=1 → logging.level=DEBUG in config.yaml
  - Preserves user-set fields (timeout, download_timeout) across re-bridge

- `tests/test_policies.py` (99 lines): tests pure policy logic
  - extract_mentions: dedup + skip self
  - apply_outbound_mentions: merge existing + edit body (m.new_content)
  - DualAllowList: DM vs group modes, open/disabled
  - HistoryBuffer: drain format, limit enforcement
