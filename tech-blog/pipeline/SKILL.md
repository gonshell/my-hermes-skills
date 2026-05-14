---
name: pipeline
version: 1.0.0
description: 技术博客多智能体协作创作流水线 — 8阶段编排入口，协调6个独立Skill完成从原始材料到发布文章的全流程
category: tech-blog
triggers:
  - 写技术博客
  - 技术文章创作
  - 博客流水线
  - 内容创作编排
  - tech blog pipeline
related_skills:
  - narrative-theme-generator
  - review-checklist-generator
  - reader-persona-feedback
  - writing-style-extractor
  - chapter-consistency-checker
  - feishu-blog-publisher
---

# 技术博客创作流水线（编排Skill）

## 概述

本Skill是**编排器**，负责按正确顺序调度6个独立Skill完成技术博客创作。自身不执行具体任务，而是告诉Agent"先做什么、后做什么、用什么Skill"。

### 系统组成

```
tech-blog/                           ← 本目录
├── pipeline/                        ← 📍 你在这里（编排器）
├── narrative-theme-generator/       ← 阶段2：叙事主线设计
├── writing-style-extractor/         ← 可选前置：风格提取
├── review-checklist-generator/      ← 阶段5：双轨审查
├── chapter-consistency-checker/     ← 阶段4后置：一致性检查
├── reader-persona-feedback/         ← 阶段6：多元读者反馈
└── feishu-blog-publisher/           ← 阶段8：格式发布
```

---

## 八阶段流水线

```
[原始材料]
    ↓
[阶段1: 材料解析]          ← Agent直接执行，无专用Skill
    ↓
[阶段2: 叙事主线设计]       ← narrative-theme-generator
    ↓ ★ 介入点A：人选择叙事线
[阶段3: 结构规划]           ← Agent直接执行，无专用Skill
    ↓
[阶段4: 初稿写作]           ← 多Agent并行 → chapter-consistency-checker后置检查
    ↓
[阶段5: 双轨审查]           ← review-checklist-generator
    ↓ ★ 介入点B：人仲裁争议（可选）
[阶段6: 多元读者反馈]       ← reader-persona-feedback
    ↓
[阶段7: 优化决策]           ← Agent直接执行，无专用Skill
    ↓ ★ 介入点C：人选择优化方案（可选）
[阶段8: 格式发布]           ← feishu-blog-publisher
```

### 可选前置步骤

在阶段2之前，可用 `writing-style-extractor` 从标杆文章提取风格指南，传递给后续写作阶段。

### 参考文档

- `references/operational-constraints.md` — delegate_task超时、API限流、素材采集策略等执行约束与踩坑记录
- `references/youtube-source-guide.md` — YouTube视频作为素材源的采集策略（含无字幕降级方案）

---

## 调度指南

### 阶段1：材料解析（无专用Skill）

**操作**：Agent自行执行
- 读取原始材料文件
- 提取：主题列表、论点清单、金句摘录、背景知识标注、目标受众推断、约束条件
- 输出结构化JSON

### 阶段2：叙事主线设计

**操作**：加载 `narrative-theme-generator`
- 输入：阶段1的结构化输出
- 输出：3个叙事线候选 + 置信度
- **介入点A**：将Top3候选呈现给用户，请用户选择

### 阶段3：结构规划（无专用Skill）

**操作**：Agent自行执行
- 输入：选定叙事主线 + 阶段1解析结果
- 输出：章节大纲（H1/H2层级、预计字数、各章亮点）

### 阶段4：初稿写作（写作部分无专用Skill）

**操作**：
1. 先产出第一章作为"标杆章"（风格锚点）— Agent自行执行
2. 用 `delegate_task` 并行写作其余章节（以标杆章为参考）— Agent自行执行
3. 写完后用 `chapter-consistency-checker` 做后置一致性检查 — 加载专用Skill
4. ⚠️ **根据一致性检查报告修改初稿中的不一致项，再进入阶段5**

**执行约束**：
- ⚠️ delegate_task有600s超时上限。单章>3000字容易超时，建议每章≤2500字，或拆为"先写大纲→逐章委托"
- ⚠️ 并行delegate_task超过2个可能触发API限流。建议分批执行（先2章→再2章），而非一次性4-5章全并行
- 如果delegate_task反复超时/限流，降级为在主session直接写作（牺牲并行性换取稳定性）

### 阶段5：双轨审查

**操作**：加载 `review-checklist-generator`
- 技术审查轨道（熔炉型）：收敛到已验证/待验证/存疑
- 编辑审查轨道（放大器型）：穷举问题保留分歧
- **介入点B**：若存在未解决争议，呈现给用户仲裁
- ⚠️ **审查完成后必须根据清单修改文章，再进入阶段6**

### 阶段6：多元读者反馈

**操作**：加载 `reader-persona-feedback`
- 5角色并行独立反馈（防平均化）
- 输出5份独立反馈报告

### 阶段7：优化决策（无专用Skill）

**操作**：Agent自行执行
- 汇总5份反馈，生成优化计划（必改/建议改/不改）
- **介入点C**：若反馈存在冲突，呈现Top3方案供用户选择

⚠️ **优化计划确认后，必须根据计划修改文章，再进入阶段8**

### 阶段8：格式发布

**操作**：加载 `feishu-blog-publisher`
- Markdown → 飞书XML富格式
- 自动图表意图识别（Mermaid/Table/Callout/Grid/HR）
- 创建飞书文档并返回链接

---

## 人机协作三个介入点

| 介入点 | 位置 | 人的角色 | 跳过条件 |
|--------|------|---------|---------|
| A | 阶段2→3 | 从3个叙事线中选择1个 | 单候选置信度>90% |
| B | 阶段5→6 | 仲裁审查争议 | 无争议项 |
| C | 阶段7→8 | 选择优化方案 | 反馈无冲突 |

**核心原则**：人是"选择者"不是"审批者"——只在有真正选择时才介入。

---

## 讨论模式说明

| 模式 | 适用阶段 | 目标 | 使用Skill |
|------|---------|------|----------|
| 放大器型 | 阶段2叙事主线、阶段5编辑审查、阶段7优化决策 | 穷举候选，保留分歧 | narrative-theme-generator, review-checklist-generator |
| 熔炉型 | 阶段5技术审查 | 收敛到唯一结论 | review-checklist-generator |

---

## 执行策略

### 长文写作：主session直接写，不要delegate

阶段4（初稿写作）和阶段7（优化修改）涉及大量内容生成（≥5000字中文）。**不要用delegate_task执行这些阶段**——原因：

1. **delegate超时硬限制600秒**（`child_timeout_seconds: 600`），长文写作+多文件读取很容易超时
2. **API限流叠加**：子Agent与主Agent共享API配额，并发时触发HTTP 429
3. **delegate无部分完成机制**：超时=全部丢失，没有"已写了一半"的降级

**推荐策略：A+B混合**
- **方案A（主session写长文）**：阶段4和阶段7由主Agent直接执行write_file，不走delegate
- **方案B（小粒度delegate做短任务）**：阶段1解析、阶段5审查、阶段6反馈用delegate_task，每个控制在200秒内完成

### delegate任务粒度控制

| 任务类型 | 适合delegate？ | 目标耗时 |
|---------|---------------|---------|
| 材料解析（阶段1） | ✅ | <120秒 |
| 叙事主线（阶段2） | ✅ | <200秒 |
| 结构大纲（阶段3） | ✅ | <150秒 |
| 初稿写作（阶段4） | ❌ 主session执行 | - |
| 技术审查（阶段5） | ✅ | <180秒 |
| 读者反馈（阶段6） | ✅ | <120秒 |
| 优化修改（阶段7） | ❌ 主session执行 | - |
| 飞书发布（阶段8） | ✅ | <120秒 |

### API限流应对

如果遇到HTTP 429（该模型当前访问量过大），立即停止delegate调用，切换到主session执行。不要重试——限流期间重试只会加剧问题。等1-2分钟后再尝试小粒度delegate。

---

## 常见陷阱

1. **跳过介入点A直接写作** → 叙事线未确认导致返工
2. **阶段6读者反馈在阶段5之前运行** → 反馈基于未审查的文章，浪费时间
3. **chapter-consistency-checker在阶段3运行** → 还没有初稿，无从检查
4. **把pipeline当成单一Skill调用** → 它是编排器，需要按阶段逐个调度子Skill
5. **阶段5审查后未修改文章直接进入阶段6** → 读者反馈基于未修复的文章，浪费反馈轮次
6. **用delegate_task写长文（≥5000字）** → 几乎必然超时或限流，应主session直接执行
6. **用delegate_task写>3000字长文会超时（600s上限）** → 拆分为"大纲+逐章写作"，每章≤2500字；或直接在主session写而不委托子Agent
7. **并行delegate_task≥3个容易触发API限流（HTTP 429）** → 控制并行数≤2，或在串行模式下依次执行；素材采集类任务尤其脆弱
8. **阶段7优化后未修改文章直接进入阶段8** → 发布的是未优化版本，浪费前面6个阶段的工作

---

## 快速启动

```
用户说"帮我写一篇关于XX的技术博客"

1. 读取原始材料 → 阶段1自行解析
2. 加载 narrative-theme-generator → 阶段2生成叙事线 → 请用户选择
3. 阶段3自行规划大纲
4. 阶段4并行写作 → chapter-consistency-checker检查
5. 加载 review-checklist-generator → 阶段5双轨审查 → ⚠️ 根据审查结果修改文章
6. 加载 reader-persona-feedback → 阶段6读者反馈
7. 阶段7自行汇总优化 → 请用户确认
8. 加载 feishu-blog-publisher → 阶段8发布到飞书
```

> 📋 执行策略详见「执行策略」章节，delegate超时诊断详见 `references/execution-diagnostics.md`
