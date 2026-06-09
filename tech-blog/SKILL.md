---
name: tech-blog
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
tech-blog/                           ← 📍 入口（你在这里）
├── SKILL.md                         ← 编排器（入口Skill）
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

**特殊场景 — 用户直接提供完整转录稿**：
当用户直接粘贴视频字幕全文时，素材采集工作已完成，跳过层级1-3采集流程，直接进入解析。详见 `references/youtube-source-guide.md` 层级0说明。

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
2. 其余章节在**主session直接写**，不要用 `delegate_task`

**原因**：
- `delegate_task` 有600秒超时硬限制，中文技术博客4500字≈2分钟写完，delegate大概率超时
- API限流叠加并发时触发HTTP 429
- delegate无部分完成机制：超时=全部丢失

**主session写作操作**：
- 用 `write_file` 一气呵成写完全文（不要分批）
- 用 `patch` 做后续修改（不要重写全文）

**阶段4后置一致性检查**：写完后用 `chapter-consistency-checker` 做后置一致性检查
   - 5个标准维度：术语/语气/细节层次/引用人称/引用格式
   - **额外补充**：段落级阅读体验检查（孤立短段、AI味总结句、突兀收尾句）——详见 `chapter-consistency-checker/references/prose-quality-issues.md`
   - ⚠️ **根据一致性检查报告修改初稿中的不一致项，再进入阶段5**

5. **阶段4前置禁止词汇检查**：动笔前通读素材/大纲，确认不包含以下贬低性词汇：
   - `"失败者""死亡""死人""遗产""被打败""碾压"` — 对任何技术流派的不尊重定性
   - `"复仇""复活""战争（for rivalry）"` — 戏剧化叙事，牺牲对研究者的尊重
   - 若叙事线本身含有上述元素，**重新设计叙事线**，而非仅做措辞替换

**执行约束**：
- ⚠️ `delegate_task` 有600秒超时上限。长文写作不要用delegate（见上方"主session写作"）
- ⚠️ **reader-persona-feedback 5角色并行**：max_concurrent_children=3，需分2批（第1批3角色，第2批2角色）
- ⚠️ 子任务context中传文件路径，不要内嵌全文

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
- ⚠️ `max_concurrent_children=3`，需分2批执行：第1批（资深工程师+普通读者+技术写作者），第2批（开源社区成员+商业决策者）

### 阶段7：优化决策（无专用Skill）

**操作**：Agent自行执行
- 汇总5份反馈，生成优化计划（必改/建议改/不改）
- **介入点C**：若反馈存在冲突，呈现Top3方案供用户选择

**优化计划确认后修改文章时**：
- 用 `patch` 做定向修改，**每次只改一个具体问题**（减少出错风险）
- 不要用 `write_file` 重写全文（会丢失未修改部分的质量）
- 修改顺序：必改项 → 建议改项

⚠️ **优化计划确认后，必须根据计划修改文章，再进入阶段8**

### 阶段8：格式发布

**操作**：加载 `feishu-blog-publisher`
- Markdown → 飞书XML富格式
- 自动图表意图识别（Mermaid/Table/Callout/Grid/HR）
- 创建飞书文档并返回链接

### lark-cli docs +create 参数速查表

| 命令 | 可行性 | 说明 |
|------|--------|------|
| `cat file.md \| lark-cli docs +create --api-version v2 --doc-format markdown --title "标题" --content -` | ✅ 唯一可行方式 | stdin传内容+标题 |
| `lark-cli docs +create --api-version v2 --doc-format markdown --content @./file.md --title "标题"` | ❌ 内容为空 | `--content`和`--doc-format`不兼容 |
| `lark-cli docs +create --api-version v2 --markdown @./file.md --title "标题"` | ❌ 参数不存在 | `--markdown`仅v1 API存在 |

⚠️ `--content @filepath` 只接受CWD相对路径（`./file.md`），绝对路径报 `unsafe file path`

---

## 人机协作三个介入点

| 介入点 | 位置 | 人的角色 | 触发条件 |
|--------|------|---------|---------|
| A | 阶段2→3 | 叙事线选择 | Top1置信度 ≤85% **或** 候选间差异度>20% |
| B | 阶段5→6 | 仲裁审查争议 | 技术/编辑两轨结论方向冲突 |
| C | 阶段7→8 | 选择优化方案 | 5角色反馈存在方向冲突 |

**核心原则**：人是"选择者"不是"审批者"——只在有真正选择时才介入。

**介入点A收敛检测**：
叙事线生成后，计算Top1与Top2的核心洞察差异度：
- 差异度 >20% → 正常呈现3个候选，请用户选择
- 差异度 ≤20% → 候选本质趋同，**不展示选择界面**，直接采用Top1并告知理由

差异度判定方法：对比候选的核心洞察句（不含标题/框架/结构），统计实质内容差异。

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

**推荐策略：优先主session直接写（一气呵成）**

对于**≤15,000字的中文技术博客**，阶段4初稿在主session一气呵成写完通常是最快最稳的方式。
- 优势：思路连贯不断、行文语气一致、无超时风险、读者反馈后直接在同一文件修改
- delegate_task适用于：**结构解析**、**风格评估**、**审查清单生成**等短任务，不适用于内容创作

**何时用并行delegate**：
- 阶段1解析（多源素材并行采集）
- 阶段5审查（技术/编辑双轨并行）
- 阶段6反馈（多角色并行）
- 以上任务均<200秒，不触发超时

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
7. **主 Agent 未亲手读原始材料**（用户纠正过）：写技术教程/速查手册/参考指南时，**主 Agent 必须自己读官方文档**，不能靠 delegate_task 间接抓取后总结。详见 `references/operational-constraints.md` §5。

8. **收到优先级列表时只修复指定级别**：用户说"只修复P0、P1" → 直接执行P0+P1，不解释其他级别、不列出完成项、不多问确认。执行结果简洁回报（改了几处、涉及哪些章节），不再重复清单。
7. **阶段6并行数限制**：5角色并行需分2批执行（`max_concurrent_children=3`），第一批3个角色（如资深工程师+普通读者+技术写作者），第二批2个角色（如开源社区+商业决策者）。详见 `reader-persona-feedback` SKILL.md。

8. **阶段7优化后必须修改文章**：优化计划确认后修改文章，再进入阶段8。发布未优化版本浪费前面所有阶段工作。

9. **技术博客P1级常见问题**（来源于多篇博客5角色审查发现的共识区）：
   - "Prompt/prompt"大小写不统一 → 全文统一为"Prompt"（专指本文讨论的概念）
   - "测试用例"首次出现缺括号说明 → 普通读者需要背景知识
   - Agentic Loop架构缺少状态传递机制说明 → 工程师无法复现
   - 表格数据缺绝对值 → 只有相对倍数的对比数据对商业决策者无效

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
