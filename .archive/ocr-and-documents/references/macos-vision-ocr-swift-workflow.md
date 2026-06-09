# Vision OCR Swift Script (Tested on 270-page Math Textbook)

> Working Swift implementation for macOS Vision OCR. Compile once, reuse for all scanned PDFs.

## Compile

```bash
cat > /tmp/vision_ocr_main.swift << 'SWIFT'
import Foundation
import Vision
import AppKit
import CoreGraphics

let args = ProcessInfo.processInfo.arguments
guard args.count >= 3 else {
    fputs("Usage: vision_ocr_main <image_path> <lang>\n", stderr)
    exit(1)
}

let imagePath = args[1]
let lang = args[2]

guard let image = NSImage(contentsOfFile: imagePath),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fputs("Failed to load image: \(imagePath)\n", stderr)
    exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
request.recognitionLanguages = [lang]

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
var errored = false

do {
    try handler.perform([request])
} catch {
    fputs("OCR failed: \(error)\n", stderr)
    exit(1)
}

for obs in request.results ?? [] {
    guard let candidate = obs.topCandidates(1).first else { continue }
    print(candidate.string)
}
SWIFT

xcrun --show-sdk-path --sdk macosx > /dev/null 2>&1
clang -o /tmp/vision_ocr_main_bin /tmp/vision_ocr_main.swift \
  -framework Vision -framework AppKit -framework CoreFoundation \
  -isysroot $(xcrun --show-sdk-path --sdk macosx) \
  -O3   # optimizations on for 270× pages
```

## Run (single page)

```bash
# Simplified Chinese
/tmp/vision_ocr_main_bin /tmp/page_0001.png "zh-Hans"

/# English
/tmp/vision_ocr_main_bin /tmp/page_0001.png "en-US"
```

## Batch Process (parallel, 270 pages)

```bash
mkdir -p /tmp/math_ocr_zh

# Write a batch runner
cat > /tmp/run_ocr_batch.sh << 'BASH'
#!/bin/bash
DIR="$1"; START="$2"; END="$3"; LANG="$4"
for i in $(seq -f "%04g" "$START" "$END"); do
    /tmp/vision_ocr_main_bin "$DIR/p${i}.png" "$LANG" > "$DIR/p${i}.txt" 2>/dev/null
done
echo "Done: $START–$END"
BASH
chmod +x /tmp/run_ocr_batch.sh

# Split into 4 parallel jobs (e.g. 270 pages: 1-70, 71-140, 141-210, 211-270)
/tmp/run_ocr_batch.sh /tmp/math_ocr_zh 1   70  "zh-Hans" &
/tmp/run_ocr_batch.sh /tmp/math_ocr_zh 71  140  "zh-Hans" &
/tmp/run_ocr_batch.sh /tmp/math_ocr_zh 141 210  "zh-Hans" &
/tmp/run_ocr_batch.sh /tmp/math_ocr_zh 211 270  "zh-Hans" &
wait
echo "ALL BATCHES DONE"
```

## Render PDF Pages to PNG (300 DPI for math)

```bash
/opt/miniconda3/bin/python3 -c "
import pymupdf, os
doc = pymupdf.open('/Users/xiesg/workspace/MDM/普通高中教科书·数学（A版）必修第一册.pdf')
os.makedirs('/tmp/math_pages', exist_ok=True)
for i in range(len(doc)):
    pix = doc[i].get_pixmap(dpi=300)
    pix.save(f'/tmp/math_pages/p{i+1:04d}.png')
doc.close()
print(f'Rendered {len(doc)} pages')
"
```

## Verify OCR Output

```bash
# Count output files
ls /tmp/math_ocr_zh/*.txt | wc -l

# Check a sample
head -c 500 /tmp/math_ocr_zh/p009.txt

# Full text of a page
cat /tmp/math_ocr_zh/p009.txt
```

## Pitfalls

- **ObjC argv encoding**: The ObjC version (`argv[2]` as language) had CJK encoding issues.
  Swift's `[.language: "zh-Hans"]` set in code is more reliable.
- **DPI for math**: 150 DPI blurs subscripts/exponents in math textbooks. 300 DPI is better
  but slower; 3× render at 150 DPI is a good alternative.
- **Blank pages**: Front matter (cover, copyright, preface) often renders to <100KB PNGs.
  Use `ls -la` to find content pages before OCR.
- **Timeout**: For 270 pages, always use parallel batches. A single sequential job times out.