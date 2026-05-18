---
name: pdf-chapter-qa-pipeline
description: 将技术手册PDF按章节切分为独立文本文件，并行生成高质量微调QA对，最后合并输出CSV的完整工作流。
---

# PDF章节问答对生成工作流

## 适用场景
将技术手册PDF按章节切分，并行生成高质量微调QA对。

## 完整流程

### 第一阶段：PDF切分（关键步骤）

```python
import subprocess, re, os

# 1. 提取PDF文本
result = subprocess.run(['pdftotext', pdf_path, '-'], capture_output=True, text=True)
text = result.stdout.replace('\x0c', '')  # 去掉所有分页符
lines = text.split('\n')

# 2. 找章节起始行（pdftotext会在每页重复章节标题，格式："第 X 章 章节名  页码"）
#    正文第一个标题行在行1620附近，第N章标题格式多样（"第１章 绪"分行、"第 2 章"间距不同等）
chapter_starts = []
for i, line in enumerate(lines):
    m = re.match(r'^第\s*([１\d])\s*章\s+(.{2,40})$', line.strip())
    if m and not re.search(r'[\d０-９]+$', m.group(2)):  # 排除带页码的重复行
        chapter_starts.append((i, m.group(1), m.group(2)))

# 3. 切分：每章 = start_line 到下一章start_line
#    过滤重复章节行（正则 r'^第\s*[\d１-９]\s*章\s+.+\s+[\d０-９]+$' 匹配页码后缀行）
```

### 关键陷阱
- **pdftotext输出规律**：每页页眉重复章节标题+页码（如"第 2 章 热处理电阻炉 13"），这些要过滤
- **章节标题分行**：有时"第"和"章"之间有空格、有时用全角数字（第１章 vs 第1章），正则要兼容
- **第1章位置**：通常在行1600-1650之间，要手动检查确认
- **subagent不可靠**：同一prompt可能每次生成格式不同（有时5列有时2列），必须逐文件验证列头

### 第二阶段：并行生成（每批≤3个并发）

```python
# 每批最多3个并发，15章分5批
delegate_task(tasks=[
    {"goal": "生成第1-3章QA，各写ch0X_qa.csv", "toolsets": ["terminal", "file"]},
    {"goal": "生成第4-6章QA，各写ch0X_qa.csv", "toolsets": ["terminal", "file"]},
    {"goal": "生成第7-9章QA，各写ch0X_qa.csv", "toolsets": ["terminal", "file"]},
], max_iterations=50)
```

### 第三阶段：合并清洗

```python
import csv, glob

csv_files = sorted(glob.glob('ch*.csv'))
all_rows = []

for f in csv_files:
    with open(f, encoding='utf-8') as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            # 标准化字段名（subagent可能输出Q,A或question,answer）
            q = row.get('question') or row.get('Q') or row.get('Question', '')
            a = row.get('answer') or row.get('A') or row.get('Answer', '')
            # 补全缺失字段...
            all_rows.append({'question': q, 'answer': a, 'chapter': ch, 'difficulty': d, 'type': t})

# 验收：章节数=15，难度分布，类型覆盖，总条数符合预期
```

### QA质量标准（每条）
- 答案200-500字，含≥3个【术语：解释】标注
- 基础40% / 进阶60%
- 类型：概念题/工艺题/设备题/选型题/故障题均有分布
- 题目优先"为什么/如何选择/有什么区别"类，禁止简单列举型

### 输出格式
```
question,answer,chapter,difficulty,type
"问题","答案200-500字含术语标注","第X章 章节名","medium","concept"
```

## 验证清单
- [ ] 章节数=15（每章独立文件）
- [ ] 每文件列头一致（5列）
- [ ] chapter字段格式统一（如"第2章 热处理设备常用材料及基础构件"）
- [ ] 难度分布符合 基础40%/进阶60%
- [ ] 类型覆盖完整
- [ ] 无重复问题
- [ ] 答案无截断化学式
