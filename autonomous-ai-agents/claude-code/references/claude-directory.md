# Claude Code .claude Directory — Official Reference

> Sourced from: https://code.claude.com/docs/en/claude-directory and related pages (memory, sub-agents, skills)

---

## CLAUDE.md vs Auto Memory

| | CLAUDE.md Files | Auto Memory |
|---|---|---|
| Who writes | You | Claude |
| Content | Instructions and rules | Learnings and patterns |
| Scope | Project, user, or org | Per working tree |
| Loaded | Every session (full file) | Every session (first 200 lines or 25KB) |
| Use for | Coding standards, workflows, project architecture | Build commands, debugging insights, preferences Claude discovers |

Auto memory: Claude saves notes for itself (build commands, debugging insights, architecture notes, code style preferences). Requires v2.1.59+.

---

## CLAUDE.md File Locations

| Scope | Location | Shared? |
|-------|----------|---------|
| Managed policy | macOS: `/Library/Application Support/ClaudeCode/CLAUDE.md`<br>Linux/WSL: `/etc/claude-code/CLAUDE.md`<br>Windows: `C:\Program Files\ClaudeCode\CLAUDE.md` | All org users |
| Project | `./CLAUDE.md` or `/.claude/CLAUDE.md` | Yes (git-tracked) |
| User | `~/.claude/CLAUDE.md` | No |
| Local | `./CLAUDE.local.md` | No (gitignored) |

**AGENTS.md**: Claude Code reads `CLAUDE.md`, not `AGENTS.md`. Import with `@AGENTS.md` in CLAUDE.md, or symlink: `ln -s AGENTS.md CLAUDE.md`.

---

## CLAUDE.md Loading Order

Claude walks up from CWD, concatenating all discovered files:

1. `~/.claude/CLAUDE.md` (global)
2. `./CLAUDE.md` (project)
3. `.claude/rules/*.md` (modular rules)
4. `.claude/CLAUDE.local.md` (local, highest priority)

Within each directory, `CLAUDE.local.md` appends after `CLAUDE.md`.

Files in subdirectories are **lazy-loaded** when Claude reads files in those directories — not at startup.

---

## Write Effective CLAUDE.md

- **Size**: Target under 200 lines. Longer files = more token cost + lower adherence.
- **Structure**: Use markdown headers + bullets. Dense paragraphs are ignored.
- **Specificity**: "Use 2-space indentation" beats "format code properly"
- **No contradictions**: Review all CLAUDE.md files + rules periodically to remove conflicts.
- **Block comments**: `<!-- maintainer notes -->` are stripped from context (preserved in Read tool).

### Import Additional Files

```markdown
See @README for overview and @package.json for npm commands.

# Additional Instructions
- git workflow @docs/git-instructions.md
```

- Relative/absolute paths allowed
- Resolved relative to the file containing the import
- Max depth: 5 hops recursive
- First use shows approval dialog

---

## Rules: .claude/rules/

For modular instructions scoped to topics or file patterns.

### Path-Specific Rules (YAML frontmatter)

```yaml
---
paths:
  - "src/api/**/*.ts"
  - "lib/**/*.ts"
---

# API Development Rules

- All API endpoints must include input validation
- Use standard error response format
```

**Glob patterns:**

| Pattern | Matches |
|---------|---------|
| `**/*.ts` | All TypeScript files in any directory |
| `src/**/*` | All files under src/ |
| `*.md` | Markdown files in project root |
| `src/components/*.tsx` | React components in specific directory |
| `src/**/*.{ts,tsx}` | Brace expansion for multiple extensions |

Rules without `paths` field load unconditionally at startup.

### Share Rules via Symlinks

```bash
ln -s ~/shared-claude-rules .claude/rules/shared
ln -s ~/company-standards/security.md .claude/rules/security.md
```

Circular symlinks are detected and handled gracefully.

### User-Level Rules

`~/.claude/rules/*.md` apply to all projects. Loaded before project rules (project rules win).

---

## Skills: .claude/skills/

Skills extend Claude's capabilities. Body loads only when invoked — long reference material costs nothing until needed.

### SKILL.md Format

```markdown
---
description: Summarizes uncommitted changes and flags risky patterns.
---

## Current changes

!`git diff HEAD`

## Instructions

Summarize changes in 2-3 bullets, then flag risks.
```

### Key Frontmatter Fields

| Field | Description |
|-------|-------------|
| `name` | Display name (max 64 chars, lowercase/hyphens/numbers) |
| `description` | What it does + when to use (first paragraph if omitted) |
| `when_to_use` | Additional trigger context (appended to description) |
| `argument-hint` | Autocomplete hint: `[issue-number]` |
| `arguments` | Named positional args for `$name` substitution |
| `disable-model-invocation` | `true` = prevent Claude from auto-triggering |
| `allowed-tools` | Whitelist specific tools |

**Total description + when_to_use capped at 1,536 chars in skill listing.**

### Dynamic Context Injection

Prefix shell commands with `!` to inject live output:

```
!`git diff HEAD`
```

Claude Code runs the command, replaces the line with output, THEN Claude reads the skill. The `!` prefix triggers injection before Claude sees content.

### Skills Location Priority (highest → lowest)

1. Enterprise (managed settings)
2. `~/.claude/skills/` (personal)
3. `.claude/skills/` (project)
4. Plugin: `<plugin>/skills/`

Plugin skills use `plugin-name:skill-name` namespace — no conflicts possible.

### Skills vs Commands vs Rules

| Mechanism | Invocation | Trigger | Best for |
|-----------|-----------|---------|----------|
| **Skill** | Automatic | Natural language match | Repeated workflows Claude auto-detects |
| **Command** | Manual | `/command-name` | Named procedures user explicitly requests |
| **Rule** | Always-loaded | Path patterns | Coding standards always in context |

Commands merged into skills. `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both create `/deploy`. Skill takes precedence if both exist.

---

## Subagents: .claude/agents/

Specialized AI assistants with their own context, tools, and permissions.

### Built-in Subagents

| Name | Model | Tools | Purpose |
|------|-------|-------|---------|
| Explore | Haiku | Read-only | File discovery, code search, exploration |
| Plan | — | — | Planning |
| General-purpose | — | — | General tasks |

### Location Priority (highest → lowest)

1. Managed settings (org-wide)
2. `--agents` CLI flag (session)
3. `.claude/agents/` (project)
4. `~/.claude/agents/` (user)
5. Plugin agents/ (lowest)

### Agent File Format

```markdown
---
name: code-reviewer
description: Expert code reviewer. Use proactively after code changes.
model: sonnet
tools: [Read, Grep, Glob, Bash]
auto-memory: user
---

You are a senior code reviewer. Focus on code quality, security, and best practices.
```

### Available Tools for Subagents

`Read`, `Grep`, `Glob`, `Bash`, `WebSearch`, `WebFetch`, `Edit`, `Write`, `Notebook`, `TodoWrite`, `mcp__*`

### Invoke Subagents

- **Automatic**: Claude delegates based on agent `description`
- **Explicit**: `@code-reviewer review auth module`

---

## Auto Memory Storage

Location: `~/.claude/projects/<project>/memory/`

```
memory/
├── MEMORY.md          # Index (first 200 lines or 25KB loaded per session)
├── debugging.md       # Topic files (lazy-loaded on demand)
├── api-conventions.md
└── ...
```

Custom location via `autoMemoryDirectory` in `~/.claude/settings.json` (absolute path or `~/`):

```json
{
  "autoMemoryDirectory": "~/my-custom-memory-dir"
}
```

Not configurable in project/local settings (security: prevents repo from redirecting writes).

---

## Settings Files

| File | Scope | Git-tracked? |
|------|-------|-------------|
| `.claude/settings.json` | Project | Yes |
| `.claude/settings.local.json` | Local | No (gitignored) |
| `~/.claude/settings.json` | User | No |

Settings hierarchy (highest → lowest): CLI flags → local → project → user.

---

## Memory: claudeMdExcludes for Large Monorepos

Skip irrelevant ancestor CLAUDE.md files:

```json
// .claude/settings.local.json
{
  "claudeMdExcludes": [
    "**/monorepo/CLAUDE.md",
    "/home/user/monorepo/other-team/.claude/rules/**"
  ]
}
```

Patterns match absolute paths via glob. Managed policy CLAUDE.md cannot be excluded.
