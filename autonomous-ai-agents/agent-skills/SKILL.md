---
name: agent-skills
description: "Create, install, discover, and share Agent Skills — the open standard for extending AI coding agents (Claude Code, Cursor, Windsurf, Codex, etc.). Skills live in .claude/skills/ or ~/.claude/skills/ as SKILL.md directories. Covers: Agent Skills specification, skills.sh ecosystem, Anthropic's official skill library, Claude Code skill extensions, best practices, and distribution."
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [Claude-Code, Agent-Skills, Skills-Standard, Claude-Code-Config, Prompt-Engineering]
    related_skills: [claude-code]
---

# Agent Skills — Create, Discover, Share

Agent Skills is an open standard for extending AI coding agents with reusable skill packages. A skill is a directory containing a `SKILL.md` file with YAML frontmatter (name, description, compatibility) and Markdown instructions the agent follows when the skill activates.

**Triggers:** 用户问如何创建/查找/安装/分享 skills；用户问 Claude Code 的 `.claude/skills/` 目录；用户问 skills.sh、agent-skills、agent skills 创建规范；用户提到 "create a skill"、"安装 skill"、"skills.sh"。

---

## 一、Agent Skills 规范（agentskills.io/specification）

### 目录结构

```
skill-name/
├── SKILL.md              # 必须：元数据 + 指令
├── scripts/              # 可选：Agent 可执行脚本
├── references/           # 可选：参考文档
├── assets/               # 可选：模板、图片等
└── ...
```

### SKILL.md 格式

两部分：**YAML frontmatter** + **Markdown 正文**。

```yaml
---
name: skill-name                    # 必须：与目录名相同
description: What this skill does and when to use it.  # 必须：1-1024 字符
license: Apache-2.0                  # 可选
compatibility: Requires Python 3.14+ and uv  # 可选
metadata:                            # 可选
  author: example-org
  version: "1.0"
allowed-tools: Bash(git:*) Read      # 可选（实验性）
---
```

**name 字段规范：**
- 1-64 字符；仅 unicode 小写字母 (a-z) 和连字符 (-)
- 禁止：以连字符开头/结尾；连续 `--`
- 必须与父目录名匹配

**description 字段规范：**
- 1-1024 字符
- 应描述技能**做什么**和**何时使用**，包含帮助 Agent 识别相关任务的关键词

**body（正文）：** Agent 执行任务所需的指令，无格式限制。建议包含：逐步指令、输入输出示例、常见边界情况。

### 可选目录

| 目录 | 用途 | 说明 |
|------|------|------|
| `scripts/` | 可执行脚本 | Python/Bash/JS；自包含，含错误处理 |
| `references/` | 参考文档 | 按需加载；保持专注；较小 = 更少 token |
| `assets/` | 静态资源 | 模板、图片、数据文件 |

### 渐进披露（Progressive Disclosure）

| 层级 | 加载时机 | Token |
|------|----------|-------|
| 元数据（name + description） | 所有技能启动时 | ~100 |
| 完整 SKILL.md 正文 | 技能激活时 | <5000 推荐 |
| references/、scripts/、assets/ | 需要时 | 按需 |

**建议：** 将主 SKILL.md 保持在 500 行以内。

### 验证工具

```bash
skills-ref validate ./my-skill
```

检查 frontmatter 有效性和命名约定。

---

## 二、skills.sh 生态（skills.sh）

### 核心资源

| 资源 | URL |
|------|-----|
| 技能目录/排名 | https://skills.sh |
| skills.sh API | https://skills.sh/api/v1/ |
| skills.sh CLI 文档 | https://skills.sh/docs/cli |
| skills.sh FAQ | https://skills.sh/docs/faq |
| Anthropic 官方技能库 | https://github.com/anthropics/skills |

### skills.sh API（Base: `https://skills.sh/api/v1/`）

所有端点通过 HTTPS 返回 JSON。认证可选（API key via `Authorization: Bearer` 获取更高限额：600/min vs 60/min）。

| 端点 | 说明 |
|------|------|
| `GET /api/v1/skills?view=all-time\|trending\|hot` | 分页排行榜 |
| `GET /api/v1/skills/search?q=<query>` | 按名称/描述搜索 |
| `GET /api/v1/skills/curated` | 官方策划的第一方技能 |
| `GET /api/v1/skills/{source}/{skill}` | 技能详情 + 完整文件树 |
| `GET /api/v1/skills/audit/{source}/{skill}` | 安全审计结果 |

```bash
# 搜索技能
curl "https://skills.sh/api/v1/skills/search?q=react%20native&limit=5"

# 获取技能详情（含文件内容）
curl "https://skills.sh/api/v1/skills/anthropics/skills/skill-creator"

# 安全审计
curl "https://skills.sh/api/v1/skills/audit/anthropics/skills/skill-creator"
```

### 安装 CLI

```bash
# 安装完整集合
npx skills add vercel-labs/agent-skills

# 安装特定技能
npx skills add anthropics/skills/skill-creator
npx skills add vercel-labs/agent-skills/next-js-development

# 禁用遥测
DISABLE_TELEMETRY=1
```

skills.sh 的 `npx skills add` 下载技能到本地，**但 Agent 如何发现它们取决于各 Agent**。

---

## 三、Claude Code 技能扩展

Claude Code 遵循 Agent Skills 规范，并扩展了以下特性。

### 技能存放位置

| 位置 | 路径 | 适用范围 |
|------|------|----------|
| 企业托管 | 托管设置中指定 | 所有用户 |
| 个人 | `~/.claude/skills/<skill-name>/SKILL.md` | 所有项目 |
| 项目 | `.claude/skills/<skill-name>/SKILL.md` | 仅当前项目 |
| 插件 | `<plugin>/skills/<skill-name>/SKILL.md` | 插件启用位置 |

优先级：企业 > 个人 > 项目。Plugin 技能使用 `plugin-name:skill-name` 命名空间，不会冲突。

### Claude 特有 Frontmatter 字段

| 字段 | 说明 |
|------|------|
| `disable-model-invocation: true` | 阻止 Claude 自动触发；必须显式用 `/skill-name` 调用 |
| `allowed-tools` | 空格分隔的预批准工具列表 |
| `context: fork` | 技能在子代理中运行（保持主对话干净） |
| `when_to_use` | 额外触发上下文（追加到 description） |
| `argument-hint` | 自动完成时的参数提示 |
| `arguments` | 命名位置参数，供正文中的 `$name` 替换 |

### Claude 特有目录布局

```
my-skill/
├── SKILL.md              # 主指令（必需）
├── template.md          # Claude 填充的模板
├── examples/
│   └── sample.md         # 示例输出
└── scripts/
    └── validate.sh       # Claude 可执行脚本
```

### 动态上下文注入

Claude Code 特有：`!` 前缀执行命令并替换输出到技能正文：

```markdown
## Current changes

!`git diff HEAD`

## Instructions

Summarize the changes above in bullet points...
```

### 技能发现机制

- **自动发现：** 启动时读取所有技能的 name + description（~100 token）；描述匹配时激活完整 SKILL.md
- **嵌套目录：** 在子目录工作时（如 `packages/frontend/`），自动发现 `packages/frontend/.claude/skills/`
- **实时变更：** 添加/编辑/删除技能立即生效；新顶级目录需重启

---

## 四、创建技能快速入门

### 最简技能（5 步）

**第一步：创建目录**
```bash
mkdir -p ~/.claude/skills/my-skill
```

**第二步：编写 SKILL.md**
```yaml
---
name: my-skill
description: What this skill does. Use when user asks about X.
---

## Instructions

Step 1: ...
Step 2: ...
```

**第三步：测试**
```bash
# 显式调用
/claude --skill my-skill

# 或让 Claude 自动触发（描述匹配时）
```

**第四步：发布到 GitHub**
1. 创建公开仓库
2. 添加 `<skill-name>/SKILL.md`
3. 写 README
4. 用户通过 `npx skills add owner/repo` 安装

**第五步：验证**
```bash
skills-ref validate ./my-skill
```

### Claude Code 技能创建示例（带动态上下文）

```bash
mkdir -p ~/.claude/skills/summarize-changes
```

```yaml
# ~/.claude/skills/summarize-changes/SKILL.md
---
description: Summarizes uncommitted changes and flags anything risky.
             Use when the user asks what changed, wants a commit message,
             or asks to review their diff.
---

## Current changes

!`git diff HEAD`

## Instructions

Summarize the changes in bullet points, then list risks
such as missing error handling or tests that need updating.
If the diff is empty, say there are no uncommitted changes.
```

---

## 五、最佳实践

### 从真实专业知识开始

避免只给 LLM 通用知识让它生成技能。好的技能来源：
- **从实际任务提取：** 有效的步骤序列、纠正内容、输入输出格式、项目特定上下文
- **从项目文件综合：** 内部文档、runbook、API 规范、代码审查评论、版本控制历史
- **用真实执行迭代：** 对比 Agent 执行轨迹，识别重复逻辑 → 打包成脚本

### 控制校准

| 场景 | 风格 |
|------|------|
| 操作不关键或 Agent 知道如何处理 | 描述性（"Use standard error handling"） |
| 操作脆弱、一致性重要、必须遵循特定顺序 | 指令性（明确命令和步骤） |

### 提供默认值，不是菜单

```markdown
# 避免
You can use pypdf, pdfplumber, PyMuPDF...

# 推荐
Use pdfplumber for text extraction.
For OCR, use pdf2image with pytesseract instead.
```

### 偏好过程而非声明

```markdown
# 特定答案（仅对当前任务有用）
Join orders to customers on customer_id, filter region='EMEA'...

# 可复用方法
1. Read schema from references/schema.yaml
2. Join tables using the _id foreign key convention
3. Apply filters as WHERE clauses
4. Format as markdown table
```

### Gotchas 部分（最高价值）

```markdown
## Gotchas

- The `users` table uses soft deletes. Queries must include
  WHERE deleted_at IS NULL or results include deactivated accounts.
- The user ID is `user_id` in the DB, `uid` in the auth service,
  and `accountId` in billing API. All three refer to the same value.
```

### 输出格式模板

当需要特定格式输出时，提供模板比散文描述更可靠。

### 验证循环

```markdown
1. Make your edits
2. Run validation: python scripts/validate.py output/
3. If validation fails, fix and re-validate
4. Only proceed when validation passes
```

### 计划-验证-执行（批量/破坏性操作）

```markdown
1. Create plan: python scripts/analyze.py input → form_fields.json
2. Create values: field_values.json
3. Validate: python scripts/validate_fields.py form_fields.json field_values.json
4. If validation fails, revise field_values.json and re-validate
5. Execute: python scripts/fill_form.py input.pdf field_values.json output.pdf
```

---

## 六、Anthropic 官方技能库（github.com/anthropics/skills）

包含 18K+ stars 的官方技能集合：

| 技能 | 说明 | 安装量 |
|------|------|--------|
| `frontend-design` | 前端设计系统 | 381.8K |
| `skill-creator` | 创建和改进技能 | 190.8K |
| `docx` | Word 文档 | - |
| `pptx` | PowerPoint | - |
| `pdf` | PDF 处理 | - |
| `xlsx` | Excel 电子表格 | - |
| `claude-api` | Claude API 使用 | - |
| `algorithmic-art` | 算法艺术生成 | - |
| `mcp-builder` | MCP 服务器构建 | - |
| `webapp-testing` | Web 应用测试 | - |

每个技能目录通常包含：`SKILL.md` + `agents/` + `references/` + `scripts/` + `assets/`。

**使用 skill-creator 技能：**
```
@skill-creator Create a skill that does X
```

---

## 七、故障排除

| 问题 | 排查 |
|------|------|
| 技能不触发 | 文件位置正确？description 描述了触发场景？name 与目录名匹配？设置了 `disable-model-invocation`？ |
| 技能触发过于频繁 | description 过于宽泛？添加具体触发短语到 `when_to_use` 或设置 `disable-model-invocation` |
| 技能描述被截断 | description + when_to_use 被截断为 1536 字符；最重要信息放前面 |
| 技能内容丢失 | SKILL.md 正文保持在 5000 token 以内；大型参考放 references/ |

---

## 八、相关资源

- [Agent Skills 规范](https://agentskills.io/specification)
- [Agent Skills 文档站](https://agentskills.io)
- [skills.sh](https://skills.sh) | [API](https://skills.sh/docs/api) | [CLI](https://skills.sh/docs/cli) | [FAQ](https://skills.sh/docs/faq)
- [anthropics/skills](https://github.com/anthropics/skills)
- [Claude Code Skills 文档](https://code.claude.com/docs/en/skills)
- [Agent Skills Discord](https://discord.gg/MKPE9g8aUy)
