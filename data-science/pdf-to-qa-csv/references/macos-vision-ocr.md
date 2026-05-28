# macOS Vision OCR 参考（模式 C：图片型 PDF，无需 tesseract）

## 适用场景
- macOS 系统（未安装 tesseract）
- 图片型/扫描型 PDF，pdftotext 提取不到文本
- 支持中文（简体/繁体）、英文混合识别

## 核心工具
macOS 内置 Vision framework，通过 Swift 调用，无需任何第三方 OCR 工具。

## 工作流程

### Step 1: 渲染 PDF 页面为图片
```python
import fitz  # PyMuPDF

pdf_path = "/path/to/document.pdf"
doc = fitz.open(pdf_path)
os.makedirs('/tmp/pdf_pages', exist_ok=True)

mat = fitz.Matrix(2.0, 2.0)  # 2x zoom
for i in range(len(doc)):
    page = doc[i]
    pix = page.get_pixmap(matrix=mat)
    pix.save(f"/tmp/pdf_pages/p{i+1:03d}.png")
doc.close()
```

### Step 2: 编译 OCR 二进制
```bash
swiftc /path/to/vision_ocr_main.swift -o /tmp/vision_ocr_main_bin
```

**`/tmp/vision_ocr_main.swift`（必须使用此版本）：**
```swift
import Vision
import AppKit

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("Usage: vision_ocr <image> <output>\n".data(using: .utf8)!)
    exit(1)
}

let imgPath = args[1]
let outPath = args[2]

guard let img = NSImage(contentsOfFile: imgPath) else {
    FileHandle.standardError.write("Cannot load image\n".data(using: .utf8)!)
    exit(1)
}

var rect = NSRect.zero
guard let cgImg = img.cgImage(forProposedRect: &rect, context: nil, hints: [:]) else {
    FileHandle.standardError.write("Cannot get CGImage\n".data(using: .utf8)!)
    exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false

// ✅ 关键：指定语言，否则中文全部乱码
request.recognitionLanguages = ["zh-Hans", "zh-Hant", "en-US"]

let handler = VNImageRequestHandler(cgImage: cgImg, options: [:])
do {
    try handler.perform([request])
} catch {
    let msg = "OCR error: \(error)\n".data(using: .utf8)!
    FileHandle.standardError.write(msg)
    exit(1)
}

guard let results = request.results else {
    exit(0)
}

var output = ""
for r in results {
    if let text = r.topCandidates(1).first?.string {
        output += text + "\n"
    }
}

do {
    try output.write(toFile: outPath, atomically: true, encoding: .utf8)
} catch {
    let msg = "Write error: \(error)\n".data(using: .utf8)!
    FileHandle.standardError.write(msg)
    exit(1)
}
```

### Step 3: 批量 OCR
```python
import subprocess, os

binary = '/tmp/vision_ocr_main_bin'
pages_dir = '/tmp/pdf_pages'
output_dir = '/tmp/ocr_output'
os.makedirs(output_dir, exist_ok=True)

total = 270  # 调整
for pg in range(1, total + 1):
    img_file = f"{pages_dir}/p{pg:03d}.png"
    out_file = f"{output_dir}/p{pg:03d}.txt"
    subprocess.run([binary, img_file, out_file], timeout=60)
    if pg % 50 == 0:
        print(f"Processed {pg}/{total}")
```

### Step 4: 收集全文
```python
all_text = {}
for pg in range(1, total + 1):
    path = f"/tmp/ocr_output/p{pg:03d}.txt"
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            all_text[pg] = f.read()

full_text = '\n'.join([all_text.get(i, '') for i in range(1, total + 1)])
```

## 关键陷阱

| 陷阱 | 错误表现 | 解法 |
|------|----------|------|
| **未指定语言** | 中文全部乱码（如 `RaanHai%`） | 必须设置 `recognitionLanguages` |
| **未设置语言列表顺序** | 英文优先时中文仍乱码 | `["zh-Hans", "zh-Hant", "en-US"]` 排前 |
| **低分辨率渲染** | OCR 质量差 | 用 `Matrix(3.0, 3.0)` 或更高 |
| **swiftc 编译报错（print to stderr）** | Swift 5.8 不支持 `print(..., to: &stderr)` | 用 `FileHandle.standardError.write()` |
| **execute_code 环境无 fitz** | `ModuleNotFoundError: fitz` | 用 `/opt/miniconda3/bin/python3` 作为解释器 |

## 质量对比（同一页中文教科书）

| 设置 | 结果 |
|------|------|
| 无 `recognitionLanguages` | `RaanHai% i im B H # #h # Sf J} RAMAISIE Ahe` |
| 设置 `["zh-Hans", "zh-Hant", "en-US"]` | `2019 全国优秀教材特等奖 人民教育出版社 普通高中教科书 数学 必修 第一册 A版` |

## 执行环境
- Python: `/opt/miniconda3/bin/python3`（内置 PyMuPDF 1.27.2）
- Swift: `/usr/bin/swiftc`（Apple Swift 5.8.1）
- 路径说明：`execute_code` 的 Python 环境无 fitz，terminal 直接调用的 conda python 有 fitz