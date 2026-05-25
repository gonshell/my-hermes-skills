# hermes-agent Native Matrix Adapter Internals

Source: `/Users/xiesg/dev/hermes-agent/gateway/platforms/matrix.py` (2872 lines)

This is the upstream adapter that HiClaw overlays via `_shim.py`. Understanding
it is essential for modifying `overlay_adapter.py` (which subclasses it) and for
debugging Matrix communication issues.

## 1. Class Hierarchy

```
BasePlatformAdapter (base.py:1389, 4126 lines)
  └── MatrixAdapter (matrix.py:317, 2872 lines)
```

Created in `GatewayRunner._create_adapter()` (run.py:6153-6158):
```python
from gateway.platforms.matrix import MatrixAdapter, check_matrix_requirements
if not check_matrix_requirements():
    return None
return MatrixAdapter(config)
```

## 2. `__init__` Configuration (L325-457)

Reads from `config.extra` dict with env var fallbacks:

| Field | Source | Default |
|-------|--------|---------|
| `_homeserver` | `config.extra.homeserver` / `MATRIX_HOMESERVER` | "" |
| `_access_token` | `config.token` / `MATRIX_ACCESS_TOKEN` | "" |
| `_user_id` | `config.extra.user_id` / `MATRIX_USER_ID` | "" |
| `_password` | `config.extra.password` / `MATRIX_PASSWORD` | "" |
| `_encryption` | `config.extra.encryption` / `MATRIX_ENCRYPTION` | false |
| `_device_id` | `config.extra.device_id` / `MATRIX_DEVICE_ID` | "" |
| `_require_mention` | `MATRIX_REQUIRE_MENTION` | true |
| `_thread_require_mention` | `config.extra.thread_require_mention` / `MATRIX_THREAD_REQUIRE_MENTION` | false |
| `_auto_thread` | `MATRIX_AUTO_THREAD` | true |
| `_dm_auto_thread` | `MATRIX_DM_AUTO_THREAD` | false |
| `_dm_mention_threads` | `MATRIX_DM_MENTION_THREADS` | false |
| `_free_rooms` | `config.extra.free_response_rooms` / `MATRIX_FREE_RESPONSE_ROOMS` | {} |
| `_allowed_rooms` | `config.extra.allowed_rooms` / `MATRIX_ALLOWED_ROOMS` | {} |
| `_reactions_enabled` | `MATRIX_REACTIONS` | true |
| `_allowed_user_ids` | `MATRIX_ALLOWED_USERS` | {} |

Key internal state:
- `_dm_rooms: Dict[str, bool]` — room_id → is-DM cache (from m.direct account data)
- `_joined_rooms: Set[str]` — all joined room IDs
- `_processed_events: deque(maxlen=1000)` — event deduplication
- `_threads: ThreadParticipationTracker` — tracks which threads the bot has replied in
- `_text_batch_delay_seconds` — 0.6s (normal) / 2.0s (split detection)
- `_proxy_url` — from `MATRIX_PROXY` env var

## 3. `connect()` — 7-Phase Startup (L607-930)

### Phase 1: Create mautrix Client (L620-637)
```python
HTTPAPI(base_url=homeserver, token=access_token, client_session=session)
Client(mxid=user_id, device_id=device_id, api=api,
       state_store=MemoryStateStore, sync_store=MemorySyncStore)
```
- Uses in-memory stores (no database dependency)
- Proxy support: HTTP/SOCKS via `_create_matrix_session()`

### Phase 2: Authentication (L641-692)
Two paths:
- **Token auth** (priority): `client.whoami()` validates + resolves user_id/device_id
- **Password auth**: `client.login(identifier, password, device_name="Hermes Agent")`

### Phase 3: E2EE Setup (L694-863) — Most complex, ~170 lines

```
1. Check python-olm installed
2. Create SQLite crypto store at <HERMES_HOME>/platforms/matrix/store/crypto.db
3. PgCryptoStore + OlmMachine
4. Set trust level UNVERIFIED (auto-accept any device)
5. crypto_store.put_device_id() BEFORE put_account() — fixes mautrix bug
   where device_id column never updates on UPSERT conflict
6. Verify device keys on server (_verify_device_keys_on_server)
7. Flush one-time keys (share_keys) — detects stale OTK conflicts
   "already exists" error = old identity signed OTKs → refuse to start
8. Cross-signing:
   a. MATRIX_RECOVERY_KEY set → verify_with_recovery_key()
   b. No recovery key → auto-bootstrap (generate_recovery_key)
      Generates MSK/SSK/USK, uploads to SSSS, publishes pub keys
      Required to avoid Element showing "not verified by its owner"
```

### Phase 4: Register Event Handlers (L865-874)
```python
client.add_dispatcher(MembershipEventDispatcher)
client.add_event_handler(EventType.ROOM_MESSAGE, self._on_room_message)
client.add_event_handler(EventType.REACTION, self._on_reaction)
client.add_event_handler(IntEvt.INVITE, self._on_invite)
```

### Phase 5: Initial Sync (L877-918)
```python
sync_data = await client.sync(timeout=10000, full_state=True)
# → populate _joined_rooms, store next_batch, refresh DM cache
# → dispatch initial sync events (for OlmMachine to-device processing)
# → join pending invites
```

### Phase 6: Post-sync key share (L920-925)

### Phase 7: Start background sync loop (L927-930)

## 4. Sync Loop (`_sync_loop`, L1405-1476)

```
while not _closing:
    sync_data = await wait_for(client.sync(since=next_batch, timeout=30000), timeout=45)
    
    Check M_UNKNOWN_TOKEN → permanent stop
    Update _joined_rooms
    Store next_batch
    client.handle_sync(sync_data) → dispatches to registered callbacks
    _join_pending_invites(sync_data)
    
    Errors: 401/403 → permanent stop; others → sleep(5) retry
```

The 45s outer timeout guards against TCP-level hangs that the 30s Matrix long-poll can't detect.

## 5. Inbound Message Processing

### 5.1 `_on_room_message` (L1538-1669) — 8-Layer Filter Chain

| Layer | Check | Effect |
|-------|-------|--------|
| 1 | `_is_self_sender(sender)` | Drop own messages (case-insensitive) |
| 2 | `_is_system_or_bridge_sender(sender)` | Drop `@_xxx:server` appservice identities |
| 3 | `_is_duplicate_event(event_id)` | Dedup via bounded deque (1000) |
| 4 | Startup grace (5s) | Drop old events from initial sync |
| 5 | Clock-skew detection | 3 consecutive consistent drops after 30s → warn NTP |
| 6 | `m.notice` filter | Drop bot responses (prevent loops) |
| 7 | `m.replace` filter | Skip edits (handled separately) |
| 8 | msgtype dispatch | `m.text` → `_handle_text_message`; `m.image/audio/video/file` → `_handle_media_message` |

`_is_self_sender` (L1482-1499): When `_user_id` is empty (whoami not resolved), returns True defensively — safer to drop own messages than echo-loop.

`_is_system_or_bridge_sender` (L1502-1536): Matches `@_something:server`, `@:server`, `:server` — prevents bridge puppet accounts from triggering agent loops.

Clock-skew heuristic (L1596-1625): After 30s post-startup, if 3+ consecutive events have consistent skew (within 60s of each other), warns about NTP. Variable-age backfill resets the counter.

### 5.2 `_resolve_message_context` (L1671-1769) — Shared Gating

Returns `(body, is_dm, chat_type, thread_id, display_name, source)` or None.

**Group message flow:**
```
1. allowed_rooms whitelist check (DMs exempt)
2. free_rooms check (skip mention gate)
3. Bot thread participation check (skip mention gate if in bot thread)
4. require_mention gate:
   - MSC3952 m.mentions.user_ids (authoritative)
   - Full MXID in body
   - localpart word-boundary match in body
   - matrix.to link in formatted_body
5. thread_require_mention gate (multi-agent loop prevention)
```

**DM flow:**
- Always passes (no mention gate)
- `dm_mention_threads`: auto-create thread on mention

**Auto-thread logic:**
- Group: `auto_thread=true` → every message starts a thread
- DM: `dm_auto_thread` independently controlled

**Mention stripping** (`_strip_mention`, L2634-2662):
- Only strips `@user:server` and `@localpart` (explicit mentions)
- Does NOT strip bare localpart words (e.g., "Hermes Agent" stays intact)

### 5.3 `_handle_text_message` (L1771-1835)

```
_resolve_message_context() → filter
Strip reply fallback (> quote blocks)
Detect commands (!/ prefix) → MessageType.COMMAND
Text messages → _enqueue_text_event() (batch aggregation)
Command messages → handle_message() (immediate)
```

### 5.4 `_handle_media_message` (L1837-2014)

```
1. Extract mxc:// URL → convert to HTTP URL
2. Encrypted media: extract from file.url
3. Download: client.download_media(ContentURI)
4. Decrypt if encrypted: decrypt_attachment(key, hash, iv)
5. Cache locally:
   - Image → cache_image_from_bytes (.jpg/.png/.gif/.webp)
   - Audio/Voice → cache_audio_from_bytes
   - Video/Doc → cache_document_from_bytes / cache_video_from_bytes
6. _resolve_message_context() → filter
7. Strip transport filename from body (_looks_like_matrix_image_filename)
8. Build MessageEvent(media_urls=[cached_path], media_types=[mimetype])
9. handle_message()
```

## 6. Outbound Messages

### 6.1 `send()` (L967-1042)

```
format_message() → strip ![image](url) markdown
truncate_message(MAX_MESSAGE_LENGTH=4000) → split into chunks
Per chunk:
  _build_text_message_content(chunk):
    1. _extract_outbound_mentions() → m.mentions.user_ids
    2. _inject_outbound_mention_links() → HTML matrix.to links
    3. _markdown_to_html() → org.matrix.custom.html format
  Add m.relates_to (reply_to / thread_id)
  client.send_message_event(room_id, ROOM_MESSAGE, content)
  E2EE error → share_keys() + retry once
```

### 6.2 `edit_message()` (L1085-1115)

Standard Matrix edit protocol (`m.replace`):
```json
{
  "body": "* edited text",
  "m.new_content": { "msgtype": "m.text", "body": "...", ... },
  "m.relates_to": { "rel_type": "m.replace", "event_id": "..." }
}
```
Propagates `m.mentions` and `formatted_body` to the edit wrapper.

### 6.3 Media Upload (`_upload_and_send`, L1291-1373)

```
E2EE encryption (if room is encrypted):
  encrypt_attachment(data) → (encrypted_data, file_metadata)

Upload to homeserver:
  client.upload_media(data, mime_type, filename, size)

Build message:
  Unencrypted: { url: "mxc://..." }
  Encrypted: { file: { url, key, iv, hashes } }
  + MSC3245 voice flag (org.matrix.msc3245.voice: {})
  + reply_to / thread_id

Send: client.send_message_event()
```

## 7. Outbound Mention System (L2530-2662)

### 7.1 `_protect_outbound_mention_regions` (L2574-2599)

Before extracting mentions, protects these regions with null-byte placeholders:
- Fenced code blocks (`` ```...``` ``)
- Inline code (`` `...` ``)
- Markdown links (`[text](url)`)

This prevents MXID patterns inside code/links from being treated as mentions.

### 7.2 `_extract_outbound_mentions` (L2545-2555)

Regex: `@[0-9A-Za-z._=/\-]:[0-9A-Za-z.\-]+(?::\d+)?`
Extracts from protected text → deduplicates → writes to `m.mentions.user_ids`.

### 7.3 `_inject_outbound_mention_links` (L2557-2572)

Wraps MXIDs in `[mxid](https://matrix.to/#/mxid)` markdown links for HTML rendering.

### 7.4 `_is_bot_mentioned` (L2601-2632) — Inbound 3-Layer Detection

1. `m.mentions.user_ids` contains bot's MXID (MSC3952, authoritative)
2. Bot's full MXID appears in body text
3. Bot's localpart matches word-boundary in body
4. `matrix.to/#/{bot_mxid}` appears in formatted_body

## 8. Reactions System (L2055-2240)

### Processing Lifecycle
```
on_processing_start(event):
  Send 👀 reaction → store in _pending_reactions[(room_id, msg_id)]

on_processing_complete(event, outcome):
  Redact 👀 (delayed 5s) →
  Send ✅ (success) or ❌ (failure)
  CANCELLED → no reaction change
```

### Approval Reactions (`send_exec_approval`, L1231-1279)
```
1. Send approval text with ✅/❎ emoji descriptions
2. Add ✅ and ❎ reactions to the approval message
3. Store bot reaction event_ids for cleanup
4. On user reaction:
   - ✅ → resolve as "once"
   - ❎ → resolve as "deny"
   - Check MATRIX_ALLOWED_USERS whitelist
   - Redact bot's seed reactions after resolution
```

### Reaction Redaction
All bot reactions are redacted with a 5s delay (`_reaction_redaction_delay_seconds`)
to ensure the homeserver has delivered the triggering event first.

## 9. Text Batch Aggregation (L2242-2307)

Handles Matrix client-side message splits (clients split at ~4000 chars).

```
_enqueue_text_event(event):
  Same session key → merge text (\n join) + merge media_urls
  Reset flush timer

_flush_text_batch(key):
  Wait delay: 0.6s (normal) or 2.0s (if last chunk ≥ 3900 chars = split detected)
  Pop and dispatch merged event
```

`_SPLIT_THRESHOLD = 3900` — if the last received chunk is this large, the client
almost certainly has more chunks coming, so wait longer.

## 10. Helper Functions

| Function | Lines | Purpose |
|----------|-------|---------|
| `send_typing/stop_typing` | 1066-1082 | 30s typing indicator |
| `send_read_receipt` | 2324-2348 | Tries 3 mautrix APIs: `set_fully_read_marker`, `send_receipt`, `set_read_markers` |
| `redact_message` | 2354-2373 | Matrix redact API |
| `create_room` | 2379-2410 | private/public/trusted_private presets |
| `invite_user` | 2412-2422 | |
| `set_presence` | 2430-2451 | online/offline/unavailable |
| `_is_dm_room` | 2483-2498 | m.direct cache → fallback: member count == 2 |
| `_refresh_dm_cache` | 2500-2524 | Read m.direct account data |
| `_mxc_to_http` | 2681-2686 | `mxc://server/id` → `{homeserver}/_matrix/client/v1/media/download/server/id` |
| `_markdown_to_html` | 2688-2872 | markdown lib (preferred) or comprehensive regex fallback |
| `_get_display_name` | 2664-2679 | State store member lookup → fallback: strip @:server |
| `get_chat_info` | 1044-1060 | Room name + DM/group type |
| `format_message` | 1281-1285 | Strip `![alt](url)` markdown (media uploaded separately) |

## 11. E2EE Internals

### `_CryptoStateStore` (L290-314)
Adapter for mautrix's OlmMachine StateStore interface:
- `is_encrypted(room_id)` — delegates to client state store
- `get_encryption_info(room_id)` — encryption event content
- `find_shared_rooms(user_id)` — returns all joined rooms (single-user bot)

### `_verify_device_keys_on_server` (L529-601)
After loading OlmMachine, re-uploads identity keys and verifies they match
what the server has. Prevents silent decryption failures from stale keys.

### Key Rotation Handling
- `put_device_id()` before `put_account()` — critical ordering fix
- `share_keys()` detects "already exists" → stale OTK conflict → fatal error
- Recovery key or auto-bootstrap cross-signing ensures device self-signing is valid

## 12. Constants

```python
MAX_MESSAGE_LENGTH = 4000           # practical Matrix message limit
_SPLIT_THRESHOLD = 3900             # detect client-side splits
_STARTUP_GRACE_SECONDS = 5          # ignore events older than startup - 5s
_STORE_DIR = <HERMES_HOME>/platforms/matrix/store/
_CRYPTO_DB_PATH = <STORE_DIR>/crypto.db
_OUTBOUND_MENTION_RE = re.compile(r"(?<![\w/])(@[0-9A-Za-z._=/-]+:[0-9A-Za-z.-]+(?::\d+)?)")
```
