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

## 2. `--content @<filepath>` 必须用相对路径

**问题**：`--content @/tmp/file.xml` 报错：`--file must be a relative path within the current directory`

**解法**：先复制到当前目录再用相对路径引用：
```bash
cp /tmp/content.xml ./content.xml
lark-cli docs +update --api-version v2 --doc "<doc_id>" --command append \
  --content @./content.xml
```

---

## 3. 删除文档用通用 API，不是 `docs +delete`

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

## 6. 大段内容用文件引用，不用 heredoc 内联

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