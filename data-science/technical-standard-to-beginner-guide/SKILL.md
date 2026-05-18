---
name: technical-standard-to-beginner-guide
description: 将技术标准（扫描版PDF或文本件）系统化地转化为面向零基础入门者的讲解材料。当用户要求将技术标准文档改写成通俗版本、将专业标准转为人话、创建标准解读文档、将技术手册转成入门指南时使用。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [document-conversion, ocr, feishu-doc, content-generation, technical-writing]
    related_skills: [pdf-to-qa-csv, lark-doc, ocr-and-documents]
---

# 技术标准 → 入门者指南

## Overview

将一份技术标准文档（扫描版PDF或文本件）系统化地转化为面向零基础读者的入门讲解材料。完整流程覆盖：PDF 提取 → 内容生成 → 飞书写入 → 修订验证。

**输入：** 技术标准 PDF（扫描件或文本件）
**输出：** 飞书在线文档（6模块结构）

---

## When to Use

- 用户要求"把这个标准写成入门版本"、"翻译成大白话"
- 用户要求"创建 XX 标准的解读文档"
- 用户上传了一份技术标准 PDF，要求生成学习材料
- 用户提到"类比"、"入门"、"通俗"等关键词搭配标准文档

**不适用于：**
- 只需要 QA 对数据集 → 用 `pdf-to-qa-csv` 或 `pdf-chapter-qa-pipeline`
- 只需要术语提取 → 单独处理，无需完整流程

---

## 完整流程

```
第1步：PDF 提取
  ├── 文本件 → pdftotext
  └── 扫描件 → pymupdf 导出图片 + Tesseract OCR
  → 输出：原文 OCR 文本文件

第2步：内容生成（4层结构 × 6模块）
  ├── 先导篇：背景动机
  ├── 术语篇：核心概念速查表
  ├── 逐章解读：按原文章节顺序
  ├── 表格解读：查询指南
  ├── 流程篇：实战应用
  └── 思考题（可选）
  → 输出：6个 Markdown 文件

第3步：整合为单一文档
  → 合并为一个 ~50KB 的完整解读文件

第4步：飞书写入
  ├── <10KB → 直接 lark-doc 写入
  ├── ≥10KB → drive import → 分块修订
  └── 表格为主 → lark-sheets
  → 输出：飞书在线文档 URL

第5步：修订与验证
  ├── str_replace 修订
  ├── 原文对照纠错
  └── 权限确认
```

---

## Step-by-Step

### Step 1：PDF 提取

**判断类型：**

```python
import fitz
doc = fitz.open("标准.pdf")
text = doc[0].get_text()
has_text = bool(text.strip())
```

**文本件（has_text=True）：**
```bash
pdftotext -layout 标准.pdf 输出.txt
```

**扫描件（has_text=False）：**

用 pymupdf + Tesseract（marker-pdf 容易超时）：
```python
import fitz, subprocess, os

doc = fitz.open("扫描件.pdf")
pages = []
for i, page in enumerate(doc):
    mat = fitz.Matrix(300/72, 300/72)
    pix = page.get_pixmap(matrix=mat)
    img_path = f"/tmp/ocr_page_{i:03d}.png"
    pix.save(img_path)
    subprocess.run(["tesseract", img_path, "/tmp/ocr_page"], capture_output=True)
    with open("/tmp/ocr_page.txt") as f:
        pages.append(f.read())
    os.remove(img_path)

full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages)
```

**确认语言包：**
```bash
tesseract --list-langs  # 确认包含 chi_sim
```

---

### Step 2：内容生成

内容生成方法论见 `references/content_guide.md`，核心原则：

**4层结构：**
| 层次 | 内容 |
|------|------|
| 第1层：背景动机 | 行业背景、解决问题、适合谁看 |
| 第2层：核心概念 | 术语速查表（15~20个），每个配类比 |
| 第3层：逐章正文 | 按原文章节，关键条款翻译+场景举例 |
| 第4层：实战应用 | 表格查询指南、完整流程、思考题 |

**关键原则：**
- 每个术语首次出现必须配生活类比
- 关键数据（温度/时间/牌号）必须从原文来，不凭记忆
- 表格空白格（"-"）≠ "无"，需从上下文判断真实含义
- 保持口语感，不要写成说明书

**并行生成策略：**
6个模块可以并行生成（`delegate_task`），但大文档建议直接在主会话生成，避免 429 限流。

---

### Step 3：整合文档

将 6 个模块合并为单一 Markdown 文件：
- 文件路径：`/root/workspace/<标准号>-完整解读.md`
- 大小：通常 40~60KB
- 结构：先导篇 → 术语篇 → 逐章解读 → 表格解读 → 流程篇 → 思考题

---

### Step 4：飞书写入路径决策

```
文档大小？
├── < 10KB → 用 lark-doc 直接写入（docs +new → docs +update str_replace）
├── ≥ 10KB → 先用 lark-drive import 上传本地文件，再分块修订
└── 表格为主 → 用 lark-sheets（sheets +new → sheets +append）
```

**权限处理：**
- 创建时加 `--remove-old-owner false`，避免 bot 成 owner
- 导入后手动/通过 API 把 full_access 授予目标用户

详见 `references/toolchain.md`

---

### Step 5：修订与验证

**str_replace 原则：**
- 只用纯中文短句（不含 block ID）
- 匹配文本必须在文档中唯一
- 不要跨多行，不要包含标点符号

**常见错误处理：**
| 错误码 | 原因 | 处理 |
|--------|------|------|
| 1013 | pattern not found | 用 `docs +read full` 确认确切原文 |
| 1003 | permission denied | 重新授予 bot full_access |
| 99991663 | unknown block type | 改用 paragraph 或 table 类型 |

详见 `references/feishu_revision_guide.md`

**验证清单：**
- [ ] 字符数与原文规模相符（不过度精简）
- [ ] 核心术语覆盖率 ≥ 80%
- [ ] 每2000字至少1个类比
- [ ] 关键数据与原文一致
- [ ] 表格空白格含义正确
- [ ] 用户对文档有 read 权限

---

## Common Pitfalls

1. **marker-pdf 超时**：扫描件 OCR 放弃 marker-pdf，直接用 pymupdf + Tesseract
2. **429 限流**：大内容生成不走子任务并行，直接主会话执行
3. **术语循环解释**：术语篇不用术语 A 解释术语 B，必须配生活类比
4. **表格空白格误解**：空白 = "无数据/不适用"，不是"零"
5. **str_replace 跨块**：只替换单一 block 内容，不跨多行
6. **原文数据凭记忆**：关键数据必须 grep 原文确认，不用记忆中的数字
7. **渲染器手敲硬编码**：知识库 YAML 正确 ≠ 输出正确。渲染层若手写字符串，知识库的修改不会反映到输出，且错误难以发现。正确做法：diagnose.py 注入数据 → render_card.py 只读 result，从不手敲知识内容。详见 `references/rendering_architecture.md`

---

## Verification Checklist

- [ ] PDF 提取完成，字符数合理（文本件用 pdftotext，扫描件用 pymupdf+Tesseract）
- [ ] 6个模块内容完整，4层结构覆盖完整
- [ ] 类比数量充足，无术语循环解释
- [ ] 关键数据与原文一致（grep 验证）
- [ ] 文档合并后 40~60KB
- [ ] 飞书写入成功，权限正确
- [ ] str_replace 修订完成，无 1013 错误残留
- [ ] 渲染器从 YAML 读取，不存在手写硬编码（新增渲染函数后必查 `alloy ==` / `state ==` 模式）
- [ ] 文档可读，格式正确
- [ ] 渲染器从 YAML 读取，不存在手写硬编码（新增渲染函数后必查）