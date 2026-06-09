# python-pptx 常见陷阱速查

> ⚠️ **2026-05-21 实测记录**：这些陷阱已导致多个 PPT 生成脚本失败。

## Float EMU → TypeError（最高频）

```python
# WRONG: Inches(val / 2.54) 产生 float EMU
bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
    MARGIN, MARGIN, CONTENT_W, cm(0.5))  # TypeError!

# CORRECT: int() 包裹所有坐标
bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
    MARGIN, MARGIN, CONTENT_W, int(Inches(0.5)))
```

**原因**：`Inches()` 内部用 `914400 / 2.54` 做除法，结果是 float。python-pptx 的 `left/top/width/height` 要求 int。

## 字符串内嵌 Curly Quotes → SyntaxError

```python
# WRONG: 内部 curly quote 终止 Python 字符串
add_text(slide, '有钱"任性"', ...)  # SyntaxError!

# CORRECT: 外层单引号
add_text(slide, "有钱'任性'", ...)  # OK
```

## Walrus Operator → SyntaxError

```python
# WRONG
H := prs.slide_height

# CORRECT
H = prs.slide_height
```

## 对象复用 → 样式泄漏

```python
# WRONG: python-pptx 会 in-place 修改 dict
opts = {"fill": {"color": "FF0000"}}

# CORRECT: 每次新建
def mk_color(r,g,b): return RGBColor(r,g,b)
shape.fill.fore_color.rgb = mk_color(0xFF,0,0)
```

## 形状数量爆炸（布局失控）

| 每页形状数 | 状态 |
|-----------|------|
| ≤ 25 | ✅ 安全 |
| 26–40 | ⚠ 警告 |
| ≥ 41 | ❌ 失控 |

**解法**：用 `add_multi_text()` 合并多行到同一个 text box，而非每行一个 text box。

## 推荐脚本结构

```python
#!/usr/bin/env python3
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# === Zone constants (define ONCE) ===
SLIDE_W  = int(Inches(10))
SLIDE_H  = int(Inches(5.625))
MARGIN   = int(Inches(0.5))
HEADER_H = int(Inches(0.6))
CONTENT_TOP = MARGIN + HEADER_H + int(Inches(0.1))
CONTENT_W   = SLIDE_W - 2 * MARGIN

# === Helpers ===
def add_text(...): ...

def add_header(...): ...

def add_page_num(...): ...

# === Slides ===
def slide_01(prs): ...

# === Main ===
def main():
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    prs.layout = None  # blank layout

    slide_01(prs)
    # ... all slides

    prs.save("/path/to/output.pptx")
    print(f"Generated {len(prs.slides)} pages")

if __name__ == "__main__":
    main()
```

**运行前必做语法验证**：
```bash
python3 -c "import ast; ast.parse(open('script.py').read())"
```
