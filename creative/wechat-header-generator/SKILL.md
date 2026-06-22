---
name: wechat-header-generator
description: Generate WeChat public-account header images for Chinese articles. CRITICAL rule - mmx image-01 backend does NOT render Chinese. It outputs English/garbled text. For any Chinese-text image, skip mmx and use PIL + matplotlib + NotoSansCJK font directly.
version: 1.0.0
metadata:
  hermes:
    tags: [image-generation, chinese, wechat, illustration]
    category: creative
---

# WeChat Header Generator (Chinese Text)

## When to Use

Trigger when user asks for 公众号头图 / 读后感配图 / 文章封面 / 笔记插图 with Chinese text.

## CRITICAL Rule

mmx `image generate` (image-01 backend) does NOT render Chinese characters. It replaces all Chinese with English or garbled text. Do NOT use mmx for Chinese-text images — go straight to PIL.

If user has a reference image without text, mmx is fine for the base; overlay Chinese text with PIL afterwards.

## Workflow

1. Skip mmx entirely for Chinese-text images.
2. Generate base visuals with matplotlib (lines, circles, shapes, icons).
3. Overlay Chinese text with PIL using NotoSansCJK fonts.
4. Output 16:9 (1600x900), save as PNG.

## matplotlib hand-drawn pattern

```python
import matplotlib.pyplot as plt
import numpy as np, math, random

def smooth_close(points, passes=2):
    for _ in range(passes):
        new = []
        n = len(points)
        for i in range(n):
            prev, cur, nxt = points[(i-1)%n], points[i], points[(i+1)%n]
            new.append((0.25*prev[0]+0.5*cur[0]+0.25*nxt[0],
                        0.25*prev[1]+0.5*cur[1]+0.25*nxt[1]))
        return points

def wobble_circle(ax, cx, cy, r, color="#1A1A1A", lw=2.2):
    n = 64
    angles = np.linspace(0, 2*math.pi, n)
    ox, oy = np.random.uniform(-0.04, 0.04, n), np.random.uniform(-0.04, 0.04, n)
    pts = [(cx+(r+ox[i])*math.cos(angles[i]), cy+(r+oy[i])*math.sin(angles[i])) for i in range(n)]
    pts = smooth_close(pts, 2)
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw, solid_capstyle="round")
```

## PIL text overlay pattern

```python
from PIL import Image, ImageDraw, ImageFont
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
font_title = ImageFont.truetype(FONT_BOLD, 78)
font_label = ImageFont.truetype(FONT_BOLD, 44)

def draw_centered(draw, text, x, y, font, fill):
    bbox = draw.textbbox((0,0), text, font=font)
    w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text((x-w/2, y-h/2-bbox[1]*0.15), text, font=font, fill=fill)

def pos(nx, ny):  # matplotlib 16x9 grid to image pixels
    return (int(nx/16*iw), int((1-ny/9)*ih))
```

## Insert into Feishu Doc

Correct path (verified) — `media-insert` + `--selection-with-ellipsis "<H1 unique text>"`. One-shot success.

```bash
cd <image-dir>  # lark-cli requires relative path
lark-cli docs +media-insert \
  --doc "<doc_token>" \
  --file ./header.png \
  --selection-with-ellipsis "唯一H1标题文字" \
  --align center \
  --caption "公众号头图"
```

## Wrong Paths (Do NOT Use)

- drive +upload then block_insert_after with img href equals token → degrade_code 2101
- img href syntax → unsupported, use media-insert instead
- mmx image generate for Chinese text → outputs English/garbled
- Absolute paths in lark-cli drive +upload → use relative path with cd first

## Output Spec

- 16:9 ratio (公众号头图 standard)
- 1600x900 px
- Mono-ink palette (black #1A1A1A + optional coral #E8655A / teal #5FA8A8)
- Hand-drawn visual-note style
- File path: `/root/workspace/illustrations/<topic-slug>/01-header.png`