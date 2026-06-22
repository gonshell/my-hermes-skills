#!/bin/bash
# Sync ~/.hermes/skills/ to the my-hermes-skills GitHub repo.
# Re-runnable: safe to call from cron. Exits non-zero on any failure.
#
# Cron pitfall: $HOME in the sandbox profile is /Users/xiesg/.hermes/home, so
# `~` does NOT expand to /Users/xiesg. Use absolute paths only.
#
# Recovery: if the local repo somehow lost its history (fresh init, accidental
# reset) and the remote has prior commits, this script resets to origin/main
# and re-overlays, so the next push is a fast-forward.

set -euo pipefail

# --- Repo discovery: try the canonical path, fall back to the sandbox path. ---
CANDIDATES=(
    "/Users/xiesg/github/my-hermes-skills"
    "/Users/xiesg/.hermes/home/github/my-hermes-skills"
    "$HOME/github/my-hermes-skills"
)
REPO=""
for c in "${CANDIDATES[@]}"; do
    if [ -d "$c/.git" ]; then
        REPO="$c"
        break
    fi
done
if [ -z "$REPO" ]; then
    echo "FATAL: repo not found. Tried: ${CANDIDATES[*]}" >&2
    exit 1
fi

SRC=/Users/xiesg/.hermes/skills
[ -d "$SRC" ] || { echo "FATAL: source not found at $SRC" >&2; exit 1; }

cd "$REPO"

# --- Ensure SSH remote (HTTPS push fails in cron: no credentials, no gh CLI). ---
CURRENT_URL=$(git config --get remote.origin.url || echo "")
case "$CURRENT_URL" in
    https://github.com/*)
        OWNER_REPO=$(echo "$CURRENT_URL" | sed 's|https://github.com/||; s|\.git$||')
        echo "Switching remote from HTTPS to SSH (HTTPS push needs creds in cron)"
        git remote set-url origin "git@github.com:${OWNER_REPO}.git"
        ;;
esac

# --- Pull latest (timeout: git data-transfer hangs in cron sandbox even when SSH auth works).
#     For one-way sync (local→remote), skipping pull is acceptable — we only push.
#     But try first: if the remote has commits we don't, fast-forward.
timeout 15 git pull --ff-only origin main 2>/dev/null || \
    echo "WARN: git pull skipped (timeout or no remote changes)"

# --- If local history diverged from remote (e.g. fresh init), reset to remote. ---
#     This is safe for a one-way sync repo: we always re-overlay from SRC anyway.
if ! git merge-base --is-ancestor origin/main HEAD 2>/dev/null; then
    if git rev-parse --verify origin/main >/dev/null 2>&1; then
        echo "WARN: local HEAD not descendant of origin/main — resetting to origin/main"
        git reset --hard origin/main
    fi
fi

# --- Mirror (rsync --delete so DST ends up identical to SRC).
#     -L: follow symlinks and copy real file content (not broken symlinks in repo).
#     --ignore-errors: continue even if broken symlinks in DST can't be deleted.
#     --exclude: preserve README.md and .gitignore (not in source).
#     2>/dev/null: suppress "symlink has no referent" warnings for broken symlinks in archive.
rsync -aL --delete --ignore-errors \
    --exclude='.git' --exclude='.gitignore' --exclude='README.md' \
    "$SRC/" "$REPO/" 2>/dev/null || true

# --- Verify (only .gitignore and README.md should differ).
LEFTOVER=$(diff -rq "$SRC" "$REPO" --exclude='.git' --exclude='.gitignore' --exclude='README.md' || true)
if [[ -n "$LEFTOVER" ]]; then
    echo "WARN: post-sync diff:" >&2
    echo "$LEFTOVER" >&2
fi

# --- Commit + push (skip if no changes).
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
