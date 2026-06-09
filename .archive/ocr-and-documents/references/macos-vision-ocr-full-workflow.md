# macOS Vision OCR — Full Batch Workflow

> Complete workflow for OCR-ing a 200+ page scanned PDF on macOS using the built-in Vision framework. No pip packages needed.

## Prerequisites

Vision framework is pre-installed on all macOS systems. The only requirement is:
- `pymupdf` installed under `/usr/local/bin/python3` (not the UV sandbox Python)
- `clang` for compiling the ObjC OCR program

## Complete Workflow for Large PDFs (200+ pages)

### Step 1 — Install pymupdf under system Python

```bash
/usr/local/bin/python3 -m pip install pymupdf --break-system-packages -q
```

### Step 2 — Compile the Vision OCR binary (once per system)

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

### Step 3 — Render all PDF pages to PNG

```bash
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

### Step 4 — Find content pages fast (no OCR needed for blank pages)

```bash
# Pages with largest PNG files have the most content
ls -la /tmp/pdf_pages/*.png | sort -k5 -nr | head -20
```

This lets you OCR only the meaningful pages instead of all 270.

### Step 5 — Run OCR in parallel batches (fastest approach)

```bash
# Write the batch script
cat > /tmp/ocr_batch.sh << 'SCRIPT'
#!/bin/bash
start=$1; end=$2
for i in \$(seq -f "%04g" \$start \$end); do
    /tmp/ocr_test /tmp/pdf_pages/page_\$i.png "zh-Hans" 2>/dev/null > /tmp/pdf_ocr/page_\$i.txt
done
echo "Batch \$start-\$end done"
SCRIPT
chmod +x /tmp/ocr_batch.sh

# Launch 4 parallel batches (e.g. 270 pages: 1-70, 71-140, 141-210, 211-270)
/tmp/ocr_batch.sh 1 70 &
/tmp/ocr_batch.sh 71 140 &
/tmp/ocr_batch.sh 141 210 &
/tmp/ocr_batch.sh 211 270 &
wait
echo "ALL DONE"
```

**Results land in `/tmp/pdf_ocr/page_0001.txt` … `page_0270.txt`**.

### Step 6 — Verify completeness

```bash
ls /tmp/pdf_ocr/ | wc -l   # should equal number of pages
```

## Key Insights

| Scenario | Behavior |
|----------|----------|
| Scanned PDF (no text layer) | pymupdf returns `len(page.get_text()) == 0` on every page |
| Content-rich page | PNG file size ~500KB–4MB at 150 DPI |
| Blank/header/footer page | PNG file size < 100KB |
| Large PDF (200+ pages) | Always use parallel batches to stay under timeout |

## Language Codes

| Code | Language |
|------|----------|
| `zh-Hans` | Simplified Chinese |
| `zh-Hant` | Traditional Chinese |
| `en-US` | English |
| `ja-JP` | Japanese |
| `ko-KR` | Korean |

Set `setUsesLanguageCorrection:NO` for CJK languages — language correction hurts accuracy for mixed math/text content.

## Why terminal() not execute_code

The UV sandbox Python (`hermes_sandbox_*`) does not have pymupdf installed. Use `terminal()` with `/usr/local/bin/python3` for all pymupdf operations on macOS.