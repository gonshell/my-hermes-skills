# MiniMax Provider Debugging

## Known Trap: `minimax` vs `minimax-cn` Provider Names

Hermes supports two MiniMax providers with different base URLs:

| Provider name | Base URL | Notes |
|--------------|----------|-------|
| `minimax-cn` | `https://api.minimaxi.com/v1` | Working config |
| `minimax` | `https://api.minimax.io/anthropic` | **Wrong** — `/anthropic` suffix is incorrect |

**Symptom:** 401 `authentication_error` with `invalid api key`, even though the API key is correct.

**Root cause:** Requests go to `https://api.minimax.io/anthropic/chat/completions` which doesn't exist.

## How to Identify

Check the logs:

```
provider=minimax base_url=https://api.minimax.io/anthropic model=MiniMax-M2.7 summary=HTTP 401: invalid api key
```

vs working:

```
provider=minimax-cn ... at https://api.minimaxi.com/v1/
```

## Session-Level vs Provider-Level Problem

- **Old session using wrong provider:** The session cached the wrong provider name. Fixing config won't recover that session — credential pool marks the key as exhausted after 401s. Delete the session or wait for key to rotate.
- **New sessions:** Will use updated config if the provider definition is corrected.

## Resolution Steps

1. **Check current session provider:** Look at log line `provider=XXX` — is it `minimax` or `minimax-cn`?
2. **Fix provider config:** `hermes config set providers.minimax.base_url "https://api.minimax.io/v1"`
3. **Reset exhausted credentials:** `hermes auth reset minimax` (if key was marked exhausted)
4. **Delete affected session:** `hermes sessions delete <session-id>` and start fresh, OR just start a new session

## Credential Pool Exhaustion

After multiple 401s, the credential pool marks the API key as exhausted:
```
credential pool: marking MINIMAX_API_KEY exhausted (status=401), rotating
credential pool: no available entries (all exhausted or empty)
```

This is per-session-state. A new session with a fresh credential pool will work if the base_url is fixed.

## Live Log Investigation

```bash
tail -100 ~/.hermes/logs/*.log | grep -E "minimax|401|auth"
```

Look for the `provider=` and `base_url=` fields to identify which provider config is being used.
