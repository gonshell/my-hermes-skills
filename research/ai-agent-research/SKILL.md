---
name: ai-agent-research
description: "Research the AI Agent technology stack — architectures, frameworks, benchmarks, and frontier research. Companion skill for deep research reports."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Research, AI Agent, LLM, Multi-Agent, Agent Framework]
    related_skills: [arxiv]
---

# AI Agent Technology Research

Research AI Agent systems end-to-end: foundation models → core architectures → frameworks → tools → evaluation. Produces structured technology stack reports.

## Research Workflow

### Phase 1: Known-Key-Paper Discovery (Batch Fetch)

Instead of relying on search (which misses key papers), fetch by known IDs + search for recent papers by date:

```bash
# Batch fetch known foundational papers
for id in "2308.00352" "2303.17580" "2308.03688" "2303.17760"; do
  curl -s "https://export.arxiv.org/api/query?id_list=$id" | python3 -c "
import sys, xml.etree.ElementTree as ET
ns = {'a': 'http://www.w3.org/2005/Atom'}
root = ET.parse(sys.stdin).getroot()
for entry in root.findall('a:entry', ns):
    title = entry.find('a:title', ns).text.strip().replace('\n', ' ')
    arxiv_id = entry.find('a:id', ns).text.strip().split('/abs/')[-1]
    published = entry.find('a:published', ns).text[:10]
    authors = ', '.join(a.find('a:name', ns).text for a in entry.findall('a:author', ns))[:80]
    summary = entry.find('a:summary', ns).text.strip()[:300]
    print(f'[{arxiv_id}] {title}')
    print(f'  {published} | {authors}')
    print(f'  {summary}...')
" 2>/dev/null
done
```

### Phase 2: Recent Papers by Category

Search by topic categories and sort by date, then filter relevant ones:

```bash
# Agent frameworks and systems (title search for precision)
curl -s "https://export.arxiv.org/api/query?search_query=ti:AI+agent+OR+ti:LLM+agent+OR+ti:agent+system&sortBy=submittedDate&sortOrder=descending&max_results=20"

# Multi-agent systems
curl -s "https://export.arxiv.org/api/query?search_query=all:multi-agent+system+framework&sortBy=submittedDate&sortOrder=descending&max_results=15"

# Agent reasoning and planning
curl -s "https://export.arxiv.org/api/query?search_query=all:agent+reasoning+planning+reflection&sortBy=submittedDate&sortOrder=descending&max_results=12"
```

**Key search prefix tip**: `ti:` (title) is more precise than `all:` (all fields). Use `all:` for broad discovery but `ti:` when you know the topic area.

### Phase 3: Read Key Paper Abstracts

Batch fetch abstracts from the most relevant results:

```bash
for id in "PAPER_ID_1" "PAPER_ID_2" "PAPER_ID_3"; do
  curl -s "https://export.arxiv.org/api/query?id_list=$id" | python3 -c "
import sys, xml.etree.ElementTree as ET
ns = {'a': 'http://www.w3.org/2005/Atom'}
root = ET.parse(sys.stdin).getroot()
for entry in root.findall('a:entry', ns):
    title = entry.find('a:title', ns).text.strip().replace('\n', ' ')
    arxiv_id = entry.find('a:id', ns).text.strip().split('/abs/')[-1]
    summary = entry.find('a:summary', ns).text.strip()[:400]
    print(f'=== [{arxiv_id}] ===')
    print(f'Title: {title}')
    print(f'Abstract: {summary}...')
" 2>/dev/null
  echo
done
```

### Phase 4: Citation Context (Optional)

Check citation counts for impact assessment:

```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:PAPER_ID?fields=title,citationCount,influentialCitationCount,year"
```

Note: Rate limited at 1 req/sec without API key.

## Known Key Papers (2023–2026)

| Paper | ID | Contribution |
|-------|----|-------------|
| MetaGPT | `2308.00352` | Multi-agent SOP collaboration (software company simulation) |
| HuggingGPT | `2303.17580` | LLM as orchestrator of ML models |
| AgentBench | `2308.03688` | Multi-dimensional LLM-as-agent benchmark |
| CAMEL | `2303.17760` | Role-playing multi-agent autonomous cooperation (verified full abstract fetched) |
| MASPO | `2605.06623` | Joint prompt optimization for LLM-based multi-agent systems |
| AI CFD Scientist | `2605.06607` | Physics-aware agents for computational fluid dynamics discovery |

### 2025-2026 Frontier Papers (cs.AI top results)

| ID | Title | Key Insight |
|----|-----|-------------|
| `2605.06639` | Recursive Agent Optimization (RAO) | RL training for recursive delegation; inference-time scaling via divide-and-conquer |
| `2605.06614` | SkillOS | Self-evolving agents: skill curation from experience |
| `2605.06642` | StraTA | Strategic Trajectory Abstraction — RL for long-horizon credit assignment |
| `2605.06647` | Superintelligent Retrieval Agent | Expert-level RAG with strong priors vs. passive retrieval |
| `2605.06635` | Cited but Not Verified | Deep Research Agent citation verification problem |
| `2605.06651` | AI Co-Mathematician | Agentic AI for open-ended mathematical research |
| `2605.06607` | AI CFD Scientist | Physics-aware agents for computational fluid dynamics |
| `2605.06664` | BAMI | Training-free GUI grounding bias mitigation |

## Report Structure Template

When producing a technology stack report, use this structure:

```
# AI Agent 技术栈调研报告

## 一、技术栈总览
[Full-layer diagram]

## 二、Foundation Model Layer
[Model comparison table, selection guide]

## 三、Core Architectures
### 3.1 Single Agent patterns (ReAct, CoT, ToT, RAO)
### 3.2 Key components (Memory, Tool Use, Planning)

## 四、Multi-Agent Systems
### 4.1 Open source frameworks (LangGraph, CAMEL, MetaGPT, CrewAI, AutoGen)
### 4.2 Collaboration patterns (Supervisor, Sequential, Group Chat, Hierarchical)

## 五、Tools & Protocol
[MCP, Function Calling, Browser/Web tools]

## 六、Evaluation
[Benchmarks: AgentBench, GAIA, WebArena, SWE-bench]

## 七、Frontier Research
[2025-2026 hot directions + key unresolved challenges]
```

## Open Source Ecosystem Quick Reference

### Layer 1: AI Assistant Platforms (End-User Products)
**These are products users interact with directly, NOT developer frameworks.**

| Project | GitHub | Stars |定位 |
|---------|--------|-------|------|
| **OpenClaw** | openclaw/openclaw | 370k ⭐ | "Any OS. Any Platform." AI assistant OS. Uses SOUL.md to define agent souls. TypeScript. |
| Hermes-Agent | NousResearch/hermes-agent | 140k ⭐ | Agent runtime framework with persistent memory. Shared ecosystem with OpenClaw. Python. |
| VoltAgent/awesome-openclaw-skills | — | 48k | 5,400+ pre-built OpenClaw agent skills |
| mergisi/awesome-openclaw-agents | — | 3k | 205 production-ready agent templates |
| CrewClaw | crewclaw.com | — | Agent template hosting + one-click deployment platform |

> **Positioning note**: OpenClaw and Hermes-Agent are **infrastructure/platform layer**, NOT orchestration frameworks like LangGraph or CrewAI. Think "AI Agent Android OS + runtime framework" vs "app-building frameworks". They sit BELOW the orchestration layer in the stack.

### Layer 2: Orchestration Frameworks (Developer Tools)

| Framework | GitHub | Strength |
|-----------|--------|---------|
| LangGraph | langchain-ai/langgraph | Production DAG workflows with state persistence |
| CAMEL | camel-ai/camel | Multi-agent role-playing with inception prompting |
| MetaGPT | others-align/MetaGPT | SOP-based software company simulation |
| CrewAI | crewAI/crewai | Easy role-based multi-agent with task delegation |
| AutoGen | microsoft/autogen | Microsoft ecosystem + human-in-the-loop |
| Swarms | openswarms/swarms | Lightweight scalable orchestration |
| Dify | langgenius/dify | Visual LLM app platform (no-code) |
| OpenHands | All-Hands/openhands | Autonomous task completion agent |

## Key Papers Reference

- `references/key-papers-2026.md` — Detailed summaries of foundational + 2025-2026 frontier papers (RAO, SkillOS, StraTA, MASPO, AI CFD Scientist, Superintelligent Retrieval Agent, Cited-but-Not-Verified, AI Co-Mathematician)
- `references/protocol-sources.md` — Authoritative sources for MCP, A2A, ACP, Function Calling, Skills protocols. Includes verification checklist to avoid misattribution (e.g. A2A belongs to a2aproject org, not Anthropic).

## Key Research Frontiers (2025-2026)

1. **Reasoning Scaling**: RAO-style recursive delegation; Long Thinking models
2. **Self-Evolving Agents**: Experience distillation, skill curation (SkillOS)
3. **Agentic RAG**: Expert-level retrieval with strong priors vs. passive search (Superintelligent Retrieval Agent)
4. **Long-Horizon RL**: Strategic trajectory abstraction for credit assignment (StraTA)
5. **Citation Verification**: Factuality in deep research agents (Cited but Not Verified)
6. **Physical Simulation Agents**: Closing the scientific discovery loop (AI CFD Scientist)
7. **Multi-Agent Prompt Optimization**: Joint optimization across interacting agents (MASPO)

## Common Failure Modes

- **Empty search results**: arXiv `all:` field is noisy — use `ti:` prefix or batch-fetch known IDs
- **Semantic Scholar 429**: Rate limited at 1 req/sec; wait or use batch mode
- **arXiv API empty entries**: XML parsing issue — always check entry count
- **Model recommendation outdated**: Technology moves fast; prefer capability categories over specific model names

## Output Format

- Primary output: structured markdown report in Chinese (user's language)
- Tone: calm, analytical, direct
- Distinguish: Fact / Assumption / Speculation
- Include: tradeoffs, constraints, failure modes
- Avoid: hype, vague claims, over-explaining basics
