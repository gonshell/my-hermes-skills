---
name: ppt-from-document
description: "从文档素材生成完整PPT的工作流：当用户提供了长篇素材（飞书文档、技术报告、文章等），需要提炼主题、设计大纲、逐页生成完整演示文稿时使用。覆盖：内容提炼→大纲设计→工具选型→python-pptx完整生成→python-pptx常见陷阱。触发：生成PPT、创建演示文稿、根据XX材料做PPT、将XX内容做成幻灯片。"
license: MIT
metadata:
  version: "1.1"
  category: productivity
---

# 从文档素材生成完整PPT

## 触发条件

用户提供了素材（飞书文档、PDF、文章等），要求：
- 提炼主题，设计PPT大纲
- 生成完整多页演示文稿（20+页）
- 逐页包含"展示内容"和"怎么讲"的演讲提示

## 完整工作流

### Step 1：读取并提炼素材内容

1. 用 `feishu_doc_read` 或 `browser_navigate` 读取原始素材
2. 提炼核心主题（100字内）
3. 提炼素材结构（章节、层级、关键数据点）

### Step 2：设计PPT大纲

按以下结构设计：

```
总页数：N页

开篇（3页）
  P01 封面
  P02 核心主题引入（用反直觉问题或对比制造认知冲突）
  P03 内容总览（全景图或目录）

历史脉络（如适用，2-3页）
  时间线/演进历程

主体内容（按主题分N节，每节2-4页）
  每节：章节标题页 + 内容页

收尾（2页）
  总结/金句
  Q&A
```

**关键原则**：
- 每页需包含**展示内容**（What/Why/How/核心思想）和**怎么讲**（演讲提示）
- 20页以上时内容需丰富：代表性人物、核心论文引用、代码片段、详细公式
- 里程碑时间线需统一协调，避免重复

### Step 3：工具选型

| 场景 | 推荐工具 |
|------|----------|
| 20页以下，有模板参考 | PptxGenJS（参考 pptx-generator skill） |
| 20页以上，内容由AI全量生成 | python-pptx（直接写Python脚本） |
| 需要复杂图表/动画 | PptxGenJS |
| 复杂中文内容精确排版 | python-pptx（控制力更强） |
| 需要生成后立即编辑 | python-pptx（文件结构简单） |

**本 session 决策**：选 python-pptx（25页全量生成，无模板，内容高度程序化）

### Step 4：python-pptx 完整生成流程

#### 4.1 安装依赖

```bash
pip3 install python-pptx
python3 -c "from pptx import Presentation; print('OK')"
```

#### 4.2 编写生成脚本

推荐脚本结构（详见 `references/python-pptx.md`）：

```python
#!/usr/bin/env python3
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# ─── 配色系统 ───────────────────────────────────
C_PRIMARY = RGBColor(0x1E, 0x3A, 0x5F)
C_ACCENT  = RGBColor(0x63, 0x66, 0xF1)

def cm(val_in_cm):
    """厘米转 EMU，必须返回整数避免浮点累加误差"""
    return int(val_in_cm * 914400 / 2.54)   # 1 inch = 914400 EMU

def add_text_box(slide, text, left, top, width, height,
                 font_size=12, bold=False, color=RGBColor(0,0,0),
                 align=PP_ALIGN.LEFT, font_name="微软雅黑"):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font_name
    return txBox

# ─── 逐页生成函数 ──────────────────────────────
def slide_cover(prs): ...
def slide_overview(prs): ...
def slide_content(prs): ...

# ─── 主函数 ───────────────────────────────────
def main():
    prs = Presentation()
    prs.slide_width = cm(16)
    prs.slide_height = cm(9)

    slide_cover(prs)
    # ... 所有slide函数

    prs.save("/path/to/output.pptx")
    print(f"Generated {len(prs.slides)} pages")

main()
```

#### 4.3 语法验证（重要！）

生成大脚本（20+页）后，**不要直接运行**，先做语法验证：

```bash
python3 -c "import ast; ast.parse(open('generate_ppt.py').read())"
```

如果有错误，逐个修复后重新验证。常见错误：

1. **嵌入引号问题**：`"包含"内部引号"的字符串"` → 改用单引号或转义
2. **walrus operator**：`H := prs.slide_height` → 去掉 `H := `，直接用 `prs.slide_height`
3. **段落索引越界**：访问 `paragraphs[N]` 时N超出范围

修复后再次验证，直到 `ast.parse` 无报错再运行脚本。

#### 4.4 运行并验证

```bash
python3 generate_ppt.py
ls -lh output.pptx
python3 -m markitdown output.pptx  # 检查内容
```

### Step 5：向用户交付

交付物清单：
1. PPT文件（`.pptx`）
2. PPT内容大纲（每页标题+核心叙述主线）
3. 讲述要点（每页如何向听众阐述）

---

## 视觉设计规范

### 四大流派四色系统（用于AI流派类PPT）

| 流派 | 颜色 | Hex |
|------|------|-----|
| 符号主义 | 深邃藏蓝 | `#1E3A5F` |
| 连接主义 | 森林绿 | `#2D5A27` |
| 概率主义 | 琥珀金 | `#8B6914` |
| 行为主义 | 深绯红 | `#8B1A1A` |
| 融合/强调 | 靛蓝紫 | `#6366F1` |

### 中性色

| 用途 | Hex |
|------|-----|
| 浅背景 | `#FAFBFC` |
| 卡片背景 | `#F4F6F8` |
| 深背景 | `#1A1D21` |
| 标题文字 | `#1F2937` |
| 正文文字 | `#374151` |
| 次要文字 | `#6B7280` |

### 常用布局模板（12种）

| 类型 | 适用场景 |
|------|----------|
| 封面型 | 封面、章节标题 |
| 总览型 | 全景图/对比表 |
| 时间线型 | 历史演进 |
| 架构图型 | 系统架构 |
| 卡片网格型 | 里程碑、人物 |
| 公式展示型 | 技术原理 |
| 三栏并列型 | 对比分析 |
| 循环图型 | 框架/流程 |
| 矩阵型 | 多维度分析 |
| 金句型 | 结语、核心观点 |
| 层级图型 | 流派关系 |
| 列表型 | 要点总结 |

---

## 参考文件

| 文件 | 内容 |
|------|------|
| `references/python-pptx.md` | python-pptx语法陷阱、API速查、脚本结构模板 |
