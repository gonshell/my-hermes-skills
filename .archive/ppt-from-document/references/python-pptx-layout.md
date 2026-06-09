---
name: python-pptx-layout
description: "python-pptx zone-based layout system for chaos-free 25+ slide decks. Use when creating PPT from scratch without Node.js/PptxGenJS. Covers: zone constants, reusable helpers, common traps (float EMU, curly quote syntax errors, walrus operator), shape budget, verified working patterns."
license: MIT
metadata:
  version: "1.0"
  category: productivity
---

# python-pptx Zone-Based Layout

## When to Use This

**Trigger**: Creating a PPT from scratch and `node --version` fails (Node.js unavailable).

python-pptx is the fallback when PptxGenJS is not available. Without a layout system, python-pptx scripts produce chaotic slides with font sizes jumping 7pt–36pt on the same page, text fragmented across dozens of shapes, and shape count explosions.

## The Zone-Based Solution

Define all layout constants **once at the top of the script**, then reuse them in every slide function. Never hardcode coordinates.

## Complete Starter Pattern

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# === Zone constants (define ONCE at top of file) ===
SLIDE_W     = int(Inches(10))    # 16:9 standard
SLIDE_H     = int(Inches(5.625))
MARGIN      = int(Inches(0.5))
HEADER_H    = int(Inches(0.6))
CONTENT_TOP = MARGIN + HEADER_H + int(Inches(0.1))
CONTENT_H   = SLIDE_H - CONTENT_TOP - MARGIN
CONTENT_W   = SLIDE_W - 2 * MARGIN

# Standard column widths (derived from CONTENT_W — never magic numbers)
THREE_COL_W = int((CONTENT_W - 2 * int(Inches(0.2))) / 3)  # ~2.8"
COL_W       = int((CONTENT_W - int(Inches(0.3))) / 2)       # ~4.35"

# Standard colors
C_WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
C_BLACK   = RGBColor(0x1A, 0x1A, 0x1A)
C_GREY    = RGBColor(0x6B, 0x6B, 0x6B)
C_ACCENT  = RGBColor(0x2A, 0x5C, 0x9B)
C_LGREY   = RGBColor(0xF5, 0xF5, 0xF5)

# Standard font sizes
SZ_TITLE   = Pt(36)
SZ_SUBTITLE= Pt(20)
SZ_HEADER  = Pt(18)
SZ_BODY    = Pt(13)
SZ_SMALL   = Pt(11)
SZ_CAPTION = Pt(9)

# === Reusable helpers ===
def add_text(slide, text, x, y, w, h,
             size=SZ_BODY, bold=False, color=C_BLACK,
             align=PP_ALIGN.LEFT, font_face="Microsoft YaHei",
             wrap=True, valign=MSO_ANCHOR.TOP):
    txBox = slide.shapes.add_textbox(x, y, w, h)
    tf = txBox.text_frame; tf.word_wrap = wrap
    p = tf.paragraphs[0]; p.alignment = align
    run = p.add_run(); run.text = text
    run.font.size = size; run.font.bold = bold
    run.font.color.rgb = color; run.font.name = font_face
    return txBox

def add_header(slide, title, school_color, school_label=None):
    """Header zone: color bar + title. Same structure every slide."""
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                MARGIN, MARGIN, CONTENT_W, HEADER_H)
    bar.fill.solid(); bar.fill.fore_color.rgb = school_color
    bar.line.fill.background()
    add_text(slide, title,
             MARGIN + int(Inches(0.15)), MARGIN + int(Inches(0.05)),
             CONTENT_W - int(Inches(0.3)), HEADER_H - int(Inches(0.05)),
             size=Pt(28), bold=True, color=C_WHITE,
             valign=MSO_ANCHOR.MIDDLE)

def add_page_num(slide, num):
    """Footer zone: bottom-right circle badge."""
    bx = SLIDE_W - MARGIN - int(Inches(0.35))
    by = SLIDE_H - MARGIN - int(Inches(0.3))
    badge = slide.shapes.add_shape(MSO_SHAPE.OVAL, bx, by,
                                  int(Inches(0.3)), int(Inches(0.25)))
    badge.fill.solid(); badge.fill.fore_color.rgb = C_ACCENT
    badge.line.fill.background()
    add_text(slide, str(num), bx, by, int(Inches(0.3)), int(Inches(0.25)),
             size=Pt(9), bold=True, color=C_WHITE,
             align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)

def add_card(slide, x, y, w, h,
             fill=C_WHITE, line=C_LGREY):
    """Reusable card shape."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shape.fill.solid(); shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line; shape.line.width = Pt(0.5)
    return shape

def new_prs():
    """Create a new 16:9 blank presentation."""
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    prs.layout = None  # blank — control all positions yourself
    return prs
```

## Common python-pptx Traps

### Trap 1: Float EMU → TypeError
```python
# WRONG: Inches(val / 2.54) produces float EMU
bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
    MARGIN, MARGIN, CONTENT_W, cm(0.5))  # TypeError!

# CORRECT: always wrap in int()
bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
    MARGIN, MARGIN, CONTENT_W, int(Inches(0.5)))
```

### Trap 2: Curly Quotes in Chinese Strings → SyntaxError
```python
# WRONG: inner " and " terminate Python string
add_text(slide, 'AI的"中心化"问题', ...)  # SyntaxError!

# CORRECT: outer single quotes
add_text(slide, "AI的'中心化'问题", ...)   # straight single
add_text(slide, 'AI的"中心化"问题', ...)  # outer single, inner curly OK
```

### Trap 3: Walrus Operator → SyntaxError
```python
# WRONG: walrus operator causes SyntaxError at runtime
H := prs.slide_height

# CORRECT: plain assignment
H = prs.slide_height
```

### Trap 4: Dict Reuse → Style Leak
```python
# WRONG: python-pptx mutates option dicts in-place
opts = {"fill": {"color": "FF0000"}}
shape1.fill.fore_color.rgb = opts["fill"]["color"]
shape2.fill.fore_color.rgb = opts["fill"]["color"]  # same color!

# CORRECT: factory function for fresh options each time
def mk_fill(col): return lambda: col
```

## Shape Count Budget

| Quality | Max shapes/slide |
|---------|-----------------|
| Safe    | ≤ 25            |
| Warning | 26–40           |
| Out of control | ≥ 41     |

If a slide exceeds 40 shapes, consolidate multiple text boxes into one.

## Minimal Slide Template

```python
def slide_XX(prs, page_num):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    # Background
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    bg.fill.solid(); bg.fill.fore_color.rgb = C_WHITE; bg.line.fill.background()
    # Header
    add_header(slide, "Page Title", RGBColor(0x1E,0x3A,0x5F), "Section Label")
    # Cards: 2-column
    card_w = (CONTENT_W - int(Inches(0.3))) / 2
    card_h = int(Inches(1.5))
    add_card(slide, MARGIN, CONTENT_TOP, card_w, card_h)
    add_text(slide, "Card Title", MARGIN+int(Inches(0.1)), CONTENT_TOP+int(Inches(0.1)),
             card_w-int(Inches(0.2)), int(Inches(0.3)), size=Pt(14), bold=True)
    add_text(slide, "Card body text", MARGIN+int(Inches(0.1)), CONTENT_TOP+int(Inches(0.45)),
             card_w-int(Inches(0.2)), card_h-int(Inches(0.55)), size=Pt(12))
    add_card(slide, MARGIN+card_w+int(Inches(0.3)), CONTENT_TOP, card_w, card_h)
    # Page number
    add_page_num(slide, page_num)
    return slide
```
