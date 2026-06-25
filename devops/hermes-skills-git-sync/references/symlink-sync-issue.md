# Symlink Sync Issue

## Problem
`~/.hermes/skills/` contains symlinks (e.g., `lark-*` → `~/.agents/skills/lark-*`). Using `rsync -a` copies the symlink itself, not the target content. This results in broken symlinks in the GitHub backup repo.

## Solution
Use `rsync -aL` instead of `rsync -a`. The `-L` flag tells rsync to follow symlinks and copy the real file content.

## Pitfall: Script Reverts
The sync script itself is synced to GitHub. If the cron job runs and the script on GitHub still has `rsync -a` (from before the fix), it can overwrite the local fixed version. 

**Prevention**: After fixing the script, immediately run the sync manually to push the fixed version to GitHub. This ensures the cron job picks up the corrected script next time.

## Verification
```bash
# Check if GitHub repo has symlinks
find /Users/xiesg/github/my-hermes-skills -type l | wc -l
# Should be 0 after fix

# Check if source has symlinks
find /Users/xiesg/.hermes/skills -type l | wc -l
# Expected: many (source has symlinks to ~/.agents/skills/)
```

## Key Distinction
- **Source** (`~/.hermes/skills/`) — HAS symlinks (this is expected, they point to `~/.agents/skills/`)
- **Destination** (GitHub repo) — should have NO symlinks (real files only)
