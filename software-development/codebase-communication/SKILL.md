---
name: codebase-communication
description: How to explain a codebase or technical system to a programmer audience — structure, depth, and communication style. Triggered when asked to read source code, explain a project, introduce a system, or walk through an architecture.
triggers:
  - "请阅读源码"
  - "介绍一下"
  - "讲解"
  - "说说设计"
  - explain
  - architecture overview
  - codebase introduction
---

# Codebase Communication

## Core Principle

**Programmers want direct technical description, not analogies or metaphors.**

When explaining a codebase:
- Say what it **is**, what it **does**, and how components **relate**
- Use the actual terminology (CRD, reconciler, homeserver, etc.)
- Draw the component relationship diagram
- Give concrete API names, protocol names, data structures

**Do not** start with: "Imagine a team...", "Like a factory...", "Think of it as..."

## Recommended Sequence

```
1. One-line定位 — 做什么的
2. Component inventory — 核心组件列表 + 技术栈
3. Component relationships — 组件关系图（ASCII 或文字）
4. Key data flows — 关键执行流程（数据怎么走）
5. Important design decisions — 关键约束和设计决策
```

## What to Include

| Item | Why |
|------|-----|
| 一句话定位 | 快速建立正确的心智模型 |
| 组件列表 + 技术栈 | 让读者知道代码库里有什么 |
| 组件关系（谁↔谁、用什么协议通信） | 核心结构 |
| 关键 API / 数据结构 | 可操作的技术细节 |
| 关键约束（如 Worker 无状态） | 理解设计决策的前提 |

## What to Skip

- 类比/比喻（包工头、工厂、乐队…）
- 过多的背景故事
- 实现细节在前两步就展开
- 列出所有文件、所有函数

## Audience Signals

**程序员默认**：
- 不要比喻
- 要技术术语准确
- 先结构后细节
- 可以直接上代码片段 / API endpoint

**如果用户明确说"举个例子"、"举个比喻"**，那例外。

## Examples

### Good (explaining HiClaw)

> HiClaw is a multi-Agent orchestration system. Manager coordinates Workers, Human supervises via Matrix.
> Components: Controller (Go Operator, K8s CRD) → creates Worker containers via Docker/K8s API.
> Manager (OpenClaw/CoPaw runtime) ↔ Workers via Matrix rooms.
> MinIO stores workspace, Higress routes LLM traffic.
> Workers are stateless — state lives in MinIO.

### Bad (what to avoid)

> "HiClaw is like a software team where the Tech Lead assigns tasks and engineers execute them..."
> (This is the kind of framing the user explicitly rejected.)

## Related Skills

- `codebase-inspection` — for analyzing code structure (LOC, languages, ratios)
- `architecture-diagram` — for generating visual diagrams
