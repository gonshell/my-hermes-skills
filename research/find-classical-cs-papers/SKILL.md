---
name: find-classical-cs-papers
description: Find classical theoretical CS papers when academic search APIs (arXiv, Semantic Scholar) are blocked by bot detection. Uses Wikipedia references as a reliable fallback, combined with known classic paper knowledge.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Research, Academic, Computer Science, Papers, Wikipedia]
---

# Find Classical CS Papers (When APIs Blocked)

## Problem

arXiv API, Semantic Scholar API, and Google Search often **block automated requests** with bot detection (CAPTCHA, 405 errors, empty responses). This is especially common for theoretical CS topics (Turing machines, computability, lambda calculus, etc.).

## Solution: Wikipedia + Knowledge

When APIs are blocked, use this two-pronged approach:

### 1. Wikipedia References (Always Works)

Wikipedia articles for classical CS topics have **excellently curated reference sections**. Steps:

1. Navigate to Wikipedia article (e.g., `https://en.wikipedia.org/wiki/Turing_machine`)
2. Scroll to **"References"** section in the table of contents
3. References are categorized (Primary literature, Computability theory, Church's thesis, etc.)
4. These references link to original papers, books, and authoritative sources

### 2. Known Classic Papers (Direct Knowledge)

For fundamental theoretical CS topics, provide well-known papers directly:

| Topic | Classic Papers |
|-------|---------------|
| Turing machines | Turing 1936 "On Computable Numbers..."; Church 1936; Kleene 1936 |
| Lambda calculus | Church 1936 "An Unsolvable Problem..."; Rosenbloom 1950 |
| Computability theory | Rogers "Theory of Recursive Functions"; Sipser "Intro to Theory of Computation" |
| Quantum computing | Deutsch 1985 "Quantum Theory, Church-Turing Principle..." |
| Neural networks | McCulloch & Pitts 1943; Rumelhart et al. 1986 |

### 3. Reliable Free Resources

| Resource | URL | Best For |
|----------|-----|----------|
| Stanford Encyclopedia of Philosophy | plato.stanford.edu | Academic-level topic explanations with original paper links |
| Wikipedia References | en.wikipedia.org/wiki/[topic] | Curated bibliography, categorized references |
| B站/YouTube | Search "[topic] 可视化" | Intuitive visual explanations |

## Workflow

```
1. Try: browser_navigate → Wikipedia article for the topic
2. If blocked: fallback to known classic papers from memory
3. Supplement with Stanford Encyclopedia for academic depth
```

## Key Insight

> For **historical/theoretical CS papers** (pre-1990s), academic search engines are often blocked BUT Wikipedia works reliably and has excellent curated references. For modern papers, you may need to try multiple sources or wait for rate limits to reset.

## Verification

- arXiv API: `curl "https://export.arxiv.org/api/query?search_query=all:Turing+machine"` → often blocked
- Semantic Scholar: web or API → often returns 405 or CAPTCHA
- Wikipedia: almost always accessible
