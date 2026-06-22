---
name: bilibili-ai-trending-pitfalls-2026-06-20
description: 2026-06-20 起多 session 实测增量。execute_code 是全新解释器（import 不持久）/ Adobe Illustrator 假阳性黑名单 / tname 字段 API 返回空 / search/all/v2 字段足够直接信任 / empty desc 视频不能用弱关键词二次过滤 / `豆包` 假阳性（字节 AI vs 食物/昵称/游戏角色）/ tier-1+tier-2 双层关键词架构。
---

# bilibili-ai-trending — 2026-06-20 实测增量

> 补充 `bilibili-ai-trending-pitfalls-2026-06-19.md`。

## 1. execute_code 是全新解释器 — import 不跨调用持久

每次 `execute_code` 都启动一个**新的 Python 解释器**。前面调用里 `import re` / `import json` / `import html` 都**不会**带到下一次。

**踩坑（2026-06-20 session）**：第一次写 `is_ai_title()` 用 `re.search()` 但只 import 了 `re`/`json`/`urllib`/`os`/`subprocess`/`time`，漏掉 `re`，29 个关键词全部报 `name 're' is not defined`，最终 0 条结果。

**正确做法 — 每个 execute_code 脚本开头一次写全所有需要的 import**：

```python
import subprocess, json, urllib.parse, time, os, re, html
from datetime import datetime, timezone, timedelta
from collections import Counter
# ... 函数定义
# ... 主逻辑
```

最少需要的 imports（绝大多数 bilibili-ai-trending 脚本）：
- `subprocess`（跑 curl）
- `json`（解析 API 响应，**用 `json.loads(s, strict=False)`**，API 返回可能含控制字符）
- `urllib.parse`（URL 编码关键词）
- `time`（rate-limit 延迟）
- `os`（文件存在检查）
- `re`（正则过滤 / HTML 标签剥离）
- `html`（`html.unescape()` 解码 HTML 实体）

**确认 2026-06-19 文档**：那次同样踩到 `json_parse is not defined` —— 那也是因为 `json_parse` 是 hermes_tools 模块函数，在 execute_code 里必须 `from hermes_tools import json_parse` 或直接用标准库 `json.loads(s, strict=False)`。

## 2. Adobe Illustrator 假阳性必须显式黑名单

`Adobe Illustrator` 简称 `AI`，标题"AI 编辑科技绘图..."会触发 `\bAI\b` 正则。**仅靠"有没有其他 AI 关键词"不够**，desc/tags 经常是空的。

**确认 2026-06-13 文档已提到**："AI" 用 word-boundary 正则避免 Illustrator 误中。但 word-boundary 单独**无法区分** "Adobe Illustrator (AI)" 和 "AI 编程"，两者 title 里 `\bAI\b` 都能命中。

**必须叠加 Illustrator 黑名单**：

```python
def is_illustrator_fake(v):
    text = f"{v['title']} {v['desc']} {v['tags']}"
    if 'Illustrator' in text or 'Adobe' in text:
        # 但允许：同时含其他 AI 关键词的真实 AI 视频
        other_ai = ['ChatGPT', 'DeepSeek', 'Claude', 'Gemini', 'Kimi', 'Qwen',
                    '人工智能', '大模型', '机器学习', '神经网络', '深度学习']
        if not any(k in text for k in other_ai):
            return True
    return False
```

**踩坑（2026-06-20）**：候选池 306 条里抓到 1 条 `Adobe Illustrator (AI) 编辑科技绘图的常见基本操作`，通过 word-boundary 误判为 AI 内容。加上 Illustrator 黑名单后正确过滤。

## 3. /view API 的 `tname` 字段现在返回空字符串（2026-06-20 实测）

调用 `https://api.bilibili.com/x/web-interface/view?bvid=xxx`，response.data 中：

| 字段 | 值 |
|------|---|
| `tname` | `""`（空字符串） |
| `tname_v2` | `""`（空字符串） |
| `tid` | `21`（分区 ID，仍可用） |
| `tid_v2` | 数字 |
| `tags` | `[]`（空数组，绝大多数视频） |
| `desc` | `""`（空字符串，绝大多数视频） |

**含义**：之前 pitfalls 文档假设的"用 tname/tags/desc 增强 AI 判定"现在基本失效 —— 这些字段对绝大多数热门视频都是空的。

**正确做法**：
- 不要花时间解析空 tname/tags
- AI 判定**只能依赖 title**，desc 仅作为加分证据（不为空时提升可信度）
- 对"title 看起来像 AI 但 desc 是空"的视频，要列入"接受"集合（不能因为 desc 空就 reject）

## 4. search/all/v2 返回的 view/like/duration 已经准确，**不需要再调 /view**

之前文档假设 search/all/v2 的 `play` 是估算值，需要 /view 补全。**2026-06-20 实测**：search/all/v2 返回的 `play`/`like`/`duration`/`author` 与 /view API 几乎完全一致（diff 通常为 0，仅偶有 +1~2 增量）。

**正确做法**：
- search/all/v2 给出的数据**直接信任**，不需要批量 /view 补全
- 仅在以下情况才调 /view：
  - `owner.name` / `author` 字段为空（兜底 UP 主名）
  - 需要 `pubdate` / `desc` 等 search/all/v2 不返回的字段
- **306 条视频全量调 /view 耗时 ~97s**，如果跳过可省 ~80% 时间

**实施注意**：批量 /view 之间仍需 `time.sleep(0.08)` 避免速率限制（实测 0.05s 触发 412，0.08s 全绿）。

## 5. "AI 弱关键词 + desc 二次过滤"反模式（2026-06-20 误踩）

之前思路：title 命中弱关键词（`\bAI\b` / `AI视频`）后，要求 desc/tags 也命中强关键词才接受。

**问题**：306 条里约 60 条 desc 是空字符串（包括很多百万播放的真实 AI 视频），这条规则会**误杀**大量真实 AI 内容：

| 被误杀的标题（desc 为空） | 真实身份 |
|--------------------------|---------|
| `杀疯了，GPT-image-2太变态了，附赠使用平台和实测报告` | OpenAI GPT-image 模型测评 |
| `让visual studio 2022用上copilot ai编程` | GitHub Copilot 教程 |
| `强推！目前最强无审查开源模型Qwen3.6！支持本地Agent` | Qwen 开源模型介绍 |
| `【2026最新Cursor使用教程】史上最强 AI 编程工具Cursor` | Cursor 编程教程 |
| `Trae 保姆级教程｜AI 编程工具完整入门` | Trae AI IDE 教程 |

**正确做法 — 把"明显 AI 产品名"升格为强关键词**：

```python
strong_patterns = [
    # ... 原有 strong
    r'GPT-image', r'GPT Image', r'GPT-Image',  # OpenAI image models
    r'\bSeedance\b', r'\bTrae\b', r'\bDoubao\b', r'\bHailuo\b',
    'AI视频', 'AI编程', 'AI画图', 'AI绘画', 'AI工具', 'AI助手', 'AI早报', 'AI写真',
]
```

只要 title 命中强关键词即视为 AI 内容，**不再要求 desc/tags 二次确认**。

**配套的 weak-title 二次过滤**应该改为"title 命中弱关键词 + (非空 desc 命中强 OR title 长度 > 15 字符且包含学习/教程/测评等教学语境词)"。

## 6. 中文标题"远嫁/受虐/非洲"假阳性

2026-06-20 抓到 1 条 `ai视频女生远嫁非洲受虐不可能存在！`，title 含 `\bai\b` 但 desc 空，**实质是评论 AI 生成内容失真**，不是 AI 教程/工具/技术。

**特征模式**（黑名单）：
- `远嫁` / `受虐` / `非洲` 等社会/剧情关键词
- 标题以"ai..." 开头但没有教学语境（教程、Prompt、提示词、怎么用、测评）

**正确做法**：在 is_blacklisted() 中加：
```python
if '远嫁' in title or '受虐' in title:
    return True
if title.lower().startswith('ai ') or 'ai女生' in title.lower() or 'ai男友' in title.lower():
    tech_words = ['AI', 'GPT', 'LLM', '模型', '智能', '学习', '训练', '生成', '推理', '工具', '画图', '绘画', '编程', '视频']
    if not any(tw in title for tw in tech_words):
        return True
```

## 7. DocxXML `<docx><body>` 包装 + BilibiliAITrending 根节点冲突

2026-06-20 cron prompt 模板要求 `<BilibiliAITrending>` 根节点 + `<title>Bilibili AI热门视频</title>`，但 lark-cli `--doc-format xml` 期望 DocxXML 包装 `<docx><title><body>`。

**实测结果（2026-06-20）**：用纯 DocxXML `<docx><title>...</title><body>...</body></docx>` 包装，lark-cli 返回：
- `ok: true`
- `result: "success"`
- `revision_id: 49`
- 2 个 `degrade_code=4007` warnings：`Unsupported tag <docx> was escaped` + `Unsupported tag <body> was escaped`

**结论**：warning 是非致命的，**目录正常生成**，内部 h1/h2/ol/li/a 全部正常渲染。优先用 DocxXML 包装（warning 更少），如果 cron prompt 强制要求自定义根节点也可以接受（仅多 2 个 warning）。

## 8. `豆包` 假阳性：字节豆包 vs 食物/人名/游戏角色（2026-06-22 实测）

字节跳动的 AI 助手叫 `豆包`（Doubao），与日常用语"豆包"（食物/小孩昵称/游戏角色）**完全同名**。单纯正则匹配 `豆包` 会引入大量非 AI 内容。

**踩坑（2026-06-22 session）**：候选池 1043 条里抓到 4 条假阳性 TOP-榜内容：

| 被误抓的标题 | 真实身份 |
|--------------|---------|
| `当豆包进入到了MC当中，并且还可以指挥豆包！如何生存呢？` | Minecraft 游戏实况，豆包是小孩昵称 |
| `【人森】傲娇粪跟豆包有机会？` | 生活模拟游戏 `人森` 的角色对话 |
| `小豆包` / `继续欺负小豆包` / `反骨小豆包` | 萌娃日常（生活记录/亲子分类） |
| `豆包决定随机金额吃一天！豆包是会配餐的` | 美食测评，外卖挑战 |

**确认这是 search/all/v2 系统性污染**：`豆包` 在 B 站搜索结果里高频出现为食物/人名；直接当 tier-1 强关键词会污染前 10 榜单。

**正确做法 — 三层防御**：

1. **弱化 `豆包` 为 tier-2**（需要 desc/tags 或其他 tier-1 关键词同时命中才接受）：
   ```python
   TIER2_PATTERNS = [
       r'豆包',  # 字节豆包 / 食物 / 昵称 / 游戏角色 — 必须有其他 AI 证据
       # ...
   ]
   ```

2. **显式黑名单"非 AI 豆包"语境词**：
   ```python
   BLACKLIST = [
       r'小豆包',           # 萌娃昵称
       r'豆包姐姐',         # 益智动画
       r'进入MC', r'进入我的世界', r'进入《我的世界',  # Minecraft
       r'傲娇粪', r'人森',  # 豆包 in 模拟游戏 `人森`
       # ...Adobe Illustrator, 远嫁, 受虐, 非洲, ai女生 等保留
   ]
   ```

3. **黑名单 + tier-1 共现检验**：如果 title 含 `豆包` 但同时含 `ChatGPT` / `AI编程` / `AI视频制作` 等 tier-1，仍接受。

**结论**：把 `豆包` 当强关键词会污染 TOP 榜；弱化为 tier-2 + 显式黑名单 + 共现检验才能稳定。同类风险适用于 `Kimi`（少见歧义，但韩国姓氏/动漫角色）、`Claude`（罕见歧义，人名），主要踩坑点在 `豆包`。

## 9. tier-1 / tier-2 双层关键词架构（2026-06-22 沉淀）

基于 2026-06-22 实测收敛的过滤模型，**比单层 strong/weak 更稳定**：

**Tier 1（title 单独命中即 AI）**：
- 品牌/产品：`ChatGPT` / `DeepSeek` / `Claude` / `Gemini` / `Grok` / `OpenAI` / `Cursor` / `Copilot` / `Trae` / `Dify` / `Coze` / `扣子` / `Manus` / `Midjourney` / `Stable Diffusion` / `ComfyUI` / `Sora` / `Vidu` / `Pika` / `Runway` / `Suno` / `可灵` / `即梦` / `Hailuo` / `Seedance` / `Seedream` / `LoRA`
- 中文 AI 概念：`人工智能` / `大模型` / `大语言模型` / `机器学习` / `深度学习` / `神经网络` / `LLM` / `RAG` / `智能体` / `AIGC` / `AGI` / `提示词` / `Embedding` / `Transformer` / `文生视频` / `图生视频` / `具身智能` / `强化学习`
- AI 复合词：`AI编程` / `AI画图` / `AI绘画` / `AI工具` / `AI视频` / `AI生成` / `AI教程` / `AI Agent` / `AI数字人`

**Tier 2（需二次证据）**：
- 高歧义单 token：`\bAI\b` / `GPT` / `豆包` / `Prompt` / `Agent` / `数字人` / `LoRA` / `Diffusion` / `大模型` / `智能`
- 二次证据条件（任一）：
  1. desc/tags 命中任意 Tier-1 关键词
  2. title 同时命中 ≥ 1 个 Tier-1 关键词
  3. title 长度 > 15 且含 ≥ 2 个 tech 上下文词（GPT/LLM/模型/智能/学习/训练/生成/推理/工具/画图/绘画/编程/视频/教程/测评/实测/开源/Agent/智能体/代码/提示词/Prompt/机器人/Sora/DeepSeek/Claude/Gemini/Copilot/Cursor/Trae/Kimi/Qwen/豆包/Dify/Manus/ComfyUI）

**效果（2026-06-22）**：候选 1043 → 过滤后 729 真正 AI 视频，TOP 榜肉眼检查无假阳性。

**重要**：黑名单必须**先于**关键词检查：
```python
def is_ai_title(title, desc, tags):
    text = f"{title} {desc} {tags}"
    # 1) blacklist 先
    for p in blacklist_compiled:
        if p.search(text): return False
    # 2) tier-1
    for p in tier1_compiled:
        if p.search(title): return True
    # 3) tier-2 + secondary
    for p in tier2_compiled:
        if p.search(title):
            if tier1_evidence_in_desc_or_tags(desc, tags): return True
            if tier1_in_title(title): return True
            if len(title) > 15 and tech_ctx_count(title) >= 2: return True
            break
    return False
```