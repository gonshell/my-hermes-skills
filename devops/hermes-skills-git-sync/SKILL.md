---
name: hermes-skills-git-sync
description: Mirror ~/.hermes/skills/ to a git-backed GitHub repository. Use when the task is "sync Hermes skills to GitHub", "backup skills", "mirror skills repo", or any cron-driven copy of the local skills directory to a remote. Covers path resolution, runtime-noise exclusion, and the correct sync sequence.
---

# Hermes Skills → GitHub Sync

Mirror `~/.hermes/skills/` into a version-controlled GitHub repo so skills survive machine loss and are reviewable as diffs.

## When to use

Trigger this skill whenever the task is one of:
- Daily/hourly cron that copies `~/.hermes/skills/` into a git repo and pushes.
- One-off backup of skills before a Hermes reinstall or migration.
- Setting up a new "skills backup" repo from scratch.

Do NOT use this skill for:
- Editing skills (use `skill_manage`).
- Cross-machine skill installation (use `hermes skills install`).
- Diffing two skill directories (use `diff -rq` directly).

## Recommended: use the sync script

**For cron jobs and automated runs, always invoke `scripts/sync.sh` directly.**
It handles everything: absolute path resolution, rsync --delete, commit, push.
Don't re-derive the sequence manually — the script IS the canonical implementation.

```bash
bash /Users/xiesg/.hermes/skills/devops/hermes-skills-git-sync/scripts/sync.sh
```

The manual sequence below is documented for understanding and debugging only.

## Path resolution (pitfall — read first)

The cron/sandbox environment often sets `$HOME` to a sandbox path like `~/.hermes/home/`, NOT the real user home. `~/github/my-hermes-skills/` will then resolve to a non-existent directory.

Always resolve the real path explicitly before `cd`:

```bash
# Detect real $HOME vs sandbox $HOME
echo $HOME                                    # if it contains ".hermes/home", you're in sandbox
ls /Users/$USER/github/                       # check real path

# Use absolute path everywhere
REPO=/Users/xiesg/github/my-hermes-skills     # or detect dynamically
SRC=/Users/xiesg/.hermes/skills
cd "$REPO"
```

If running in a non-interactive cron, prefer absolute paths over `~`.

## The sync sequence

```bash
REPO=/Users/xiesg/github/my-hermes-skills
SRC=/Users/xiesg/.hermes/skills

cd "$REPO" || { echo "FATAL: repo not found at $REPO"; exit 1; }

# 1. Pull latest (cron job may run on multiple machines)
git pull origin main

# 2. Dry-run preview of what rsync WOULD change
#    (catches symlink drift, stale files in DST, etc.)
rsync -ain --delete --exclude='.git' --exclude='.gitignore' "$SRC/" "$REPO/"

# 3. Mirror with rsync --delete so orphaned entries in DST
#    (skills deleted/archived in SRC) are removed automatically.
#    cp -r would NOT do this — it only overlays new content and
#    leaves stale files (e.g. an old symlink in repo root) forever.
rsync -a --delete --exclude='.git' --exclude='.gitignore' "$SRC/" "$REPO/"

# 4. Verify (the only diff remaining should be the excluded .gitignore)
diff -rq "$SRC" "$REPO" --exclude='.git' --exclude='.gitignore'

# 5. Stage and commit
git add .
git -c user.email="hermes@local" \
    -c user.name="hermes-cron" \
    commit -m "sync: $(date +%Y-%m-%d)" || echo "Nothing to commit"
git push origin main
```

### Why rsync --delete (not cp -r)

The original prompt this skill was extracted from said `cp -r` in step 4.
That instruction is buggy: if a skill is deleted in SRC (or moved into
`.archive/`), `cp -r` leaves the stale copy in REPO until someone manually
removes it. Real-world example: the `mmx-cli` symlink sat in the DST repo
root for weeks because the SRC copy had been moved into `.archive/`.

`rsync -a --delete` is a one-way true mirror — DST ends up identical to SRC
modulo the excluded `.git/` and `.gitignore`. This is what you want for a
backup repo.

## .gitignore (required — add once at repo init)

`~/.hermes/skills/` contains Hermes runtime metadata that must NEVER enter git history. Add this `.gitignore` to the repo root on first run:

```gitignore
# Hermes runtime metadata (not user-edited skills)
.bundled_manifest
.curator_backups/
.curator_state
.hub/
.usage.json
.usage.json.lock

# Python bytecode caches
__pycache__/
*.py[cod]
*$py.class

# Common venv artifacts
.venv/
venv/
```

**Why:** Without this, every commit bloats with 50+ files of curator state and usage telemetry that have nothing to do with the user's skills.

## Pitfalls

- **`rsync` reports `*deleting` items in dry-run that are pure DST cruft.** Expected — those are exactly the files `--delete` will remove. Read the dry-run output, don't panic.
- **rsync will NOT follow broken symlinks (and will warn).** That's correct — skills like `lark-*` are symlinks into `~/.agents/skills/`; if the target exists, rsync syncs the link. If the target is missing on the DST side, `diff -rq` will report "No such file" — that's the symlink pointing into the user's own filesystem, not a sync failure.
- **`.archive/` is user-archived content.** It IS skill content (just superseded), so it SHOULD be synced. The .gitignore above intentionally does NOT exclude it.
- **`git -c user.email/name` flags beat relying on global git config** — cron environments often have no global identity set, leading to "Please tell me who you are" errors.
- **Empty commits are fine to skip** — wrap the commit in `|| echo "Nothing to commit"` so the cron doesn't fail when there are no changes.
- **The sandbox `$HOME` gotcha** (see Path resolution above) bites every fresh cron invocation. Detect via `echo $HOME` before any `cd ~`. In this profile `$HOME=/Users/xiesg/.hermes/home` so `~` resolves to a non-existent `github/` subdir.
- **Never `git push --force`** — this is a backup repo. Force pushes destroy history other machines may have pushed.
- **The `.gitignore` excludes runtime metadata from `git add`, but rsync still copies them to the working tree.** That's correct — the DST repo is a full mirror on disk; git is just the history. The `.usage.json`, `.hub/`, `.curator_state/` files will live in the working tree untracked.

## Verification

After each run, confirm:

```bash
cd "$REPO"
git log --oneline -3          # commit landed
git status                    # clean working tree
git ls-files | wc -l          # file count roughly matches SRC file count
```

If `git status` shows untracked `.bundled_manifest`, `.usage.json`, `__pycache__/`, etc., the `.gitignore` is missing or broken — re-add it before the next commit.

## Variants

**Multi-machine cron:** multiple machines running this simultaneously will race. Acceptable workaround: tolerate push rejection (`git push` returns non-zero if remote advanced); the next pull on the next run reconciles.

**Pre-migration full snapshot:** add `--mirror` semantics by `git tag` after each successful push:

```bash
git tag "snapshot-$(date +%Y-%m-%d-%H%M)" && git push origin --tags
```

This gives you a restore point per run without polluting main history.