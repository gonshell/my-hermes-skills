---
name: lark-doc-pitfalls
version: 1.0.0
description: "lark-doc 操作中的高风险踩坑点记录。overwrite 清空文档、@filepath 相对路径、LaTeX \\text{} 渲染失败、文档内容重排序、删除文档方法等。遇到飞书文档操作问题时先查此处。"
metadata:
  requires:
    bins: [lark-cli]
  cliHelp: lark-cli docs --help
---

# lark-doc 踩坑记录

> 本文件记录 lark-doc 操作中的高风险踩坑点，是 `lark-doc-update.md` 的补充。
> 遇到类似场景时先查此处。

---

## 1. `overwrite` 会清空文档且必须传 `--content`

**问题**：`overwrite` 必须传 `--content` 参数，即使只想改标题，传入空字符串会把文档内容全部清空。

**场景**：修复文档标题时想用 `--new-title` 参数，但 `+update` 没有这个参数，改用 `overwrite` 传入空 content → 文档正文全部丢失。

**正确做法**：改标题用 `str_replace`：
```bash
lark-cli docs +update --api-version v2 --doc "<doc_id>" --command str_replace \
  --pattern "<title>旧标题</title>" --content "<title>新标题</title>"
```

---

## 2. `<code_block>` 在 `append` 时内容丢失：用 `<pre><code>` 替代

**问题**：写入含代码块的 Markdown 时，用 `<code_block>...</code_block>` 标签，`append` 指令返回 `result: "success"` 但文档中无代码块。API fetch 确认 block 被写入但内容为空。

**根因**：`append`（= `block_insert_after`）在序列化 `code_block` type 时有空内容校验 bug，导致代码块内容被静默丢弃。

| 标签格式 | Feishu Block Type | `append` | `overwrite` |
|----------|-------------------|----------|-------------|
| `<code_block>...</code_block>` | `code_block` | ❌ 内容丢失 | ⚠️ 不稳定 |
| `<pre lang="x"><code>...</code></pre>` | `paragraph`（含 code 内联） | ✅ 正确 | ✅ 正确 |

**解法**：所有代码块都用 `<pre lang="..."><code>...</code></pre>`，不要用 `<code_block>`。

```python
def md_code_block_to_feishu_xml(code_text: str, lang: str) -> str:
    escaped = code_text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
    if lang:
        return f'<pre lang="{lang}"><code>\n{escaped}\n</code></pre>'
    else:
        return f'<pre><code>\n{escaped}\n</code></pre>'
```

**验证**：
```bash
lark-cli docs +fetch --api-version v2 --doc "<doc_id>" --detail with-ids | python3 -c "
import sys, json, re; data=json.load(sys.stdin); content=data['data']['document']['content']
matches=list(re.finditer(r'<pre[^>]*><code>(.*?)</code></pre>', content, re.DOTALL))
print(f'<pre><code> blocks: {len(matches)}'); [print('Sample:', repr(m.group(1)[:80])) for m in matches[:1]]
"
```
正确写入时 `<pre><code>` 内应含换行符和原始文本，非空。

**来源**：2026-05-25，写入 hiclaw-source-analysis.md（77KB，53 个代码块）时发现。

---

## 4. `--content @<filepath>` 必须用相对路径

**问题**：`--content @/tmp/file.xml` 报错：`--file must be a relative path within the current directory`

**解法**：先复制到当前目录再用相对路径引用：
```bash
cp /tmp/content.xml ./content.xml
lark-cli docs +update --api-version v2 --doc "<doc_id>" --command append \
  --content @./content.xml
```

---

## 6. 删除文档用通用 API，不是 `docs +delete`

```bash
lark-cli api DELETE "/open-apis/drive/v1/files/<token>?type=docx" \
  --params '{"type":"docx"}'
```
token 是 URL 中的 token，例如 `https://www.feishu.cn/docx/ABCDEF` → `ABCDEF`。

---

## 4. LaTeX `\text{}` 在飞书文档中渲染失败

飞书使用 KaTeX 子集渲染，不支持 `\text{}`、`\mbox{}`、`\mathrm{}`。

公式中 `\text{汉字}` 会显示为 `\ 汉字`（反斜杠+空格+汉字），原因是 KaTeX 不识别 `\text` 命令。

**检测**：fetch 文档内容后搜索 `\text{` 或 `\ 汉字` 模式。

**修复**：
```python
content = content.replace(r'\text{ 个 }', ' 个 ')
content = content.replace(r'\text{ 弧度}', ' 弧度')
content = content.replace(r'\ 个', '个')   # 清理残留
content = content.replace(r'\ 弧度', '弧度')
```

**正确写法**：
```latex
✅ E = \{x \mid x 是等腰三角形\}
❌ E = \{x \mid x \text{是等腰三角形}\}
```

详见 skill `feishu-math-rendering`。

---

## 5. 文档内容重排序：禁止直接 overwrite，必须先 fetch

场景：把「知识结构总览」从文档末尾移到开头。

**错误做法**：直接 fetch → overwrite → whiteboard token 失效，内容丢失。

**正确做法**：

```python
import subprocess, json

result = subprocess.run(
    ['/usr/local/bin/lark-cli', 'docs', '+fetch', '--api-version', 'v2', '--doc', '<doc_id>'],
    capture_output=True, text=True, cwd='/Users/xiesg/workspace'
)
content = json.loads(result.stdout)['data']['document']['content']

# 重排序
title_tag_end = content.find('</title>') + len('</title>')
h1_title_end = content.find('</h1>', title_tag_end) + len('</h1>')
chapter1_start = content.find('<h1>第一章')
overview_start = content.find('<h1>知识结构总览')

title_section = content[:h1_title_end]
overview_section = content[overview_start:]
body_section = content[chapter1_start:overview_start]

new_content = title_section + overview_section + body_section

with open('/Users/xiesg/workspace/reordered.xml', 'w') as f:
    f.write(new_content)
```

```bash
cd /Users/xiesg/workspace
cp reordered.xml ./reordered.xml
lark-cli docs +update --api-version v2 --doc "<doc_id>" --command overwrite \
  --content @./reordered.xml --doc-format xml
```

关键：fetch 是为了保留 whiteboard block token，overwrite 后飞书会重建 whiteboard 但 token 引用可能失效。

---

## 7. 大段内容用文件引用，不用 heredoc 内联

---

## 8. Mermaid 内容换行太多会导致 whiteboard 解析失败

**问题**：Mermaid 内容中包含大量 `\n` 换行时（如 `--content` 传入格式化后的多行 Mermaid），飞书返回 `2107: Whiteboard content parse failed`。

**场景**：`block_replace` 一个 ASCII 流程图为 Mermaid 时，命令执行失败但不影响文档。

**原因**：飞书 Mermaid 解析器对多行内容处理有路径限制，内容行数过多时报解析失败。

**解法**：压缩为单行或最少换行，或在 `whiteboard` 标签后紧跟一个 `<p>` 占位段：

```xml
<!-- 推荐：单行 -->
<whiteboard type="mermaid">flowchart TB\n  A["节点"] --> B["节点"]</whiteboard>

<!-- 次选：多行但行数少（<5行） -->
<whiteboard type="mermaid">flowchart TB
  A --> B
  B --> C</whiteboard>
```

**经验值**：flowchart 节点定义 3-5 个以内基本安全，序列图（sequenceDiagram）行数多时更容易失败。超过 5 个节点的复杂图，先验证简单版，再逐步添加。

**不阻塞**：whiteboard 解析失败时飞书降级但不报错，`result: "success"` 仍返回，内容变成空白 block。如遇此情况，换用 `<callout>` + 文字描述代替。

---

## 9. `block_insert_after` 依赖已知 block_id，必须先 fetch

---

## 11. "仅优化图表" → 必须用 XML 格式，不能用 Markdown

**问题**：用户说"仅优化图表/图元"时，Agent 用 Markdown 格式创建文档，被拒绝后重建。

**根因**：Markdown 格式无法表达颜色表头、条件行背景等视觉增强。XML 可以。

**规则**：

| 用户说... | 格式 |
|---------|------|
| "创建文档"（neutral） | XML（默认） |
| "导入这个 .md 文件" | Markdown（用户提供.md） |
| "仅优化图表/图元" | **XML** |
| "让表格看起来更好" | **XML** |
| "只写入内容，不改格式" | Markdown |

**XML 视觉增强能力**：
- 表格表头：`background-color="light-blue"`（或 `#E8F4FD`）
- 条件行背景：`background-color="light-yellow"` / `"light-gray"` / `"light-green"`
- Callout 块、Grid 布局、Checkbox 样式

**表格彩色表头标准写法**：
```xml
<table>
  <thead background_color="#E8F4FD">
    <tr>
      <th style="background-color:#E8F4FD">列1</th>
      <th style="background-color:#E8E8E8">列2</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>内容</td>
      <td>内容</td>
    </tr>
    <tr>
      <td style="background-color:#FFF9E6">高亮行</td>
      <td>内容</td>
    </tr>
  </tbody>
</table>
```

Markdown 一个都没有。

**不阻塞**：`overwrite` 场景下，即使目标只是"加颜色"，仍然用 XML --command overwrite。Format 选择逻辑不受操作类型影响。

---

## 附：飞书 LaTeX 公式渲染规范（来源：feishu-math-rendering）

飞书文档的 LaTeX 渲染基于 KaTeX 子集，存在已知限制。

### ✅ 支持的写法
- 汉字直接写在公式内：`$E = \{x \mid x 是等腰三角形\}$`
- 纯 LaTeX 符号：$\sqrt{ab} \leq \frac{a+b}{2}$
- Unicode 符号在公式内：$180°$, $a \geq b$

### ❌ 不支持的写法
- **`\text{}`**：不支持 amsmath 的 `\text{}`、`\mbox{}`、`\mathrm{}`
  - `$\pi \text{ 弧度} = 180°$` → 显示为 `$\pi \text{ 弧度} = 180°$`（原样显示）
- **后果**：未支持的命令被原样显示，破坏公式可读性

### ✅ 正确写法
```latex
% 错误
$\pi \text{ 弧度} = 180°$

% 正确
$\pi 弧度 = 180°$
```

### 修复已有文档（检测 + 替换）
```python
import re

# 查找问题模式
text_issues = re.findall(r'\\text\{[^}]+\}', content)
space_chinese = re.findall(r'\\ [\u4e00-\u9fff]', content)  # 如 \ 弧度

# 替换
content = content.replace(r'\text{ 弧度}', ' 弧度')
content = content.replace(r'\text{或}', '或')
content = content.replace(r'\text{ 个 }', ' 个 ')
content = content.replace(r'\ 弧度', '弧度')
content = content.replace(r'\ 个', '个')
content = content.replace(r'\ 或', '或')

# 验证无残留
assert '\\text{' not in content
assert not re.search(r'\\ [\u4e00-\u9fff]', content)
```

---

## 附：飞书云文档权限与所有权（来源：lark-drive-permission-owner）

### 核心概念

| 权限操作 | API | 执行主体限制 |
|----------|-----|-------------|
| 查询权限 | `permission.members auth` | 任意有权限者 |
| 授权/添加协作者 | `permission.members create` | owner 或有 `manage_public` 者 |
| 转移 owner | `permission.members transfer_owner` | **仅 owner** |
| 删除文档 | `drive +delete` | **仅 owner** |

### Owner 转移的限制
- Bot 无法将自己设为用户文档的 owner（`permission denied`）
- Owner 转移只能发生在同一租户内的用户之间
- 转移后原 owner 可选择保留权限（`old_owner_perm` 参数）

### Wiki 文档的 token 分辨率
Wiki URL（`/wiki/<node_token>`）**不能**直接作为 file_token 使用：
```bash
lark-cli wiki spaces get_node --params '{"token":"<WIKI_NODE_TOKEN>"}'
# 返回：node.obj_token = 真实文档 token（如 docx）
```

### Delete 操作要求
```bash
lark-cli drive +delete --file-token "<obj_token>" --type <obj_type> --yes
```
- **必须使用 `obj_token`（真实文档 token），不是 `node_token`**
- 执行者必须是文档 owner，否则 `forbidden`

### ⚠️ `transfer_owner` CLI 命令 bug（v1.0.19）

`lark-cli drive permission.members transfer_owner` 命令存在参数解析 bug，所有传参方式均报错 "missing required path parameter: token"。

**workaround**：用 curl 调用 REST API：
```bash
TENANT_TOKEN=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "app_id=${FEISHU_APP_ID}&app_secret=${FEISHU_APP_SECRET}&grant_type=client_credentials" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")

curl -s -X POST "https://open.feishu.cn/open-apis/drive/v1/permissions/<file_token>/members/transfer_owner?type=docx&remove_old_owner=false" \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"member_id":"<open_id>","member_type":"openid"}'
```

---

## 9.5 骨架 + 并行 Agent 追加 → 内容重复

**问题**：使用「先 create 骨架（空标题 + 占位描述）→ spawn 并行 Agent 用 append 追加完整内容」模式时，骨架中的占位标题/段落会保留在文档中，与 Agent 追加的正式内容形成重复。

**场景**：`docs +create` 创建含 7 个 h1 标题 + `<p>（占位描述）</p>` 的骨架 → 3 个并行 Agent 各自 `--command append` 追加完整章节 → 文档中出现两套相同标题（一套空壳、一套有内容）。

**解法**（推荐按优先级）：
1. **骨架只放 title + callout**，不放章节标题。章节标题由第一个 append 的 Agent 写入。这样骨架永远只有 2-3 个 block，不会产生歧义。
2. 如果必须放章节标题作骨架，在 Agent 全部完成后，用 `docs +fetch --detail with-ids --scope outline` 获取所有 block ID → 定位骨架 block → `--command block_delete` 批量删除（逗号分隔）。
3. 或直接用 `overwrite` 全文重写（仅当文档无图片/评论等不可重建内容时）。

**批量删除示例**：
```bash
# 1. fetch outline 拿到所有 block ID
lark-cli docs +fetch --api-version v2 --doc "<doc_id>" --detail with-ids --scope outline

# 2. 提取骨架 block ID（第一套重复标题范围的 ID）
# 3. 批量删除
lark-cli docs +update --api-version v2 --doc "<doc_id>" --command block_delete \
  --block-id "id1,id2,id3,...,id42"
```

---

## 9.6 并行 Agent append → 标题层级嵌套错误

**问题**：多个并行 Agent 各自 `--command append` 追加章节时，飞书将 append 的内容嵌套在当前最后一个 block 的子树中。outline 中 h1 标题显示为前一章的 h2 子节，导致目录结构错误。

**场景**：`docs +create` 写入第一章 → 并行 Agent A append 阶段二（h1）→ 并行 Agent B append 阶段三（h1）→ outline 显示阶段二和阶段三都在阶段一的子树下。

**修复**（推荐按优先级）：
1. **避免并行 append**：串行 append 或让主 Agent 直接写完整内容，不 spawn 子 Agent。
2. **overwrite 重建**：`docs +fetch --scope full` 取回全文 → 检查/修正 h1/h2 标签 → `overwrite` 重写。overwrite 会重建 block 树结构，嵌套问题自然消除。Mermaid whiteboard 会产生 `partial_success` 警告（`Whiteboard clone failed`）但不影响内容。
3. **block_replace 不可靠**：用 block_replace 把 h2 改为 h1 时，飞书会在文档末尾创建新的 h1 block，原位置的 h2 内容不变——两级标题同时存在。

**overwrite 修复示例**：
```bash
# 1. 取回全文
lark-cli docs +fetch --api-version v2 --doc "<doc_id>" --detail simple --scope full > content.json

# 2. 用 Python 修正标签层级后保存
python3 -c "
import json, re
data = json.load(open('content.json'))
content = data['data']['document']['content']
# 修正：把嵌套的 h2 改为 h1，h3 改为 h2
content = content.replace('<h2>阶段二', '<h1>阶段二')
content = content.replace('<h3>子节', '<h2>子节')
open('fixed.xml', 'w').write(content)
"

# 3. overwrite 重写
cp fixed.xml ./fixed.xml
lark-cli docs +update --api-version v2 --doc "<doc_id>" --command overwrite \
  --content @./fixed.xml
```

---

## 10. `block_insert_after` 依赖已知 block_id，必须先 fetch

**场景**：想在某个章节标题后插入 callout，但不知道该标题的 block_id。

**解法**：先 `docs +fetch --detail with-ids` 获取完整 block 树，从 XML 中用正则提取目标 block 的 id：

```python
import re, json, subprocess

result = subprocess.run(
    ['lark-cli', 'docs', '+fetch', '--api-version', 'v2', '--doc', '<doc_id>'],
    capture_output=True, text=True
)
content = json.loads(result.stdout)['data']['document']['content']

# 找到 "01 产品概述" 这个 h2 的 block_id
match = re.search(r'<h2[^>]*id="([^"]+)"[^>]*>01 产品概述</h2>', content)
if match:
    block_id = match.group(1)
    print(f"目标 block_id: {block_id}")
```



**问题**：heredoc 通过管道传 `--content "$(cat << 'EOF' ... EOF)"` 时，shell 会解析 `<>`/`&` 等字符，导致 XML 解析失败。

**正确做法**：
```bash
cat > ./content.xml << 'EOF'
<h1>标题</h1>
<p>内容...</p>
EOF
lark-cli docs +update --api-version v2 --doc "<doc_id>" --command append \
  --content @./content.xml
```