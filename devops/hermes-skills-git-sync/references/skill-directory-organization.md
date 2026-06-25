# Moving Skills to Subdirectories

## Impact Assessment

When moving a skill from `~/.hermes/skills/<name>/` to `~/.hermes/skills/<category>/<name>/`, check:

### 1. References by Other Skills
```bash
# Find skills that reference the moved skill by name
grep -r "<skill-name>" ~/.hermes/skills/ --include="SKILL.md" -l
```

- **Text references** (e.g., "应使用 `stock-deep-analysis`") — **no update needed**. These are skill names, not file paths.
- **File path references** (e.g., `../stock-deep-analysis/SKILL.md`) — **must update** to reflect new path.

### 2. Hermes Skill System
- `skills_list` resolves skills by name, not path — moving to a subdirectory works automatically
- Skills in subdirectories get a `category` from the directory name (e.g., `finance-analysis/`)
- No registration or config changes needed

### 3. Cron Jobs
- Cron jobs reference skills by name (e.g., `"skills": ["stock-deep-analysis"]`) — no update needed
- The skill system resolves the name regardless of directory depth

### 4. Git Sync
- The sync script mirrors `~/.hermes/skills/` to GitHub, including subdirectories
- No changes needed to the sync script

## Summary
Moving a skill to a subdirectory is safe as long as no other skills reference it by file path. Most references are by name and will continue to work.
