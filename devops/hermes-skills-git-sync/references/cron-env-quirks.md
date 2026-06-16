# Cron/Sandbox Environment Quirks

## HOME override
The Hermes cron sandbox sets `$HOME=/Users/xiesg/.hermes/home` (not `/Users/xiesg`).
`~` resolves to the sandbox path. Always use absolute paths for repos, SSH keys, etc.

**Detection:** `echo $HOME | grep -q '.hermes/home' && echo "SANDBOX"`

## Git behavior (confirmed 2026-06-15)
| Operation | Works? | Notes |
|-----------|--------|-------|
| `ssh -T git@github.com` | ✅ | SSH auth works fine |
| `curl https://github.com` | ✅ | HTTP works fine |
| `curl https://api.github.com/...` | ✅ | GitHub REST API works |
| `git fetch / pull / clone` | ❌ hangs | Data-transfer protocol times out (60-180s+) |
| `git push` | ✅ | Push succeeds even when pull hangs |

**Root cause:** Likely the git pack-data transfer protocol stalls in the sandbox, but the smaller push-upload path works.

**Workaround for pull:** `timeout 15 git pull --ff-only origin main 2>/dev/null || true`

**Workaround for repo state check:** Use GitHub API:
```bash
curl -s https://api.github.com/repos/OWNER/REPO/branches
curl -s https://api.github.com/repos/OWNER/REPO/commits?per_page=5
```

## git config
Global git config may not exist in sandbox. Always use `-c user.email=... -c user.name=...` flags.
