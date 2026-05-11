---
name: hermes-agent-skill-authoring
description: "Author in-repo SKILL.md: frontmatter, validator, structure."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, authoring, hermes-agent, conventions, skill-md]
    related_skills: [writing-plans, requesting-code-review]
---

# Authoring Hermes-Agent Skills (in-repo)

## Overview

There are two places a SKILL.md can live:

1. **User-local:** `~/.hermes/skills/<maybe-category>/<name>/SKILL.md` — personal, not shared. Created via `skill_manage(action='create')`.
2. **In-repo (this skill is about this case):** `/home/bb/hermes-agent/skills/<category>/<name>/SKILL.md` — committed, shipped with the package. Use `write_file` + `git add`. `skill_manage(action='create')` does NOT target this tree.

## When to Use

- User asks you to add a skill "in this branch / repo / commit"
- You're committing a reusable workflow that should ship with hermes-agent
- You're editing an existing skill under `/home/bb/hermes-agent/skills/` (use `patch` for small edits, `write_file` for rewrites; `skill_manage` still works for patch on in-repo skills, but not for `create`)

## Required Frontmatter

Source of truth: `tools/skill_manager_tool.py::_validate_frontmatter`. Hard requirements:

- Starts with `---` as the first bytes (no leading blank line).
- Closes with `\n---\n` before the body.
- Parses as a YAML mapping.
- `name` field present.
- `description` field present, ≤ **1024 chars** (`MAX_DESCRIPTION_LENGTH`).
- Non-empty body after the closing `---`.

Peer-matched shape used by every skill under `skills/software-development/`:

```yaml
---
name: my-skill-name               # lowercase, hyphens, ≤64 chars (MAX_NAME_LENGTH)
description: Use when <trigger>. <one-line behavior>.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [short, descriptive, tags]
    related_skills: [other-skill, another-skill]
---
```

`version` / `author` / `license` / `metadata` are NOT enforced by the validator, but every peer has them — omit and your skill sticks out.

## Size Limits

- Description: ≤ 1024 chars (enforced).
- Full SKILL.md: ≤ 100,000 chars (enforced as `MAX_SKILL_CONTENT_CHARS`, ~36k tokens).
- Peer skills in `software-development/` sit at **8-14k chars**. Aim for that range. If you're pushing past 20k, split into `references/*.md` and reference them from SKILL.md.

## Peer-Matched Structure

Every in-repo skill follows roughly:

```
# <Title>

## Overview
One or two paragraphs: what and why.

## When to Use
- Bulleted triggers
- "Don't use for:" counter-triggers

## <Topic sections specific to the skill>
- Quick-reference tables are common
- Code blocks with exact commands
- Hermes-specific recipes (tests via scripts/run_tests.sh, ui-tui paths, etc.)

## Common Pitfalls
Numbered list of mistakes and their fixes.

## Verification Checklist
- [ ] Checkbox list of post-action verifications

## One-Shot Recipes (optional)
Named scenarios → concrete command sequences.
```

Not every section is mandatory, but `Overview` + `When to Use` + actionable body + pitfalls are the minimum for the skill to feel like a peer.

## Directory Placement

```
skills/<category>/<skill-name>/SKILL.md
```

Categories currently in repo (confirm with `ls skills/`): `autonomous-ai-agents`, `creative`, `data-science`, `devops`, `dogfood`, `email`, `gaming`, `github`, `leisure`, `mcp`, `media`, `mlops/*`, `note-taking`, `productivity`, `red-teaming`, `research`, `smart-home`, `social-media`, `software-development`.

Pick the closest existing category. Don't invent new top-level categories casually.

## Workflow

1. **Survey peers** in the target category:
   ```
   ls skills/<category>/
   ```
   Read 2-3 peer SKILL.md files to match tone and structure.
2. **Check validator constraints** in `tools/skill_manager_tool.py` if unsure.
3. **Draft** with `write_file` to `skills/<category>/<name>/SKILL.md`.
4. **Validate locally**:
   ```python
   import yaml, re, pathlib
   content = pathlib.Path("skills/<category>/<name>/SKILL.md").read_text()
   assert content.startswith("---")
   m = re.search(r'\n---\s*\n', content[3:])
   fm = yaml.safe_load(content[3:m.start()+3])
   assert "name" in fm and "description" in fm
   assert len(fm["description"]) <= 1024
   assert len(content) <= 100_000
   ```
5. **Git add + commit** on the active branch.
6. **Note:** the CURRENT session's skill loader is cached — `skill_view` / `skills_list` will not see the new skill until a new session. This is expected, not a bug.

## Cross-Referencing Other Skills

`metadata.hermes.related_skills` unions both trees (`skills/` in-repo and `~/.hermes/skills/`) at load time. You CAN reference a user-local skill from an in-repo skill, but it won't resolve for other users who clone the repo fresh. Prefer referencing only in-repo skills from in-repo skills. If a frequently-referenced skill lives only in `~/.hermes/skills/`, consider promoting it to the repo.

## Editing Existing In-Repo Skills

- **Small fix (typo, added pitfall, tightened trigger):** `skill_manage(action='patch', name=..., old_string=..., new_string=...)` works fine on in-repo skills.
- **Major rewrite:** `write_file` the whole SKILL.md. `skill_manage(action='edit')` also works but requires supplying the full new content.
- **Adding supporting files:** `write_file` to `skills/<category>/<name>/references/<file>.md`, `templates/<file>`, or `scripts/<file>`. `skill_manage(action='write_file')` also works and enforces the references/templates/scripts/assets subdir allowlist.
- **Always commit** the edit — in-repo skills are source, not runtime state.

## Structuring Technical Concept Documents

When writing a skill that explains a technical concept (not just a how-to), the structure must answer the reader's actual questions, not follow a generic What/Why/How template blindly.

### The Problem → What → How Pattern

Every technical concept exists to solve a problem. Structure each section as:

```
1. Problem (面临什么问题)
   — What pain does this technology solve? Why did it need to exist?
   — Frame it from the DEVELOPER's perspective, not the technology's.

2. What (是什么)
   — Concrete, runnable examples: actual JSON output, actual config, actual file tree.
   — NOT generic description. Developers need to recognize what they will see/use.

3. How (怎么做)
   — Minimal working example + workflow steps.
   — Include: directory structure if applicable, commands to run, pitfalls.
```

### Why This Order Matters

Leading with "What is X" forces the reader to hold a definition they can't yet appreciate. Leading with "Problem" gives them a reason to care before seeing the solution.

### Common Structural Mistakes

| Mistake | Why it's wrong |
|---------|----------------|
| All chapters follow What → Why → How identically | Assumes every concept needs the same structure; flattens the narrative |
| "Trends" section appended at the end | Destroys the structure. Embed trends inside each chapter, not as a separate block |
| Multiple levels of hierarchy (file-per-chapter) for a single concept | Over-fragmentation. One file, sequential chapters, is clearer for a coherent topic |
| Describing without showing concrete examples | "LLM outputs JSON" vs actual `{function: "get_weather", arguments: {...}}` |

### Before Writing: Ask These Questions Per Chapter

- Who is reading this? (Developer who needs to USE this, not researcher who needs to UNDERSTAND it deeply)
- What is the ONE thing they should take away?
- What would they Google if this section was missing?
- Do the section headings answer real questions, or just label topics?

### Document-Level Structure (Single File)

For a document covering multiple related concepts:

```
# Title

## 架构总览图  ← top-level overview first, so readers have a mental map

## Chapter 1
## Chapter 2
## ...
## 全链路示例  ← tie it together with a concrete end-to-end walkthrough
```

One file. Sequential chapters. No separate "趋势" chapter — embed it in each section.

### Pre-Writing Phase: Confirm Structure First

**Do NOT start writing until structure is confirmed.** This is the most common浪费 (waste) in document writing sessions.

Before writing any chapter:
1. Clarify the **problem** each chapter solves — who is reading it and what they take away
2. Define **boundaries** — what is in this chapter, what is explicitly NOT in this chapter (especially when removing content like a whole chapter)
3. Resolve **cross-references** — are terms consistent across chapters? Does Chapter N+1 depend on Chapter N being read first?
4. Verify **facts that affect structure** — protocol specs, version numbers, attribution — before committing to them in writing

**Signals you need to stop and re-confirm structure:**
- User says "去掉 X 的内容" → confirm if the removal creates a gap, or if remaining chapters need renumbering
- Discovered a fact that contradicts what was already drafted → stop, correct the plan, then rewrite
- Chapter boundaries are fuzzy → draw the line explicitly before writing

This applies to both single-chapter additions and full-document creation. The cost of rewriting a paragraph is low; the cost of rewriting a chapter because structure was wrong is high.

## Common Pitfalls

1. **Using `skill_manage(action='create')` for an in-repo skill.** It writes to `~/.hermes/skills/`, not the repo tree. Use `write_file` for in-repo creation.

2. **Writing protocol/project attribution from memory.** If the document covers a specific open-source project or standard (e.g. A2A, MCP, etc.), verify the actual origin/maintainer before writing. "Anthropic推出 A2A" vs "Google开发→Linux Foundation托管" is a fact-level error that invalidates the document. When in doubt, check the official spec page (e.g. a2a-protocol.org, modelcontextprotocol.io/specification).

3. **Leading whitespace before `---`.** The validator checks `content.startswith("---")`; any leading blank line or BOM fails validation.

3. **Description too generic.** Peer descriptions start with "Use when ..." and describe the *trigger class*, not the one task. "Use when debugging X" > "Debug X".

4. **Forgetting the author/license/metadata block.** Not validator-enforced, but every peer has it; omitting makes the skill look half-finished.

5. **Writing a skill that duplicates a peer.** Before creating, `ls skills/<category>/` and open 2-3 peers. Prefer extending an existing skill to creating a narrow sibling.

6. **Expecting the current session to see the new skill.** It won't. The skill loader is initialized at session start. Verify in a fresh session or via `skill_view` using the exact path.

7. **Linking to skills that don't exist in-repo.** `related_skills: [some-user-local-skill]` works for you but breaks for other clones. Prefer only in-repo links.

## Verification Checklist

- [ ] File is at `skills/<category>/<name>/SKILL.md` (not in `~/.hermes/skills/`)
- [ ] Frontmatter starts at byte 0 with `---`, closes with `\n---\n`
- [ ] `name`, `description`, `version`, `author`, `license`, `metadata.hermes.{tags, related_skills}` all present
- [ ] Name ≤ 64 chars, lowercase + hyphens
- [ ] Description ≤ 1024 chars and starts with "Use when ..."
- [ ] Total file ≤ 100,000 chars (aim for 8-15k)
- [ ] Structure: `# Title` → `## Overview` → `## When to Use` → body → `## Common Pitfalls` → `## Verification Checklist`
- [ ] `related_skills` references resolve in-repo (or are explicitly OK to be user-local)
- [ ] `git add skills/<category>/<name>/ && git commit` completed on the intended branch
