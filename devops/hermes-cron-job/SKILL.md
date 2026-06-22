---
name: hermes-cron-job
description: Hermes cron job 设计模式：prompt 结构、通知行为配置（成功静默/失败告警）、常见陷阱。用于创建、修改或诊断 Hermes 定时任务时加载。
triggers:
  - 创建定时任务 prompt
  - 修改定时任务 deliver 配置
  - 定时任务执行成功但仍收到推送消息
  - 想让定时任务失败时才发通知
  - 参考其他定时任务的 prompt 设计
---

# Hermes Cron Job 设计模式

## 核心机制：deliver 与 [SILENT]

| 配置 | 成功时 | 失败时 |
|---|---|---|
| `deliver: origin` | 系统推送 agent 完整输出 → 收到消息 | 系统推送 agent 完整输出 → 收到消息 |
| `deliver: local` | 不推送 → 静默 | 不推送 → 静默（系统错误报告由 scheduler 发送） |
| `deliver: feishu:oc_xxxxxxxx` | 推送至指定飞书群 → 收到消息 | 推送至指定飞书群 → 收到消息 |
| `deliver: origin` + prompt 输出 `[SILENT]` | 系统抑制推送 → 静默 | agent 正常输出 → 系统推送 |
| `deliver: feishu:oc_xxx` + prompt 输出 `[SILENT]` | 系统抑制推送 → 静默 | agent 正常输出 → 推送到飞书群 |

**关键区别**：`[SILENT]` 对 `local` 无意义（local 已静默）；对 `feishu:oc_xxx` 同样生效（成功时静默，失败时推送）。

**静默规则格式（必须精确）**：
```
静默规则： 完成后输出 [SILENT] 终止。
```
- 冒号后有空格
- `[SILENT]` 单独成行，前后无其他内容
- 格式错误会导致静默失效，任务成功仍会推送消息（本 Session 实测根因）

## 成功静默模式（推荐）

prompt 末尾加一行（**注意格式**：静默规则前无额外空行，直接跟在代码块或正文后面）：

```
静默规则： 完成后输出 [SILENT] 终止。
```

示例（参考 AI 新闻采集 prompt）：
```

⚠️ 注意：
- 必须用 `+update` 而非 `+import`
- 必须指定 `--doc-format xml`
- XML 文件需包含完整根节点

静默规则： 完成后输出 [SILENT] 终止。
```

当 agent 成功完成任务后，输出 `静默规则： 完成后输出 [SILENT] 终止。`，系统检测到该字符串后自动抑制 deliver 推送。

**验证方法**：检查 `~/.hermes/cron/output/<job_id>/<timestamp>.md`，其中 `## Response` 部分应为 `[SILENT]`。

## 失败告警模式

在 prompt 里加错误处理块：

```
**错误处理：失败时发飞书群通知**
如果任何步骤出错，捕获错误并发送通知：
lark-cli im +messages-send --chat-id "oc_xxxxxxxx" --text "🚨 定时任务执行出错

📌 任务：<任务名>
⏰ 时间：<当前时间>
❌ 阶段：<git pull/目录检查/文件同步/飞书写入/未知>
📝 错误：<具体错误描述>"
```

然后在 prompt 末尾加上 `静默规则： 完成后输出 [SILENT] 终止。`。

## deliver 配置对比

| 使用场景 | deliver 设置 |
|---|---|
| 需要区分成功静默/失败告警 | `feishu:oc_xxx` + prompt 末尾 `静默规则： 完成后输出 [SILENT] 终止。` + 失败告警逻辑 |
| 完全静默（不需要任何通知） | `local` + 脚本内错误主动发消息 |
| 始终推送完整报告 | `origin`（默认） |

## 陷阱

- **静默规则格式必须精确**：正确的格式是 `静默规则： 完成后输出 [SILENT] 终止。`，`[SILENT]` 必须单独成行且前后无其他内容。曾经用的 `→ 完成：[SILENT]` 格式系统无法识别，导致成功执行但仍然推送消息。本 Session 中用户问「为什么任务执行成功了还会发消息」，根因即在此——job fa294bf7d232 的 prompt 里用的是旧格式。验证方法：检查 output 文件中 `## Response` 部分是否为独立的 `[SILENT]`（无其他前缀/后缀）。
- **prompt 结尾 `→ 完成：[SILENT]` 但 `deliver: local`**：`[SILENT]` 对 `local` 无意义（local 已静默），两者同时存在时 `[SILENT]` 是冗余的。
- **失败时只在 prompt 里写"发消息"但没有 lark-im skill**：agent 没有发消息工具，告警失效。
- **4个内容任务全部漏加静默规则**：2026-05-31 修复前，YouTube AI 早/晚、Bilibili AI、Bilibili 全站 四个 cron job 全部缺少静默规则，导致每次成功执行都向用户推送完整报告。教训：任何内容类任务必须在 prompt 末尾加 `静默规则： 完成后输出 [SILENT] 终止。`。
- **参照系偏差**：修改 cron job 前先查现有任务的 prompt 设计，确保风格一致。本会话中用户明确说"不要参考 GitHub 任务"——因为 GitHub 同步用的是 `deliver: local`，和内容任务的 `deliver: origin` 是两种不同机制，不能互相参照。
- **内容类 prompt 缺少输出格式规范**：如果 prompt 只说"写入飞书文档"但没规定文档标题格式（如 `{任务名} · {日期} · {档期}`）和内容结构（如 h1/h2 层级 + Markdown 列表 vs lark-table），agent 会自由发挥导致格式不一致。**教训**：Bilibili 两个任务的 prompt 未指定标题格式，agent 用了固定标题（无日期）和 lark-table 格式，与 YouTube 档的动态标题 + Markdown 列表完全不同。所有写入飞书的 prompt 必须显式规定：标题模板、h1/h2 结构、内容格式。

## 修改现有 cron job 的流程

1. `cronjob action=list` 列出所有任务，找到 job_id
2. **核对 doc token**：用 `lark-cli docs +fetch --doc <token>` 确认目标文档存在且有内容（标题为 "Untitled" 意味着是空文档，需要重新创建或更换 token）
3. 读取 prompt 全文（从 `~/.hermes/cron/jobs.json`），确认当前静默规则格式
4. **展示当前状态**：修改前先展示 prompt/deliver 配置，说明可能的选项和后果，再问用户确认。不要在用户仅提问时就主动执行修改
5. 修改：用 `cronjob action=update` 改 prompt（prompt 是完整内容，不是 diff）
6. 测试：用 `cronjob action=run job_id=xxx` 触发一次（`cron run` 是异步的，无串行等待机制，只能并行触发多个）
7. 验证：**检查 output 文件中 `## Response` 部分是否为 `[SILENT]`**。方法：
   ```bash
   # 等待足够时间后（如 sleep 90），检查各任务最新 output
   ls -lt /Users/xiesg/.hermes/cron/output/<job_id>/ | head -2
   cat /Users/xiesg/.hermes/cron/output/<job_id>/<latest>.md | grep -A1 "## Response"
   ```
   同时用 `lark-cli docs +fetch --doc <token>` 验证飞书文档内容（标题、格式）是否符合规范。
   - output 文件最新时间无变化 → 任务尚未完成，继续等待（每次 sleep 60 后重查）
   - output 有新文件但 `## Response` 非 `[SILENT]` → 静默规则未生效，需检查 prompt 末尾格式
   - 文档 title 为 "Untitled" → doc token 指向空文档，需重建

## 飞书文档写入 prompt 的格式规范模板

内容类 cron job（视频推送、新闻采集等）写入飞书文档时，**必须在 prompt 中显式规定**文档标题、目录结构、内容格式。否则 agent 自由发挥会导致：标题无日期、用 lark-table 而非列表、格式跨任务不一致。

**prompt 中应包含的格式规范段（加在步骤2之后）：**

```
**文档格式规范（必须严格遵守）：**
- 文档标题：`<title>XXX · 档期</title>`，固定不变
- 一级标题：`<h1>XXX · {当日日期} · 档期</h1>`
- 内容使用 DocxXML 格式，不使用 lark-table、callout
- 视频条目用 `<ol><li seq="auto">` 有序列表
- 目录结构：
  <h2>分类名 TOP N</h2>
  每条：<a href="链接">标题</a> ｜字段1：xxx ｜字段2：xxx
```

**标题格式设计决策（用户确认的规则）：**
- 文档标题（`<title>`）固定不变，不包含日期
- 一级标题（`<h1>`）带当日日期，如 `Bilibili AI热门视频 · 2026-05-31`
- 每次执行 overwrite 整篇文档

**四个视频推送任务的设计（2026-05-31 确认）：**

| 任务 | `<title>` | `<h1>` 模板 |
|------|-----------|-------------|
| YouTube AI 早间档 | `YouTube AI热门视频 · 早间档` | `YouTube AI热门视频 · {日期} · 早间档` |
| YouTube AI 晚间档 | `YouTube AI热门视频 · 晚间档` | `YouTube AI热门视频 · {日期} · 晚间档` |
| Bilibili AI 热门 | `Bilibili AI热门视频` | `Bilibili AI热门视频 · {日期}` |
| B站全站热门 | `B站全站热门视频` | `B站全站热门视频 · {日期}` |

## 常见陷阱

- **空文档陷阱**：飞书文档 token 有效但文档内容为空（标题为 "Untitled"），通常是早期 `+import` 导入失败留下的空壳。**所有内容任务都应逐个验证 doc token**：`lark-cli docs +fetch --doc <token>` 检查 title，不为 "Untitled" 才算正常。doc token 写在 prompt 里，肉眼难以发现，验证必须用 CLI 查询。
- **飞书文档 URL 格式陷阱**：`docs +create` 创建的是 docx 类型文档，链接应为 `feishu.cn/docx/{token}`，不是 `feishu.cn/wiki/{token}`。给用户分享链接时用错格式会导致 404。验证方法：`lark-cli wiki +get --token <token>` 对非 wiki 文档会失败。
- **飞书文档链接获取方式**：`lark-cli docs +create` 的返回 JSON 里**直接包含完整的 `data.document.url` 字段**（如 `https://xxx.feishu.cn/docx/doxcnXXX`）。cron 任务的通知模板中，不需要硬编码域名或自己构造链接——直接指示 agent 从 `lark-cli docs +create` 的返回结果中提取 `data.document.url` 字段即可。**错误做法**：prompt 里写死 `https://xxx.feishu.cn/docx/<doc_token>` 模板让 agent 替换。**正确做法**：prompt 里写"从 lark-cli docs +create 的返回结果中提取 data.document.url 字段"。
- **lark-cli drive +delete flag**：删除文档用 `--file-token` 而非 `--token`，即 `lark-cli drive +delete --file-token <token> --type docx --yes`。
- **prompt 无收敛指令 + `deliver: origin`**：agent 正常输出完整报告，系统直接推送，用户收到"成功时还发消息"的困扰。**这是最常见的配置错误**，几乎所有新建内容类 cron job 都会犯。
- **用户问"列出 cron + 对应飞书 doc"时不要扩展成覆盖度研究**（2026-06-14 session 实测）。用户原话："你有哪些定时任务，及其对应飞书文档，请列出来。"——期望输出是一张表（任务名 / 调度 / 写入 doc / 状态）。错误做法：跑去分析"3 个 doc 哪些我读过 / 没读过"、"哪些 task 写的是 user drive 不是 bot drive"、"4 个任务是否合并写到同一 doc"，把这些做成覆盖度矩阵 + 多个跟进问。**正确动作**：`cronjob list` 拿任务，再 `lark-cli drive files list` 拿 bot 名下 doc 列表，做最小化映射表。**只标已知 + 标未知**（如"早间档 doc 不在 bot drive，无法直接获取 token"），不补全未知也不发起澄清问。**判别规则**：用户问"列 X" → 列 X。涉及覆盖度 / 数据完整性 / 多源对账等是**后续问题**，不是当前问题的隐含任务。触发用户"重来"硬停止信号的高发场景。
- **多任务修改应逐个确认**：用户偏好"逐个设计、逐个确认、逐个修改"，不要一次性全部改完再汇报。每个步骤都需要用户确认的闭环。
- **查找 cron 任务对应飞书 doc token 的标准动作（2026-06-14 实测）**：用户问"列出定时任务及其飞书文档"时，**直接读 `~/.hermes/cron/jobs.json` 的 prompt 全文找 doc token**。`cronjob` 工具的 `prompt_preview` 字段被截断（几百字符），doc token 经常出现在截断位置之后看不见。**正确步骤**：
  1. `hermes cron list`（或 `cronjob action=list`）拿任务清单
  2. `cat ~/.hermes/cron/jobs.json | python3 -c "..."` 打印每个 job 的 prompt 完整原文
  3. 在 prompt 里找 `飞书文档Token <token>` 模式（中文"Token" + 27 字母数字 token）
  4. **不要**用通用正则 `\b[A-Za-z0-9_-]{13,30}\b` 匹配——因为 token 紧贴中文"Token"前后无词边界，**正则 `\b` 失败 0 匹配**。用字符串包含已知前缀（EbH / HhyM / Virb / Tcjb）做检查，或用 `re.findall(r'[A-Za-z][A-Za-z0-9_-]{20,30}', prompt)` 不用词边界
  5. **不要**绕远路去翻 `lark-cli drive files list`（只能列 bot 名下 doc，看不到 user 名下 doc）——bot drive 列表不全，与 cron prompt 里的 doc token 经常对不上
  6. **不要**翻 `~/.hermes/cron/output/` 的 XML 文件（XML 是步骤 1 视频内容，不含 doc token）
  7. **不要**翻 `lark-cli wiki spaces list`（cron 任务不写 wiki）
- **4 个视频推送任务（2026-05-31 确认）的真实 doc token 表**（写到这里防止再翻一遍 jobs.json）：
  | 任务 | job_id | doc token | doc 标题 |
  |------|--------|-----------|----------|
  | YouTube AI 早间档 | fa294bf7d232 | `EbHDdKARYo4vEExQiNGc3qiGnSe` | YouTube AI热门视频 · 早间档 |
  | YouTube AI 晚间档 | d470b5d9b593 | `HhyMdusqdoVcW9xLyd2c2Yc2nnf` | YouTube AI热门视频 · 晚间档 |
  | Bilibili AI 热门 | 1f4c7fb989aa | `Virbd3YyBoYK9XxqaZOccEGRnio` | Bilibili AI热门视频 |
  | B站全站热门 | 0e9f3cb36fe6 | `TcjbdsX0ToprvCxXPbQcbLqknTq` | B站全站热门视频 |
- **cron 环境下 `~` 解析路径与真实路径不一致**：cron 触发的 agent 会话中 `$HOME=/Users/xiesg/.hermes/home`（沙箱化），导致 `~/github/...` 和 `~/.hermes/skills/` 解析到一个**空的、非 git 的镜像目录**，而非真实的 `/Users/xiesg/github/...` 和 `/Users/xiesg/.hermes/skills/`。症状：`git status` 报 `fatal: not a git repository`、`~/.hermes/skills/` 只有 `.archive/`、`diff -rq` 比对失败。**解决方法**：所有 cron job 的 prompt 里涉及文件操作的路径必须用**绝对路径**（如 `/Users/xiesg/github/my-hermes-skills`），禁用 `~` 和相对路径。第一步先用 `echo $HOME && pwd && ls <绝对路径>` 验证目标真实存在。
- **用户说"先不要看记忆"= 禁止先套记忆给答案，必须实时查证（2026-06-14 实测）**：用户原话"先不要看记忆。先列举出定时任务，并从定时任务中找出他写入了哪个飞书文档？"——明确要求**实时查证**，不要套用历史 session 记忆里的"4 个 doc 都存在 / 4 个 doc 都是 docx 类型"等结论。**正确动作链**：
  1. **不引用 `MEMORY.md` / `USER.md` 任何内容**——这些是历史 session 的结论，可能已过期
  2. 实时跑：`hermes cron list` → `cat ~/.hermes/cron/jobs.json | python3` → 打印每个 prompt 全文
  3. 在 prompt 原文里**找 doc token**（见上一条 pitfall 的标准动作）
  4. 拿到的 token 是当前真实状态，比记忆里"我之前以为"的更可靠
  5. **记忆里的内容可作背景参考**（如 doc 标题命名规范），但**不能作为当前事实**
  
  **判别规则**：用户说"不要看记忆"= 强制走实时查证 = **信任磁盘/CLI > 信任记忆**。记忆里的"4 个视频任务均为 docx"是历史观察，**不能代替今天的实时 doc token 拉取**。