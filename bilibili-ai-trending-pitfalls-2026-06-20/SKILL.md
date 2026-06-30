---
name: bilibili-ai-trending-pitfalls-2026-06-20
description: 2026-06-20 起多 session 实测增量。execute_code 是全新解释器（import 不持久）/ Adobe Illustrator 假阳性黑名单 / tname 字段 API 返回空 / search/all/v2 字段足够直接信任 / empty desc 视频不能用弱关键词二次过滤 / `豆包` 假阳性（字节 AI vs 食物/昵称/游戏角色）/ tier-1+tier-2 双层关键词架构 / 2026-06-29 search/all/v2 改成 search/type 端点 / 标题 `|tag|tag` 后缀主标题提取 / lark-cli 必须相对路径。
---

# bilibili-ai-trending — 2026-06-20 实测增量

> 补充 `bilibili-ai-trending-pitfalls-2026-06-19.md`。

**已知好用的完整脚本**（2026-06-29 cron 实测通过）见 `references/2026-06-29-working-script.py` — 直接复制修改即可使用。

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

## 4. search/all/v2 返回的 view/like/duration 已经准确，**但跨 API 字段类型不一致**（2026-06-24 实测）

之前文档（2026-06-20）说 search/all/v2 数据足够准，无需 /view 补全。但**必须区分两种场景**：

**场景 A：仅用 popular 全榜（top 50 × N 页）作为候选源** —— search/all/v2 的 play/duration 字段足够，无需 /view。popular 本身就是高播放池，play 不会为 0。

**场景 B：用 popular + search/all/v2 关键词扫荡（常见做法）** —— 必须做 `/view` 二次补全：
- 大量 search/all/v2 返回的视频 **play=0 或缺失**（候选池 200 条里 26 条 play=0，占 13%）
- 这些往往是低质量 spam（AI 生成的几秒钟短视频），如果不补全会污染排序
- 补全后才能正确按播放量过滤（如 `play >= 5000`）和排序

**正确做法**：
- 如果用了 search/all/v2 关键词扫荡，**必须 /view 补全**
- 实施注意：批量 /view 之间需 `time.sleep(0.08)` 避免 412（0.05s 触发限速，0.08s 全绿）
- 200 条全量 /view 约 ~64s（每次响应快，瓶颈在 sleep）

### 4.1 `duration` 字段类型不一致 — 必须显式归一化（2026-06-24 实测踩坑）

| API | duration 字段类型 | 示例 |
|-----|------------------|------|
| `search/all/v2` | **mm:ss 字符串** | `"46:54"` |
| `/view` | **整数秒** | `168862` |

**踩坑**：本次脚本直接 `print(v['duration'])` 用了 search 抓的 `"46:54"`，但 /view 补全后字段被覆盖为整数 168862，紧接着的 `fmt_dur` 函数按 mm:ss 解析整数秒 → 输出 `"46:54:22"`（46 小时 54 分钟 22 秒！）。

**正确做法 — 归一化 helper**：
```python
def fmt_dur(sec_or_str):
    """统一处理 mm:ss 字符串 OR 整数秒，输出 mm:ss 或 h:mm:ss"""
    if isinstance(sec_or_str, str):
        # search/all/v2 格式 "mm:ss"
        return sec_or_str
    if isinstance(sec_or_str, (int, float)):
        s = int(sec_or_str)
        if s >= 3600:
            h, rem = divmod(s, 3600)
            m, sec = divmod(rem, 60)
            return f"{h}:{m:02d}:{sec:02d}"
        return f"{s//60}:{s%60:02d}"
    return "?"
```

**关键规则**：**搜索结果只用于发现，不用于排序字段**。所有排序字段（play/like/duration）都要走 /view 二次归一化。

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

## 10. 2026-06-24 验证的工作候选池配方

经过 2026-06-24 session 实测，**以下配方产出的 TOP 15/TOP 7 榜无需人工干预、零肉眼假阳性**：

```python
candidates = []

# 1) popular 全榜（top 50 × 2 页 = 100 条，高播放池）
for pn in [1, 2]:
    url = f"https://api.bilibili.com/x/web-interface/popular?ps=50&pn={pn}"
    # ... 解析到 candidates

# 2) search/all/v2 关键词扫荡（× 多关键词 × 双排序）
keywords = ['AI', 'ChatGPT', 'DeepSeek', 'Claude', '大模型', '人工智能',
            '机器学习', '深度学习', '神经网络', 'AIGC', 'AI编程', 'AI绘画', 'AI视频']
for kw in keywords:
    for order in ['click', 'pubdate']:  # 双排序，召回更多
        url = f"https://api.bilibili.com/x/web-interface/search/all/v2?keyword={urllib.parse.quote(kw)}&order={order}&page=1&pagesize=50"
        # ... 解析
        time.sleep(0.15)  # search API 比 /view 慢一点，0.15 安全

# 3) 去重 (按 bvid)
# 4) tier-1/tier-2 + blacklist 过滤
# 5) /view 批量补全 play/like/duration（必须，见 §4）
# 6) 过滤 play < 5000（剔除 spam）
# 7) 按 duration 拆分：>180s 长视频，<=180s 短视频
# 8) 各按 play 排序，取 TOP 15 / TOP 7
```

**实测数据流（2026-06-24）**：
- popular pn=1+2：100 条
- search × 13 关键词 × 2 排序：520 条
- 合并去重：328 条 unique
- tier 过滤后：200 条 AI 视频
- play >= 5000 过滤：124 条
- 长视频 (>180s)：109 条 → 取 TOP 15
- 短视频 (<=180s)：15 条 → 取 TOP 7

**关键参数**：
- `ps=50`（popular 每页上限）
- `pagesize=50`（search 单页上限）
- `play >= 5000`（剔除低质 spam 的阈值，实测 124/200 留存）
- 长短视频切分点 = **180 秒（3 分钟）**

### 10.1 ⚠️ 2026-06-29 重大变更：`search/all/v2` 返回结构变了 — 必须改用 `search/type`

**踩坑（2026-06-29 cron）**：原 §10 配方直接用 `search/all/v2?pagesize=50`，但 2026-06-29 实测 `result[]` 已经变成**混合 feed**（`tips` / `brand_ad` / `esports` / `activity` / `web_game` / `card` / `media_bangumi` / `media_ft` / `bili_user` / `user` / `star` / `video` 等 12 种 type 混排），`pagesize=50` 实际只返回 ~12 条混合项，**其中 video 类型只占 1 条**。每页召回从 20+ 视频暴降到 1 视频，候选池从 328 unique 直接降到 100（只剩 popular），AI 过滤后仅 1 条 — 整张榜废了。

**正确做法 — 改用 `x/web-interface/search/type?search_type=video`**：

```python
for kw in keywords:
    for order in ['click', 'pubdate']:
        for page in [1, 2]:  # 多翻几页召回更多
            url = (
                f"https://api.bilibili.com/x/web-interface/search/type"
                f"?search_type=video"
                f"&keyword={urllib.parse.quote(kw)}"
                f"&order={order}"
                f"&page={page}"
                f"&pagesize=20"
            )
            data = curl_json(url)
            if not data or data.get('code') != 0: continue
            results = data.get('data', {}).get('result', []) or []
            for item in results:
                # search/type 端点的 video 项直接是 video 字典
                if item.get('type') != 'video': continue
                bvid = item.get('bvid')
                if not bvid or bvid in candidates: continue
                candidates[bvid] = {
                    'bvid': bvid,
                    'title': item.get('title', ''),       # 仍带 <em> 标签
                    'desc': item.get('description', ''),
                    'author': item.get('author', ''),
                    'play': item.get('play', 0) or 0,
                    'like': item.get('like', 0) or 0,
                    'duration': item.get('duration', '0:00') or '0:00',
                    'source': 'search',
                }
            time.sleep(0.2)
```

**关键差异（search/all/v2 vs search/type）**：

| 字段 | `search/all/v2` (旧) | `search/type?search_type=video` (新) |
|------|---------------------|--------------------------------------|
| 端点 | `x/web-interface/search/all/v2` | `x/web-interface/search/type` |
| result[] 内容 | 混合 feed（视频+用户+广告+...） | 纯 video 列表 |
| pagesize=50 实际返回 | ~12 条混合项（视频 1 条） | 20 条 video |
| video 项 type 字段 | `result_type == 'video'`, 数据在 `data[]` 数组 | `type == 'video'`, 数据就是 item 本身 |
| video 项 bvid 位置 | `data[0].bvid`（嵌套） | `item.bvid`（直接） |
| video 项 play 字段 | `data[0].play` | `item.play` |
| video 项 duration 字段 | `data[0].duration` (mm:ss 字符串) | `item.duration` (mm:ss 字符串) |
| video 项 desc 字段 | `data[0].description` | `item.description` |
| pageinfo | 每个分类单独 numResults | 仅顶层 numResults / numPages |

**回归测试**：用 search/type 改写后，2026-06-29 session 数据流恢复正常：
- popular pn=1+2：100 条
- search/type × 13 关键词 × 2 排序 × 2 页 = 520 → 去重 617 unique
- tier 过滤 + play>=5000：90 条
- 长视频 73 / 短视频 17

**重要：旧的 `search/all/v2` 不能再用**。本 skill 之前所有提到 `all/v2` 的代码（§4、§10、§11）都需要替换为 `search/type?search_type=video`。

## 10.2 B站中文标题 `|tag|tag|tag` 后缀污染 — 主标题提取（2026-06-29 实测）

**新踩坑**：B站创作者在标题末尾用 `|` 拼接一堆关键词做 SEO，例如：

```
Python入门零基础必看教程，这绝对是今年最全最细的教程，全程干货无废话！python|程序员|python入门||人工智能|python零基础
```

主标题显然是「Python入门零基础必看教程…」，但 `人工智能` 出现在 `|` 后缀里，**会被 `人工智能` tier-1 关键词误判为 AI 内容**。结果：21M 播放的 Python 入门教程被错误地推上 AI 榜 #1。

**正确做法 — 提取 main title（主标题在第一个 `|` 之前）**：

```python
def get_main_title(t):
    if not t: return t
    if '|' not in t: return t.strip()
    return t.split('|', 1)[0].strip()
```

**配套的 tier-1 检查要改用 main title**：

```python
def is_ai_title_strict(title_raw, desc, tags):
    main = get_main_title(title_raw)  # ← 关键：用 main 而非完整 title
    if is_blacklisted(main, desc, tags): return False
    return any(p.search(main) for p in tier1_compiled)
```

**配套的过滤参数也要更新**（§10 配方步骤 4 替换为）：
```python
# 用 main title 而非 title_clean 做 AI 判定
ai_videos = [v for v in candidates if is_ai_title_strict(
    v.get('title_real') or v['title_clean'],
    v.get('desc', ''),
    v.get('tags_real', '')
)]
```

**回归**：2026-06-29 改用 main title 提取后，21M 播放 Python 教程正确从 #1 降至 #4（被 PyTorch 教程等真正 AI 视频顶替）。TOP 榜肉眼检查无 Python/Matlab 等非 AI 教程污染。

**注意**：search/type 端点返回的 title 也带 `<em class="keyword">` 标签（高亮命中关键词），需 `re.sub(r'<[^>]+>', '', t)` 先剥 HTML。`/view` 返回的 title 是干净的实际标题。**强烈建议先 /view 补全再用 main title 提取**（见 §4）。

## 13. lark-cli `--content @file` 必须用**相对路径**（2026-06-29 实测踩坑）

**踩坑（2026-06-29）**：第一版命令用 `/tmp/merged_bilibili-ai.xml` 绝对路径：

```bash
lark-cli docs +update --api-version v2 --doc "Virbd3YyBoYK9XxqaZOccEGRnio" \
  --command overwrite --content @/tmp/merged_bilibili-ai.xml --doc-format xml
```

返回错误（exit_code=2, ok=false）：
```json
{
  "ok": false,
  "identity": "bot",
  "error": {
    "type": "validation",
    "message": "--content: invalid file path \"/tmp/merged_bilibili-ai.xml\": --file must be a relative path within the current directory, got \"/tmp/merged_bilibili-ai.xml\" (hint: cd to the target directory first, or use a relative path like ./filename)"
  }
}
```

**根因**：lark-cli 在某个时间点升级后对 `--content @<path>` 参数新增了**相对路径校验**（防止任意文件读取），绝对路径会被拒绝。

**正确做法 — 三选一**：

1. **方案 A（推荐）**：cd 到目标目录再传相对路径
   ```bash
   cd /Users/xiesg
   lark-cli docs +update --api-version v2 --doc "Virbd3YyBoYK9XxqaZOccEGRnio" \
     --command overwrite --content @merged_bilibili-ai.xml --doc-format xml
   ```

2. **方案 B**：复制 XML 到当前目录后再调用
   ```bash
   cp /tmp/merged_bilibili-ai.xml ./merged_bilibili-ai.xml
   lark-cli docs +update --api-version v2 --doc "Virbd3YyBoYK9XxqaZOccEGRnio" \
     --command overwrite --content @merged_bilibili-ai.xml --doc-format xml
   ```

3. **方案 C**：用 Python `subprocess.run(..., workdir='/Users/xiesg')` 指定工作目录
   ```python
   subprocess.run(
       ['lark-cli', 'docs', '+update', '--api-version', 'v2',
        '--doc', 'Virbd3YyBoYK9XxqaZOccEGRnio',
        '--command', 'overwrite',
        '--content', '@/tmp/merged_bilibili-ai.xml',  # 或 @merged_bilibili-ai.xml
        '--doc-format', 'xml'],
       workdir='/Users/xiesg',
       capture_output=True, text=True)
   ```

**历史对比**：
- 2026-06-20、2026-06-24 的 cron 命令也用了 `@/tmp/merged_bilibili-ai.xml` 绝对路径，但当时 lark-cli 旧版本接受该路径未报错。
- 2026-06-29 触发新错误（exit_code=2），是 lark-cli 新增的相对路径校验。

**经验**：**任何 lark-cli `--content @<path>` 调用都要用相对路径**（cd 到目标目录，或先 `cp` 到 cwd），即便早期版本允许绝对路径。cron 任务执行时必须先把 XML 放到 `cwd` 或显式 `cd`。

## 15. execute_code 5 分钟硬超时 — 顺序脚本会被杀（2026-06-30 实测踩坑）

**坑**：cron 调用走 `execute_code` 跑端到端脚本，**单次硬超时 300 秒**。2026-06-29 那版"工作脚本"在 `execute_code` 里跑会**直接 timeout**：

| 阶段 | 顺序耗时（2026-06-30 实测） | 占比 |
|------|---------------------------|------|
| popular pn=1+2 | ~2s | 0.7% |
| search/type × 13 关键词 × 2 排序 × 2 页（52 calls × 0.2s sleep） | ~14s | 5% |
| **/view 顺序补全（116 条 × 0.08s sleep + 每次响应）** | **~80s** | 27% |
| search/type × 25 关键词 × 2 × 2（追加 100 calls × 0.1s） | ~20s | 7% |
| **/view 顺序补全（509 条 × 0.08s sleep + 每次响应）** | **~200s** | 67% |
| 累计 | **~316s** | 超时 ✗ |

第一次跑端到端 300s 整卡死、0 输出。

**根因**：原工作脚本（§14）`for v in need: ... time.sleep(0.08)` 是单进程串行。/view API 响应快（~50-100ms）但 sleep 0.08s × 600+ 条累积起来就 ~50-100s 纯等待。配合网络抖动和 search 阶段，300s 必爆。

**正确做法 — `xargs -P 20` 并发 /view（实测 509 条 11.9s 完成）**：

```python
import subprocess, json, time, os

# 把所有要 /view 的 bvid 写入文件
bvids = [b for b, v in candidates.items() if v['source'] == 'search' and 'title_real' not in v]
with open('/tmp/bvids.txt', 'w') as f:
    f.write('\n'.join(bvids))

# 20 并发 curl，每个响应写自己的文件（避免 stdout 拼接乱）
subprocess.run(
    ['xargs', '-P', '20', '-I', '{}', 'curl', '-sS', '--max-time', '10',
     '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 13_7_8) AppleWebKit/537.36',
     'https://api.bilibili.com/x/web-interface/view?bvid={}',
     '-o', '/tmp/v_{}.json'],
    input=open('/tmp/bvids.txt').read(),
    capture_output=True, text=True, timeout=600
)

# 逐文件读回、enrich candidate、删除临时文件
for bvid, v in need:
    fp = f'/tmp/v_{bvid}.json'
    if not os.path.exists(fp): continue
    try:
        with open(fp) as f:
            data = json.load(f, strict=False)
    except: continue
    if not data or data.get('code') != 0: continue
    d = data['data']
    stat = d.get('stat', {})
    v['play'] = stat.get('view', 0) or v['play']
    v['like'] = stat.get('like', 0) or 0
    v['duration'] = d.get('duration', v['duration'])
    v['author'] = d.get('owner', {}).get('name', v['author'])
    v['title_real'] = d.get('title', v['title'])
    v['desc'] = d.get('desc', '') or v['desc']
    os.remove(fp)
```

**实测数据**（2026-06-30）：
- 116 条 /view 并发：4.6s
- 509 条 /view 并发：11.9s
- 完全不触发 412 限速（20 并发下 B 站 /view 不限流；popular/search 用 0.1-0.2s 串行 sleep 仍稳定）

**配套约束**：
- `xargs -P` 上限设 20 即可；再大本地 fd 可能不够，且 B 站 /view 返回快，并发收益边际递减
- 必须 `-o /tmp/v_{bvid}.json` 每个响应一个文件，**不能** stdout 拼接（并发会乱序/截断）
- 超时设 600s，xargs 自身会等所有进程退出

**2026-06-30 实测**（用 20 并发 /view + 增量 search）：popular 100 → search 116 → /view 4.6s → 再 search 509 → /view 11.9s → 全流程 ~50s 完成，**300s 余量充足**。

**重要**：`execute_code` 工具是 **5 分钟** 硬上限，**不是** 之前假设的"可以慢慢跑"。任何把"全量 popular + 全量 search + 全量 /view"塞进单个 `execute_code` 的脚本都得用并发 /view，否则必超时。

## 16. 视频 duration 超过 24h — 多为合法课程合集（2026-06-30 实测）

**现象**：AI 过滤后出现多 `duration > 24h` 的视频：

| bvid | duration | title 摘要 | 是否合法 |
|------|----------|-----------|----------|
| `BV1Wv411h7kN` | 87h | 李宏毅 2021/2022 机器学习课程 | ✓ 跨 2 学期合集 |
| `BV1JE411g7XF` | 67h | 李宏毅 2020 机器学习深度学习(完整版) | ✓ 完整版合集 |
| `BV1j6qzYzE4h` | 47h | 上海交大+腾讯 Python+ML+DL 系列 | ✓ 系列合集 |
| `BV16F411G7iz` | 39h | 2024 总复习系统课（大合集） | ✗ 与 AI 无关（是物理合集） |
| `BV168Kf6EEkg` | 44h | MIT 6.034 人工智能 (Patrick Winston) | ✓ |
| `BV1LBjV6kE9f` | 25h | IBM 安全情报 | ✗ 与 AI 无关 |

**含义**：
- 长 duration 不一定是脏数据 — 教学/课程合集 24-100h 是正常现象
- 但**脏数据也混在里面**（物理合集、安全合集命中 tier-1 弱关键词如"学习""智能"），所以 main_title + tier-1 过滤**不能完全剔除非 AI 合集**
- 当前 cron 用 tier-1 strict（必须含具体 AI 产品/技术词），配合 main_title（剔除 `|` 后缀）已经是合理折中

**实践**：
- 不要因为 duration > 24h 就过滤掉 — 会误杀合法课程合集
- TOP 15 长视频里出现 1-2 条 30h+ 的课程**是正常的**，不视为脏数据
- 但 168862 秒（46h）这种"差 1-2 小时到整"的数字看起来很怪 — 那是因为 `168862 / 60 / 60 = 46.906`，不是真"46:54:22"。display 用 `fmt_dur` 仍按整数除法渲染，会显示 `46:54:22`，**视觉上不美观但数值正确**

**不需要额外修复** — top 榜里放 1-2 条"几十小时 AI 课程合集"是 AI 教程生态的真实形态，不是 bug。

## 14. 2026-06-29 完整工作流 checklist

cron 任务从 0 到完成的标准流程：

```python
# Step 1: 拉取 popular
for pn in [1, 2]:
    url = f"https://api.bilibili.com/x/web-interface/popular?ps=50&pn={pn}"
    # ... 解析，bvid 去重

# Step 2: search/type 关键词扫荡（注意：不是 search/all/v2！见 §10.1）
for kw in keywords:
    for order in ['click', 'pubdate']:
        for page in [1, 2]:
            url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={urllib.parse.quote(kw)}&order={order}&page={page}&pagesize=20"
            # ... 解析
            time.sleep(0.2)

# Step 3: /view 补全 play/like/duration/title/desc（必做，见 §4）
for v in candidates.values():
    if v['source'] == 'search' or v['play'] == 0:
        # /view call
        time.sleep(0.08)

# Step 4: 用 main title 提取做 AI 判定（见 §10.2）
def get_main_title(t):
    if not t: return t
    if '|' not in t: return t.strip()
    return t.split('|', 1)[0].strip()
ai_videos = [v for v in candidates.values()
             if is_ai_title_strict(get_main_title(v.get('title_real', v['title'])),
                                   v.get('desc', ''), '')]

# Step 5: play >= 5000 过滤
filtered = [v for v in ai_videos if v['play'] >= 5000]

# Step 6: 按 duration 分长短视频（>180s vs <=180s），各取 TOP
long_v  = sorted([v for v in filtered if dur_secs(v) > 180],  key=lambda x: x['play'], reverse=True)[:15]
short_v = sorted([v for v in filtered if dur_secs(v) <= 180], key=lambda x: x['play'], reverse=True)[:7]

# Step 7: 生成 XML（DocxXML 包装 + title tag，见 §11.2 warning 1017 可接受）
# 含 <?xml?> 头 + <docx><title>...<body>...</body></docx>
# 写本地时戳文件名 + canonical merged_bilibili-ai.xml

# Step 8: 复制到 cwd，再用 lark-cli --content @相对路径 上传（见 §13）
import shutil
shutil.copy('/tmp/merged_bilibili-ai.xml', './merged_bilibili-ai.xml')
subprocess.run(['lark-cli', 'docs', '+update', '--api-version', 'v2',
                '--doc', 'Virbd3YyBoYK9XxqaZOccEGRnio',
                '--command', 'overwrite',
                '--content', '@./merged_bilibili-ai.xml',
                '--doc-format', 'xml'],
               cwd='/Users/xiesg', check=True)
```

**2026-06-29 数据流实测**：
- popular pn=1+2: 100 条
- search/type × 13 关键词 × 2 排序 × 2 页: 617 unique 候选
- tier + main-title 严格过滤: 82 条
- play >= 5000: 82 条
- 长视频 65 / 短视频 17
- TOP 15 长 / TOP 7 短 零肉眼假阳性
- lark-cli upload: revision_id 61, result: success, 4 warnings (3 个 degrade_code=4007, 1 个 degrade_code=1017)

## 11. lark-cli v2 实测：warnings 演进

### 11.1 2026-06-24 — 3 个 warning

本次 cron 调用：
```bash
lark-cli docs +update --api-version v2 --doc "Virbd3YyBoYK9XxqaZOccEGRnio" \
  --command overwrite --content @merged_bilibili-ai.xml --doc-format xml
```

返回 `revision_id: 53`、`result: "success"`，warnings：
- `Unsupported tag <?xml> was escaped`
- `Unsupported tag <docx> was escaped`
- `Unsupported tag <body> was escaped`

**比 2026-06-20 多一个** `<?xml>` warning（之前 2 个）。原因：本次脚本输出包含 `<?xml version="1.0" encoding="UTF-8"?>` 声明行。建议：未来模板去掉 `<?xml ?>` 声明行，仅输出 `<docx>...</docx>` 主体，可能少 1 个 warning。

### 11.2 2026-06-29 — 4 个 warning（新出现 `degrade_code=1017` Duplicate title）

2026-06-29 cron 调用同样使用 §11.1 命令（无变化），返回 `revision_id: 61`、`result: "success"`，warnings：
- `degrade_code=4007,msg=Unsupported tag <?xml> was escaped`
- `degrade_code=4007,msg=Unsupported tag <docx> was escaped`
- `degrade_code=4007,msg=Unsupported tag <body> was escaped`
- `degrade_code=1017,msg=Duplicate document title was filtered: 1 duplicate <title> tag was filtered; the first <title> was kept. Keep only one document title; when using --title, do not also generate another <title> in content`

**新坑**：第 4 个 warning 出现。原因是文档 body 内含 `<title>Bilibili AI热门视频</title>` 标签，而 lark-cli 自身也会生成一个 `<title>` 标签（来自 doc 自身的标题），两者重复。

**注意**：本次 2026-06-29 命令**没有**用 `--title` 参数，只传 `--content @file.xml`，但 lark-cli 仍然自动检测到文件内的 `<title>` 与文档自身标题重复。看起来 lark-cli 2026-06-29 新增了对 body 内 `<title>` 标签的检测（之前不报）。

**结论**：warning 仍是 4 个、非致命，目录正常生成。但 1017 提示可以优化：
- **方案 A**：body 内不放 `<title>`，只靠 lark-cli 自动继承 doc 标题
- **方案 B**：body 内保留 `<title>` 标签（便于 XML 自包含），接受 1017 warning
- 当前 cron 任务使用方案 B（XML 模板要求 `<title>` 固定不变），可继续接受 warning

## 12. DocxXML `<docx><body>` 包装 + BilibiliAITrending 根节点冲突（原 §7，2026-06-20 实测）

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