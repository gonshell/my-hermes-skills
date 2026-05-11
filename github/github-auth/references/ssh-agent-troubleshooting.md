# SSH Agent Troubleshooting (Session Notes)

## Problem

Push to `git@github.com:gonshell/my-hermes-skills` failed with:
```
ERROR: internal error performing authentication
fatal: Could not read from remote repository.
```

Root cause: SSH key exists on disk (`~/.ssh/id_ed25519`) but `ssh-agent` has no loaded identities.

## Diagnosis Commands

```bash
# Check SSH key exists
ls -la ~/.ssh/

# Check ssh-agent identities
ssh-add -l
# Expected (good): "2048 SHA256:xxxx ... (RSA)"
# Bad: "The agent has no identities."

# Test GitHub connectivity
ssh -T git@github.com
```

## Fix

```bash
# Load the key (use correct path — may differ from default ~/.ssh/)
ssh-add ~/.ssh/id_ed25519

# Or for RSA key:
ssh-add ~/.ssh/id_rsa

# Verify
ssh-add -l
ssh -T git@github.com
```

## Cron/Scheduled Job Environment Issue

The cron job ran with `HOME=/Users/xiesg/.hermes/home`, which differs from the user's interactive shell `HOME=/Users/xiesg`. This caused `~/.ssh/` to resolve to `/Users/xiesg/.hermes/home/.ssh/` (non-existent), making SSH fail silently.

Symptoms:
- `ls ~/.ssh/` → "No such file or directory"
- Interactive shell SSH works fine; cron job SSH fails

Solutions:
1. **Use HTTPS token auth** for cron jobs (preferred — no key loading needed)
2. **Set HOME explicitly** in the cron job before running git commands
3. **Use absolute paths** in scripts (`/Users/xiesg/.ssh/id_ed25519` instead of `~/.ssh/`)
