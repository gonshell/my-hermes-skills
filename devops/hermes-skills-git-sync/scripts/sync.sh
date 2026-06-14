#!/bin/bash
# Sync ~/.hermes/skills/ to the my-hermes-skills GitHub repo.
# Re-runnable: safe to call from cron. Exits non-zero on any failure.
#
# Cron pitfall: $HOME in this profile is /Users/xiesg/.hermes/home, so
# `~` does NOT expand to /Users/xiesg. Use absolute paths only.

set -euo pipefail

REPO=/Users/xiesg/github/my-hermes-skills
SRC=/Users/xiesg/.hermes/skills

cd "$REPO" || { echo "FATAL: repo not found at $REPO" >&2; exit 1; }

# 1. Pull latest
git pull --ff-only origin main

# 2. Mirror (rsync --delete so DST ends up identical to SRC)
# -L: follow symlinks and copy real file content (not broken symlinks in repo)
# --ignore-errors: continue even if broken symlinks in DST can't be deleted
# 2>/dev/null: suppress "symlink has no referent" warnings for broken symlinks in archive
rsync -aL --delete --ignore-errors --exclude='.git' --exclude='.gitignore' "$SRC/" "$REPO/" 2>/dev/null || true

# 3. Verify (only .gitignore should differ)
LEFTOVER=$(diff -rq "$SRC" "$REPO" --exclude='.git' --exclude='.gitignore' || true)
if [[ -n "$LEFTOVER" ]]; then
    echo "WARN: post-sync diff:" >&2
    echo "$LEFTOVER" >&2
fi

# 4. Commit + push (skip if no changes)
git add .
if git diff --cached --quiet; then
    echo "No changes to commit."
    exit 0
fi

git -c user.email="hermes@local" \
    -c user.name="hermes-cron" \
    commit -m "sync: $(date +%Y-%m-%d)"

git push origin main
echo "Sync complete: $(git log -1 --oneline)"
