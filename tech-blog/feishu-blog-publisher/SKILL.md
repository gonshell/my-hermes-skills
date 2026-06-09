---
name: feishu-blog-publisher
version: 1.1.0
description: "将 Markdown 技术博客文章自动转换为飞书富格式文档发布。支持 Callout/Table/Mermaid/HR 等富块转换、图表意图识别（按内容特征自动选择 Mermaid/PlantUML/表格），调用 lark-cli 创建文档并写入。依赖 lark-doc skill。"
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [feishu, blog, markdown, publisher, lark, docx-xml]
    related_skills: [lark-doc, lark-whiteboard, tech-blog, reader-persona-feedback, narrative-theme-generator, writing-style-extractor, chapter-consistency-checker, review-checklist-generator]
references:
  - references/md-to-docx-conversion.md
---

# 飞书博客发布器（feishu-blog-publisher）

## 概述

将 Markdown 格式的技术博客文章自动转换为飞书云文档（DocxXML 富格式），并通过 `lark-cli docs +create` 发布到飞书。核心能力：

1. **Markdown → DocxXML 转换**：逐元素映射，支持标题、段落、列表、代码块、引用、表格、分割线、图片、链接等
2. **图表意图识别**：扫描内容语义特征，自动判断应使用 Mermaid 流程图、时序图、PlantUML 类图，还是表格/分栏展示
3. **飞书富格式增强**：自动插入 Callout（提示框）、分栏 Grid、待办 Checkbox 等飞书特有块
4. **一键发布**：调用 `lark-cli docs +create --api-version v2` 创建文档

## 两种创建路径（先判断再行动）

### 路径 A：本地已有 Markdown 文件（大多数真实场景）

用户已准备好本地 `.md` 文件（PRD、设计文档、技术规范），直接用 `--content @file` 一步创建，再逐步美化：

**典型工作流：**
1. `cd` 到文件所在目录（lark-cli 的 `@filepath` 必须用 CWD 相对路径如 `./file.md`）
2. `lark-cli docs +create --api-version v2 --doc-format markdown --content @./file.md`
3. 记录返回的 `document_id`
4. `lark-cli docs +fetch --detail with-ids` 获取文档 block 结构
5. 逐步美化：
   - 开头摘要 → `callout`（`block_replace` 替换原 block）
   - ASCII 架构/流程图 → `whiteboard type="mermaid"`（`block_replace`）
   - 章节引导 → `callout`（`block_insert_after` 插入各章节标题 block-id 后）
   - 文字密集段落 → `table` / `grid` / `callout`

**不需要走四波创作流程。** 内容已在本地文件中，创作已完成，只需要发布 + 美化。

### 路径 B：从零创作（无本地文件）

当用户只有主题/需求描述，没有任何现成文档时，按下方「四波创作流程」从零生成。

## 何时使用

- 用户说「把这篇 Markdown 发到飞书」「发布博客到飞书」「把 md 转成飞书文档」
- 用户提供 Markdown 文本或 `.md` 文件，需要转为飞书云文档
- 用户需要将技术博客以富格式展示在飞书中（含图表、Callout 等）

**不适用场景：**
- 用户只想创建飞书文档但无 Markdown 源文件 → 直接使用 `lark-doc` skill
- 用户需要编辑已有飞书文档 → 使用 `lark-doc` skill 的 `docs +update`
- 用户明确要求保留原有富格式（Callout、画板等）→ 需要使用 XML 格式发布，不是 Markdown 格式；此时应加载 `lark-doc` skill 并阅读 `references/lark-doc-xml.md`

## 前置条件

**执行前必须完成：**

1. 加载 `lark-doc` skill 并阅读其 `references/lark-doc-xml.md`（XML 语法规则）
2. 确认 `lark-cli` 已安装且认证通过（见 `lark-shared` skill）
3. 获取用户的 Markdown 源内容（文本粘贴或本地 `.md` 文件路径）

## 核心工作流

### 第零步：选择发布格式（Markdown vs XML）

发布前先判断用哪种格式：

| 条件 | 推荐格式 | 说明 |
|------|---------|------|
| 用户明确要求"不改变内容仅优化格式" | **XML 格式** | 才能启用 Callout、分栏、画板等富块 |
| 文档以文字为主，表格少（<5个）| Markdown 直发 | 快速简单，表格渲染正常 |
| 文档表格密集（10+表格）| XML 格式 | Markdown 的 GFM 表格渲染效果差 |
| 需要嵌入 Mermaid/PlantUML 图表 | **必须 XML 格式** | Markdown 不支持画板嵌入 |
| 源文件 Markdown 格式良好、无需增强 | Markdown 直发 | 可跳过 XML 转换 |

**判断步骤**：
1. 读取源 Markdown 文件
2. 扫描是否有 `:::tip`、````mermaid`、`<callout>` 等飞书特有语法 → 必须 XML
3. 扫描表格密度（>5个表格）→ 推荐 XML
4. 用户明确说"保留格式/不改变格式" → XML
5. 都不是 → Markdown 直发快捷路径

**⚠️ 特别注意**：如果源 `.md` 文件是从 read_file 工具读取的（行首有 `1|` `2|` 格式的行号前缀），**必须先用 `re.sub(r"^\s*\d+\|", "", raw)` 清除行号再写入临时文件发布**。read_file 输出格式为 `LINE_NUM|CONTENT`，不是纯 Markdown，直接写入会导致整篇文档每行都以行号开头。

### 第一步：解析 Markdown 结构

将 Markdown 文本解析为元素序列，识别以下元素类型：

| Markdown 元素 | 解析规则 |
|---|---|
| `# ~ ######` 标题 | 提取级别和文本，映射为 `<h1>` ~ `<h6>` |
| 普通段落 | 映射为 `<p>`，处理行内 `**粗体**`、`*斜体*`、`` `代码` ``、`[链接](url)` |
| ` ```lang ` 代码块 | 映射为 `<pre lang="lang" caption="标签"><code>...</code></pre>` |
| `- / *` 无序列表 | 映射为 `<ul><li>...</li></ul>` |
| `1. 2.` 有序列表 | 映射为 `<ol><li seq="auto">...</li></ol>` |
| `> 引用` | 映射为 `<blockquote><p>...</p></blockquote>` |
| `---` 分割线 | 映射为 `<hr/>` |
| `![alt](url)` 图片 | 映射为 `<img href="url" caption="alt"/>` |
| Markdown 表格 | 映射为 `<table>` + `<thead>`/`<tbody>` 结构 |
| `:::tip` 等容器 | 映射为 `<callout>`（见下方 Callout 映射表） |

### 第二步：图表意图识别

扫描解析后的元素序列，根据内容语义特征自动判断最佳可视化方式：

#### 识别规则表

| 内容特征 | 触发关键词 / 模式 | 推荐图表类型 | 飞书 XML 映射 |
|---|---|---|---|
| **流程/步骤描述** | 「步骤」「流程」「首先→然后→最后」「Step 1/2/3」、有序步骤列表 | Mermaid 流程图（flowchart） | `<whiteboard type="mermaid">flowchart TD\n  A --> B --> C</whiteboard>` |
| **时序交互** | 「请求→响应」「调用」「发送」「返回」「客户端/服务端」、A→B→A 模式 | Mermaid 时序图（sequenceDiagram） | `<whiteboard type="mermaid">sequenceDiagram\n  A->>B: 请求</whiteboard>` |
| **架构/层次关系** | 「架构」「组件」「模块」「层」「系统由…组成」、含层级缩进 | Mermaid 流程图（上下/左右布局） | `<whiteboard type="mermaid">flowchart TB\n  A --> B</whiteboard>` |
| **类/数据模型** | 「类图」「继承」「接口」「字段」「UML」、数据模型定义 | PlantUML 类图 | `<whiteboard type="plantuml">@startuml\nclass A {}\n@enduml</whiteboard>` |
| **状态变迁** | 「状态」「转换」「生命周期」「状态机」 | Mermaid 状态图（stateDiagram） | `<whiteboard type="mermaid">stateDiagram-v2\n  [*] --> A</whiteboard>` |
| **对比/参数表** | 「对比」「差异」「参数」「配置」「vs」、多列数据 | 飞书原生表格 | `<table>...</table>` |
| **并列双栏** | 「优势/劣势」「前后对比」「左右对比」、两段并列内容 | 分栏布局 | `<grid><column width-ratio="0.5">...</column><column width-ratio="0.5">...</column></grid>` |
| **关键总结/提示** | 「注意」「警告」「提示」「总结」「关键点」「⚠️💡❗」 | Callout 高亮框 | `<callout emoji="⚠️" background-color="light-yellow">...</callout>` |
| **甘特/排期** | 「排期」「里程碑」「时间线」「甘特」 | Mermaid 甘特图（gantt） | `<whiteboard type="mermaid">gantt\n  title 排期</whiteboard>` |
| **饼图/占比** | 「占比」「比例」「分布」「百分比」、含 `%` 数据 | Mermaid 饼图（pie） | `<whiteboard type="mermaid">pie title 分布\n  "A" : 40</whiteboard>` |

#### 识别优先级

当一段内容同时匹配多个规则时，按以下优先级选择：

1. **PlantUML 类图**（最窄匹配，需要明确的 UML 关键词）
2. **状态图 / 甘特图 / 饼图**（特定领域模式）
3. **时序图**（A→B 交互模式）
4. **流程图**（最通用，步骤/流程关键词即触发）
5. **表格**（有明确列结构或对比语义时）
6. **分栏**（只有双栏并列时使用）

#### 识别流程

```
对每个章节/段落块：
  1. 提取文本内容 + 上下文（前后块类型、标题层级）
  2. 匹配「触发关键词 / 模式」表
  3. 如命中 → 生成对应图表 XML，插入到该段落之后
  4. 如未命中但段落为连续3段以上的纯文本 → 标记为「建议图表」，在最终审查时尝试用 Callout 或表格增强
```

### 第三步：Markdown → DocxXML 转换

#### Callout 映射表

Markdown 中常见的提示块语法映射为飞书 Callout：

| Markdown 语法 | Callout 属性 |
|---|---|
| `:::tip` / `> 💡 提示` | `emoji="💡" background-color="light-blue"` |
| `:::warning` / `> ⚠️ 警告` | `emoji="⚠️" background-color="light-yellow" border-color="yellow"` |
| `:::danger` / `> ❌ 危险` | `emoji="❌" background-color="light-red" border-color="red"` |
| `:::note` / `> 📝 备注` | `emoji="📝" background-color="light-gray"` |
| `> [!NOTE]` / `> [!TIP]` | 按类型映射到上述对应样式 |
| `> [!IMPORTANT]` | `emoji="❗" background-color="light-orange" border-color="orange"` |

#### 行内样式映射

| Markdown | 飞书 XML |
|---|---|
| `**粗体**` | `<b>粗体</b>` |
| `*斜体*` | `<em>斜体</em>` |
| `` `代码` `` | `<code>代码</code>` |
| `~~删除线~~` | `<del>删除线</del>` |
| `[文本](url)` | `<a href="url">文本</a>` |
| `![alt](url)` | `<img href="url" caption="alt"/>` |

**行内样式嵌套顺序**（必须严格遵循）：`<a> → <b> → <em> → <del> → <u> → <code> → <span> → 文本`

#### 文本转义规则

- 标签本身 **禁止转义**（`<p>` 保持原样）
- 仅文本内容中的特殊字符转义：`<` → `&lt;`、`>` → `&gt;`、`&` → `&amp;`
- **占位符转义**（重要）：源 markdown 中作为占位符的尖括号（如 `/skill <name>`、`hermes cron edit <id>`、`--context-from <A的job_id>`、`mcp_<server>_<tool>`）：
  - 在 **Markdown 模式**下需要写为 `\<name>` `\<id>` 等（反斜杠使 `<` 不被识别为 HTML 标签起始）
  - 在 **DocxXML 模式**下需要写为 `&lt;name&gt;` `&lt;id&gt;` 等（XML 文本节点里 `<` 必须转义为实体）
  - 详见 `references/md-to-docx-conversion.md`

#### 表格转换模板

```
Markdown:
| 列A | 列B |
|-----|-----|
| 值1 | 值2 |

→ 飞书 XML:
<table>
  <colgroup><col width="120"/><col width="120"/></colgroup>
  <thead><tr><th background-color="light-gray">列A</th><th background-color="light-gray">列B</th></tr></thead>
  <tbody><tr><td>值1</td><td>值2</td></tr></tbody>
</table>
```

### 第四步：文档组装与增强

将所有转换后的 XML 块组装为完整文档内容，应用以下增强策略：

1. **开头添加元信息 Callout**：
   ```xml
   <callout emoji="📌" background-color="light-blue">
     <p><b>原文格式</b>：Markdown 技术博客 ｜ <b>发布时间</b>：{当前日期}</p>
   </callout>
   ```

2. **章节间插入 `<hr/>`**：在 h1/h2 级别的章节之间插入分割线（章节内 h3+ 不插入）

3. **代码块添加 caption**：为每个 `<pre>` 添加有意义的 `caption` 属性（从上下文推断）

4. **连续文本打断**：超过 3 段连续 `<p>` 时，主动插入 Callout/表格等富块

5. **图表插入位置**：图表意图识别生成的图表块，插入在触发段落之后、下一段落之前

### 第五步：发布到飞书

**核心陷阱（必读）**：`--content @file` 和 `--title` 不能同时使用。`--content` 只接受内联字符串，不接受文件路径；`--title` 只在 `--markdown` 模式下有效。

正确做法：用 `--markdown -` 读取 stdin 管道，结合 `--title`：

```bash
# ✅ 正确：用 stdin 管道传入本地 .md 文件（中文内容正常）
cd /Users/xiesg/workspace
cat prompting-playbook-blog.md | lark-cli docs +create --api-version v2 --doc-format markdown --title "文章标题" --markdown -

# ❌ 错误：--content @file 和 --title 同时使用会报 "unknown flag: --new-title" 或 "--content is required"
lark-cli docs +create --api-version v2 --content @./file.md --title "标题"   # 不支持
```

**三种内容传递方式：**

| 方式 | 适用场景 | 示例 |
|------|---------|------|
| `--new-title "$(head -1 {file} \| sed 's/^# //')" --content @file` | **推荐**：本地 `.md` 文件，第一行是 `# 标题` | 自动从文件第一行提取标题，不会出现"Untitled" |
| `--markdown -`（stdin管道）+ `--title "标题"` | 无本地文件、Markdown 内容在变量中 | `cat file.md \| lark-cli docs +create --api-version v2 --doc-format markdown --title "标题" --markdown -` |
| `--doc-format xml --content @file` | **源文件已是完整 DocxXML**（含 `<title>` 元素和 `<table>`/`<pre>` 等富块） | 不需要任何标题参数——XML 内的 `<title>` 元素会被飞书作为文档标题使用 |

**关于第三种方式的典型用法**：

当源 markdown 已通过脚本（`md_to_docx.py` 等）转成了 DocxXML，或**用户要求"保留文字内容、优化图表展示"**时，应该走这条路：

```bash
# ✅ 正确：XML 自带标题，不需要 --new-title / --title
lark-cli docs +create --api-version v2 --doc-format xml --content @./handbook.docx.xml

# XML 文件首部必须含 <title>xxx</title>，否则文档会显示为 "Untitled"
head -1 handbook.docx.xml   # 应该是 <title>文档标题</title>
```

**关于 `--title` 的误解澄清：**
- ❌ `--title` 不能与 `--content @file` 同时使用（会报 "unknown flag: --new-title" 或 "content is required"）
- ✅ `--new-title` 可以与 `--content @file` 同时使用 — 它从文件内容的第一行提取标题（需要文件第一行是 `# 标题` 格式）
- ✅ `--title` 只在 `--markdown -`（stdin 模式）下有效，用于显式指定标题字符串

**长文档策略：**
- 内容 ≤ 4000 字符 → 一次性 `--markdown -` 发布
- 内容 > 4000 字符 → 先 `--markdown -` 创建骨架，再用 `docs +update --command append` 追加剩余章节

## 完整示例

### 输入 Markdown

```markdown
# 微服务架构设计指南

## 架构流程

用户请求经过 API 网关，再路由到各微服务：

1. 用户发起 HTTP 请求
2. API 网关鉴权与限流
3. 路由到对应微服务
4. 服务间通过消息队列通信

> 💡 提示：建议使用异步通信降低耦合

## 技术选型对比

| 框架 | 语言 | 性能 |
|------|------|------|
| Gin | Go | 高 |
| Express | Node.js | 中 |
```

### 输出飞书 XML

```xml
<title>微服务架构设计指南</title>

<callout emoji="📌" background-color="light-blue">
  <p><b>原文格式</b>：Markdown 技术博客 ｜ <b>发布时间</b>：2026-05-13</p>
</callout>

<h1>架构流程</h1>

<p>用户请求经过 API 网关，再路由到各微服务：</p>

<ol>
  <li seq="auto">用户发起 HTTP 请求</li>
  <li seq="auto">API 网关鉴权与限流</li>
  <li seq="auto">路由到对应微服务</li>
  <li seq="auto">服务间通过消息队列通信</li>
</ol>

<whiteboard type="mermaid">flowchart TD
  A[用户请求] --> B[API 网关]
  B --> C[鉴权与限流]
  C --> D[微服务路由]
  D --> E[消息队列通信]</whiteboard>

<callout emoji="💡" background-color="light-blue">
  <p>提示：建议使用异步通信降低耦合</p>
</callout>

<hr/>

<h1>技术选型对比</h1>

<table>
  <colgroup><col width="120"/><col width="120"/><col width="120"/></colgroup>
  <thead><tr><th background-color="light-gray">框架</th><th background-color="light-gray">语言</th><th background-color="light-gray">性能</th></tr></thead>
  <tbody>
    <tr><td>Gin</td><td>Go</td><td>高</td></tr>
    <tr><td>Express</td><td>Node.js</td><td>中</td></tr>
  </tbody>
</table>
```

## 常见陷阱

1. **未读取 lark-doc-xml.md 就生成 XML**：XML 嵌套顺序、转义规则、支持的标签都有严格限制，不看规范直接写必然出错。务必先读取 `lark-doc` skill 的 `references/lark-doc-xml.md`。

2. **行内样式嵌套顺序错误**：飞书要求 `<a> → <b> → <em> → <del> → <u> → <code> → <span>` 的固定嵌套顺序，关闭顺序必须严格反转。顺序错误会导致样式丢失或渲染异常。

4. **博客文件必须有标题字段**：本地博客草稿文件（如 `ai-school-blog-draft.md`）的第一行必须是 Markdown 标题（`# 标题文本`），发布命令用 `--new-title` 参数提取标题：`-new-title "$(head -1 {file} | sed 's/^# //')"`。如果文件第一行不是 `# 标题` 格式，文档在飞书中会显示为"Untitled"。生成后立即用 `head -1 {file}` 验证。

4. **Callout 内放了不支持的子块**：Callout 子块仅支持文本、标题、列表、待办、引用。不要在 Callout 内放 `<table>`、`<pre>`、`<whiteboard>` 等。

5. **内容过长一次性创建失败**：飞书 API 对单次请求内容有长度限制。超过 4000 字符时必须分批追加（先 `create` 骨架，再 `append` 章节）。

6. **忘记 `--api-version v2`**：所有 `docs +create` 和 `docs +update` 命令必须带 `--api-version v2`，否则会调用旧版 API 导致参数不兼容。

7. **标签内部文本未转义**：文本中的 `<`、`>`、`&` 必须转义为 `&lt;`、`&gt;`、`&amp;`，否则 XML 解析失败。但标签本身（如 `<p>`）禁止转义。

8. **图表意图误判**：不是所有流程描述都需要图表。如果原文只有 1-2 步简单描述，不需要生成 Mermaid 图表。一般超过 3 步或涉及多个角色交互时才触发图表生成。

9. **颜色使用不合规**：飞书美化系统仅支持特定命名色（gray/red/orange/yellow/green/blue 及其 light-/medium- 变体）。不要使用 `#RRGGBB` 或随意命名色。

10. **@file 路径必须是 CWD 相对路径**：`--content @./file.md` 中的路径必须是当前工作目录的相对路径（`./file.md`），传绝对路径（`/Users/.../file.md`）会报 `unsafe file path` 错误。解法：先 `execute_code` 把文件写到 CWD，或 `cd` 到文件所在目录。

11. **标题丢失陷阱（"Untitled"）**：当使用 `--content @file.md` 时，飞书从文件内容提取标题（取 Markdown 第一个 `# 标题` 或 XML `<title>` 标签）。如果源文件第一行不是标题行（如直接是正文段落），创建的文档会显示为"Untitled"。**发布前必须验证**：用 `head -1 {file}` 检查文件第一行是否是 `# ` 开头。不是的话先用 `execute_code` 在文件头部插入一行 `# 文档标题` 再发布。

11. **lark-cli 可能不在 PATH 中**：如果 `lark-cli` 命令找不到，尝试全路径 `/Users/xiesg/dev/cli/lark-cli`。用 `which lark-cli || find /Users/xiesg -name "lark-cli" -type f` 定位。

12. **bot 身份创建文档后权限问题**：以 bot 身份创建的文档，当前用户可能没有编辑权限。`permission_grant.status = "skipped"` 表示自动授权失败。如需用户编辑权限，需先用 `lark-cli auth login` 确保有用户 open_id，再重新授权。**关键区分**：
    - **查看权限**：bot 身份创建的文档，**任何打开链接的登录用户默认有查看权限**（飞书行为），不需要 `auth login`。
    - **编辑权限**：需要 `lark-cli auth login` 后用 `--as user` 身份重新授权，或由 bot 管理员在飞书文档的"分享"面板手动添加协作者。
    - 因此**如果用户只要求"打开就能看"**，bot 身份创建就够用，警告可忽略。

13. **read_file 输出的文件含行号前缀**：从 read_file 读取的 `.md` 文件，行首是 `1|` `2|` 格式的行号，不是纯 Markdown。直接写入发布会导致整篇文档都是行号。**必须先 `re.sub(r"^\s*\d+\|", "", raw)` 清除行号**，再写入临时文件。

14. **execute_code 的 read_file 返回值结构与工具不同**：`execute_code` 内部 import 的 `read_file` 返回 `{"content": ..., "total_lines": N}` 是正确的，但当脚本从文件读取时，用 `open(...).read()` 直接读文件内容，**不要**试图用 `read_file` 的返回值字典的 `'content'` 键——`execute_code` 的 `read_file` 是工具不是函数，直接调用 `read_file()` 在脚本中是未定义的。正确做法：

```python
# ✅ 正确：直接用 open 读文件
with open('/path/to/file.md', 'r') as f:
    content = f.read()
cleaned = re.sub(r'^\s*\d+\|\s*', '', content, flags=re.MULTILINE)

# ❌ 错误：用 hermes_tools.read_file 返回值 .content 键
# execute_code 中 read_file 是工具（通过 hermes_tools 导入），
# 返回字典的 'content' 键，但工具本身不在 execute_code 运行时可用
result = read_file('/path/to/file.md')  # 这会失败！
content = result['content']  # KeyError
```

解法：文件 I/O 用原生 Python `open()`/`read()`，不要用 `read_file` 工具的返回值。

15. **占位符尖括号在 Markdown 与 DocxXML 模式下的转义不同**（常被遗漏）：源 markdown 文档里大量出现的占位符（如 `/skill <name>`、`hermes cron edit <id>`、`--context-from <A的job_id>`、`mcp_<server>_<tool>`），是**用户文档里的字面文本**，但在不同发布模式下转义写法不同：

    - **Markdown 模式**：`/skill \<name>` `\<id>`（反斜杠告诉飞书"`<` 不要当 HTML 标签起始"——飞书文档会显示为 `/skill <name>`）
    - **DocxXML 模式**：`/skill &lt;name&gt;` `&lt;id&gt;`（XML 文本节点里 `<` 必须转义为实体——飞书文档会显示为 `/skill <name>`）

    **常见错误**：
    - 在 DocxXML 模式里写 `\<name>`（带反斜杠）→ 飞书会显示成字面 `\<name>`，多了个反斜杠
    - 在 Markdown 模式里写 `<name>`（不带反斜杠）→ 飞书会解析为 HTML 标签起始，显示丢失 `<name>` 三个字符

    **判断自己用的是哪种模式**：看发布命令的 `--doc-format` 参数。脚本里转义时务必按目标模式选对应规则。详细转换经验见 `references/md-to-docx-conversion.md`。

16. **用户要求"保留内容不要更改"时的双重要求**（决策陷阱）：当用户说"内容写入飞书" + "保留内容" + "优化图表展示"时，这是**有微妙冲突**的双重要求——"不修改"和"优化"是反向的。正确处理：

    - **内容字面 1:1 保留**：用户文字、所有标点、占位符语义都不动
    - **结构/样式可以优化**：表格升级为飞书原生 `<table>`、代码块加 `lang` 属性、关键提示升级为 callout
    - **明确告诉用户"做了一处微调"**：占位符转义是必须的（飞书会吞掉未转义的 `<name>`），但**显示结果与原内容字面一致**——这点必须让用户知道

    **如果用户明确说"源码字符也 1:1 不变"**：走 Markdown 模式直发，跳过 DocxXML 转换。

## 验证清单

- [ ] 已加载 `lark-doc` skill 并读取 `references/lark-doc-xml.md`
- [ ] 已读取 `lark-shared` skill 确认认证状态
- [ ] 已判断使用 Markdown 直发还是 XML 格式（见"第零步"）
- [ ] 源文件行号前缀已清除（`re.sub(r"^\s*\d+\|", "", raw)`）
- [ ] Markdown 源内容已完整解析，所有元素已映射
- [ ] 图表意图识别已执行，匹配的章节已插入对应图表
- [ ] Callout 映射正确（emoji、background-color、border-color）
- [ ] 行内样式嵌套顺序正确（`<a> → <b> → <em> → <del> → <u> → <code> → <span>`）
- [ ] 文本特殊字符已转义（`&lt;` `&gt;` `&amp;`）
- [ ] 占位符已按目标模式（Markdown/DocxXML）正确转义（见陷阱 15）
- [ ] 表格包含 `<colgroup>`、`<thead>`（含 `background-color`）和 `<tbody>`
- [ ] 章节间已插入 `<hr/>`
- [ ] 文档总长度 > 4000 字符时已规划分批追加策略
- [ ] `lark-cli docs +create` 命令包含 `--api-version v2`
- [ ] 发布后用 `lark-cli docs +fetch` 验证内容是否正确
- [ ] 创建成功后已返回文档 URL 给用户
