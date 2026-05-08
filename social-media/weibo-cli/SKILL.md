---
name: weibo-cli
description: Weibo CLI tool for terminal — hot search, timeline, search, user profiles. Project at /Users/xiesg/.hermes/skills/social-media/weibo-cli
category: social-media
---

# weibo-cli SKILL

## Project Location
`/Users/xiesg/.hermes/skills/social-media/weibo-cli`

## Install / Update
```bash
cd /Users/xiesg/.hermes/skills/social-media/weibo-cli
uv pip install -e .     # install or update

# Link weibo command to PATH (required after every install)
ln -sf ~/.hermes/skills/social-media/weibo-cli/.venv/bin/weibo ~/.local/bin/weibo

# Verify
weibo --version
```

## Run
```bash
# Hot search (needs auth — see below)
weibo hot -n 10
weibo hot -f json       # JSON output

# Search
weibo search Python
weibo search AI -f yaml

# User timeline / profile
weibo timeline -u 1195230310
weibo user 1195230310
## Auth
```bash
weibo auth status          # check login status
weibo auth login           # auto-detect browser with weibo cookies, extract SUB cookie
weibo auth qr-login        # scan QR code (DEPRECATED — Weibo disabled this API)
weibo auth logout
```
**Auth status**: `weibo auth status` — check if SUB cookie is configured.

**How auth works**: `weibo auth login` uses browser-cookie3 to auto-detect Chrome/Safari/Firefox/etc., extracts weibo.com cookies.
**⚠️ macOS limitation**: browser-cookie3 cannot read Chrome cookies on macOS — Chrome stores cookies encrypted in the macOS Keychain. If Chrome is your only browser, use manual SUB cookie input instead.
**Prerequisite**: Must be logged into weibo.com in a supported browser (Firefox is known to work on macOS).

**Manual SUB cookie setup**: If browser extraction fails, you can manually provide the SUB cookie value. Chrome: open devtools → Network → any weibo.com request → Request Headers → copy Cookie value starting with SUB=.

### macOS Chrome Cookie Limitation (IMPORTANT)
`browser-cookie3` on macOS **cannot** read Chrome cookies. Chrome stores cookies encrypted in the macOS Keychain, and the library lacks the decryption key. Error message: `"Unable to get key for cookie decryption"`.

**Workarounds (in order of effort):**
1. **Manual SUB cookie** (fastest): Chrome → weibo.com → F12 Network → any request → Request Headers → Copy Cookie value → give to assistant to configure
2. **Use Firefox** instead: browser-cookie3 can read Firefox cookies on macOS (Firefox stores them unencrypted in SQLite)
3. **Use Safari**: cookies may be readable depending on system configuration

## Test
```bash
cd /Users/xiesg/.hermes/skills/social-media/weibo-cli
source .venv/bin/activate
python -m pytest tests/ -v
```

## Architecture
```
weibo_cli/
  __init__.py       — __version__
  __main__.py      — entry: python -m weibo_cli
  cli.py           — Click commands (hot, search, user, timeline, comments, etc.)
  client.py        — WeiboClient: HTTP client wrapping all API calls
  auth.py          — Cookie extraction (browser-cookie3) + QR login flow
  config.py        — Credentials & config file (~/.config/weibo-cli/credentials.json)
  cache.py         — File-based cache with TTL
  constants.py     — API endpoints, headers, timeouts
  exceptions.py    — WeiboError hierarchy
  models.py        — Dataclasses: Weibo, User, HotItem, Comment, Credentials
  parser.py        — Response parsers
  formatter.py     — Rich table/text formatters
  serialization.py — JSON/YAML/Compact output
  commands/        — (reserved)
```

## Key Design Decisions
- **Auth**: browser-cookie3 extracts cookies from Chrome/Safari/Firefox; QR login is deprecated and disabled by Weibo
- **API base**: m.weibo.cn (mobile API) — ALL endpoints require SUB cookie; alternative is open-im.api.weibo.com (app_id+app_secret, but limited coverage and needs special access)
- **Anti-bot behavior**: m.weibo.cn returns HTTP 432 for blocked requests (no token/cookie); old QR login returns `{"ok":0,"msg":"链接无效"}`
- **All model classes** have `to_dict()` for JSON/YAML serialization

## Common Issues
- **"No Weibo cookies found"**: browser-cookie3 failed. On macOS Chrome is encrypted via Keychain. Use Firefox (works), or manually extract SUB cookie from Chrome devtools.
- **"Unable to get key for cookie decryption"**: macOS Chrome limitation — browser-cookie3 cannot decrypt Keychain-encrypted cookies. Use Firefox or manual cookie.
- **"二维码登录已不支持"**: QR login API is deprecated by Weibo. Use `weibo auth login` instead.
- **m.weibo.cn returns 432**: Anti-bot/blocked — no access without valid SUB cookie.
- **"Not authenticated" on all commands**: re-run `weibo auth login` after logging into weibo.com in your browser.

## Adding New Commands
1. Add API method to `client.py`
2. Add parser in `parser.py`
3. Add Click command in `cli.py`
4. Add tests in `tests/test_client.py`
