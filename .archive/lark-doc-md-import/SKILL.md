---
name: lark-doc-md-import
version: 1.0.0
description: "飞书文档 Markdown 多文件导入预处理：当用户提供多个本地 .md 文件要求合并写入飞书文档时，必须先预处理（剥离 YAML frontmatter、转换 Obsidian callout、合并文件）再调用 docs +create。依赖 lark-doc skill。"
metadata:
  requires:
    bins: ["lark-cli"]
    skills: ["lark-doc"]
---

# lark-doc / Markdown 导入预处理参考

当用户要求将多个本地 `.md` 文件合并写入飞书文档时，必须先预处理，否则飞书会解析失败或格式错乱。

## 必须预处理的问题

| 问题 | 原因 | 预处理方法 |
|------|------|-----------|
| **YAML frontmatter** | `---` 包裹的元数据块在飞书 Markdown 下会被解析为正文导致乱码 | 剥离所有 `---` 包裹的 frontmatter：找到内容中第 2 个 `\n---\n` 的位置（含结束 `---` 本身），全部删除 |
| **Obsidian Callout 语法** `> [!NOTE]` | 飞书不支持 `> [!KIND]` 语法，会原样显示为普通文本 | 用正则转换为标准引用块：`re.sub(r'^> \[!([^\]]+)\]\s*([^\n]*)\n', fix_callout, content, flags=re.MULTILINE)`；`[!NOTE]` → `[补充说明]`，`[!WARNING]` → `[警告]`，以此类推 |
| **多个文件合并时的文档标题** | 飞书从第一个 H1 自动提取为文档标题；`<title>` XML 仅在 XML 格式下生效 | 文件之间用 `\n\n---\n\n` 分隔符连接；文档标题从第一个 H1 自动提取，**不要**在内容中重复写标题 |
| **ASCII 架构图变成乱码** | 非代码块的 ASCII box drawing 字符（`┌─┐│└┘` 等）会被飞书按表格/特殊符号解析 | 确认所有 ASCII 图表都在 ` ``` ` 代码块内；检查方式：在代码块外寻找含 3+ 种 box drawing 字符的行 |
| **文档标题显示"Untitled"** | 飞书从 Markdown 导入时，`<title>` XML 标签不会被识别；飞书使用第一个 H1 作为标题 | 导入后立即用 XML str_replace 修复：先 fetch 获取 block ID，再用 `--command str_replace --doc-format xml --pattern "Untitled" --content "真实标题"` 修复 |

## 合并写入标准流程（Python 预处理脚本）

```python
import re, os

def preprocess_md_for_lark(input_paths, output_path):
    """
    预处理本地 .md 文件用于飞书文档导入。
    1. 剥离 YAML frontmatter
    2. 转换 Obsidian callout 语法
    3. 合并文件（用分隔符）
    """
    callout_map = {
        'NOTE': '补充说明', 'WARNING': '⚠️ 警告', 'TIP': '💡 提示',
        'DANGER': '❗ 危险', 'INFO': 'ℹ️ 信息', 'SUCCESS': '✅ 成功',
    }
    def fix_callout(m):
        kind = m.group(1).upper()
        rest = m.group(2)
        label = callout_map.get(kind, kind)
        return f'> [{label}]{rest}'

    parts = []
    for path in input_paths:
        with open(path, 'r') as f:
            content = f.read()
        # Strip YAML frontmatter
        if content.startswith('---'):
            end = content.find('\n---\n', 4)
            if end != -1:
                content = content[end+5:]
        # Fix Obsidian callouts
        content = re.sub(
            r'^> \[!([^\]]+)\]\s*([^\n]*)\n',
            fix_callout, content, flags=re.MULTILINE
        )
        parts.append(content.strip())

    merged = '\n\n---\n\n'.join(parts)
    with open(output_path, 'w') as f:
        f.write(merged)
    return output_path

# 用法
preprocess_md_for_lark([
    'ch01.md', 'ch02.md', 'ch03.md'
], '/tmp/merged.md')
```

## 写入后标题修复

```bash
# 1. 创建文档（获取 doc_id）
lark-cli docs +create --api-version v2 \
  --doc-format markdown \
  --parent-position my_library \
  --content @/tmp/merged.md

# 2. 获取标题 block ID
lark-cli docs +fetch \
  --api-version v2 --doc "$DOC_ID" \
  --detail with-ids 2>&1 | python3 -c "
import sys,json,re
d=json.load(sys.stdin)
blocks=d['data']['document']['content']
m=re.search(r'<title[^>]*id=\"([^\"]+)\"', blocks)
print(m.group(1) if m else '')
"

# 3. 修复标题（如显示"Untitled"）
lark-cli docs +update --api-version v2 \
  --doc "$DOC_ID" \
  --command str_replace \
  --doc-format xml \
  --pattern "Untitled" \
  --content "真实文档标题"
```

## 关键陷阱

- **YAML frontmatter 必须在文件级别剥离**，不能用 `docs +create --content @file.md` 直接导入而不预处理（飞书 Markdown 模式仍会解析 `---`）
- **分隔符用 `\n\n---\n\n`**（三个短横线在空行之间），不能用 `---\n` 单行（会被解析为分隔线而非章节标记）
- **callout 转换是行级别的**，正则须带 `flags=re.MULTILINE` 使 `^` 匹配每行开头
- **"Untitled" 修复必须用 XML str_replace**，Markdown str_replace 会匹配失败（因为文档内部是 XML 格式存储）
- **lark-doc SKILL.md 前置条件中引用了不存在的 `style/lark-doc-create-workflow.md`**，该文件不存在，应忽略；工作流文件位于 `references/` 目录下