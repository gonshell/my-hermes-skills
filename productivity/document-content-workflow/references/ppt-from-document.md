# ppt-from-document 参考

## 完整工作流

### Step 1：读取并提炼素材内容

1. 用 `feishu_doc_read` 或 `browser_navigate` 读取原始素材
2. 提炼核心主题（100字内）
3. 提炼素材结构（章节、层级、关键数据点）

### Step 2：设计 PPT 大纲

```
总页数：N页

开篇（3页）
  P01 封面
  P02 核心主题引入（用反直觉问题或对比制造认知冲突）
  P03 内容总览（全景图或目录）

主体内容（按主题分N节，每节2-4页）
  每节：章节标题页 + 内容页

收尾（2页）
  总结/金句
  Q&A
```

### Step 3：工具选型

| 场景 | 推荐工具 |
|------|----------|
| 20页以下，有模板参考 | PptxGenJS |
| 20页以上，内容由AI全量生成 | python-pptx |
| 复杂中文内容精确排版 | python-pptx |

**本 workflow 决策**：选 python-pptx（25页全量生成，无模板，内容高度程序化）

### Step 4：python-pptx 脚本结构

```python
#!/usr/bin/env python3
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

C_PRIMARY = RGBColor(0x1E, 0x3A, 0x5F)
C_ACCENT  = RGBColor(0x63, 0x66, 0xF1)

def cm(val_in_cm):
    """厘米转 EMU，必须返回整数避免浮点累加误差"""
    return int(val_in_cm * 914400 / 2.54)

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

def main():
    prs = Presentation()
    prs.slide_width = cm(16)
    prs.slide_height = cm(9)
    # ... slide functions ...
    prs.save("/path/to/output.pptx")
    print(f"Generated {len(prs.slides)} pages")

main()
```

### Step 5：语法验证（重要！）

生成大脚本（20+页）后，**不要直接运行**，先做语法验证：

```bash
python3 -c "import ast; ast.parse(open('generate_ppt.py').read())"
```

常见错误：
1. **嵌入引号问题**：`"包含"内部引号"的字符串"` → 改用单引号或转义
2. **walrus operator**：`H := prs.slide_height` → 去掉
3. **段落索引越界**：访问 `paragraphs[N]` 时 N 超出范围

### Step 6：运行并验证

```bash
python3 generate_ppt.py
ls -lh output.pptx
python3 -m markitdown output.pptx  # 检查内容
```

## 常用布局模板（12种）

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