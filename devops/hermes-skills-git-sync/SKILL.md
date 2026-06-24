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

### ⚠️ The user-facing cron prompt is the #1 source of confusion

The instructions embedded in the nightly cron job say:

> 1. `cd ~/github/my-hermes-skills/`
> 2. `git pull origin main`
> 3. `cp -r` from `~/.hermes/skills/`
> 4. `git add . && git commit && git push origin main`

This is **outdated and contradicts this skill.** It causes three known failure modes
every time a fresh agent runs the cron:

1. `cd ~` resolves to the wrong path under the sandbox `$HOME` (see "Path resolution" below).
2. `cp -r` (no `-L`) leaves broken symlinks in the repo.
3. `git pull` hangs in the sandbox (see `references/cron-env-quirks.md`).

**If you receive the cron prompt verbatim, your first action should be to recognize
it and call `scripts/sync.sh` instead.** The skill's Pitfalls section below
documents why every step in the prompt is buggy. Treat the prompt as legacy
documentation, not authoritative instructions.

**Suggested cron job payload (replace the old prompt):**
```bash
bash /Users/xiesg/.hermes/skills/devops/hermes-skills-git-sync/scripts/sync.sh
```
Or, if the cron framework requires inline steps, copy the script's body verbatim
(see "The sync sequence" below) — do not paraphrase back to `cp -r` + `git pull`.

## Critical: symlinks in ~/.hermes/skills/

**Problem:** Many skills in `~/.hermes/skills/` are **symlinks** pointing to `~/.agents/skills/`, NOT real directories. Using `rsync -a` (or `cp -r`) preserves symlinks as-is, creating a broken backup repo that's useless on other machines.

**Example:**
```bash
$ ls -la ~/.hermes/skills/lark-doc
lrwxr-xr-x  1 user  staff  30 Apr 25 23:58 lark-doc -> ../../.agents/skills/lark-doc
```

**Solution:** Use `rsync -aL` — the `-L` flag follows symlinks and copies the actual file content.

```bash
# Wrong - preserves symlinks as-is
rsync -a --delete "$SRC/" "$REPO/"

# Correct - follows symlinks, copies real content
rsync -aL --delete "$SRC/" "$REPO/"
```

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
# -aL: follow symlinks and copy real file content (not broken symlinks in repo)
# --ignore-errors: continue even if broken symlinks in DST can't be deleted
# --exclude README.md: preserve repo-only files not in source
# 2>/dev/null || true: suppress "symlink has no referent" warnings
rsync -aL --delete --ignore-errors --exclude='.git' --exclude='.gitignore' --exclude='README.md' "$SRC/" "$REPO/" 2>/dev/null || true

# 3. Mirror with rsync --delete so orphaned entries in DST
#    (skills deleted/archived in SRC) are removed automatically.
#    cp -r would NOT do this — it only overlays new content and
#    leaves stale files (e.g. an old symlink in repo root) forever.
#
#    -aL: follow symlinks and copy real file content (CRITICAL - see symlinks section above)
#    --ignore-errors: continue even if broken symlinks in DST can't be deleted
#    --exclude='README.md': preserve README.md that exists in DST but not in SRC
#    2>/dev/null: suppress "symlink has no referent" warnings for broken symlinks in archive
rsync -aL --delete --ignore-errors --exclude='.git' --exclude='.gitignore' --exclude='README.md' "$SRC/" "$REPO/" 2>/dev/null || true

# 4. Verify (the only diff remaining should be the excluded .gitignore)
diff -rq "$SRC" "$REPO" --exclude='.git' --exclude='.gitignore' --exclude='README.md'

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

`rsync -aL --delete` is a one-way true mirror — DST ends up identical to SRC
modulo the excluded `.git/`, `.gitignore`, and `README.md`. The `-L` flag
follows symlinks (critical since skills may be symlinked from `~/.agents/skills/`).
This is what you want for a backup repo.

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

See also `references/cron-env-quirks.md` for known cron/sandbox environment behaviors.

- **`git pull`/`fetch`/`clone` hang or fail with sideband disconnect (2026-06-15, 2026-06-19 confirmed)**: Git data-transfer operations hang indefinitely or fail with `fetch-pack: unexpected disconnect while reading sideband packet`. This is NOT sandbox-specific — it's a network-level issue where small packets (SSH auth, `git ls-remote`, API metadata) succeed but large data transfers (pack fetch, archive downloads) stall or disconnect. **Diagnostic pattern:** if `git ls-remote origin main` works but `git fetch` hangs, the issue is large-transfer network instability, not auth or repo problems. **Push still works** (upload path is different from download). Workaround: `timeout 15 git pull --ff-only origin main 2>/dev/null || true` and proceed. For repo state checks, use GitHub API: `curl -s https://api.github.com/repos/gonshell/my-hermes-skills/branches`.
- **README.md deletion**: `rsync --delete` removes any file in DST that doesn't exist in SRC. If you maintain a README.md in the repo root (not in `~/.hermes/skills/`), it WILL be deleted on next sync. **Add `--exclude='README.md'`** to the rsync command.
- **Symlinks in source directory**: Many skills in `~/.hermes/skills/` are symlinks to `~/.agents/skills/`. Using `rsync -a` preserves these as broken symlinks in the repo. **Always use `rsync -aL`** to follow symlinks and copy real content.
- **Broken symlinks in destination**: After running with `-aL`, old symlinks in the destination repo become broken (target no longer exists). rsync will warn "symlink has no referent" but `--ignore-errors` + `2>/dev/null || true` handles this gracefully.
- **`rsync` reports `*deleting` items in dry-run that are pure DST cruft.** Expected — those are exactly the files `--delete` will remove. Read the dry-run output, don't panic.
- **`.archive/` is user-archived content.** It IS skill content (just superseded), so it SHOULD be synced. The .gitignore above intentionally does NOT exclude it.
- **`git -c user.email/name` flags beat relying on global git config** — cron environments often have no global identity set, leading to "Please tell me who you are" errors.
- **`-aL` flag is required** — skills in `~/.hermes/skills/` may be symlinks to `~/.agents/skills/` (common for hub-installed or shared skills). Without `-L`, rsync copies the symlink itself, which breaks on clone. With `-L`, rsync follows the link and copies the real file content.
- **`--exclude='README.md'`** — if the repo has a README.md that doesn't exist in `~/.hermes/skills/`, `rsync --delete` will remove it. Always exclude repo-only files.
- **Broken symlinks in DST cause rsync warnings** — `--ignore-errors` + `2>/dev/null || true` suppresses "symlink has no referent" errors for stale symlinks in the archive directory.
- **Empty commits are fine to skip** — wrap the commit in `|| echo "Nothing to commit"` so the cron doesn't fail when there are no changes.
- **The sandbox `$HOME` gotcha** (see Path resolution above) bites every fresh cron invocation. Detect via `echo $HOME` before any `cd ~`. In this profile `$HOME=/Users/xiesg/.hermes/home` so `~` resolves to a non-existent `github/` subdir.
- **Never `git push --force`** — this is a backup repo. Force pushes destroy history other machines may have pushed.
- **HTTPS push needs credentials; SSH doesn't.** In this user's setup (sandbox/cron), there is no `gh` CLI, no `~/.netrc`, no `~/.git-credentials`, no `GITHUB_TOKEN` env var. `git push https://github.com/...` will hang ~75s then fail with `could not read Username: Device not configured`. **Always use SSH remote** (`git@github.com:OWNER/REPO.git`) for both fetch and push. If the repo's remote is HTTPS on first run, switch it: `git remote set-url origin git@github.com:OWNER/REPO.git`. Verify auth with `ssh -T git@github.com` (which prints `Hi OWNER!` on success).
- **Recovering from a botched first push to an empty repo.** If the local repo is on a fresh commit but the remote already has prior sync history (e.g. the cron was reset, or the script was re-run after a long gap), `git push` will be rejected with "remote contains work that you do not have locally". Recovery: `git reset --hard origin/main`, re-overlay the source (`rsync -aL` again, or re-call the script), then `git add . && git commit && git push`. Never force-push on a sync repo.
- **Symlink copies that "fail" with `cannot overwrite directory X with non-directory X`.** This is the `cp -R` (no `-L`) trap on macOS. `cp -R` preserves symlinks, so a source symlink `lark-doc -> /Users/xiesg/.agents/skills/lark-doc` is copied as a symlink (a "non-directory" from the copy's perspective) and refuses to overwrite the existing real directory at the destination. **Always use `rsync -aL` (or `cp -RL`)** to follow symlinks. This pitfall was hit in 2026-06-20 cron run and required re-copying 25 of 61 skills individually.
- **mtime-backwards skip: `rsync -au` does NOT re-sync when DST mtime is newer than SRC, even if SRC content changed.** (Hit 2026-06-23 on `lark-pitfalls/SKILL.md`.) This bites after `git checkout HEAD -- <file>` restores DST mtime to the commit time while SRC was edited later — rsync sees DST as newer and skips. **Symptom:** `git status` shows no diff but SRC and DST genuinely differ. **Fix:** after rsync, verify with `diff -rq` (already in the script), and force a content-based re-sync of any files that differ: `cp -f "$SRC/$f" "$REPO/$f"` for each divergent file, OR add `--checksum` to the rsync flag set (slower but mtime-independent). Better: when in doubt, drop `-u` and use `rsync -aL --delete` — last-write-wins by source mtime is the safer default for one-way backup.
- **macOS rsync 2.6.9 does not support `--max-delete=0`.** (Hit 2026-06-23.) Documented rsync 3.x flag for "no deletions" is silently ignored or rejected on the system rsync. The portable equivalent is `--ignore-existing` (won't delete, won't overwrite — only adds new) combined with `--update` to skip already-newer DST files. For a true backup mirror that needs `--delete`, accept the deletion; just exclude non-source files explicitly (the script does this via `--exclude=.git`, `--exclude=.gitignore`, `--exclude=README.md`).
- **BSD `cp` does not support `-u`.** (Hit 2026-06-23.) `cp: illegal option -- u`. On macOS, `cp` is BSD-derived and lacks the GNU `cp -u` (update only if newer) flag. Use `rsync -au` or shell loops with `[ "$src" -nt "$dst" ] && cp "$src" "$dst"` instead.
- **The `.gitignore` excludes runtime metadata from `git add`, but rsync still copies them to the working tree.** That's correct — the DST repo is a full mirror on disk; git is just the history. The `.usage.json`, `.hub/`, `.curator_state/` files will live in the working tree untracked.

## Verification

After each run, confirm:

```bash
cd "$REPO"
git log --oneline -3          # commit landed
git status                    # clean working tree
git ls-files | wc -l          # file count roughly matches SRC file count
ls -la README.md              # README.md preserved (not deleted by rsync --delete)
diff -rq "$SRC" "$REPO" --exclude='.git' --exclude='.gitignore' --exclude='README.md'  # should be empty
```

**Never trust `git status` alone for sync correctness.** rsync's mtime-based skip logic can leave DST stale even when `git status` shows no changes (DST mtime is newer than SRC after `git checkout`). Always run `diff -rq` post-sync — if it shows file differences, force a content-based re-sync with `cp -f` or `rsync --checksum`.

**Critical verification — check for remaining symlinks:**
```bash
find "$REPO" -type l | wc -l  # should be 0 after fix
```

If this shows symlinks > 0, the rsync `-aL` flag is not working or the source has changed.

If `git status` shows untracked `.bundled_manifest`, `.usage.json`, `__pycache__/`, etc., the `.gitignore` is missing or broken — re-add it before the next commit.

## Variants

**Multi-machine cron:** multiple machines running this simultaneously will race. Acceptable workaround: tolerate push rejection (`git push` returns non-zero if remote advanced); the next pull on the next run reconciles.

**Pre-migration full snapshot:** add `--mirror` semantics by `git tag` after each successful push:

```bash
git tag "snapshot-$(date +%Y-%m-%d-%H%M)" && git push origin --tags
```

This gives you a restore point per run without polluting main history.