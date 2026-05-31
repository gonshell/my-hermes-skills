# lark-doc-pitfalls 核心参考

> 飞书文档操作的高风险踩坑点。遇到飞书文档操作问题时先查此处。

## 最高频 Pitfall（必须背熟）

### `overwrite` + Markdown 内容必须带 `--doc-format markdown`

否则 API 返回 `partial_success` + warning `"Instruction produced no document changes"`，文档内容**完全不更新**。

```bash
# 错误 ❌
lark-cli docs +update --api-version v2 --doc "<doc_id>" --command overwrite --content @./lark_content.md

# 正确 ✅
lark-cli docs +update --api-version v2 --doc "<doc_id>" --command overwrite --doc-format markdown --content @./lark_content.md
```

### `--content @<filepath>` 必须用相对路径

```bash
# 错误 ❌
--content @/tmp/file.xml

# 正确 ✅
cp /tmp/content.xml ./content.xml
--content @./content.xml
```

### XML 内容禁止包含 `<title>` 标签

`<title>xxx</title>` 会被飞书解析为文档标题，覆盖手动设置的标题。每次 overwrite 后 `+fetch` 返回 `title: "Untitled"`。

```xml
<!-- ❌ 禁止 -->
<title>YouTube AI热门视频</title>
<h1>YouTube AI热门视频</h1>

<!-- ✅ 正确 -->
<!-- 每日AI热门视频推送 | 2026-05-29 21:00:00 -->
<h1>YouTube AI热门视频</h1>
```

## 标题修改

**`+update --new-title` 无法修改 UI 标题**（v1 API 写入成功但 fetch 返回 null；v2 API 根本不支持）。

用户偏好解法：**删除重建**
```bash
lark-cli drive +delete --file-token "<token>" --type docx --yes
lark-cli docs +create --api-version v2 --title "新标题" --content @./file.xml --doc-format xml
```

## 删除文档

```bash
lark-cli api DELETE "/open-apis/drive/v1/files/<token>?type=docx" --params '{"type":"docx"}'
```

## 代码块写入

| 标签格式 | Feishu Block Type | `append` |
|----------|-------------------|----------|
| `<code_block>...</code_block>` | `code_block` | ❌ 内容丢失 |
| `<pre lang="x"><code>...</code></pre>` | `paragraph` | ✅ 正确 |

```python
def md_code_block_to_feishu_xml(code_text: str, lang: str) -> str:
    escaped = code_text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
    if lang:
        return f'<pre lang="{lang}"><code>\n{escaped}\n</code></pre>'
    else:
        return f'<pre><code>\n{escaped}\n</code></pre>'
```

## LaTeX 渲染

飞书使用 KaTeX 子集，**不支持 `\text{}`、`\mbox{}`、`\mathrm{}`**。

```latex
% 错误
$\pi \text{ 弧度} = 180°$

% 正确
$\pi 弧度 = 180°$
```

## 并行 Agent append 陷阱

1. **骨架 + 并行追加 → 内容重复**：骨架中占位标题/段落会保留，与 Agent 追加内容重复。解法：骨架只放 title + callout，不放章节标题。
2. **并行 append → 嵌套层级错误**：append 的内容嵌套在上一章节的子树中。解法：用 `overwrite` 重建 block 树。

## `block_insert_after` 必须先 fetch

```python
# 找到目标 block 的 id
match = re.search(r'<h2[^>]*id="([^"]+)"[^>]*>01 产品概述</h2>', content)
block_id = match.group(1)
```