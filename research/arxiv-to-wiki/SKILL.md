---
name: arxiv-to-wiki
description: "Ingest arXiv papers into an LLM Wiki knowledge base — search, verify IDs, fetch metadata, save raw sources, and create cross-referenced entity/concept pages. Works even when curl is blocked by using Python urllib instead."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [arxiv, wiki, knowledge-base, research, paper-ingestion]
    category: research
    related_skills: [llm-wiki, arxiv]
    config:
      - key: wiki.path
        description: Path to the LLM Wiki knowledge base
        default: "~/wiki"
---

# arXiv → Wiki Pipeline

从 arXiv 论文自动建立 LLM Wiki 知识库的完整流程。

## 关键经验（试错得出）

1. **curl 被限制，Python urllib 可用** — 如果 `curl` 被 block，用 `urllib.request` 替代
2. **arXiv ID 可能记错** — 用浏览器访问 `https://arxiv.org/abs/{id}` 直接验证论文标题
3. **Python API 搜索结果不精准** — 直接用浏览器搜索更可靠，Python 用于批量获取已知 ID 的元数据
4. **先验证再存储** — 错误 ID 存入 raw/ 后清理麻烦，应该先确认

## Pipeline

### Step 1: 搜索论文

**优先用浏览器搜索**（比 Python API 更准确）：
```
https://arxiv.org/search/?searchtype=all&query=KEYWORD
```

**Python API 作为备用**（可能被 block）：
```python
import urllib.request, xml.etree.ElementTree as ET

def search_arxiv(query, max_results=8):
    url = f"https://export.arxiv.org/api/query?search_query=all:{query.replace(' ', '+')}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    with urllib.request.urlopen(url, timeout=15) as resp:
        data = resp.read().decode()
    root = ET.fromstring(data)
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    results = []
    for entry in root.findall('a:entry', ns):
        arxiv_id = entry.find('a:id', ns).text.strip().split('/abs/')[-1]
        # ... extract title, authors, summary
    return results
```

### Step 2: 验证 arXiv ID

在存储之前，访问以下 URL 确认论文标题：
```
https://arxiv.org/abs/{arxiv_id}
```

检查返回页面中的 `<h1>` 标题是否匹配预期论文。

### Step 3: 批量获取元数据

```python
def fetch_arxiv_metadata(ids):
    """Fetch metadata for multiple papers by arXiv IDs"""
    id_str = ','.join(ids)
    url = f"https://export.arxiv.org/api/query?id_list={id_str}"
    with urllib.request.urlopen(url, timeout=20) as resp:
        data = resp.read().decode()
    root = ET.fromstring(data)
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    papers = {}
    for entry in root.findall('a:entry', ns):
        raw_id = entry.find('a:id', ns).text.strip().split('/abs/')[-1].split('v')[0]
        papers[raw_id] = {
            'title': entry.find('a:title', ns).text.strip().replace('\n', ' '),
            'authors': [a.find('a:name', ns).text for a in entry.findall('a:author', ns)],
            'date': entry.find('a:published', ns).text[:10],
            'abstract': entry.find('a:summary', ns).text.strip(),
            'categories': [c.get('term') for c in entry.findall('a:category', ns)],
        }
    return papers
```

### Step 4: 保存原始论文

每篇论文保存为 `raw/papers/{arxiv_id}.md`，包含 frontmatter 和完整摘要：
```markdown
---
title: "{title}"
arxiv_id: {arxiv_id}
authors: {', '.join(authors)}
published: {date}
categories: {', '.join(categories)}
pdf_url: https://arxiv.org/pdf/{arxiv_id}
---

# {title}

**Authors:** ...
**Published:** ...
**arXiv:** [{id}](https://arxiv.org/abs/{id})
**PDF:** ...

## Abstract

{abstract text}
```

### Step 5: 创建 Wiki 页面

根据论文内容创建/更新以下类型的页面：

**Entity 页面**（技术方法）：`entities/{method-name}.md`
- 定义、核心思想、技术细节表格
- 衍生变体（wikilinks）
- 相关技术（wikilinks）
- 引用

**Concept 页面**（核心概念）：`concepts/{concept-name}.md`
- 定义、当前认知、开放问题
- 相关概念（wikilinks）
- 主要方法对比表格

### Step 6: 更新 index.md 和 log.md

- index.md：添加新页面（按字母顺序），更新 total pages 计数
- log.md：追加 ingest 条目，列出所有创建/更新的文件

## 注意事项

- arXiv API 有速率限制（~1 req / 3 seconds），批量获取时加 sleep
- 同一个 ID 可能有多个版本，取 latest version（URL 中的 vN 后缀）
- 有些旧 ID 是 Old format（如 `hep-th/0601001`），新 API 支持但需注意
- 如果需要全文内容，用 `web_extract(urls=['https://arxiv.org/pdf/{id}'])` 提取 PDF

## 经验总结（从本次构建 LLM 微调论文知识库得出）

**已验证的 arXiv ID（可信赖）**：
- LoRA: 2106.09685
- Adapter: 1902.00751
- BitFit: 2106.10199
- RLHF/InstructGPT: 2203.02155
- Constitutional AI: 2212.08073
- QLoRA: 2305.14314
- DPO: 2305.18290
- LoRA-FA: 2308.03303
- GRPO/DeepSeekMath: 2402.03300
- DoRA: 2402.09353

**已确认错误的 ID（避免再用）**：2312.07545, 2212.11160, 1908.08593, 2204.01306, 2312.09392, 2312.00001, 2305.13014

**Pipeline 教训**：
1. arXiv API 对 batch query 返回结果不可靠——搜索用浏览器，批量元数据获取才能用 Python
2. ID 验证必须在存储 raw 文件之前完成——错误 ID 存进去再清理比先验证后存储更麻烦
3. log.md 只追加不覆盖——patch 时小心别把之前的 entry 也改掉了
4. SCHEMA.md 多次 patch 后可能产生重复块——重复块出现时直接重写整个文件，别继续 patch
