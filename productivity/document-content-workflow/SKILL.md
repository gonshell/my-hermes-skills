---
name: document-content-workflow
description: "文档内容工作流：从文档素材（飞书、PDF、文章等）提取内容、生成PPT、或发布到飞书的完整管道。覆盖：内容提炼 → 大纲设计 → 工具选型 → python-pptx生成 → 飞书发布。触发：生成PPT、创建演示文稿、从XX材料做PPT、将XX内容做成幻灯片。"
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [document, ppt, powerpoint, ocr, feishu, productivity, content-creation]
    absorbed: [ppt-from-document, ocr-and-documents, lark-doc-pitfalls]
---

# 文档内容工作流

从文档素材（飞书文档、PDF、文章等）提取内容 → 生成完整演示文稿或发布到飞书的完整管道。

## 内容提炼 → PPT 生成

### `ppt-from-document`（主 skill）

从文档素材生成完整 PPT 的完整工作流。

**适用场景**：用户提供了长篇素材（飞书文档、技术报告、文章等），需要：
- 提炼主题，设计 PPT 大纲
- 生成完整多页演示文稿（20+页）
- 每页包含"展示内容"和"怎么讲"的演讲提示

**工具选型**：

| 场景 | 推荐工具 |
|------|----------|
| 20页以下，有模板参考 | PptxGenJS（参考 pptx-generator skill） |
| 20页以上，内容由AI全量生成 | python-pptx |
| 复杂中文内容精确排版 | python-pptx |

**python-pptx 生成要点**：
1. 生成后**先做语法验证**：`python3 -c "import ast; ast.parse(open('generate_ppt.py').read())"`
2. 常见错误：嵌入引号、walrus operator、段落索引越界
3. 运行后用 `python3 -m markitdown output.pptx` 验证内容

详见 `references/ppt-from-document.md`

### `ocr-and-documents`（支持 skill）

从 PDF/扫描件提取文本。使用 macOS Vision 框架：

```bash
# macOS Vision OCR
swift -framework Vision -framework AppKit ...  # 见 references/macos-vision-ocr-swift-workflow.md
```

详见 `references/ocr-and-documents.md`

---

## 飞书文档操作

### `lark-doc-pitfalls`（必读参考）

飞书文档操作的高风险踩坑点记录。**遇到飞书文档操作问题时先查此处**。

核心 Pitfall：
1. **`overwrite` 必须带 `--doc-format markdown`**（否则内容不生效，静默降级）
2. **`--content @<filepath>` 必须用相对路径**（禁止 `@/absolute/path`）
3. **XML 内容禁止包含 `<title>` 标签**（会覆盖文档 UI 标题）
4. **LaTeX `\text{}` 渲染失败** — 用纯文字替代
5. **`block_insert_after` 依赖已知 block_id**，必须先 fetch
6. **`docs +create --title` 必须同时传 `--content`**
7. **大段内容用文件引用，不用 heredoc**
8. **Mermaid 多行换行太多会导致 whiteboard 解析失败**

详见 `references/lark-doc-pitfalls.md`

---

## 视觉设计（PPT 配色）

### 四大流派四色系统（AI 流派类 PPT）

| 流派 | 颜色 | Hex |
|------|------|-----|
| 符号主义 | 深邃藏蓝 | `#1E3A5F` |
| 连接主义 | 森林绿 | `#2D5A27` |
| 概率主义 | 琥珀金 | `#8B6914` |
| 行为主义 | 深绯红 | `#8B1A1A` |
| 融合/强调 | 靛蓝紫 | `#6366F1` |

### 中性色

| 用途 | Hex |
|------|-----|
| 浅背景 | `#FAFBFC` |
| 卡片背景 | `#F4F6F8` |
| 深背景 | `#1A1D21` |
| 标题文字 | `#1F2937` |
| 正文文字 | `#374151` |
| 次要文字 | `#6B7280` |

---

## 触发条件

- "生成PPT"、"创建演示文稿"、"根据XX材料做PPT" → `ppt-from-document`
- "从PDF/扫描件提取文字" → `ocr-and-documents`
- 飞书文档操作问题 → 先查 `lark-doc-pitfalls`