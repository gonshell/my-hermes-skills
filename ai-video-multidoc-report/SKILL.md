---
name: ai-video-multidoc-report
description: |
  跨多个飞书视频清单 doc 做综合分析报告。
  当用户给出一组飞书 doc token（默认 5 个混合数据源 doc），要求做
  趋势/技术/热点/商业/产品/安全治理 6 维度的综合分析报告时使用。
  输出新飞书 doc，结构为：数据底座 callout → §1-6 主题章（每章 事实/反方/洞见）
  → §7 调研建议（5 字段微型简报）→ 附录 A 视频 ID 索引。
  来源：与牧羊的机器人迭代多版本沉淀的方法论（详见 `provenance`）。
triggers:
  - "分析三个定时任务的飞书文档"
  - "做 AI 视频综合分析报告"
  - "跨飞书 doc 视频清单综合分析"
  - "做一份多 doc 综合分析报告"
version: 1
created: 2026-06-14  # skill 首次创建日期（固定值，与 provenance 同源）
provenance: 2026-06-14 与牧羊的机器人迭代多版本沉淀（涵盖 5 doc EbHD/HhyM/Virb/SWLX/ZzPa 共 200+ 条数据）
runtime_invariants:
  report_date: "{today}"  # 每次运行时填入当天日期（动态值）
  report_title_prefix: "AI 视频综合分析"  # 标题前缀，运行时拼成 "AI 视频综合分析 · {当天日期}"
---

# ai-video-multidoc-report

跨多个飞书视频清单 doc 做综合分析报告。
默认 5 个数据源 = 4 个 cron 任务飞书 doc（早间档 / 晚间档 / B 站 AI / 每日 AI 新闻早报） + 1 个 B 站 AI 工具合集 doc。
  - 早间档：`EbHDdKARYo4vEExQiNGc3qiGnSe`（YouTube 中文实测）
  - 晚间档：`HhyMdusqdoVcW9xLyd2c2Yc2nnf`（YouTube 英文行业事件）
  - B 站 AI：`Virbd3YyBoYK9XxqaZOccEGRnio`（B 站 AI 教学）
  - 每日 AI 新闻早报：`SWLXdMOQXoi0WFxML3zcDXuCnTd`（事件流，6-7~6-14 ~130+ 事件）
  - B 站 AI 工具合集：`ZzPad3g4NotV9OxUO9WcLTpAnEd`（时间窗互补，6-7~6-11 ~135 视频）
输出覆盖 6 主题维度 + 涌现 2 个主题 + 5-7 条洞见 + 5 字段调研建议。

---

## When to use this skill

**触发条件（满足任一）：**
- 用户明确说"做 AI 视频综合分析报告"
- 用户给了 ≥2 个飞书 doc token，里面是"视频清单"（XML/HTML/JSON 任一格式）
- 用户引用了类似的工作流（"按 v11 骨架做""洞见 + 反方 + 调研建议"）

**不触发：**
- 单个飞书 doc 的内容分析（用普通 `lark-cli docs +fetch` 流程）
- 不是"视频清单"类型的 doc（如会议纪要、代码文档、报告）
- 用户没提供 doc token 且没接受默认（见"前置输入"）

---

## 前置输入

### 必需输入
- **数据源 doc token**（默认 5 个混合数据源）：

| doc token | 类型 | 性质 | 调度 |
|---|---|---|---|
| `EbHDdKARYo4vEExQiNGc3qiGnSe` | YouTube 早间档视频清单 | 视频（中文 YouTube）| 06:00 |
| `HhyMdusqdoVcW9xLyd2c2Yc2nnf` | YouTube 晚间档视频清单 | 视频（英文 YouTube）| 20:00 |
| `Virbd3YyBoYK9XxqaZOccEGRnio` | B 站 AI 视频清单（6-13） | 视频（B 站）| 21:00 |
| `SWLXdMOQXoi0WFxML3zcDXuCnTd` | 每日 AI 新闻早报 | **事件流**（按日期分组的结构化新闻，非视频）| 单独 |
| `ZzPad3g4NotV9OxUO9WcLTpAnEd` | B 站 AI 工具视频合集（6-7~6-11）| 视频（B 站，与 Virb 时间窗互补）| 单独 |

**类型说明**：
- 3 个视频 doc（YouTube × 2 + B 站 × 1）= 72 条视频，**反映"用户看什么"**
- 1 个事件流 doc（AI 新闻早报）= 130+ 条结构化新闻事件，**反映"行业发生什么"**
- 1 个时间窗互补 B 站 doc = 135 条视频（5 天 × 27），**扩展时间窗**

**两者互补**：视频 doc 反映"用户兴趣"（带播放量、UP 主维度），事件流 doc 反映"行业全景"（带来源媒体、完整事件链）。综合分析时**必须交叉验证**。

### 可选输入
- **覆盖默认数据源**：用户给新的 doc token 列表
- **加新维度**：用户说"加 ESG / 绿色 AI / 中国监管层"维度
- **覆盖涌现主题数量**：默认涌现 2 个，可改 0-3
- **覆盖洞见数量**：默认 5 固定 + 1-2 涌现，可改
- **输出形式**：默认新建飞书 doc + 写入用户 Home Channel（`feishu:oc_de41dc899cd2e0f9afad7dddb8fa1e89`）
  - 可改为只输出本地 Markdown，不写飞书
  - 可改 doc 标题前缀

### 用户没给输入时的处理

**默认行为（不打扰用户）：**
1. 用 5 个默认 doc token
2. 用 6 主题默认（趋势/技术/热点/商业/产品/安全治理）
3. 用 5 固定洞见 + 2 涌现
4. 用 5 字段调研建议模板
5. 新建飞书 doc，标题：`AI 视频综合分析 · {当天日期}`
6. 写入 Home Channel

**不确认的原因**：
- 5 个 doc token 来自用户长期偏好（"不要重复确认已知输入"）
- 6 主题 / 5 洞见 / 5 字段是迭代出的稳定结构（详见 `provenance`）
- 如果用户不认这套默认结构，会在结果出来后明确说"换结构"

**例外：首次执行本 skill 时**，**先告诉用户默认**：
> "我准备用默认 5 doc token（3 个视频 doc + 1 个事件流 doc + 1 个时间窗互补 B 站 doc）做 6 主题分析。
> 如果你想换数据源或改结构，现在说；否则我直接做。"

---

## 报告架构（v11 骨架 + 2 涌现主题）

> **v11 骨架说明**：6 主题（§1-§6）来自 v11 迭代结果，命名固定但**内容可调整**。

### 文档结构

```
# AI 视频综合分析 · {当天日期}
> 数据底座（callout 块，不占 H2 编号）
  - 5 doc / 200+ 条数据 / 播放量按运行时汇总（举例数值，实际计算）
  - 加权说明
---
## §1 趋势
### 1.1 事实
### 1.2 反方
### 1.3 洞见 N
## §2 技术
### 2.1 事实
### 2.2 反方
### 2.3 洞见 N
## §3 热点
### 3.1 事实
### 3.2 反方
### 3.3 洞见 N
## §4 商业
### 4.1 事实
### 4.2 洞见 N（如本章无独立反方，反方并入洞见内）
## §5 产品
### 5.1 事实
### 5.2 反方
### 5.3 洞见 N
## §6 安全治理
### 6.1 事实（如实标注：本章暂无洞见、无反方）
---
## §7 调研建议
### 7.1 建议 N（3 核心字段 + 2 可选字段）
---
## 附录 A 视频 ID 索引
### A.1 早间档
### A.2 晚间档
### A.3 B 站 AI
```

### 主题选择规则
- **§1-6 固定**：趋势 / 技术 / 热点 / 商业 / 产品 / 安全治理
- **涌现 2 个主题**：从 5 doc 内容里识别 §1-6 之外反复出现的主题
  - 例：视频 doc + 事件流 doc 里"国产 AI 商业化"反复出现（Kimi M3 / 阿里 Token Foundry / 豆包收费 / 智源 Physis）→ 涌现"国产 AI 商业化"主题
  - 例：5 个 doc 里"模型分级 / 主动受限"反复出现（Anthropic Fable 5 出口管制 / Mythos / Glasswing / 出口管制事件）→ 涌现"AI 出口管制"主题
  - 涌现主题放在 §6 之后、§7 调研建议之前，作为 §6.x 子节

### 单事件不重复切分（用户硬性偏好）
- **症状**：一个事件（如 Anthropic Fable 5）出现在 §2.2、§2.3、§3.3、§5.2、§7.1 五处
- **根因**：维度即切面 = 同一事件在不同视角下重复展开
- **解法**：用"主述 + 引用"模式
  - 主场展开：事件核心矛盾在哪层就放哪层
  - 其他章节：1 句话 + 内部链接（"详见 §3.3 洞见 1"）
- **反例**：早期报告 §2 §3 §5 §7 都有 Fable 5 完整展开 → 5 次重复
- **正例**：v11 骨架主场放 §3.3（技术层），§5 商业只引用，不重复展开

### 章节内部 H3 强制
- §1-§6 每章必须拆为「事实 / 反方 / 洞见」H3 三层
- 即使某章无洞见 / 反方，必须**显式标注**"本章为事实层，暂无洞见"——**不省略**
- 内部段落不用粗体伪装 H3，目录树必须能展开

### 编号系统
- 洞见：全局编号 `洞见 1 ~ N`，跨章节连续
- 反方：全局编号 `反方 1 ~ N`，跨章节连续
- 事实小节：跟章节号 `1.1 / 1.2`，只在本章内
- 这样引用时可以说"见洞见 2"或"见反方 3"

---

## 洞见模板（5 个核心要素）

每个洞见必须有这 5 个要素，**不省略、不错位**：

### 1. 现象（1-2 句反常描述 + 判断钩子）
- 用反常点切入，不用数据罗列
- 必须有判断钩子（"高播放 ≠ 热点"类）
- 对比性数字用 OK，绝对量少用

### 2. 可能的解释（涌现维度，不是预设三维）
- 维度名从现象涌现（"为什么是 X 形态""为什么集中在这个时间点"）
- 不强制 3 个，2-4 个均可
- 维度名本身就是问题（不是"技术/产品/商业"标签）

### 3. 倾向（主动判断 + 一句理由）
- 标"更相信 X 解释" + 一句为什么
- 不是结论，是立场标记
- 跟"未验证"段配合使用

### 4. 未验证 / 替代假设
- 不是"缺数据"，是"如果我是错的，替代解释是什么"
- 必须包含"怎么区分"（可验证的判别方法）
- 数据缺口可以保留，但**不是主体**

### 5. 来源锚点
- 指向"现象"出现的具体数据点（哪条视频 / 哪个 doc）
- 可独立核验（带视频 ID 或频道名）

### 洞见模板示例（来自真实运行产物，洞见 2 案例）

```
### 2.3 洞见 2：B 站 AI 教学是"用户补课"还是"算法推流"？
**现象：** B 站排名第一的视频不是 AI 新闻（DiDi_OK 1990 万播放），
而是与 AI 无关的 B 站创作大赛。22 条里 11 条是教学，但播放量最高
的那条跟 AI 无关。高播放 ≠ 热点，高播放 = 补课。

**可能的解释：**
- **为什么是搬运 + 中文字幕而不是原创：** 中文世界对英文资源的
  结构性依赖（MIT 课程、Andrew Ng、SD 整合包都是英文原版翻译）
- **为什么集中在这个时间点：** LLM 把"Prompt+Agent"变成新基础
  能力，传统 IT 培训跟不上需求
- **B 站的生态选择：** 长视频教学在抖音/小红书不成立，B 站是
  中文世界唯一承接"系统化补课"的平台

**倾向：** 更相信"结构性语言依赖"——如果只是技术补课需求，
不会集中出现"搬运 + 中文字幕"这种特定形态，这个形态指向的
是中文世界对英文资源的依赖，不是知识本身。

**未验证 / 替代假设：** 如果"再教育基础设施"是错的，替代解释
是"B 站推荐算法对长视频教学的系统性倾斜"。区分方法：看这些
教程的完播率（用户主动补课 → 完播率高；算法推流 → 完播率低）。

**来源锚点：** 22 条 B 站视频里 11 条是教学（virb #2 AlfredTaylorHD
1046 万、#3 PyTorch 土堆 815 万、#8 Nenly SD 447 万）
```

### 洞见数量
- 5 个固定（覆盖 §1-§6）
- 1-2 个涌现（从涌现主题里挖）
- 涌现的洞见也要走完整 5 要素模板

### 洞见筛选门槛（"人/心理/处境"维度）
每条洞见必须能回答下列之一：
- 这件事背后是**什么样的人**在做什么？
- 用户 / 创作者 / 公司的**心理状态**是什么？
- 行业 / 市场的**结构性处境**是什么？

不能只说"事件 A 发生了，数据是 X"——这不构成洞见。

---

## 反方模板

每条强判断必须配 1 条反方。**3-5 条关键反方**（不是每个都配）。

### 反方模板
```
**反方：** [1-2 句质疑 + 1 句独立证据 + 1 句"该判断需补 XX 才能下结论"]
```

### 反方放置位置
- 跟强判断同章，反方放在该章"反方" H3 段
- 如本章无独立反方（如 §4 商业），反方并入洞见内的"未验证"段
- 不在文档末尾集中放反方（破坏"读一章就能拿全信息"）

### 反方与未验证的区别
- **反方** = 对**已发生事实数据**的质疑（ARR 自报 / 估值虚高 / 流量集中在 1 条）
- **未验证 / 替代假设** = 对**现象的解释**的替代（"算法推流 vs 用户补课"）
- 不能混淆

---

## 调研建议模板（3 核心字段 + 2 可选字段）

### 5 字段定义

| 字段 | 必需 | 例子 |
|---|---|---|
| **核心问题** | 必需 | 不是话题，是问题（"主动受限：差异化策略还是合规防御？"）|
| **类型** | 必需 | 技术 / 市场 / 商业 / 政策 |
| **为什么现在做** | 可选 | 时间窗口 + 不做会错过什么 |
| **切入路径** | 必需 | 3 步动作清单，每步"具体动作 + 数据源" |
| **预期产出** | 必需 | 查完手里有什么（判断 / 数据集 / 框架）|

### 调研建议数量
- 5-6 条
- **建议结构**（按"来源"分 3 类）：
  - **A 类（洞见延伸）**：从洞见的"未验证 / 替代假设"延伸——每条洞见至少可挖 1 个调研问题
  - **B 类（纯技术 / 政策学习）**：不来自洞见，纯粹是"用户应该学的技术/政策"——如 "1M token 工程实现"、"网信办 14 类执行细节"
  - **C 类（错位补救）**：当**事件流有重要新闻但视频 doc 0 覆盖**时，调研建议要补这个错位——v12 跑出来的 6 条调研建议里 3 条是这种
- **正例（v12 跑出来的错位补救）**：
  - "AI 出口管制对 LLM 行业结构的实际影响"（事件流 6-14 #1 头条但视频 doc 0 覆盖）
  - "OpenAI IPO 估值与商业基本面"（事件流 6-14 #7 头条但视频 doc 0 覆盖）
  - "华强北 AI 终端消费品赛道"（事件流 6-14 #10 头条但视频 doc 0 覆盖）
- **错位判断标准**：事件流有完整 "标题 + 来源 + 摘要" 三字段 + 视频 doc 同一关键词出现 0 次 = 错位补救候选

### 调研建议放置位置
- 放在 §7（在文末，**不在开头**——它是输出物，逻辑上应在所有分析之后）
- 每条用 H3（### 建议 N：xxx）
- §7.1 评估口径**不保留**（评估逻辑融入每条的"为什么现在做"）

---

## 工作流（执行步骤）

按顺序执行，**不跳步**：

### Step 1：拉 5 doc 全文

**5 个 doc 都要拉**：

```bash
# === 3 个视频清单 doc（XML 格式，每个 doc 一个 fetch）===
lark-cli docs +fetch --api-version v2 \
  --doc EbHDdKARYo4vEExQiNGc3qiGnSe \
  --doc-format xml --scope full

lark-cli docs +fetch --api-version v2 \
  --doc HhyMdusqdoVcW9xLyd2c2Yc2nnf \
  --doc-format xml --scope full

lark-cli docs +fetch --api-version v2 \
  --doc Virbd3YyBoYK9XxqaZOccEGRnio \
  --doc-format xml --scope full

# === 1 个事件流 doc（每日 AI 新闻早报）===
lark-cli docs +fetch --api-version v2 \
  --doc SWLXdMOQXoi0WFxML3zcDXuCnTd \
  --doc-format xml --scope full

# === 1 个时间窗互补 B 站 doc ===
lark-cli docs +fetch --api-version v2 \
  --doc ZzPad3g4NotV9OxUO9WcLTpAnEd \
  --doc-format xml --scope full
```

**重要**：
- 全部 `--doc-format xml --scope full`，5 个 doc 都不能省
- 事件流 doc（SWLX）跟视频 doc 解析方式不同，见 Step 2
- doc 引用用 `+update`（不是 `+import`）

### Step 2：解析 5 doc
按 doc 类型分别解析：

**视频 doc（4 个）**：
- 提取 `<li>` 内 `<a href>` 标题
- 提取 `频道：xxx` / `UP主：xxx` / `播放：xxx` / `时长：xxx` / `上传：xxx` 字段
- 分类为 TOP 10 / TOP 5 / 当日新发 等子节

事件流 doc（1 个，SWLX）：
- 按 `<h2>2026年06月XX日（周X）</h2>` 切分日期段
- 每段内 `<b>N. 标题</b>` + 来源 + 摘要
- 提取：日期 / 编号 / 标题 / 来源媒体 / 摘要前 80 字
- **完整解析配方**（含兜底方案、跨日统计、关键词提取）：见 `references/event-stream-doc-parsing.md`

### Step 3：跨 doc 数据汇总
- 统计：每 doc 条数、总播放量、5 doc 播放量比
- 重复检测：同一视频在多 doc 出现（如 Anthropic Fable 5 出现在早间档 + 晚间档）
- 频道 / UP 主频次：找出 5 doc 共同出现的高频创作者（如"橘鸦 Juya"出现 4 次）
- 关键词频次：粗略主题分布
- **关键错位识别**（v12 跑通的核心步骤）：
  - 跨 5 doc 统计同一关键词的"视频 doc 出现次数" vs "事件流 SWLX 出现次数"
  - 错位 = 事件流有完整 "标题 + 来源 + 摘要" 三字段 + 视频 doc 同一关键词 0 次
  - v12 找到的 6 大错位：Fable 5 出口管制 / OpenAI IPO / OpenAI 调查 / Microsoft MAI 7 / 智源大会 / 华强北转型
  - **错位补救**是 §7 调研建议的特殊类别（见下文）
- **数据快照时间戳**：报告 §0 写"数据快照 YYYY-MM-DD HH:MM（基于 5 doc 当前内容）"——不写历史日期（cron 任务当天会覆盖，详见 P0 陷阱）
- 关键词频次：粗略主题分布

### Step 4：写 6 主题章（§1-§6）
每章写"事实 + 反方（如有）+ 洞见（如有）" 3 段：
- **事实段**：本主题下 5 doc 里出现的事件罗列 + 关键数据
  - 视频 doc 数据：作为"用户兴趣"佐证
  - 事件流 doc 数据：作为"行业全景"佐证
  - **两者必须交叉验证**（"用户看的"vs"行业发生的"是否一致）
  - **5 doc 交叉验证矩阵**（3 种错位 + 写入位置 + 实战限制）：见 `references/multi-source-cross-validation.md`
- **反方段**（如有）：1-2 条对该章强判断的质疑
- **洞见段**（如有）：1 条洞见，走完整 5 要素模板

### Step 5：识别 2 个涌现主题
从 5 doc 内容里识别 §1-6 之外反复出现的主题，作为 §6.x 子节。
**5 doc 涌现示例**：
- "国产 AI 商业化"（Kimi M3 / 阿里 Token Foundry / 豆包收费 / 智源 Physis）
- "AI 出口管制"（Anthropic Fable 5 出口管制 / Mythos / Glasswing / 出口管制事件）
每个涌现主题至少 1 条洞见。

### Step 6：写 §7 调研建议（5-6 条）
- 4 条从洞见延伸（每条核心问题 + 类型 + 切入路径 + 预期产出 + 来源锚点）
- 1-2 条非洞见驱动的纯技术 / 政策学习

### Step 7：写附录 A 视频 ID 索引
按 doc 分组列 4 个视频 doc 全部视频（200+ 条），不省略。
事件流 doc（SWLX）不展开列，引用"事件流"指向 SWLX doc。

### Step 8：覆盖写回飞书 doc
```bash
# 路径陷阱：lark-cli 不接受绝对路径
# 解法：cp 到 cwd（/Users/xiesg）后用 ./filename
cp ./v12_report.md ./v12_report.md  # 已在 cwd
lark-cli docs +update --api-version v2 \
  --doc {user_target_doc} \
  --doc-format markdown \
  --command overwrite \
  --content @./v12_report.md
```

**默认输出目标 doc**：`MLR7duTUnoln0WxI0ErcLrrun4g`（历史综合分析报告同一 doc）
**新建默认行为**：
- 用户没指定目标 doc 时，新建一个
- 标题格式：`{runtime_invariants.report_title_prefix} · {runtime_invariants.report_date}`，运行时填充当天日期
- 写入 Home Channel（`feishu:oc_de41dc899cd2e0f9afad7dddb8fa1e89`）

---

## 输出形态

### 默认输出
1. 新飞书 doc，标题 `AI 视频综合分析 · {当天日期}`
2. 写入 Home Channel
3. 用户在飞书里直接打开阅读

### 替代输出
- 用户说"只输出本地" → 写到 `/Users/xiesg/workspace/ai_video_report_{日期}.md`，不写飞书
- 用户说"覆盖现有 doc" → 默认 `MLR7duTUnoln0WxI0ErcLrrun4g`，可用 `--doc` 覆盖
- 用户说"读出到聊天" → 不写飞书，直接 send_message 报告摘要

### 报告长度
- 5 doc / 200+ 条数据 → ~25-30 KB Markdown
- 3 doc / 72 条数据 → ~17-20 KB
- **不要超 35 KB**（飞书 doc 加载慢）

---

## Pitfalls（踩过的坑）

### P0：找 cron 任务 doc token 的正确路径（历史严重错误，绕 4 圈）

**症状**：历史报告找 5 个 doc token 走了 4 圈错误路径。

**错误路径（不要走）：**
- 1. `lark-cli drive files list` —— 只能看到 bot 名下 doc，cron 任务写的 doc 不一定都在 bot 名下
- 2. `~/.hermes/home/.hermes/cron/output/*.xml` —— XML 是步骤 1 产物（视频内容），不包含 doc token
- 3. `lark-cli wiki spaces list` —— bot 未授权任何 wiki 空间
- 4. jobs.json 全文 `\b[A-Za-z0-9_-]{13,30}\b` 正则匹配 —— 0 匹配，因为 doc token 紧跟中文"飞书文档Token"无词边界

**正确路径：**
- 直接读 cron 任务的 **prompt 全文**（不是 prompt_preview 截断）
- 在 prompt 文本里找**"写入飞书文档Token {token}"** 模式
- 4 个 cron doc token 都在 prompt 文本里直接出现

**正确代码：**
```bash
# 1. 找 jobs.json
SNAPSHOT=$(ls -d ~/.hermes/state-snapshots/*/cron/jobs.json | tail -1)
# 2. 直接打印 prompt 全文
python3 -c "
import json
with open('$SNAPSHOT') as f: d = json.load(f)
for j in d['jobs']:
    print('='*60)
    print('JOB:', j.get('name'))
    print(j.get('prompt', ''))
"
# 3. 在 prompt 里搜"写入飞书文档Token X"模式
#    或"飞书文档Token X"或"lark-cli docs +update --doc X"
```

**反例（历史犯的错）：** 用 `\b[A-Za-z0-9_-]{13,30}\b` 在 prompt 全文里搜 token → 0 匹配 → 误以为 prompt 不含 token → 走 bot drive / XML / wiki 4 圈绕路。

### P0：用"标题"当"事件"（历史严重错误）
- **症状**：把"FireShip 评 Fable 5"（5:09 评论）当成"Anthropic Fable 5 产品发布"事件
- **根因**：评论（短片）的高播放来自"事件报道 + 短片转译"二阶传播链，不是产品本身
- **解法**：区分"事件"和"评论"——看视频时长、播放量来源、频道性质
  - Bloomberg 47 分钟 92.8 万 = 事件报道
  - Fireship 5:09 56.9 万 = 二阶评论
  - 不能并列分析

### P0：维度即切面，不是洞见（历史严重错误）
- **症状**：把 6 维度当"分类器"用，每条说"什么属于趋势"没说"为什么是趋势"
- **根因**：维度 = 视角，不是事实。强行按维度切片导致同一事实在 2-3 个维度里出现
- **解法**：洞见 = 可证否的强判断 + 反方观点 + 替代假设，不是"维度里讲一遍"

### P0：数据覆盖不全（历史严重错误）
- **症状**：早期报告只读了 1/3 doc（晚间档 25 条），主题严重失衡（全英文）
- **根因**：bot drive 里只能看到自己名下的 doc，cron 任务写的 doc 不一定都是 bot 名下
- **解法**：**从 cron 任务的 prompt 找 doc token**（prompt 里有"步骤 2：写入飞书文档Token xxx"），不是从 bot drive 找
  - 找 doc token 的正确路径：`hermes auth list` / cron jobs.json 全文 / 5-30 本地 XML（**不**含 token，没用）
  - bot drive `lark-cli drive files list` 是辅助验证，不是首选

### P0：cron 任务当天会覆盖历史 doc（数据时效性陷阱）
- **症状**：早期报告引用的"6-13 晚间档 25 条"内容，**6-14 跑 skill 时已被 6-14 内容替换**——所有引用 6-13 晚间档的事实陈述过几小时就失效
- **根因**：cron 任务的 `+update overwrite` 模式用同一 doc 反复覆盖，**不保留历史版本**
- **解法**：
  1. 报告 doc 写"基于 6-14 早间档数据"而不是"基于 6-13 晚间档"
  2. 报告生成时间戳用"今天"而不是引用 doc 的标题日期
  3. 如果用户引用了 v9 报告的旧事实，**用今天的 doc 重拉**确认是否仍成立
- **正例**：报告 §0 写"数据快照 2026-06-14 09:00（基于 5 doc 当前内容）"
- **反例**：报告 §0 写"基于 6-13 晚间档 25 条视频"——6-14 跑时这条引用已经过期

### P0：lark-doc 路径陷阱（skill 自己踩过 —— 强化版）
- **症状**：`--content @/absolute/path` 报错 "invalid file path"
- **根因**：lark-cli 只接受 CWD 相对路径
- **解法**：cp 文件到 cwd（`/Users/xiesg`），用 `--content @./filename.md`
- **skill 自己的失败模式**：在 execute_code 里用 subprocess.run + 列表参数构造命令时，**`./` 前缀会被 shell / Python 字符串处理掉或转义**，导致实际跑的还是 `@/Users/xiesg/xxx`（绝对路径），仍然报错
- **正确解法**：**用 terminal() 工具跑 lark-cli，不要在 execute_code 里跑**——terminal 直接吃 shell 字符串，`./` 前缀能正确传递
- **正例（terminal 跑）**：
  ```bash
  lark-cli docs +update --api-version v2 --doc XXX --doc-format markdown --command overwrite --content @./v12_report.md
  ```
- **反例（execute_code 跑）**：
  ```python
  subprocess.run(['lark-cli', 'docs', '+update', '--content', '@/Users/xiesg/v12_report.md'])
  # rc=2, stderr: invalid file path "/Users/xiesg/v12_report.md"
  ```

### P0：YouTube 直 curl 太慢（外部抓取不可用）
- **症状**：`curl https://www.youtube.com/watch?v=xxx` 超时
- **解法**：用 oembed / Invidious 公共实例拿 description/字幕
  - oembed：`https://www.youtube.com/oembed?url=xxx&format=json`（无 key）
  - Invidious：`https://yewtu.be/api/v1/videos/xxx`（无 key）
  - yt-dlp 可用但慢（60s+ 超时）

### P0：飞书 doc 拉取用 markdown 会被截断（关键陷阱）
- **症状**：`--doc-format markdown` 拿到的内容缺 `<li>` 后的频道 / 播放 / 时长等字段——只看到标题看不到元数据
- **根因**：lark-cli markdown 模式单次只返回一屏（约 10 KB），超过就截断
- **解法**：**必须**用 `--doc-format xml --scope full` 拿完整内容
- **验证**：拉完解析后，看 `<li>` 数量是否 = 文档里视频条目数（早间档 25 / 晚间档 25 / B 站 22 = 72）。markdown 模式只看到一半
- **正例**：72 条全在 → 用 xml 模式
- **反例**：拿到 25 条就开始分析 → 误以为是"全部" → 主题失衡（只看到英文 YouTube 主题）

### P1：ZzPa 文档结构特殊 —— 日期段是空的，实际内容在末尾汇总 section
- **症状**：`ZzPad...` doc 有 24 个 `<h2>` 分日 section，但**每个日期 section 几乎是空的**（只有 `<hr/>` 分隔线）
- **根因**：ZzPa doc 的真实内容结构是"日期占位 + 末尾汇总"——`📺 一周内新发 · 最热门长视频 TOP 20` 和 `🎵 一周内新发 · 最热门短视频 TOP 7` 两个 section 才是真正可读内容
- **解法**：
  1. 不要按 `<h2>日期</h2>` 切 ZzPa，会得到 24 个空 section
  2. 直接找"📺 一周内新发 · 最热门长视频 TOP 20"和"🎵 一周内新发 · 最热门短视频 TOP 7"两个 section
  3. ZzPa 的视频条目格式是 `<p><b>N.</b> 标题</p><blockquote>UP主 + 时长 + 播放 + 点赞 + 日期 + 链接 + 标签</blockquote>`，**不是**其他 doc 的 `<li>` 格式
- **正例**：
  ```python
  for sec_label in ['📺 一周内新发 · 最热门长视频 TOP 20', '🎵 一周内新发 · 最热门短视频 TOP 7']:
      m = re.search(rf'<h2>{re.escape(sec_label)}</h2>(.*?)(?=<h2>|$)', zc, re.S)
      # 解析 <p><b>N.</b> 标题</p><blockquote>...链接...</blockquote>
  ```

### P1：SWLX 事件流标题在 `<b>...</b>` 里，不是 `<text>`
- **症状**：用 `<b>N.</b> <text>标题</text>` 正则找不到 SWLX 事件
- **根因**：SWLX 实际格式是 `<b>1. 完整标题</b><br/>来源：xxx<br/>摘要：xxx`——**整条标题都在 `<b>` 标签里**，没有第二个 `<text>` 标签
- **解法**：
  ```python
  b_m = re.match(r'\s*<b>(\d+)\.\s*(.+?)</b>\s*(.*)', txt, re.S)
  # 标题 = b_m.group(2)
  # 来源/摘要 = re.split(r'<br/>', b_m.group(3))
  ```
- **正例（v12 已跑通）**：5 doc 解析后 SWLX 95 事件 = 6-7(16) + 6-8(9) + 6-12(48) + 6-13(12) + 6-14(10)

### P1：飞书 doc fetch 单次不能拉全
- **症状**：用 `--scope section --section "6"` 拿到不完整
- **解法**：用 `--scope full` 拉全部，分页解析

### P1：execute_code 在 sandbox 里跑，cwd 是 /Users/xiesg
- **症状**：以为 cwd 是 sandbox 临时目录，纠结"绝对路径 vs 相对路径"
- **实际**：sandbox cwd **已经是** `/Users/xiesg`，所以：
  - 写文件 `write_file /Users/xiesg/xxx` = 直接写到家目录，**OK**
  - `terminal` 命令里用 `./filename` 引用 cwd 文件 = **OK**
  - `subprocess.run(..., cwd=None)` 默认 cwd 就是 `/Users/xiesg` = **OK**
- **解法**：**优先用绝对路径**（最稳，不依赖 sandbox 行为），相对路径只在 lark-cli 调用时用
- **lark-cli 例外**：`--content @/Users/xiesg/foo.md` 报"unsafe file path"——必须用 `./foo.md` 引用 cwd 文件

### P0：用户偏好"先给方案再执行" + "逐个确认，不一次铺开"
- **症状**：直接动笔写报告 / 直接改结构 / 直接重构 / 一次性做完所有事
- **根因**：用户的方法论是"做选择需要的输入 → 判断框架 → 决策点"——不要给 A/B/C/D/E 选项让他选，先解释选项背后的依据、假设、盲区
- **解法**（每一步大改动前）：
  1. 先反思：找出 3-5 个可能方案，标"我倾向 X 因为 Y"
  2. 给出方案：每个方案列"假设/依据/盲区"
  3. 让用户选：让用户做"判断"，不是"挑选项"
  4. 用户点头后再执行
- **反例（历史多次犯的错）**：
  - 早期版本：每版都直接改，没让用户选
  - 后续：直接重写而不是"先反思给方案"
  - skill 设计：直接给完整 skill，没先讨论结构
- **正例**：之前先问"§7 §0 怎么处理" → 用户选 → 改
- **例外**：用户已经明确说"按你的方案做"或"直接做"——这时候直接做，不重复确认

### P1：用户偏好"反思后整理方案让我确认"
- **症状**：直接动笔写报告，被用户打回"反思后整理方案让我确认"
- **解法**：每个大改动前先给方案 → 4 选 1 让用户确认 → 确认后再写
- **附加**：方案里要标"反方观点/盲区/无法证伪的假设"——不能只给正面方案，必须自我批判

### P1：execute_code 在 sandbox 里跑，cwd 是 /Users/xiesg（已移到上面）

### P2：报告"综合性" = 跨 doc 整合，不是 doc 内罗列
- **症状**：5 个 doc 独立罗列，没做"跨 doc 主题互补 / 商业信号分歧 / 信源重合 / 时间窗 / 验证"5 类跨 doc 洞见
- **解法**：必须做"跨 doc 洞见"——5 doc 主题互补 / 跨语种叙事差异 / 信源重合度

### P0：skill 文档不要写死日期或历史版本号
- **症状**：skill 的 `provenance` / `description` 写了具体日期（如 `2026-06-14`）或迭代版本号（`v1→v11`）——用户问"以后这个 skill 生成的所有飞书文档都是这个日期么？"——答"不是"，因为 skill 只标 provenance，**runtime 填 {today}**
- **根因**：误把 provenance 当生成时间
- **解法**：
  - **provenance / created**：写具体日期 `2026-06-14`（skill 创建时间）——这是元数据，**不**会变
  - **runtime_invariants.report_date**：用占位符 `{today}`（每次运行填入当天日期）——这是动态值
  - **runtime 字段**（`report_date` / `report_title_prefix`）：用 `{today}` 等占位符，每次 runtime 填
  - **历史版本号引用**（`v1-v11` / `v9 失败`）：不要写在 skill 里——改为"历史严重错误"等描述性文字
  - 全文 grep 验证：`grep -nE "(v[0-9]+-v[0-9]+|今天 N|今天\\d)" SKILL.md` 应返回 0 行

### P0：用户给 N 个 doc token，必须确认全部拉取到才能开始分析（防止"漏读 2/3"反复发生）

- **症状**：用户给了 5 个 doc token，agent 实际只读了 1 个就开始写报告 → 主题严重失衡 → 用户打回"重做"
- **根因**：
  - 拉第一个 doc 成功后想"差不多够了"
  - 找不到其余 doc 的 token 时"先做能做的"
  - bot drive `lark-cli drive files list` 只能看到自己名下的 doc，**其他 doc token 用户已给但 agent 没去拉**
- **解法（必须按顺序做）**：
  1. 用户给的每个 doc token **先全部 `lark-cli docs +fetch` 一次**，不要在中间停下来"先写一些"
  2. 每个 fetch 后**立刻**统计 `<li>` 数量 / `<h2>` 数量 / 总字节数，**写到 todo 列表里**——不靠记忆
  3. 任何 doc 拉失败 / `<li>` 数 < 预期 / 拿不到元数据，**暂停** → 报告"该 doc 拉取失败" → 问用户怎么办，**不**继续假装拉到了
  4. **拉完 5 个 doc 才开始写报告**——把"全部拉取完毕"作为写报告的前置条件
- **验证清单新增项**：
  - [ ] 用户给的每个 doc token 都有对应的 fetch 调用记录
  - [ ] 每个 doc 的 `<li>` / `<h2>` 数量已记录，且与 doc 类型匹配（视频 doc ≥ 20 / 事件流 doc ≥ 30）
  - [ ] 拉失败的 doc 在报告里**显式标注**"该 doc 未拉到"，不**在分析里跳过**就当没这个 doc
- **历史教训**：
  - 第一轮报告：用户给了多个 doc token，agent 只读了晚间档 1 个（25 条），其余 100+ 条 B 站 + 早间档 + 事件流**全部漏读**。主题严重偏向英文 YouTube 行业事件
  - 修复后用户又加了 2 个新 doc（事件流 SWLX + 时间窗互补 B 站 ZzPa），变成 5 doc。如果不及时更新 skill，又会发生"只读 3 个老的、漏 2 个新的"

### P0：HERMES HOME 路径（单层，不是双层嵌套）
- **症状**：错误认为 `~/.hermes/` 指向 `~/.hermes/home/.hermes/`（双层嵌套）
- **实际**：`$HERMES_HOME=/Users/xiesg/.hermes`（**单层**），skills 在 `$HERMES_HOME/skills/` 下直接放顶层
- **解法**：用 `$HERMES_HOME` 环境变量，不要硬编码 `~/.hermes/`
- **陷阱**：`write_file /Users/xiesg/.hermes/skills/foo/SKILL.md` 看似写对——其实是双层嵌套的浅层，**hermes 不会读**；必须用 `$HERMES_HOME/skills/foo/SKILL.md` 或在 shell 里 `echo $HERMES_HOME` 确认
- **验证**：`ls $HERMES_HOME/skills/ | grep <skill_name>` 应该返回 1 行

### P2：minimax provider 双账户 base_url 陷阱
- **症状**：`minimax` provider base_url 错误，请求 401
- **解法**：用 `minimax-cn`（base_url = `api.minimaxi.com/anthropic`），不是 `minimax`（base_url = `api.minimax.io/anthropic`）

### 参考资料
- `references/event-stream-doc-parsing.md`：事件流 doc（SWLX）完整解析配方
- `references/multi-source-cross-validation.md`：5 doc 交叉验证矩阵
- `references/lark-drive-ownership-ops.md`：飞书云文档所有权管理操作（转移 / 删除 / 权限查询）

### P1：方案堆叠让用户懵（历史教训）
- **症状**：反思后给方案时，列出 3-5 个 A/B/C/D 选项让用户选。用户答"你把我弄懵了"
- **根因**：选项太多，每条都说一遍假设/依据/盲区=堆信息
- **解法**：反思时**只给 2-3 个**明确差异的方案（不是一个方案 vs 另一个小差异），并**主动标"我倾向 X"**——把判断交回给用户，他只做"确认 vs 改方向"两步决策
- **正例**：5 洞见→A/B/C 三选项 + "我倾向 A"+ 一句理由 → 用户"A" 一步搞定
- **反例**：之前给 5 维变体选项 + 5 内容形式选项 + 5 元信息位置选项 = 15 个排列组合

### P0：反思粒度 = 2-3 个方案，不超过 3
- **症状**：用户问"接下来怎么走"时，我列 A/B/C/D 4 个方案 + 各自利弊——用户答"看着可以"或"你让我明确什么？"——因为我把"反思"做成了"4 选 1 选择题"
- **根因**：用户偏好"反思是看思路对不对"不是"挑选项"
- **解法**：
  - **最多 2-3 个**互相差异大的方案（不是一个方案 + 2 个变体）
  - 每个方案 = 1 段假设 + 1 段依据 + 1 段盲区（不是 5 段铺开）
  - **主动标倾向**："我倾向 A 因为 X"——把"判断"做掉，让用户做"确认 vs 反例"两步
  - **不明列选项标签**：不写 A/B/C，直接"方向 1：... / 方向 2：..."
- **正例**：方向 1（保留 v11 骨架 6 主题不变）/ 方向 2（减为 4 主题）。我倾向 1 因为……→ 用户答"1" 一句话
- **反例**：先列 5 维变体（A/B/C/D/E），再列内容格式 5 种（X/Y/Z/W/V），再列元信息 3 个位置 = 75 个组合让用户挑

---

## 验证清单

完成报告后跑这个清单，**全部 ✓ 才能交付**：

- [ ] 5 doc token 全部拉取到完整内容（`--doc-format xml --scope full`）
- [ ] 4 个视频 doc 视频清单全部解析（条数 / 播放量 / 频道 / 时长 / 上传日期）
- [ ] 1 个事件流 doc（SWLX）按日期切分解析（日期 / 编号 / 标题 / 来源媒体 / 摘要）
- [ ] 跨 doc 数据汇总（条数 / 播放量分布 / 重复检测 / 频道频次）
- [ ] 数据底座 callout 含播放量（不是只有条数）
- [ ] §1-§6 每章有"事实" H3
- [ ] §1-§6 中至少 4 章有"反方" H3
- [ ] §1-§6 中至少 4 章有"洞见" H3（§6 安全治理可无）
- [ ] 5 条固定洞见 + 1-2 条涌现洞见 = 6-7 条洞见
- [ ] 每条洞见走完整 5 要素模板（现象 / 解释 / 倾向 / 未验证 / 来源锚点）
- [ ] 3-5 条反方，跟强判断同章
- [ ] §7 调研建议 5-6 条，每条 3 核心 + 2 可选字段
- [ ] §7 调研建议不带"评估口径"段
- [ ] 附录 A 视频 ID 索引含 4 个视频 doc 全部视频（不省略）
- [ ] 章节内部 H3 是真 H3（不是粗体段落）
- [ ] 飞书 doc 写入成功（revision_id 递增）
- [ ] outline fetch 验证目录树结构（每章子节点可展开）

---

## 变更记录

- **v1.2 (本轮)**: 跑通 skill 后的 5 个 patch——新增 P0 "cron 覆盖" 陷阱、新增 P1 "ZzPa 空日期段" 陷阱、新增 P1 "SWLX `<b>` 标题" 陷阱、强化 P0 "lark-doc 路径" 陷阱（加 execute_code 反例）、Step 3 加"关键错位识别"步骤、调研建议分 3 类（A 洞见延伸 / B 纯学习 / C 错位补救）
- **v1.1 (本轮)**: 5 个 patch——升级 2 个陷阱到 P0（markdown 截断 + HERMES HOME 路径）、新增 2 个 P0（反思粒度 + 写死日期）、Step 1 加解析字段提示
- **v1 (2026-06-14)**: 从 `provenance` 字段沉淀。涵盖 5 doc（EbHD / HhyM / Virb / SWLX / ZzPa）共 200+ 条数据。
- 未来改动建议：v2 增加"非中文 cron 任务适配"（如果用户有英文 cron 任务）；v3 增加"非视频类 doc 适配"（如果用户要做会议纪要类多 doc 分析）

- **占位符说明**：
  - **静态元数据**（写具体值，不变）：`created: 2026-06-14` / `provenance: 2026-06-14 ...` —— 写在 frontmatter 里，不要占位符
  - **动态值**（runtime 填入）：`runtime_invariants.report_date: "{today}"` —— 每次运行时填入当天日期
  - **反例（不要做）**：把 `created` 写成 `{skill_first_written_date}` 是矫枉过正——它是 skill 自带元数据，写具体日期就行

## 本轮更新（v1.1）

- 强化 P0"lark-cli markdown 模式截断"陷阱，加 72 条验证标准
- 升级 HERMES HOME 路径陷阱从 P2 到 P0（错误会**直接导致 skill 失效**）
- 新增 P0"反思粒度 = 2-3 个方案"（用户"我把你弄懵了"直接反馈）
- 新增 P0"skill 不要写死日期 / 历史版本号"（用户"2026-06-14 是啥意思"直接反馈）
- Step 1 增加"解析时要看 li 后的频道 / 播放 / 时长 / 上传字段"提示（区分事件 vs 评论的关键依据）
