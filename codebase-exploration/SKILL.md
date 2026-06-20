---
name: codebase-exploration
version: 1.0.0
description: Codebase exploration and explanation toolkit — inspect repo metrics (LOC, languages, ratios) with pygount and explain architectures/designs to a programmer audience. Use when asked to "explain this codebase", "read the source", "walk through the architecture", or "how big is this repo".
category: software-development
triggers:
  - 介绍一下这个项目
  - 阅读源码
  - 讲解架构
  - codebase introduction
  - architecture overview
  - repo size
  - how big is this repo
  - LOC count
---

# Codebase Exploration & Explanation

Two related but distinct skills for working with an unfamiliar codebase:

1. **Inspection (metrics)** — use `pygount` to get LOC, language breakdown, code/comment ratios
2. **Communication (explanation)** — explain the codebase's design, architecture, and components to a programmer audience

Both are essential for any "investigate this repo" task: inspect first to know the size/shape, then communicate the result.

---

## §1. Inspect: pygount Metrics

When the user asks "how big is this repo" / "what languages" / "LOC" / "code-to-comment ratio", use `pygount`.

### Prerequisites

```bash
pip install --break-system-packages pygount 2>/dev/null || pip install pygount
```

### Basic Summary (Most Common)

```bash
cd /path/to/repo
pygount --format=summary \
  --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,.eggs,*.egg-info" \
  .
```

**IMPORTANT:** Always use `--folders-to-skip` to exclude dependency/build directories, otherwise pygount will crawl them and take a very long time or hang.

### Folder Exclusions by Project Type

```bash
# Python projects
--folders-to-skip=".git,venv,.venv,__pycache__,.cache,dist,build,.tox,.eggs,.mypy_cache"

# JavaScript/TypeScript projects
--folders-to-skip=".git,node_modules,dist,build,.next,.cache,.turbo,coverage"

# General catch-all
--folders-to-skip=".git,node_modules,venv,.venv,__pycache__,.cache,dist,build,.next,.tox,vendor,third_party"
```

### Filter by Language

```bash
pygount --suffix=py --format=summary .
pygount --suffix=py,yaml,yml --format=summary .
```

### Detailed File-by-File Output

```bash
pygount --folders-to-skip=".git,node_modules,venv" .
pygount --folders-to-skip=".git,node_modules,venv" . | sort -t$'\t' -k1 -nr | head -20
```

### Output Formats

- `pygount --format=summary .` — summary table (default recommendation)
- `pygount --format=json .` — JSON for programmatic use
- `pygount --format=summary . 2>/dev/null` — pipe-friendly: Language, file count, code, docs, empty, string

### Interpreting Results

Summary table columns:
- **Language** — detected programming language
- **Files** — number of files of that language
- **Code** — lines of actual code (executable/declarative)
- **Comment** — lines that are comments or documentation
- **%** — percentage of total

Special pseudo-languages: `__empty__`, `__binary__`, `__generated__`, `__duplicate__`, `__unknown__`.

### Inspection Pitfalls

1. **Always exclude .git, node_modules, venv** — without `--folders-to-skip`, pygount will crawl everything and may take minutes or hang on large dependency trees.
2. **Markdown shows 0 code lines** — pygount classifies all Markdown content as comments, not code.
3. **JSON files show low code counts** — pygount may count JSON lines conservatively. For accurate JSON line counts, use `wc -l` directly.
4. **Large monorepos** — consider using `--suffix` to target specific languages rather than scanning everything.

---

## §2. Communicate: Explaining to a Programmer Audience

When asked to "explain this codebase" / "walk through the architecture" / "introduce the project":

### Core Principle

**Programmers want direct technical description, not analogies or metaphors.**

When explaining a codebase:
- Say what it **is**, what it **does**, and how components **relate**
- Use the actual terminology (CRD, reconciler, homeserver, etc.)
- Draw the component relationship diagram
- Give concrete API names, protocol names, data structures

**Do not** start with: "Imagine a team...", "Like a factory...", "Think of it as..."

### Recommended Sequence (Default)

```
1. One-line定位 — 做什么的
2. Component inventory — 核心组件列表 + 技术栈
3. Component relationships — 组件关系图（ASCII 或文字）
4. Key data flows — 关键执行流程（数据怎么走）
5. Important design decisions — 关键约束和设计决策
```

### User-preferred variant: Concepts → Architecture → Design → Mechanisms

When the user explicitly asks for a structured walkthrough ("从核心概念说起，再说架构、设计理念、工作机制"), use this order instead:

1. **核心概念** — Key entities, identities, terminology (what things *are*)
2. **系统架构** — Component diagram + layer separation (how things *connect*)
3. **设计理念** — Why these choices: tradeoffs, constraints, security model (why it's *designed this way*)
4. **工作机制** — Step-by-step flows for key operations (how things *work in practice*)

This maps to What → Structure → Why → How, which the user finds more natural than the default What → Inventory → Relationships → Flows → Decisions order.

### What to Include

| Item | Why |
|------|-----|
| 一句话定位 | 快速建立正确的心智模型 |
| 组件列表 + 技术栈 | 让读者知道代码库里有什么 |
| 组件关系（谁↔谁、用什么协议通信） | 核心结构 |
| 关键 API / 数据结构 | 可操作的技术细节 |
| 关键约束（如 Worker 无状态） | 理解设计决策的前提 |

### What to Skip

- 类比/比喻（包工头、工厂、乐队…）
- 过多的背景故事
- 实现细节在前两步就展开
- 列出所有文件、所有函数

### Audience Signals

**程序员默认**：
- 不要比喻
- 要技术术语准确
- 先结构后细节
- 可以直接上代码片段 / API endpoint

**如果用户明确说"举个例子"、"举个比喻"**，那例外。

### Examples

#### Good (explaining HiClaw)

> HiClaw is a multi-Agent orchestration system. Manager coordinates Workers, Human supervises via Matrix.
> Components: Controller (Go Operator, K8s CRD) → creates Worker containers via Docker/K8s API.
> Manager (OpenClaw/CoPaw runtime) ↔ Workers via Matrix rooms.
> MinIO stores workspace, Higress routes LLM traffic.
> Workers are stateless — state lives in MinIO.

#### Bad (what to avoid)

> "HiClaw is like a software team where the Tech Lead assigns tasks and engineers execute them..."
> (This is the kind of framing the user explicitly rejected.)

---

## §3. Workflow: Combining Both

For a complete "investigate this repo" task:

1. **Inspect first** with pygount:
   ```bash
   pygount --format=summary --folders-to-skip=".git,node_modules,venv,.venv,__pycache__" /path/to/repo
   ```
   Report the size, language breakdown, and any surprising skews.

2. **Map components** by `ls`, `tree -L 2`, or `find` to identify the main packages/dirs.

3. **Read key files** with `read_file`:
   - Top-level `README.md`, `ARCHITECTURE.md`, `AGENTS.md`
   - Entry-point files (main, server, app)
   - Config files (pyproject.toml, package.json, go.mod, Cargo.toml)

4. **Communicate the result** using the sequence from §2, with language grounded in the actual terminology found.

## Related

- `github-repo-management` — clone and manage the repo as a whole
- `architecture-diagram` — for generating visual diagrams once you have a model
- `simplify-code` — for reviewing recent changes
