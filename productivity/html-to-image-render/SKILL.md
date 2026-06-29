---
name: html-to-image-render
description: Render any local HTML file (report, dashboard, digest, mockup, sketch, artifact) to a single PNG or PDF image for visual sharing. Trigger when the user asks to "把这个页面做成一整图片" / "render as image" / "导出图片" / "save as PNG" / "做成 PDF" / "give me a screenshot" / "turn this HTML into an image" / "shareable image" — especially after producing an HTML artifact that looks good but isn't directly shareable in chat (WebUI supports `MEDIA:` paths, but most other surfaces don't render HTML). Uses headless Google Chrome for rendering + Pillow for crop-to-content. macOS-first, works on Linux with chromium.
---

# html-to-image-render

## When to use

User has an HTML file (locally produced) and wants a single shareable image of it. Typical cases:

- HTML report / dashboard / digest rendered to PNG for embedding in chat / email / Feishu / blog
- Trend-digest HTML → shareable image
- Frontend mockup → screenshot
- Long single-page artifact → tall PNG

Do NOT use when:
- The source is a remote URL you don't control (use `browser_navigate` + `browser_vision`)
- The user wants an interactive artifact (HTML is already the answer)
- The user wants per-section images (use a multi-step loop or cropping script)

## Method (macOS, Chrome available)

### Step 1 — Render with headless Chrome

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HTML="/absolute/path/to/file.html"
OUT="/absolute/path/to/out.png"

# window-size: width = target logical width, height = generous overestimate
# force-device-scale-factor=2 → retina-quality 2x output
# hide-scrollbars → no scrollbar artifact in screenshot
"$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=1100,3500 \
  --force-device-scale-factor=2 \
  --screenshot="$OUT" \
  "file://$HTML" 2>&1 | tail -2
```

Notes:
- Errors like `task_policy_set TASK_SUPPRESSION_POLICY` and `CVDisplayLinkCreateWithCGDisplay failed` are macOS-headless noise — **ignore them**, the screenshot still writes.
- Output dimensions = `window-size × device-scale-factor`. So `1100×3500` window + 2x scale = `2200×7000` PNG.
- For dark-themed pages, default Chromium background is white — add `<style>html,body{background:#0f1115}</style>` if the page doesn't set it.
- For Chinese fonts, ensure the system has PingFang/Microsoft YaHei/Noto Sans CJK installed.

### Step 2 — Crop to content (remove bottom whitespace)

The window-size height is an overestimate, so the PNG will have trailing whitespace. Crop it with Pillow:

```python
from PIL import Image
im = Image.open('/abs/path/out.png')
bg = (15, 17, 21)  # match your page background, or use sampling
w, h = im.size
# Scan from bottom in 5px steps looking for first row with non-background pixels
last = 0
for y in range(h - 1, -1, -5):
    row = im.crop((100, y, w - 100, y + 1))
    pixels = list(row.getdata())
    non_bg = sum(1 for p in pixels if abs(p[0]-bg[0])+abs(p[1]-bg[1])+abs(p[2]-bg[2]) > 15)
    if non_bg > 5:
        last = y
        break
cropped = im.crop((0, 0, w, min(last + 30, h)))
cropped.save('/abs/path/out.png')
```

Tune `bg` to your page's actual background, or sample first:
```python
print(im.getpixel((10, 10)))  # corner pixel = background
```

### Step 3 — Deliver as MEDIA path

In WebUI chat, embed the result with:
```
MEDIA:/abs/path/out.png
```

The WebUI renders this as an inline image preview.

## Output variants

| Need | Change |
|---|---|
| PNG (default) | as above |
| PDF (vector, sharper text) | add `--print-to-pdf=out.pdf` instead of `--screenshot` |
| Lower file size (email) | change scale to `--force-device-scale-factor=1` |
| Specific crop region (no auto-trim) | use Pillow `.crop((left, top, right, bottom))` directly |
| Multiple sections | render once, crop multiple `(x,y,w,h)` rectangles |

## Common pitfalls

1. **Missing Chrome** — check with `ls "/Applications/Google Chrome.app"` (macOS) or `which chromium` (Linux). If absent, fallback is `wkhtmltopdf` for PDFs, or install Chrome.
2. **Headless error spam** — `TASK_SUPPRESSION_POLICY` / `CVDisplayLinkCreateWithCGDisplay` errors are noise on macOS headless. **Check the output file exists, not the exit code.**
3. **Empty / white image** — usually the HTML path is wrong, or it loaded before JS rendered. For JS-heavy pages, add `--virtual-time-budget=3000` and/or wait + screenshot via a tiny wrapper script.
4. **Background not preserved** — Chrome's default white leaks through if your CSS doesn't set `html { background: ... }`.
5. **Bottom whitespace** — never trust your window-size estimate; always run the Pillow crop.
6. **MemoryError on Pillow** — for very tall images, use `im.crop(...)` (returns a view) instead of `np.array(im)` (materializes the array).
7. **Chrome single-process hang on Linux** — add `--no-sandbox --disable-dev-shm-usage` if running in containers.

## When to escalate

- User wants batch rendering of N HTML files → wrap the two commands in a Python loop
- User wants animation/GIF → out of scope; use `creative/ascii-video` or a different toolchain
- User wants a real screenshot of a *remote* site with their cookies / logged-in state → use `browser_navigate` then `browser_vision` instead

## Reusable script

A drop-in helper lives at `scripts/render_html_to_image.py` (in this skill's directory). Usage:

```bash
python3 scripts/render_html_to_image.py report.html report.png --width 1100 --scale 2
```

Auto-detects macOS Chrome, falls back to PATH lookup. `--bg auto` samples the corner for crop detection; pass `R,G,B` to override. Produces an optimized PNG with bottom whitespace trimmed.

## Example: end-to-end (report → image)

```bash
# 1. Render
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HTML="/Users/xiesg/workspace/report.html"
OUT="/Users/xiesg/workspace/report.png"
"$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=1100,3500 --force-device-scale-factor=2 \
  --screenshot="$OUT" "file://$HTML"

# 2. Crop
python3 -c "
from PIL import Image
im = Image.open('$OUT')
bg = (15, 17, 21)
w, h = im.size
last = 0
for y in range(h - 1, -1, -5):
    row = im.crop((100, y, w - 100, y + 1))
    non_bg = sum(1 for p in row.getdata() if abs(p[0]-bg[0])+abs(p[1]-bg[1])+abs(p[2]-bg[2]) > 15)
    if non_bg > 5: last = y; break
im.crop((0, 0, w, min(last + 30, h))).save('$OUT')
print('OK')
"
```

Then in chat: `MEDIA:/Users/xiesg/workspace/report.png`