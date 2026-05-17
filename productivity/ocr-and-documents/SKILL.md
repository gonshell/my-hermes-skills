---
name: ocr-and-documents
description: "Extract text from PDFs/scans (pymupdf, marker-pdf)."
version: 2.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [PDF, Documents, Research, Arxiv, Text-Extraction, OCR]
    related_skills: [powerpoint]
---

# PDF & Document Extraction

For DOCX: use `python-docx` (parses actual document structure, far better than OCR).
For PPTX: see the `powerpoint` skill (uses `python-pptx` with full slide/notes support).
This skill covers **PDFs and scanned documents**.

## Step 1: Remote URL Available?

If the document has a URL, **always try `web_extract` first**:

```
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
web_extract(urls=["https://example.com/report.pdf"])
```

This handles PDF-to-markdown conversion via Firecrawl with no local dependencies.

Only use local extraction when: the file is local, web_extract fails, or you need batch processing.

## Step 2: Choose Local Extractor

| Feature | pymupdf (~25MB) | marker-pdf (~3-5GB) |
|---------|-----------------|---------------------|
| **Text-based PDF** | ✅ | ✅ |
| **Scanned PDF (OCR)** | ❌ | ✅ (90+ languages) |
| **Tables** | ✅ (basic) | ✅ (high accuracy) |
| **Equations / LaTeX** | ❌ | ✅ |
| **Code blocks** | ❌ | ✅ |
| **Forms** | ❌ | ✅ |
| **Headers/footers removal** | ❌ | ✅ |
| **Reading order detection** | ❌ | ✅ |
| **Images extraction** | ✅ (embedded) | ✅ (with context) |
| **Images → text (OCR)** | ❌ | ✅ |
| **EPUB** | ✅ | ✅ |
| **Markdown output** | ✅ (via pymupdf4llm) | ✅ (native, higher quality) |
| **Install size** | ~25MB | ~3-5GB (PyTorch + models) |
| **Speed** | Instant | ~1-14s/page (CPU), ~0.2s/page (GPU) |

**Decision**: Use pymupdf unless you need OCR, equations, forms, or complex layout analysis.

If the user needs marker capabilities but the system lacks ~5GB free disk:
> "This document needs OCR/advanced extraction (marker-pdf), which requires ~5GB for PyTorch and models. Your system has [X]GB free. Options: free up space, provide a URL so I can use web_extract, or I can try pymupdf which works for text-based PDFs but not scanned documents or equations."

---

## pymupdf (lightweight)

```bash
pip install pymupdf pymupdf4llm
```

**Via helper script**:
```bash
python scripts/extract_pymupdf.py document.pdf              # Plain text
python scripts/extract_pymupdf.py document.pdf --markdown    # Markdown
python scripts/extract_pymupdf.py document.pdf --tables      # Tables
python scripts/extract_pymupdf.py document.pdf --images out/ # Extract images
python scripts/extract_pymupdf.py document.pdf --metadata    # Title, author, pages
python scripts/extract_pymupdf.py document.pdf --pages 0-4   # Specific pages
```

**Inline**:
```bash
python3 -c "
import pymupdf
doc = pymupdf.open('document.pdf')
for page in doc:
    print(page.get_text())
"
```

---

## macOS Vision Framework OCR (built-in, no install needed)

When pymupdf extracts **zero text** (scanned/image PDF with no OCR layer), use the
built-in Vision framework on macOS to OCR rendered pages. Requires **no additional
package installation** and works for 90+ languages including Chinese.

**Step 1 — Render PDF pages to PNG** (find the right Python with pymupdf first):
```bash
# Try system Python3 first; install pymupdf if needed
/usr/local/bin/python3 -c "import pymupdf; print(pymupdf.__version__)" 2>/dev/null || \
  /usr/local/bin/python3 -m pip install pymupdf --break-system-packages -q

# Render all pages, identify content pages by file size
/usr/local/bin/python3 -c "
import pymupdf, os
doc = pymupdf.open('document.pdf')
os.makedirs('/tmp/pdf_pages', exist_ok=True)
for i in range(len(doc)):
    pix = doc[i].get_pixmap(dpi=150)
    pix.save(f'/tmp/pdf_pages/page_{i+1:04d}.png')
doc.close()
"
```

**Step 2 — Compile the Vision OCR program** (one-time, keep binary at `/tmp/ocr_test`):
```bash
cat > /tmp/ocr_test.m << 'EOF'
#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <AppKit/AppKit.h>

int main(int argc, char *argv[]) {
    @autoreleasepool {
        if (argc < 3) { NSLog(@"Usage: %s <image_path> <lang>", argv[0]); return 1; }
        NSString *path = [NSString stringWithUTF8String:argv[1]];
        NSString *lang = [NSString stringWithUTF8String:argv[2]];
        NSImage *image = [[NSImage alloc] initWithContentsOfFile:path];
        CGImageRef cgImage = [image CGImageForProposedRect:NULL context:nil hints:nil];
        if (!cgImage) { NSLog(@"Failed CGImage"); return 1; }
        VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] init];
        [request setRecognitionLevel:VNRequestTextRecognitionLevelAccurate];
        [request setUsesLanguageCorrection:NO];
        [request setRecognitionLanguages:@[lang]];
        VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:cgImage options:@{}];
        NSError *error = nil;
        if (![handler performRequests:@[request] error:&error]) {
            NSLog(@"OCR failed: %@", error); return 1;
        }
        for (VNRecognizedTextObservation *obs in [request results]) {
            for (VNRecognizedText *candidate in [obs topCandidates:1]) {
                printf("%s\n", [[candidate string] UTF8String]);
            }
        }
    }
    return 0;
}
EOF

clang -o /tmp/ocr_test /tmp/ocr_test.m \
  -framework Vision -framework AppKit -framework CoreGraphics \
  -isysroot $(xcrun --show-sdk-path --sdk macosx)
```

**Step 3 — Run OCR on any rendered PNG**:
```bash
/tmp/ocr_test /tmp/pdf_pages/page_0005.png "zh-Hans"
```

**Find content pages fast** (no OCR needed for blank pages):
```bash
# Pages with largest PNG files have the most content
ls -la /tmp/pdf_pages/*.png | sort -k5 -nr | head -20
# Then OCR only the interesting ones
/tmp/ocr_test /tmp/pdf_pages/page_0005.png "zh-Hans"
```

**Language codes**: `"zh-Hans"` (Simplified Chinese), `"zh-Hant"` (Traditional),
`"en-US"`, `"ja-JP"`, `"ko-KR"`, etc. Omit `setRecognitionLanguages:` to
auto-detect (less reliable for mixed-language docs).

**Key insight**: pymupdf returns `len(page.get_text()) == 0` for scanned pages.
Use rendered PNG file size to identify which pages have content, then OCR only those.
The Vision framework is pre-installed on every macOS system — no pip install needed.

---

## marker-pdf (high-quality OCR)

```bash
# Check disk space first
python scripts/extract_marker.py --check

pip install marker-pdf
```

**Via helper script**:
```bash
python scripts/extract_marker.py document.pdf                # Markdown
python scripts/extract_marker.py document.pdf --json         # JSON with metadata
python scripts/extract_marker.py document.pdf --output_dir out/  # Save images
python scripts/extract_marker.py scanned.pdf                 # Scanned PDF (OCR)
python scripts/extract_marker.py document.pdf --use_llm      # LLM-boosted accuracy
```

**CLI** (installed with marker-pdf):
```bash
marker_single document.pdf --output_dir ./output
marker /path/to/folder --workers 4    # Batch
```

---

## Arxiv Papers

```
# Abstract only (fast)
web_extract(urls=["https://arxiv.org/abs/2402.03300"])

# Full paper
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])

# Search
web_search(query="arxiv GRPO reinforcement learning 2026")
```

## Split, Merge & Search

pymupdf handles these natively — use `execute_code` or inline Python:

```python
# Split: extract pages 1-5 to a new PDF
import pymupdf
doc = pymupdf.open("report.pdf")
new = pymupdf.open()
for i in range(5):
    new.insert_pdf(doc, from_page=i, to_page=i)
new.save("pages_1-5.pdf")
```

```python
# Merge multiple PDFs
import pymupdf
result = pymupdf.open()
for path in ["a.pdf", "b.pdf", "c.pdf"]:
    result.insert_pdf(pymupdf.open(path))
result.save("merged.pdf")
```

```python
# Search for text across all pages
import pymupdf
doc = pymupdf.open("report.pdf")
for i, page in enumerate(doc):
    results = page.search_for("revenue")
    if results:
        print(f"Page {i+1}: {len(results)} match(es)")
        print(page.get_text("text"))
```

No extra dependencies needed — pymupdf covers split, merge, search, and text extraction in one package.

---

## Notes

- `web_extract` is always first choice for URLs
- pymupdf is the safe default — instant, no models, works everywhere
- marker-pdf is for OCR, scanned docs, equations, complex layouts — install only when needed
- Both helper scripts accept `--help` for full usage
- marker-pdf downloads ~2.5GB of models to `~/.cache/huggingface/` on first use
- For Word docs: `pip install python-docx` (better than OCR — parses actual structure)
- For PowerPoint: see the `powerpoint` skill (uses python-pptx)
- For macOS Python environments: see `references/python-env-macos.md` for finding the right
  Python interpreter (system vs. hermes venv) and installing packages without pip conflicts.
- **macOS Vision OCR full workflow**: see `references/macos-vision-ocr-full-workflow.md` — complete
  6-step workflow for 200+ page scanned PDFs, including parallel batch OCR and content-page
  identification via PNG file size. Compile once to `/tmp/ocr_test` then reuse.
- **macOS execute_code sandbox**: pymupdf not available in the UV sandbox Python; use
  `terminal()` with `/usr/local/bin/python3` for pymupdf access. See `references/macos-python-env.md`.
- **macOS Vision OCR full workflow**: see `references/macos-vision-ocr-full-workflow.md` — complete
  6-step workflow for 200+ page scanned PDFs, including parallel batch OCR and content-page
  identification via PNG file size.
