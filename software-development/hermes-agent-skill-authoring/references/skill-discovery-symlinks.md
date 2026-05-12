# Skill Discovery & Symlink Conventions in ~/.hermes/skills/

## The Problem

When syncing skills from `~/.hermes/skills/` to a GitHub repo, a `find` without `-L` silently skips symlinked skill directories. All 22 `lark-*` skills were symlinks pointing to `/Users/xiesg/.agents/skills/lark-*`, and a plain `find "$SKILLS_DIR" -maxdepth 5 -name "SKILL.md"` found zero of them.

## Directory Structure Conventions

`~/.hermes/skills/` contains two types of entries at the top level:

### Type A — Nested category directory
```
~/.hermes/skills/
├── lark/
│   └── lark-cli-hermes-setup/   ← nested skill, category=lark
│       └── SKILL.md
├── apple/
│   ├── apple-notes/             ← nested skill, category=apple
│   │   └── SKILL.md
│   └── apple-reminders/
│       └── SKILL.md
```

Skill path (strip `SKILLS_DIR` prefix, strip `/SKILL.md`): `lark/lark-cli-hermes-setup`
Target repo path: `lark/lark-cli-hermes-setup/`

### Type B — Top-level symlink (external mount)
```
~/.hermes/skills/
├── lark-approval@    → /Users/xiesg/.agents/skills/lark-approval/   (symlink)
├── lark-base@        → /Users/xiesg/.agents/skills/lark-base/       (symlink)
```

`@` = symlink. `test -L` returns true. `find` (no `-L`) skips them entirely.
Skill path: `lark-approval`
Target repo path: `lark-approval/`

**Both types coexist in the same parent directory and are both valid skills.**

## The Fix

Two-line fix when writing a sync script:

```bash
# 1. Discover skills — MUST use -L to follow symlinks
find -L "$SKILLS_DIR" -maxdepth 5 -name "SKILL.md" -type f | \
    while read f; do
        rel="${f#$SKILLS_DIR/}"
        echo "${rel%/*}"
    done | sort -u

# 2. Copy skill content — MUST use --copy-links to dereference symlinks
rsync -a --copy-links --exclude='.DS_Store' --exclude='__pycache__' \
      "$src/" "$dst/"
```

### Why each flag matters

| Flag | Reason |
|------|--------|
| `find -L` | Without it, symlinked skill directories are invisible to the find command |
| `rsync --copy-links` | Without it, the symlink itself (not its content) is copied into the target repo, resulting in broken pointers |

## Diagnostic Recipe

When a sync claims to succeed but skills are missing:

```bash
# 1. Count skills found by find vs what's on disk
find /path/to/skills -maxdepth 5 -name "SKILL.md" | wc -l
find -L /path/to/skills -maxdepth 5 -name "SKILL.md" | wc -l

# 2. Find symlinks in source
find /path/to/skills -maxdepth 1 -type l

# 3. Compare source vs target leaf skills
find /path/to/skills -maxdepth 5 -name "SKILL.md" | \
    sed 's|/SKILL.md||' | sort > /tmp/src.txt
find /path/to/target -name "SKILL.md" | \
    sed 's|/SKILL.md||' | sort > /tmp/dst.txt
echo "Missing from target:"
comm -23 /tmp/src.txt /tmp/dst.txt
echo "Extra in target:"
comm -13 /tmp/src.txt /tmp/dst.txt

# 4. Dry run the rsync
rsync -avn --copy-links "$src/" "$dst/" | grep "/$"
```

## What NOT to do

- **Do not** `rsync` the entire `SKILLS_DIR` root — that would also copy `.hub/`, `.usage.json`, and other Hermes internals
- **Do not** use `--delete` in rsync unless you have verified the source is the authoritative complete set — it will wipe files from target that aren't in source
- **Do not** modify anything under `~/.hermes/skills/` (the skill source directory) — it's the ground truth and must remain untouched
