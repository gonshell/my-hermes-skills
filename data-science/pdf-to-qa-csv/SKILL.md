---
name: pdf-to-qa-csv
description: Convert a Chinese PDF into structured Q&A CSV for LLM fine-tuning. Handles both (A) scanned/image-based PDFs via OCR (tesseract) and (B) text-based PDFs via pdftotext. For terminology standards and technical manuals.
version: 2.0.0
category: data-science
metadata:
  hermes:
    tags: [PDF, QA, 微调, 热处理, OCR, pdftotext]
    use_case: 将中文技术文档 PDF 转为微调训练问答数据
---

## 两种工作模式

### 模式 A：扫描版 PDF（图片型，需 OCR）
> 适用：扫描版中文手册、无法用 pdftotext 提取文本的 PDF
> 工具：tesseract-ocr + tesseract-ocr-chi-sim

### 模式 B：文本版 PDF（可直接提取）
> 适用：数字出版的 PDF（如机械工业出版社等正规出版物的数字版）
> 工具：pdftotext（poppler-utils）
> 已知问题：PDF 分页符 `\x0c` 打乱章节标题、目录页干扰正文、表格数据不适合作 QA
# PDF to Q&A CSV Pipeline

Convert a Chinese PDF standard document (with terminology definitions) into structured Q&A training pairs via OCR.

## When to Use
- PDF is scanned/image-based (no extractable text)
- PDF contains terminology definitions with section numbers (e.g., 3.1.1, 4.2.15)
- Goal is to generate Q&A training data for LLM fine-tuning

## Workflow

### Step 1: Install OCR Tools
```bash
apt-get update -qq && apt-get install -y -qq tesseract-ocr tesseract-ocr-chi-sim poppler-utils
```

### Step 2: Convert PDF to Images
```bash
pdftoppm -r 200 /path/to/document.pdf /tmp/pdf_pages/all -png
# Naming: all-01.png, all-02.png, ...
```

### Step 3: OCR All Pages
```python
import subprocess, os, time

os.makedirs('/tmp/ocr_output', exist_ok=True)
TOTAL_PAGES = 68  # adjust per document

for i in range(1, TOTAL_PAGES + 1):
    page_file = f'/tmp/pdf_pages/all-{i:02d}.png'
    r = subprocess.run(
        ['tesseract', page_file, 'stdout', '-l', 'chi_sim', '--psm', '6'],
        capture_output=True, text=True, timeout=30
    )
    with open(f'/tmp/ocr_output/page_{i:02d}.txt', 'w') as f:
        f.write(r.stdout)
    print(f'OCR page {i}/{TOTAL_PAGES} - len={len(r.stdout)}')
```

### Step 4: Parse Terms and Generate Q&A

Key normalization steps:
- Replace OCR artifacts: `淳火/深火/沪火/济火` → `淬火`
- Replace special chars: em-dash, curly quotes, middle dot
- Section pattern: `^\d+\.\d+\.\d+$` at line start (e.g., 3.1.1, 4.2.15)

```python
import os, re, csv

# Read all OCR pages
all_text = {}
for i in range(1, TOTAL_PAGES + 1):
    path = f'/tmp/ocr_output/page_{i:02d}.txt'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            all_text[i] = f.read()

full_text = '\n'.join([all_text.get(i, '') for i in range(1, TOTAL_PAGES + 1)])

# Normalize OCR artifacts (common Chinese 热处理 OCR errors)
full_text = full_text.replace('淳火', '淬火')
full_text = full_text.replace('深火', '淬火')
full_text = full_text.replace('沪火', '淬火')
full_text = full_text.replace('济火', '淬火')
full_text = full_text.replace('国溶', '固溶')
full_text = full_text.replace('\u2014', '-')   # em dash
full_text = full_text.replace('\u201d', '"')
full_text = full_text.replace('\u201c', '"')
full_text = full_text.replace('\u00b7', '.')

# Find section blocks: lines matching X.Y.Z at start
section_re = re.compile(r'^(\d+\.\d+\.\d+)\s*$', re.MULTILINE)
matches = list(section_re.finditer(full_text))

terms = []
for idx, match in enumerate(matches):
    section_num = match.group(1)
    start = match.end()
    end = matches[idx + 1].start() if idx + 1 < len(matches) else len(full_text)
    block = full_text[start:end].strip()
    
    # Remove header lines
    lines = [l.strip() for l in block.split('\n') if l.strip() and 'GB/T' not in l]
    if not lines:
        continue
    
    # Find where definition starts (long Chinese sentence with definition keywords)
    def_start = 0
    for li, line in enumerate(lines):
        if len(line) > 15 and re.match(r'^[\u4e00-\u9fff]', line):
            if any(kw in line for kw in ['将工件', '采用', '使工件', '材料或', '在一定', '通过', '为', '供', '用', '把工件', '对工件']):
                def_start = li
                break
    
    term_lines = lines[:def_start] if def_start > 0 else lines[:3]
    def_lines = lines[def_start:] if def_start < len(lines) else lines
    definition = ' '.join(def_lines).strip()
    
    if not definition or len(definition) < 5:
        continue
    
    # Extract Chinese term
    chinese_match = re.match(r'^([\u4e00-\u9fff\u2014\-\·\•]+)', ' '.join(term_lines))
    chinese_term = chinese_match.group(1).strip() if chinese_match else ''
    chinese_term = re.sub(r'["\'\s]+$', '', chinese_term).strip()
    
    # Extract English term (fallback)
    english_match = re.search(
        r'([A-Za-z][\w\s\-]+(?:treatment|annealing|cooling|heating|phase|steel|'
        r'curve|diagram|zone|rate|process|method|property|system|measurement|'
        r'value|effect|operation|device|test|analysis|phenomenon|structure|'
        r'transformation|formation|result))',
        ' '.join(term_lines), re.IGNORECASE
    )
    eng_term = english_match.group(1).strip().rstrip(',;').strip() if english_match else ''
    
    # Determine category from section number (GBT 7232-2023 structure)
    major = int(section_num.split('.')[0])
    minor = int(section_num.split('.')[1])
    
    if major == 3 and minor == 1:
        category = '基础术语-总称'
    elif major == 3 and minor == 2:
        category = '基础术语-加热类'
    elif major == 3 and minor == 3:
        category = '基础术语-冷却类'
    elif major == 4:
        cat_map = {1: '热处理工艺-退火类', 2: '热处理工艺-正火类', 3: '热处理工艺-淬火类',
                   4: '热处理工艺-回火类', 5: '热处理工艺-渗碳类', 6: '热处理工艺-渗氮类',
                   7: '热处理工艺-氮碳共渗类', 8: '热处理工艺-渗金属类',
                   9: '热处理工艺-化学气相沉积类', 10: '热处理工艺-其他'}
        category = cat_map.get(minor, '热处理工艺-其他')
    elif major == 5:
        sub_map = {1: '组织与性能-金相组织类', 2: '组织与性能-力学性能类', 3: '组织与性能-热处理缺陷类'}
        category = sub_map.get(minor, '组织与性能')
    elif major == 6:
        sub_map = {1: '热处理装备-设备类', 2: '热处理装备-辅助设备类', 3: '热处理装备-传感器与仪表类'}
        category = sub_map.get(minor, '热处理装备')
    else:
        category = '其他'
    
    terms.append({
        'section': section_num,
        'chinese': chinese_term,
        'english': eng_term,
        'definition': definition,
        'category': category,
    })

# Generate 3 Q&A per term
qa_pairs = []
for t in terms:
    if not t['chinese'] or not t['definition']:
        continue
    
    eng_suffix = f"（{t['english']}）" if t.get('english') else ''
    
    qa_pairs.append({
        'question': f"什么是{t['chinese']}？",
        'answer': f"{t['chinese']}{eng_suffix}：{t['definition']}",
        'term': t['chinese'],
        'english_term': t.get('english', ''),
        'section': t['section'],
        'category': t['category'],
        'difficulty': 'easy',
        'question_type': 'definition',
    })
    qa_pairs.append({
        'question': f"请解释金属热处理术语\"{t['chinese']}\"及其含义",
        'answer': f"{t['chinese']}{eng_suffix}：{t['definition']}",
        'term': t['chinese'],
        'english_term': t.get('english', ''),
        'section': t['section'],
        'category': t['category'],
        'difficulty': 'medium',
        'question_type': 'explanation',
    })
    qa_pairs.append({
        'question': f"在热处理工艺中，{t['chinese']}是指什么？",
        'answer': f"{t['chinese']}{eng_suffix}：{t['definition']}",
        'term': t['chinese'],
        'english_term': t.get('english', ''),
        'section': t['section'],
        'category': t['category'],
        'difficulty': 'medium',
        'question_type': 'contextual',
    })

# Write CSV
with open('output.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'question', 'answer', 'term', 'english_term', 'section', 'category', 'difficulty', 'question_type'
    ])
    writer.writeheader()
    writer.writerows(qa_pairs)
```

## Pitfalls
- **Low OCR quality**: Use `-r 300` DPI or higher for pdftoppm; `--psm 6` works well for single-column Chinese text
- **OCR errors in Chinese**: `淬火` is frequently misrecognized as `淳火/深火/沪火/济火` — always normalize post-OCR
- **Synonym terms**: Some entries have multiple English equivalents — extract primary only, or split into separate entries
- **Index/appendix pages**: Pages 43 (appendix) and 68 (index) contain tables, not definitions — parser handles gracefully
- **Short section numbers**: Some pages show section numbers out of order; the parser finds all matches

## Verification
```python
# Check for empty/malformed entries
empty_terms = [r for r in rows if not r['term'].strip()]
short_answers = [r for r in rows if len(r['answer']) < 15]
print(f"Empty terms: {len(empty_terms)}, Short answers: {len(short_answers)}")

# Category distribution
from collections import Counter
cats = Counter(r['category'] for r in rows)
for cat, cnt in cats.most_common():
    print(f"  {cat}: {cnt}")
```

---

# 模式 B：文本版 PDF → 微调问答对（pdftotext）

## 适用场景
数字出版的 PDF，pdftotext 可直接提取可读文本，无需 OCR。

## 工作流程

### Step 1: 提取全文并清理
```bash
pdftotext "/path/to/manual.pdf" - 2>/dev/null | sed 's/\x0c/\n/g' > /tmp/fulltext.txt
wc -l /tmp/fulltext.txt  # 查看总行数
```

### Step 2: 确定正文起始行（跳过目录）
```python
lines = open('/tmp/fulltext.txt', encoding='utf-8').read().split('\n')
body_start = None
for i, line in enumerate(lines):
    if i > 1600 and ('实质性关键词' in line or '热处理设备是指' in line):
        body_start = i
        break
body_text = '\n'.join(lines[body_start:])
print(f"正文字数: {len(body_text)}")
```

### Step 3: 按字符偏移分块
```python
chunk_size = 45000
chunks = []
for i in range(0, len(body_text), chunk_size):
    chunk = body_text[i:i+chunk_size]
    # 截断到段落末尾（避免句子被切断）
    last_nl = chunk.rfind('\n')
    if last_nl > chunk_size * 0.7:
        chunk = chunk[:last_nl]
    chunks.append(chunk)
print(f"共 {len(chunks)} 块，每块约 {chunk_size} 字")
```

### Step 4: 并行子任务生成 QA
每个子任务负责 7-8 块，每块 10-15 个 QA。
```
子任务 prompt 要点：
- 读取指定块的文本内容
- 覆盖该块核心知识点（定义/分类、工艺参数、设备结构、选型依据）
- 答案包含【术语：解释】格式
- 输出 CSV：question, answer, chapter, difficulty, type
```

### Step 5: 合并 + 字段标准化
```python
import csv, os
from collections import Counter

files = sorted(glob('/tmp/qa_chunk*.csv'))
all_rows = []
for f in files:
    with open(f, encoding='utf-8') as fp:
        all_rows.extend(list(csv.DictReader(fp)))

# 标准化 difficulty
diff_map = {'easy': '基础', 'medium': '进阶', 'hard': '进阶',
            '基础': '基础', '进阶': '进阶'}

# 标准化 type
type_map = {
    'definition': '概念题', 'concept': '概念题', 'conceptual': '概念题',
    'procedure': '工艺题', 'process': '工艺题', 'technical': '设备题',
    'parameter': '工艺题', 'explanation': '概念题', 'principle': '概念题',
    'comparison': '选型题', 'classification': '选型题', 'application': '选型题',
    'component': '设备题', 'feature': '设备题', 'reason': '故障题',
    'problem': '故障题', 'composition': '设备题', 'contextual': '概念题',
    '概念题': '概念题', '工艺题': '工艺题', '设备题': '设备题',
    '选型题': '选型题', '故障题': '故障题',
}

for r in all_rows:
    r['difficulty'] = diff_map.get(r.get('difficulty', '').strip(), '进阶')
    r['type'] = type_map.get(r.get('type', '').strip(), '概念题')

out = '/tmp/最终QA文件.csv'
with open(out, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['question','answer','chapter','difficulty','type'])
    writer.writeheader()
    writer.writerows(all_rows)

print(f"合计: {len(all_rows)} QA，文件: {out} ({os.path.getsize(out)} 字节)")
print(Counter(r['difficulty'] for r in all_rows))
print(Counter(r['type'] for r in all_rows))
```

## 已知问题（模式 B）

| 问题 | 原因 | 解决 |
|------|------|------|
| 章节标题被分页符切断 | `\x0c` 出现在标题中间 | `sed 's/\x0c/\n/g'` 合并行 |
| 目录页（前1600行）干扰正文 | PDF 前半部分是目录 | 从正文起始行开始截取 |
| QA 块边界切断句子 | 固定字符数截断 | 截断到最后一个 `\n` 之前 |
| 大量表格数据（不适合作 QA） | 手册含热工参数表 | LLM 阅读时自行过滤 |
| 章节名称不一致 | 不同子任务输出格式不同 | 合并后统一映射 |
