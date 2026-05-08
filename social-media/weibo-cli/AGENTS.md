# AGENTS.md — weibo-cli

## Project
`/Users/xiesg/.hermes/skills/social-media/weibo-cli` — A CLI for Weibo (微博)

## Setup
```bash
cd /Users/xiesg/.hermes/skills/social-media/weibo-cli
source .venv/bin/activate
uv pip install -e .
```

## Run
```bash
weibo hot -n 10
weibo search Python
weibo user 1195230310
```

## Test
```bash
cd /Users/xiesg/.hermes/skills/social-media/weibo-cli
source .venv/bin/activate
python -m pytest tests/ -v
```

## Key Constraints
- m.weibo.cn API requires authentication for most endpoints (SUB cookie)
- Hot search also requires auth (returns ok=-100 without)
- Use `weibo auth login` for authentication (extracts browser cookies); `weibo auth qr-login` is deprecated and disabled
- All dates parsed as "%a %b %d %H:%M:%S %z %Y" (Weibo format)
- All model classes have `to_dict()` for serialization

## Auth Issues
- **macOS + Chrome**: browser-cookie3 cannot read Chrome cookies — Chrome stores them encrypted in macOS Keychain. Workaround: use Firefox, or manually extract SUB cookie from Chrome DevTools Network tab
