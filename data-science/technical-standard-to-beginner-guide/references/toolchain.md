# 工具链：PDF → OCR → 飞书写入 → 验证 → 纠错

---

## 1. PDF 检测与预处理

### 判断是扫描件还是文本件

先用 pymupdf 提取一段文字，检测是否有内容：

```python
import fitz
doc = fitz.open("标准.pdf")
text = doc[0].get_text()
if text.strip():
    # 有文字层 → 文本件，直接用 pdftotext
else:
    # 无文字层 → 扫描件，走 OCR
```

### 扫描件 vs 文本件 处理路径

| 类型 | 工具 | 命令 |
|------|------|------|
| 文本件 | pdftotext | `pdftotext -layout 标准.pdf 输出.txt` |
| 扫描件 | pymupdf 图片 + Tesseract | 见下方 OCR 流程 |

### 扫描件 OCR 流程（推荐）

marker-pdf 容易超时，用 pymupdf + Tesseract 更稳定：

```python
import fitz, subprocess, os

doc = fitz.open("扫描件.pdf")
pages = []
for i, page in enumerate(doc):
    # 导出 300 DPI PNG
    mat = fitz.Matrix(300/72, 300/72)
    pix = page.get_pixmap(matrix=mat)
    img_path = f"/tmp/ocr_page_{i:03d}.png"
    pix.save(img_path)
    
    # Tesseract OCR
    result = subprocess.run(
        ["tesseract", img_path, "/tmp/ocr_page"],
        capture_output=True, text=True
    )
    with open("/tmp/ocr_page.txt") as f:
        pages.append(f.read())
    os.remove(img_path)

full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages)
```

**Tesseract 语言包：** 标准技术中文+英文混排需要 `chi_sim+eng`，首次运行前确认已安装：
```bash
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
```

---

## 2. 飞书写入路径决策树

```
原文字符数？
├── < 10KB → 直接用 lark-doc 的简单写入
├── ≥ 10KB → 走 drive import 流程（分块写入）
└── 表格为主 → 考虑 lark-sheets 创建表格，然后 append rows
```

### 路径 A：直接写入（< 10KB）

用 `lark-doc` 的 `docs +new` 创建文档，然后逐块写入。

### 路径 B：Drive Import（≥ 10KB）

当文档较大时，用本地文件导入飞书云空间，避免 API 分片写入的复杂性：

1. 先在飞书云空间找目标文件夹（用 `lark-drive` 的 `docs +search`）
2. 用 `lark-cli drive upload` 或 API 上传本地文件（支持 docx/xlsx）
3. 导入后用 `lark-doc` 的 `docs +update` 逐块修订

### 路径 C：表格为主

用 `lark-sheets` 的 `sheets +new` 创建表格，再用 `sheets +append` 追加数据行。

---

## 3. 权限转移两步法

导入文档后默认 owner 是 bot，需要转移给实际用户：

**第一步：** 创建时带 `remove_old_owner: false`，避免 bot 自动成 owner：
```
lark-cli docs create --title "xxx" --folder-token <folder_token> --remove-old-owner false
```

**第二步：** 导入完成后，通过飞书界面或 API 把 full_access 权限授予目标用户。

**验证：** 用 `lark-cli docs info` 查看权限列表，确认用户有 full_access。

---

## 4. 原文 vs 产出对照纠错流程

### 4.1 术语一致性核对

对每个关键术语，在原文 OCR 中 grep，核对该术语在产出文档中的定义是否一致：

```bash
grep -n "固溶" HB5480-1991_原文.txt
# 确认产出文档中"固溶处理"的定义与原文一致
```

### 4.2 数据点核对

关键数据（温度/时间/百分比/牌号）必须逐条验证：

```python
# 伪代码：数据点核对
original_data = {
    "ZL101A 抗拉强度": "≥310 MPa",
    "T6 固溶温度": "530±5℃",
    "T6 时效温度": "175±5℃",
}
for term, value in original_data.items():
    assert value in 产出文档, f"数据不一致: {term}"
```

### 4.3 表格空白格核对

表格中"-"表示"无数据"或"不适用"，不是"零"：
- 空白 = 该牌号该指标不要求，不是强度为0
- 遇到空白格必须从上下文判断真实含义

---

## 5. 验证检查点

| 检查项 | 标准 |
|--------|------|
| 字符数 | 原文 ~50KB → 产出 ~40-60KB（适当精简但不离谱） |
| 术语覆盖率 | 术语篇应覆盖原文 80%+ 的核心术语 |
| 类比数量 | 平均每2000字至少1个类比 |
| 原文引用 | 关键条款有原文对照，不是凭空写 |
| 无术语循环 | 术语篇没有用"术语A解释术语B"的情况 |