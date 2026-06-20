# Markdown → DocxXML 转换实战参考

> 配套主 SKILL.md 的「陷阱 15」「陷阱 16」使用。适用于"用户要求保留内容、优化图表展示"场景。

## 何时用本参考

- 用户有现成 `.md` 文件
- 要求"保留文字 1:1，只优化图表、图元"
- 表格 >5 个 / 想用飞书原生表格（带列宽 + 表头底色）/ 想用 callout
- 不想走"Markdown 直发"路径（GFM 表格展示效果差）

## 决策树

```
源文件 → 读第一行
   ├─ 是 `# 标题` → 走 Markdown 模式 `--doc-format markdown`（快、表格弱）
   └─ 不是 → 走 DocxXML 模式（先转 XML 再发）
        └─ 表格 >5 个？├─ 是 → 必转 DocxXML
                       └─ 否 → 仍可转（用户体验更好）
```

## 转换器骨架（Python）

完整脚本见 `/Users/xiesg/workspace/md_to_docx.py`（一次会话产出的可复用脚本）。骨架：

```python
import re

def esc(s: str) -> str:
    """XML 文本节点转义：& < >"""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# 行内元素转换（注意：行内 code 必须先用占位符保护，避免被 */[]/() 干扰）
INLINE_CODE = re.compile(r"`([^`\n]+)`")
INLINE_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")
INLINE_EM   = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
INLINE_IMG  = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
INLINE_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)\)")

def inline_md_to_xml(text: str) -> str:
    # text 必须是已经 esc() 过的
    code_placeholders = {}
    def _code_sub(m):
        i = len(code_placeholders)
        key = f"\x00CODE{i}\x00"
        code_placeholders[key] = f"<code>{m.group(1)}</code>"
        return key
    text = INLINE_CODE.sub(_code_sub, text)
    text = INLINE_IMG.sub(lambda m: f'<img href="{m.group(2)}"/>', text)
    text = INLINE_LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)
    text = INLINE_BOLD.sub(lambda m: f"<b>{m.group(1)}</b>", text)
    text = INLINE_EM.sub(lambda m: f"<em>{m.group(1)}</em>", text)
    for k, v in code_placeholders.items():
        text = text.replace(k, v)
    return text

# 块级解析要点：
# - 围栏代码 ```lang caption → <pre lang="lang" caption="..."><code>...</code></pre>
# - GFM 表格 | --- | --- | → <table> + <colgroup> + <thead> (th 灰底) + <tbody>
# - 引用 > → 开篇元信息用 <callout>，普通引用用 <blockquote>
# - 分隔线 --- → <hr/>
# - 标题 # ~ ### → <h1> ~ <h3>
# - 关键提示段落（"**坑**/⚠️/💡"开头）→ <callout>
# - 列表 - / 1. → <ul><li> / <ol><li seq="auto">
```

## 转换规则速查表

| Markdown 元素 | DocxXML 映射 | 关键属性 |
|---|---|---|
| `# 标题` | `<title>`（仅第一个 h1）或 `<h1>` | - |
| `## 标题` | `<h2>` | - |
| `### 标题` | `<h3>` | - |
| `**粗体**` | `<b>粗体</b>` | - |
| `*斜体*` | `<em>斜体</em>` | - |
| `` `code` `` | `<code>code</code>` | - |
| ` ```bash ` | `<pre lang="bash" caption=""><code>...</code></pre>` | `lang`, `caption` |
| `> 引用` | `<blockquote><p>...</p></blockquote>` 或 `<callout>` | emoji/background-color/border-color |
| `> 💡 提示` | `<callout emoji="💡" background-color="light-blue">` | 关键词驱动 |
| `- item` | `<ul><li>item</li></ul>` | - |
| `1. item` | `<ol><li seq="auto">item</li></ol>` | `seq="auto"` |
| `---` | `<hr/>` | 自闭合 |
| `| a | b |` 表 | `<table><colgroup>...</colgroup><thead>...</thead><tbody>...</tbody></table>` | th 必带 background-color |
| `![alt](url)` | `<img href="url"/>` | - |
| `[text](url)` | `<a href="url">text</a>` | - |

## 占位符转义（最容易踩的坑）

**典型占位符模式**（技术文档中常见）：
- `/skill <name>`
- `hermes cron edit <id>`
- `--context-from <A的job_id>`
- `mcp_<server>_<tool>`

**两种模式下的转义写法**：

| 发布模式 | 源文件写法 | 飞书显示 |
|---|---|---|
| Markdown | `/skill \<name>` | `/skill <name>` |
| DocxXML | `/skill &lt;name&gt;` | `/skill <name>` |

**关键**：用户文档里**字面是 `<name>`**，但发布时要按目标模式选对应转义。脚本转换时如果搞错模式，会出现：
- DocxXML 写了 `\<name>` → 显示成字面 `\<name>`（多了反斜杠）
- Markdown 写了 `<name>` → 显示丢失（HTML 标签被解析）

## callout 关键词驱动

把"开头是 `**坑**` / `**注意**` / `**提示**` / `⚠️` / `💡` / `❗`"的段落自动升级为 callout：

```python
KEY_HINT_PREFIX = re.compile(r"^\s*(?:\*\*[^*]*坑[^*]*\*\*|\*\*[^*]*注意[^*]*\*\*|⚠️|❗|💡|❌|✅|📌|⭐|🏁)\s*[:：]?\s*")

def extract_hint_label(text):
    m = re.match(r"^\s*\*\*([^*]+)\*\*\s*[:：]?\s*(.*)$", text, re.DOTALL)
    if m:
        label, body = m.group(1).strip(), m.group(2).strip()
        emoji_map = {"坑": "⚠️", "注意": "⚠️", "提示": "💡", "重要": "❗",
                     "成功": "✅", "失败": "❌", "关键": "📌"}
        return emoji_map.get(label, "💡"), body
    return "💡", text
```

## 发布命令（DocxXML 路径）

```bash
# 1. 转换
python3 md_to_docx.py handbook.md handbook.docx.xml

# 2. 验证 XML 头部有 <title>
head -1 handbook.docx.xml   # 必须是 <title>xxx</title>

# 3. 发布（XML 自带标题，不需要 --new-title / --title）
cd /Users/xiesg/workspace
lark-cli docs +create --api-version v2 --doc-format xml --content @./handbook.docx.xml

# 4. 验证渲染效果
lark-cli docs +fetch --api-version v2 --doc <doc_id> --scope outline --detail with-ids
lark-cli docs +fetch --api-version v2 --doc <doc_id> --scope section --start-block-id <h2_id> --max-depth 3 --format pretty
```

## 踩坑清单

1. **exec 脚本里 `read_file` 工具**：`execute_code` 的 `read_file` 是工具不是函数，从 `hermes_tools` 导入时不会在脚本运行时可用。文件 I/O 一律用 `open()`/`read()`。

2. **`<th background-color="light-gray">` 飞书渲染吞属性**：fetch 回来的 block 里看不到 `background-color`，但底层接受了，**视觉上仍然有灰底**。别误以为失败。

3. **连续引用 `>` 行被合并成一段**：转换器要把每行 `>` 当独立 `<p>`，不要 join 成一段——视觉上会拥挤。

4. **关键提示段落升级 callout 后的颜色选择**：
   - `💡 提示/小贴士` → `light-yellow` + `yellow` 边
   - `⚠️ 坑/注意` → `light-red` + `yellow` 边
   - `❗ 重要` → `light-red` + `red` 边
   - `✅ 成功/完成` → `light-green` + `green` 边

5. **表格行数解析的边界**：`is_table_separator` 判断需要所有 cell 都匹配 `:?-+:?` 模式。空表分隔行（只有 `|`）会失败，导致表格降级为段落。

## 端到端最小工作流

1. 读源 md → 2. 转换器跑一遍 → 3. 验证 XML 头部 + 占位符转义 → 4. `lark-cli docs +create` 发布 → 5. `docs +fetch` 验证 → 6. 把 doc_id 和 URL 回报用户。
