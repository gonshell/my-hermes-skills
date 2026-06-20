---
name: tech-blog
version: 1.1.0
description: 技术博客多智能体协作创作流水线 — 8阶段编排入口，协调6个子技能完成从原始材料到发布文章的全流程
category: tech-blog
triggers:
  - 写技术博客
  - 技术文章创作
  - 博客流水线
  - 内容创作编排
  - tech blog pipeline
---

# 技术博客创作流水线（编排Skill）

## 概述

本Skill是**编排器**，负责按正确顺序调度6个子技能完成技术博客创作。自身不执行具体任务，而是告诉Agent"先做什么、后做什么、用什么子技能"。

### 子技能位置

6 个子技能现已合并为本 skill 的 references/subskills/ 子目录（早期它们是独立 skill，2026-06 整合）。每个子技能都是完整 SKILL.md + 自己的 references/ 目录：

```
tech-blog/                                    ← 📍 入口（你在这里）
├── SKILL.md                                  ← 编排器（入口）
├── references/subskills/
│   ├── narrative-theme-generator/            ← 阶段2：叙事主线设计
│   │   ├── SKILL.md
│   │   └── references/ (debate-protocol, narrative-ethics)
│   ├── writing-style-extractor/              ← 可选前置：风格提取
│   │   └── SKILL.md + references/extraction-dimensions.md
│   ├── chapter-consistency-checker/          ← 阶段4后置：一致性检查
│   │   └── SKILL.md + references/(consistency-rules, prose-quality-issues)
│   ├── review-checklist-generator/           ← 阶段5：双轨审查
│   │   └── SKILL.md + references/checklist-templates.md
│   ├── reader-persona-feedback/              ← 阶段6：多元读者反馈
│   │   └── SKILL.md + references/feedback-template.md
│   └── feishu-blog-publisher/                ← 阶段8：格式发布
│       └── SKILL.md + references/(feishu-permissions, md-to-docx-conversion, incremental-doc-editing)
└── references/                               ← 编排器自身参考文档
    ├── operational-constraints.md
    ├── execution-diagnostics.md
    ├── research-verification-patterns.md
    ├── youtube-source-guide.md
    ├── author-voice-taxonomy.md
    ├── post-write-reflection-checklist.md
    └── latent-reasoning-fact-card.md
```

加载某个子技能时直接 `cat references/subskills/<name>/SKILL.md` 即可。它和独立 skill 一样工作。

### 早期独立 skill 列表（已合并）

合并前的 6 个独立 skill 现都已归档：narrative-theme-generator / review-checklist-generator / reader-persona-feedback / writing-style-extractor / chapter-consistency-checker / feishu-blog-publisher。它们的 SKILL.md 和 references/ 现在是 `references/subskills/<name>/` 下的子文件。调度本 skill 时直接 `cat` 即可。

---

## 八阶段流水线

```
[原始材料]
    ↓
[阶段1: 材料解析]          ← Agent直接执行，无专用Skill
    ↓
[阶段2: 叙事主线设计]       ← references/subskills/narrative-theme-generator/
    ↓ ★ 介入点A：人选择叙事线
[阶段3: 结构规划]           ← Agent直接执行，无专用Skill
    ↓
[阶段4: 初稿写作]           ← 多Agent并行 → references/subskills/chapter-consistency-checker/ 后置检查
    ↓
[阶段5: 双轨审查]           ← references/subskills/review-checklist-generator/
    ↓ ★ 介入点B：人仲裁争议（可选）
[阶段6: 多元读者反馈]       ← references/subskills/reader-persona-feedback/
    ↓
[阶段7: 优化决策]           ← Agent直接执行，无专用Skill
    ↓ ★ 介入点C：人选择优化方案（可选）
[阶段7.5: 读者视角剪裁]     ← Agent直接执行（发布前必做，不可跳过）
    ↓
[阶段7.6: 写后反思自检]     ← Agent直接执行（不可跳过，5 维度自检）
    ↓
[阶段8: 格式发布]           ← references/subskills/feishu-blog-publisher/
```

### 可选前置步骤

在阶段2之前，可用 `references/subskills/writing-style-extractor/SKILL.md` 从标杆文章提取风格指南，传递给后续写作阶段。

### 参考文档

- `references/operational-constraints.md` — delegate_task超时、API限流、素材采集策略等执行约束与踩坑记录
- `references/youtube-source-guide.md` — YouTube视频作为素材源的采集策略（含无字幕降级方案）
- `references/research-verification-patterns.md` — **网络调研数据验证**：delegate_task返回的web search结果可能包含参数量单位混淆、代际混用、变体错误等，阶段5技术审查是必须的事实安全网（2026-06 NVIDIA GTC Taipei 博客实证）
- `references/latent-reasoning-fact-card.md` — 写"潜在推理 / 神经元语 / Thinking Budget"类博客前必读的验证事实卡（含 Coconut / LRT / Deep Think / Thinking Machines 等论文的常见误读与正确措辞，2026-06 由 Neuralese 博客实战整理）
- `templates/paradigm-naming-blog-outline.md` — 范式/概念命名类博客大纲模板（如 Loop Engineering、Prompt Caching 类新概念解读的章节骨架，含 10 章 + 附录的完整结构）
- `references/post-write-reflection-checklist.md` — **写后反思自检清单**：阶段 7.5 之后、阶段 8 之前必做的作者自检，5 维度（完整性/口吻/真实性/逻辑/可落地性）+ 必修/建议/可选三档优先级。**专门覆盖 5 角色反馈抓不到的问题**（未核实数字、不可证伪断言、时效声明缺失）

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

**操作**：加载 `references/subskills/narrative-theme-generator/SKILL.md`
- 输入：阶段1的结构化输出
- 输出：3个叙事线候选 + 置信度
- **介入点A**：将Top3候选呈现给用户，请用户选择

### 阶段3：结构规划（无专用Skill）

**操作**：Agent自行执行
- 输入：选定叙事主线 + 阶段1解析结果
- 输出：章节大纲（H1/H2层级、预计字数、各章亮点）

**⚠️ 标题命名原则**（2026-06 Neuralese 博客用户强纠正实证）：
- **禁止冒号式标题**（`命名时刻：为什么必须有一个新词`）——用户原话"狗屁"，理由是"看见哪个正式的文章标题有那么多冒号的？"
- **统一为名词短语**：`模型的母语` / `Neuralese 的由来` / `显微镜下的概念空间` / `三条技术路径` / `思考的定价` / `四个未解问题` / `三类读者的判断` / `不是终局`
- **每个标题自身能传达章节核心信息**——不需要上下文读者就知道这章讲什么
- **所有标题单独读就是一条完整论证线**——从"是什么"推进到"怎么办"再收口
- **长度均匀**（4-7 字），视觉节奏一致——但要避免"为了凑长度"硬改章节名（如把"后记"改成"一年后的图景"）。如章节天然是 2 字短标题（如"引子""结语"），允许保留，但需保证全篇 ≤2 处长短标题间隔出现，不形成节奏断裂。
- **统一是逻辑统一不是格式统一**——不要靠加冒号/编号/前缀来制造一致性，要靠内容自身的逻辑递进
- 详见 `references/author-voice-taxonomy.md` §标题设计

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

**阶段4后置一致性检查**：写完后用 `references/subskills/chapter-consistency-checker/SKILL.md` 做后置一致性检查
   - 6个标准维度：术语/语气/细节层次/人称/引用格式/读者视角完整性
   - **第6维度（读者视角完整性）**：扫描过程性内容残留（元叙事、自我指令、术语速查、章末小结等）——这些是阶段4-7审查流水线的副产品，不删会导致"不能直接给读者看"
   - **额外补充**：段落级阅读体验检查（孤立短段、AI味总结句、突兀收尾句）——详见 `references/subskills/chapter-consistency-checker/references/prose-quality-issues.md`
   - ⚠️ **根据一致性检查报告修改初稿中的不一致项，再进入阶段5**

5. **阶段4前置禁止词汇检查**：动笔前通读素材/大纲，确认不包含以下贬低性词汇：
   - `"失败者""死亡""死人""遗产""被打败""碾压"` — 对任何技术流派的不尊重定性
   - `"复仇""复活""战争（for rivalry）"` — 戏剧化叙事，牺牲对研究者的尊重
   - 若叙事线本身含有上述元素，**重新设计叙事线**，而非仅做措辞替换

**执行约束**：
- ⚠️ `delegate_task` 有600秒超时上限。长文写作不要用delegate（见上方"主session写作"）
- ⚠️ **reader-persona-feedback 5角色并行**：`max_concurrent_children=3`，需分2批（第1批3角色，第2批2角色）
- ⚠️ 子任务context中传文件路径，不要内嵌全文

### 阶段5：双轨审查

**操作**：加载 `references/subskills/review-checklist-generator/SKILL.md`
- 技术审查轨道（熔炉型）：收敛到已验证/待验证/存疑
- 编辑审查轨道（放大器型）：穷举问题保留分歧
- **介入点B**：若存在未解决争议，呈现给用户仲裁
- ⚠️ **审查完成后必须根据清单修改文章，再进入阶段6**

**单源访谈/转录类博客的熔炉型轨道追加项（2026-06 实证）**：当素材是单一发言者转录（访谈/演讲/Podcast），且主 session 已按 `references/subskills/narrative-theme-generator/SKILL.md` 例外条款4跳过 3 轮辩论时，**必须在技术审查轨道中追加"逐字引用核查"步骤**：

1. 用 `re.findall(r'"([^"]+)"', article_text)` 抽出文章中所有引号内容
2. 人工挑选 5-10 条关键引语（含核心论点 + 含完整英文长句的引用）
3. 对每条引语在原稿中 `re.find` 比对，确认逐字一致（包括大小写、标点、`...` 省略位置）
4. 不一致的引语降级为意译（删除引号、改写），或在文章中标注 "[原文为意译]"
5. 把核查脚本输出写入审查报告，作为"事实层已通过"的证据

**为什么必须做**：单源转录的"事实错误"最常出现在"我以为我引的是原话但其实改了几个词"——`re.findall` + 5-10 条抽样的 70 秒脚本能拦下 90% 的此类问题。视觉上"看起来像引用"不等于"逐字引用"，读者的信任建立在字面一致上。

### 阶段6：多元读者反馈

**操作**：加载 `references/subskills/reader-persona-feedback/SKILL.md`
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

⚠️ **优化计划确认后，必须根据计划修改文章，再进入阶段7.5**

### 阶段7.5：读者视角剪裁（发布前必做，不可跳过）

**问题根因**：阶段4-7的每一轮（一致性检查→双轨审查→读者反馈→优化修补）都在**往文章里加东西**——加表格、加清单、加术语说明、加行动列表。但**从头到尾没有人从读者视角做整体剪裁**。结果是成品像一份"不断增厚的过程性文档"，而非"面向读者的博客"。

**操作**：Agent自行执行，对全文做一轮"删除扫描"——

**必须删除的过程性内容**（P0，读者会困惑"这是什么"）：

| 类型 | 典型表现 | 来源 |
|------|----------|------|
| 元叙事痕迹 | "按照反方观点的原则，这一章是必须写的" | 阶段3大纲指令残留 |
| 自我指令 | "这一章必须配上Anthropic报告里的一个观察" | 阶段4写作时的自我提醒 |
| 作者自我辩护 | "这一章用三句话给三类读者。有意不平衡" | 阶段7优化时的结构解释 |
| 元自指 | 标题下"一篇关于范式跳跃的技术博客" | 标题不应该自述体裁 |
| 自检标记 | "全文完。约5000字。证据闭环。" | 写完后的自评 |
| 预告正文内容 | "本文是X的一份系统笔记：它从哪里来…"、"这一章梳理…"、"理论归理论。这一章看…" | 作者行程单，读者要的是内容不是目录 |
| 标榜章节/证据地位 | "这一章是整篇文章的事实基石"、"最直接证据"、"最有力背书"、"最尴尬的反方观点" | 作者替读者下结论、贴情绪标签 |
| 解释结构安排 | "治理研究者的内容最长——因为这是最迫切的视角" | 解释自己的篇幅安排，读者不关心 |
| 稻草人再反驳 | "常见误读"、"不是外挂一个轻量网络而是…"、"不必把它当神迹膜拜" | 否定一个没人提出的极端立场；注意：技术对比中"不是X是Y"有信息量时保留 |
| 自我抒情收束 | "回到开头的比喻"、"同一片大陆"、"值得被记住名字" | 作者自指文章结构+情感渲染 |

> ⚠️ **7.5 需要两轮扫描**：第一轮通常只抓到显性痕迹（章末小结、自检标记），嵌入正文句子里的元叙事（预告/标榜/稻草人/抒情）需要通读全文逐段判断"这是给读者看的还是作者内心独白"。详见 `references/author-voice-taxonomy.md`。

**建议删除的整理性内容**（P1，像复习提纲/教学手册）：

| 类型 | 典型表现 | 来源 |
|------|----------|------|
| 术语速查表 | "三个核心术语速查（不熟可以先看这一段）" | 阶段4怕读者不懂加的 |
| 风格规范 | "术语锁定：本文中X一律保留英文形式" | 阶段4后置检查加的编辑指令 |
| 章末小结 | 每章末尾"> 小结：..." | 学术报告结构，博客不需要 |
| 重叠补丁表 | 阶段7为回应某角色反馈临时加的表，与已有表高度重叠 | 读者反馈的副作用 |

**执行方式**：
1. 读完全文，逐段标记"这是给读者看的"还是"这是过程性内容"
2. P0 直接删除，P1 建议删除（保留有信息价值的）
3. 用 `patch` 做定向删除，不动正文叙事骨架
4. 删完净减约 800-1200 字（5000字→4000字级别）

⚠️ **此阶段不做"重写"，只做"删除"**。不碰正文叙事，不改章节结构。剪裁是减法不是加法。

### 阶段8：格式发布

**操作**：加载 `references/subskills/feishu-blog-publisher/SKILL.md`
- Markdown → 飞书XML富格式
- 自动图表意图识别（Mermaid/Table/Callout/Grid/HR）
- 创建飞书文档并返回链接

### lark-cli docs +create 实测可行的命令（2026-06 验证）

| 命令 | 可行性 | 说明 |
|------|--------|------|
| `lark-cli docs +create --api-version v2 --doc-format markdown --content @./file.md` | ✅ **唯一最简方式** | 飞书从首行 `# 标题` 提取标题；不需 `--title` 也不需 `--new-title` |
| `lark-cli docs +create --api-version v2 --doc-format xml --content @./file.xml` | ✅ XML 自带 `<title>` | XML 模式，必备 `<title>` 首行 |

**❌ 不可行的命令（踩过的坑）：**

| 命令 | 报错 |
|------|------|
| `lark-cli docs +create ... --new-title "..."` | `unknown flag: --new-title`（旧版 SKILL 文档误传） |
| `lark-cli docs +create ... --content @file.md --title "..."` | `--content is required`（互斥冲突） |
| `lark-cli docs +create ... --markdown @file.md` | `--markdown` flag 在 v2 不存在（仅 v1 旧 API） |

**⚠️ Mermaid 图在飞书画板中会降级失败**（warning 2107）：源 .md 含 ```` ```mermaid ` ```` 代码块时，飞书会尝试解析为 `<whiteboard type="mermaid">`，但**渲染失败、显示为空白**。Mermaid 在飞书原生不支持。**解法：**用 mermaid.live 或 mermaid.ink 导出 PNG/SVG，**手动**在飞书文档中插入图片。本地 .md 用 Typora / VSCode + Mermaid 插件可正常显示。

**⚠️ `--content @filepath` 只接受 CWD 相对路径**（`./file.md`），绝对路径（`/Users/.../file.md`）会报 `unsafe file path`。解法：`cd` 到文件所在目录后再发布。

**验证发布的命令：**

```bash
# 验证文档结构
lark-cli docs +fetch --doc <doc_id> --scope outline --format pretty

# ⚠️ 注意:是 --doc 不是 --document-id（后者不存在）
lark-cli docs +fetch --api-version v2 --doc <doc_id> --scope outline
```

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
| 放大器型 | 阶段2叙事主线、阶段5编辑审查、阶段7优化决策 | 穷举候选，保留分歧 | references/subskills/narrative-theme-generator/, references/subskills/review-checklist-generator/ |
| 熔炉型 | 阶段5技术审查 | 收敛到唯一结论 | references/subskills/review-checklist-generator/ |

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
3. **chapter-consistency-checker 在阶段3运行** → 还没有初稿，无从检查
4. **把pipeline当成单一Skill调用** → 它是编排器，需要按阶段逐个调度子Skill
5. **阶段5审查后未修改文章直接进入阶段6** → 读者反馈基于未修复的文章，浪费反馈轮次
6. **用delegate_task写长文（≥5000字）** → 几乎必然超时或限流，应主session直接执行
7. **主 Agent 未亲手读原始材料**（用户纠正过）：写技术教程/速查手册/参考指南时，**主 Agent 必须自己读官方文档**，不能靠 delegate_task 间接抓取后总结。详见 `references/operational-constraints.md` §5。

8. **收到优先级列表时只修复指定级别**：用户说"只修复P0、P1" → 直接执行P0+P1，不解释其他级别、不列出完成项、不多问确认。执行结果简洁回报（改了几处、涉及哪些章节），不再重复清单。
7. **阶段6并行数限制**：5角色并行需分2批执行（`max_concurrent_children=3`），第一批3个角色（如资深工程师+普通读者+技术写作者），第二批2个角色（如开源社区+商业决策者）。详见 `references/subskills/reader-persona-feedback/SKILL.md`。

8. **阶段7优化后必须修改文章**：优化计划确认后修改文章，再进入阶段8。发布未优化版本浪费前面所有阶段工作。

9. **技术博客P1级常见问题**（来源于多篇博客5角色审查发现的共识区）：
   - "Prompt/prompt"大小写不统一 → 全文统一为"Prompt"（专指本文讨论的概念）
   - "测试用例"首次出现缺括号说明 → 普通读者需要背景知识
   - Agentic Loop架构缺少状态传递机制说明 → 工程师无法复现
   - 表格数据缺绝对值 → 只有相对倍数的对比数据对商业决策者无效

10. **阶段1材料解析漏掉"自我关联"检查**（P0 常见坑，2026-06 Loop Engineering 博客发现）：写"概念解读"类博客时，如果作者本人/团队与该概念有产品关联（如"Hermes Agent 也实现了这套思想"），**文章中出现自我引用是 P0 阻断项**——5 角色反馈中会有 ≥3 个角色标记为"软广"或"损害中立性"。**解法：**阶段 1 输出"约束条件"时显式列出"是否包含产品自指"作为检查项；若答案为"是"，阶段 4 写作时禁用第一人称关联。

11. **介入点 C（优化范围选择）实际是强干预不是可选项**：5 角色反馈产出 10+ 项 P0/P1/P2 时，**用户对"全做/只做 P0/全做+图表"等组合几乎都给出明确偏好**。本会话实证：用户直接选"P0 + P1 强烈建议"——**不要让用户自己组合**，应提供 3 个预定义套餐（只 P0 / P0+P1 / 全做），并附 5-10 字的影响说明（如"5 分钟改动 / 15 分钟改动 / 文章成标杆但改动量大"）。

12. **"lark-cli docs +create" 命令的可行性以实际报错为准**（2026-06 验证）：skill 文档速查表与真实 CLI 行为可能不一致。本会话实测：
    - `--new-title` flag 在当前版本**不存在**（旧 SKILL 文档误传）
    - `--title` + `--content @file` **互斥**
    - 唯一稳定可用：`--doc-format markdown --content @./file.md`（首行 `# 标题` 提取）
    - 详见阶段 8 速查表与 `references/subskills/feishu-blog-publisher/SKILL.md`。

13. **Mermaid 图无法在飞书原生画板渲染**：Mermaid 块会被解析为 `<whiteboard type="mermaid">` 但**渲染失败**（warning 2107）。如果博客含 Mermaid，必须**额外用 mermaid.live 导出 PNG 手动插入**。本会话两个 Mermaid 图（范式层级图 + Loop 时序图）均未在飞书渲染。

14. **资深工程师读者反馈是事实错误的最高效拦截器**（2026-06 Neuralese 博客实证）：在 5 角色并行反馈中，资深工程师角色在 70 秒内揭出 5 个**论文级事实硬伤**（Coconut / LRT / Deep Think / Thinking Machines / O(1) 表述），全部是其他角色不会触达的范畴。**实操含义**：
    - 永远不要省略 5 角色反馈中的资深工程师角色——它是技术类博客的"事实安全网"
    - 在子任务 context 中**显式提供证据源链接**（论文标题 + 团队 + 时间），让 sub-agent 能交叉验证
    - 资深工程师给出的 5 项 P0 中，**至少 3-4 项是事实错误，不是风格偏好**——必须硬修，不能用"风格差异"搪塞
    - 详见 `references/subskills/reader-persona-feedback/SKILL.md` 中"资深工程师"角色定义

15. **新事实密集型技术话题的写作模式**（2026-06 Neuralese 博客实证）：对"我了解概念但不确定论文细节"的话题，阶段 1 素材采集时应**优先列 8-10 个一手来源清单**（论文 + 团队 + 链接 + 时间），让主 Agent 自己对齐事实，**而不是仅靠 1-2 篇二手报道**。本会话阶段 1 收集了 9 份来源（Anthropic × 3, Meta, Goyal, 哈工深 LRT, Thinking Machines, King's College, Gemini Deep Think），是资深工程师能在 70 秒内揭出 5 个事实错误的**前提条件**。如发现阶段 1 素材不足 5 个一手来源，**停下来补齐再进入阶段 2**。

16. **delegate_task 调研返回的数据不等于事实**（2026-06 NVIDIA GTC Taipei 博客实证）：web search 子代理返回的技术规格可能包含参数量单位混淆（320亿→320B）、代际混用（上代Grace 72核混入Vera CPU）、变体参数错误（Cosmos 3 Super 32B实际64B）。**阶段5技术审查必须逐条验证关键数字**，不能假设"多个来源一致=正确"（可能是同一错误源的传播）。详见 `references/research-verification-patterns.md`。

16. **阶段 4-7 的审查流水线只做加法不做减法**（2026-06 Neuralese 博客实证，P0 级发现）：一致性检查、双轨审查、5 角色反馈、优化修补——每一轮都在往文章里**加**内容（加表格、加清单、加术语说明、加行动列表）。但**从头到尾没有人从读者视角做整体剪裁**。用户在初稿通过全部审查后指出："还是不能直接给读者看，内容有点乱入，如一些整理、过程性的内容都在里面"。**根因**：阶段 4-7 的审查角色（checker / reviewer / reader personas）各自只关心自己的维度，没有一个人负责"这份文章从读者第一段读到末段，有没有不必要的作者内心独白"。**解法**：阶段 7.5（读者视角剪裁）是发布前**不可跳过**的步骤，详见上方阶段 7.5 描述。

17. **`lark-cli docs +update` 覆盖发布的正确命令**（2026-06 验证）：`+create` 用 `--doc-format markdown --content @./file.md`，但 `+update` 的 flag 不同：

    | 命令 | 可行性 | 说明 |
    |------|--------|------|
    | `lark-cli docs +update --api-version v2 --doc <token> --command overwrite --doc-format markdown --content @./file.md` | ✅ **唯一正确方式** | 覆盖整个文档，revision 递增 |
    | `--markdown @file.md` | ❌ v2 不存在 `--markdown` | 仅 v1 旧 API |
    | `--doc-id <token>` | ❌ flag 是 `--doc` 不是 `--doc-id` | |
    | `--mode overwrite` | ❌ v2 用 `--command` 不是 `--mode` | v1 用 `--mode` |

    覆盖成功后返回 `"result": "success"`。

18. **冒号式标题是 P0 级设计错误**（2026-06 Neuralese 博客用户强纠正）：不要用"阶段词：具体内容"格式统一标题——这是机械统一不是逻辑统一。正确做法见阶段 3 标题命名原则。**教训**：用户指出问题时，先诊断三个层面（修辞/信息量/逻辑层）再出方案，不要直接跳到"全部加冒号"的伪统一。

19. **7.5 读者视角剪裁需要两轮**（2026-06 Neuralese 博客实证）：第一轮（路径1/外科手术）通常只删除显性痕迹（章末小结、自检标记、元叙事开头），但嵌入正文句子里的元叙事（预告/标榜/解释结构/稻草人/抒情）需要第二轮通读全文才能发现。**实操**：第一轮删完后，必须再通读一遍逐段问"这是给读者看的还是作者内心独白？"——用 `references/author-voice-taxonomy.md` 的 5 型分类做系统扫描。

20. **写后反思自检环节不可跳过**（2026-06-13 Loop Engineering 博客实证，P0 级发现）：阶段 4-7 加法 + 阶段 7.5 剪裁之后、阶段 8 发布之前，必须由**作者本人**执行一轮 5 维度自检（完整性 / 口吻 / 真实性 / 逻辑 / 可落地性），**不能外包给 5 角色反馈或一致性检查**。本次实证：5 角色反馈**全部未抓到**以下 4 类问题——(1) 未核实数字（"800 万人围观"）、(2) 不可证伪断言（"中文市场空白"）、(3) 单价未标时点、(4) 全文缺时效声明。这些是"文章整体姿态"问题，5 角色只关心"段落级质量"。**执行模板与三档优先级清单见 `references/post-write-reflection-checklist.md`。** 反思后**不要重新跑 5 角色反馈**——成本不抵，直接按自检清单修改 .md 即可。

21. **范式/概念命名类博客的反对过度设计原则**（用户偏好硬约束，2026-06-13 Loop Engineering 博客实证）：用户对"做选择需要哪些输入"的方法论是——**先要输入、再要框架、再要决策点**。套用到本 pipeline：
    - 优化范围选项**不要给"全做/不做/只改 P0"等开放组合**，要**预定义 3 个套餐**（"只 P0 / P0+P1 / 全部"）+ 各自时间与影响说明
    - 修改过程中**不要为"完整性"加额外章节**——用户偏好"最小改动"而非"覆盖全面"
    - 反方观点的密度足够即可，**不要为了"看起来全面"再加第 6、第 7 个反方维度**
    - 详见 `references/post-write-reflection-checklist.md` "三档优先级清单"和"用户对优化范围的选择偏好"

22. **单源访谈转录类博客的"逐字引用核查"不可省**（2026-06 Claude Code 周年博客实证）：单源转录类博客（访谈/演讲/Podcast）的最大事实风险不是观点争议，而是"我以为我引的是原话但其实改了几个词"——视觉上"看起来像引用"但字面不一致，读者一旦对照原文发现，信任全部崩塌。**解法**：阶段5熔炉型轨道必须包含 `re.findall` 抽取引号内容 + 与原稿逐字对比的脚本，5-10 条关键引语抽样即可拦下 90% 的此类问题。详细见阶段5补充说明。

23. **标题长度一致性检查的盲区**（2026-06 实证）：阶段3的"标题命名原则"列了"4-7 字长度均匀"——但实操中常出现"2 字短标题"（如"后记""引子"）单独破坏节奏。本轮 Claude Code 周年博客的"后记"标题（仅 2 字）就是被自动检查器捕获并被改写为"一年后的图景"（5 字）。**解法**：阶段3出大纲后，用 `len(name.replace(" ", ""))` 对所有 H2 标题跑一次长度分布，标记长度偏离均值 ±3 字的标题，要么改写、要么保留（但全篇 ≤2 处的硬性限制）。
    - 优化范围选项**不要给"全做/不做/只改 P0"等开放组合**，要**预定义 3 个套餐**（"只 P0 / P0+P1 / 全部"）+ 各自时间与影响说明
    - 修改过程中**不要为"完整性"加额外章节**——用户偏好"最小改动"而非"覆盖全面"
    - 反方观点的密度足够即可，**不要为了"看起来全面"再加第 6、第 7 个反方维度**
    - 详见 `references/post-write-reflection-checklist.md` "三档优先级清单"和"用户对优化范围的选择偏好"

24. **厂商发布会综合报道的"快速通道"与输入形态识别**（2026-06-19 NVIDIA GTC Taipei keynote 博客实证）：当用户输入是 **YouTube 视频链接（厂商 keynote 完整回放）+ 厂商官方活动页面**时，不需要走完整 pipeline。这是一种**新型输入形态**，与"单源访谈/转录类"（陷阱 22）和"概念命名类"（陷阱 21）都不同：

    - **素材特性**：视频本身只是"事件锚点 + 章节结构"，**实质内容都在厂商 Newsroom / Blog / 产品页里**
    - **工具链不同**：不走 `fetch_transcript.py`（多半 IP 阻断）、不走 `browser_navigate`（视频描述里没有内容），直接用 `mcp_websearch_searxng_searxng_web_search` + `mcp_websearch_searxng_web_url_read` 抓官方一手页
    - **可跳过的阶段**：阶段 2（叙事线生成不需要，结构是产品线维度）、阶段 6（多角色反馈不需要，用户要的是"详实真实可信"而非"读者体验"）、阶段 7.5（过程性内容少，本来就是产品列表式）
    - **不能跳过的**：阶段 1（章节 + 主题列表）、阶段 4（主 session 一气呵成写）、阶段 5（数字审查是**最重要**的安全网——产品发布会数字错误代价高）
    - **文档结构**：基础设施 → 硬件 → 软件 → 端侧 → 物理 AI → 智能体 → 现场非技术信号 → 判断与启示（按用户洞见 v2 模板）→ 数字一览表 → 参考资料
    - **详细工作流**：见 `references/youtube-source-guide.md` "层级 0.5"段和 `references/research-verification-patterns.md` "2026-06-19 实证"段

25. **Hermes 默认 web 工具不可用时的 MCP 替代**（2026-06-19 验证）：Hermes 的 `web_search` / `web_extract` 走 Firecrawl，未配置时返回 "Web tools are not configured"。**替代入口**：
    - `mcp_minimax_web_search` — 主搜索引擎，返回带 relevance_score
    - `mcp_websearch_searxng_searxng_web_search` — SearXNG 元搜索，可指定 num_results / time_range / categories
    - `mcp_websearch_searxng_web_url_read` — 单页 markdown 提取，maxLength 可调
    - **不要**继续尝试 `terminal curl YouTube`（30s 超时几乎一定失败）
    - **不要**尝试 `browser_navigate` 抓 YouTube（描述里只有章节没有内容，且 YouTube 检测机器人）
    - 详见 `references/youtube-source-guide.md` "层级 0.5"段的工具链选择表

26. **厂商发布会数字必须"先官方后二手"验证**（2026-06-19 NVIDIA GTC Taipei 实证）：与陷阱 16（delegate 调研错误）相比，本轮验证了**正确流程**：先读厂商 Newsroom 新闻稿（参数最准）→ 再读官方 Blog（功能 + 生态）→ 最后读产品页（规格）→ 数字不一致时**以 Newsroom 为准**。本轮 12 个关键数字（Vera CPU 88核 / Rubin 50 PFLOPS / RTX Spark 1 PFLOPS 等）全部通过此流程零错误验证。**注意**：第一次（2026-06 同期）的同一主题博客就有 Vera 核心数 72 vs 88、代际混淆（Grace 规格混入 Vera）等问题——证明这个验证流程不是装饰，是**必要的安全网**。

---

## 快速启动

```
用户说"帮我写一篇关于XX的技术博客"

1. 读取原始材料 → 阶段1自行解析
2. 加载 references/subskills/narrative-theme-generator/SKILL.md → 阶段2生成叙事线 → 请用户选择
3. 阶段3自行规划大纲
4. 阶段4并行写作 → references/subskills/chapter-consistency-checker/SKILL.md 检查
5. 加载 references/subskills/review-checklist-generator/SKILL.md → 阶段5双轨审查 → ⚠️ 根据审查结果修改文章
6. 加载 references/subskills/reader-persona-feedback/SKILL.md → 阶段6读者反馈
7. 阶段7自行汇总优化 → 请用户确认
8. 阶段7.5读者视角剪裁 → 删除过程性内容（不可跳过）
9. 阶段7.6写后反思自检 → 5 维度自检（不可跳过，详见 references/post-write-reflection-checklist.md）
10. 加载 references/subskills/feishu-blog-publisher/SKILL.md → 阶段8发布到飞书
```

> 📋 执行策略详见「执行策略」章节，delegate超时诊断详见 `references/execution-diagnostics.md`
