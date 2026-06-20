# Cron/Sandbox Environment Quirks

## HOME override
The Hermes cron sandbox sets `$HOME=/Users/xiesg/.hermes/home` (not `/Users/xiesg`).
`~` resolves to the sandbox path. Always use absolute paths for repos, SSH keys, etc.

**Detection:** `echo $HOME | grep -q '.hermes/home' && echo "SANDBOX"`

## Git behavior (confirmed 2026-06-15, 2026-06-19)
| Operation | Works? | Notes |
|-----------|--------|-------|
| `ssh -T git@github.com` | ✅ | SSH auth works fine |
| `git ls-remote origin main` | ✅ | Small packet exchange works |
| `curl https://github.com` | ✅ | HTTP works fine |
| `curl https://api.github.com/...` | ✅ | GitHub REST API (metadata) works |
| `curl` archive download (zip/tarball) | ❌ hangs/disconnects | Large HTTP transfers also fail |
| `git fetch / pull / clone` | ❌ hangs | `fetch-pack: unexpected disconnect while reading sideband packet` |
| `git push` | ✅ | Upload path works even when download stalls |

**Root cause:** Network-level issue with large data transfers to GitHub, not sandbox-specific. Small packets (SSH handshake, ls-remote, API metadata) succeed, but pack-data download and HTTP archive downloads stall or disconnect. Likely GFW/ISP throttling of GitHub bulk transfers.

**Diagnostic pattern:**
1. `git ls-remote origin main` → works? Auth is fine, repo accessible.
2. `git fetch origin main` → hangs or `unexpected disconnect while reading sideband packet`? Large-transfer network issue.
3. `curl -sI https://github.com/OWNER/REPO -o /dev/null -w "%{http_code}"` → works? HTTP connectivity fine.
4. `curl -sL https://github.com/OWNER/REPO/archive/main.zip -o /dev/null` → hangs? Confirms bulk transfer issue.

**Workarounds:**
- Pull: `timeout 15 git pull --ff-only origin main 2>/dev/null || true` (skip gracefully)
- Repo state check: Use GitHub API (`curl -s https://api.github.com/repos/OWNER/REPO/branches`)
- Push: works without workaround

## git config
Global git config may not exist in sandbox. Always use `-c user.email=... -c user.name=...` flags.
