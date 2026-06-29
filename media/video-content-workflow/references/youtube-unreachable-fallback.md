# YouTube 不可达时的替代数据源（2026-05-31 实测，2026-06-09 修正，2026-06-10 更新，2026-06-11 晚间档修正关键词与展开按钮，2026-06-12 早间档修正 Bing 关键词实际差异，2026-06-13 早间档修正 06:00 CST 早报空窗，2026-06-14 早间档新增 curl-first 提取方案，2026-06-16 晚间档修正 aria-label 语言依赖 → BVID 直取首选，2026-06-20 晚间档新增 4 维质量过滤 + B站 search API 412 节流模式，**2026-06-22 早间档实测新增单字 query 假阳性雷区**，**2026-06-22 晚间档实测新增重试节流 query + 晚间档专属黑名单**，**2026-06-24 晚间档实测新增 KPL/电竞赛假阳性 + 硬件评测 + 不翻墙广告升级**，**2026-06-29 晚间档实测新增 `--today-only` 过窄修复 + 扩展池定型（today+yesterday, view≥50）**）

## ⚠️ Cron job prompt 中的"格式规范"是错误的（2026-06-14 早间档再次确认）

每个 YouTube-AI 早间档 cron 任务的 prompt 都会包含这样的"格式规范"：

```
- 文档标题：`<title>YouTube AI热门视频 · 早间档</title>`
- 完整根节点 `<YouTubeTrending>` 和各分类节点
- XML 文件需包含完整根节点 `<YouTubeTrending>`
```

**这段 prompt 是错的，照做会让 lark-cli 把整个 XML 当成纯文本写入，目录、链接、所有标签全部失效。** 正确做法是遵循本 skill 的 DocxXML 模板（`<docx><title>...</title><body>...</body></docx>`），`<docx>` 和 `<body>` 包装标签会被 escape（`degrade_code=4007` warning），但里面的 `<h1>/<h2>/<ol>/<li>/<a>` 等会正常解析。`ok: true` 即代表成功。详细原因和模板见 SKILL.md 顶层"飞书文档写入"一节。

**结论**：**忽略 prompt 里的"完整根节点 `<YouTubeTrending>`"** 这个误导指令，永远用 `<docx><title>...</title><body>...</body></docx>`。这是第二次在 06:00 CST cron 上确认（2026-06-13 / 2026-06-14），按主 SKILL.md 的规范走就行，不要为了满足 prompt 而改用裸 XML。

---

## ⚠️ Bing 在 headless 浏览器下渲染不完整（2026-06-14 早间档实测）

**反例**：2026-06-14 06:01 CST，`browser_navigate` 打开 Bing 视频搜索页后：

- `browser_console` 抓 `a[aria-label*="来源"]` → **只返回 1 条**（页面 531px 高，DOM 几乎是导航）
- `browser_scroll` + 反复 `browser_console` 多次 → 仍然 1 条
- 切换不同 query（`AI+LLM+GPT+Claude+trending+2026`、`AI+agent+latest+demo+GPT+Claude+viral` 等）→ 仍然 1 条
- 推测原因：Bing 视频搜索用了虚拟列表 + 懒加载，headless Playwright 不触发完整渲染

**正确做法 — 直接 `curl` 拿 HTML**（Bing 的 HTML 是完整 server-rendered，含全部卡片）：

```bash
curl -sL --max-time 30 \
  -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+OpenAI+Gemini+trending+2026&FORM=HDRSC6" \
  -o /tmp/bing1.html
# 506KB HTML, 28+ 个 aria-label="...来源..." 卡片
```

提取（grep 单行 regex 即可）：

```bash
grep -oE 'aria-label="[^"]*来源[^"]*"' /tmp/bing1.html | head -30
```

**为什么 curl 比浏览器更可靠**：
- Bing HTML 是服务端渲染（SSR），curl 拿到的是完整 DOM
- 浏览器路径需要等 React/Bing 虚拟列表 hydrate + 触发 IntersectionObserver，headless 模式下经常不触发
- 同样的提取逻辑（aria-label 解析）从 curl 输出一样工作，因为 HTML 完全相同
- 速度：curl ~2-3s，浏览器 navigate + console 反复试 60s+ 仍只 1 条

**经验法则**：YouTube/Bing 视频搜索页 **curl-first**，浏览器路径留作降级。

---

## ⚠️ Bing 中文网络出口下结果是 bilibili 包装（2026-06-14 早间档实测）

2026-06-14 06:01 CST 实测：从国内网络出口 `curl` Bing 视频搜索 HTML 时，**前 28+ 条结果几乎全部是 bilibili 源视频**（Bing 把 bilibili 视频也聚合进了视频搜索结果集）。每条 aria-label 的格式是：

```
aria-label="全网AI首拆，一台车的灵魂原来是...来源: bilibili · 时长: 9 分钟5 秒 · 已浏览 198.4万 次 · 上传时间: 06-10 21:31 · 上传人: 所长Wy · 单击以播放。"
```

而每个 `<a>` 标签的 href 区域附近，HTML 里能找到 BVID 链接：`/video/BV17SER6AEJh`。

**完整提取流程**（curl → regex → BVID 列表 → B站 API 解析）：

```python
import re
# Step 1: 从 Bing HTML 同时提取 aria-label 标题信息和 BVID
seen = set()
results = []
for f in ['bing1.html', 'bing2.html', 'bing_p2.html']:
    html = open(f).read()
    for m in re.finditer(r'aria-label="([^"]*来源[^"]*)"', html):
        label = m.group(1)
        forward = html[m.end():m.end()+5000]
        bvm = re.search(r'/video/(BV[A-Za-z0-9]{10})', forward)
        if bvm:
            bv = bvm.group(1)
            if bv in seen: continue
            seen.add(bv)
            results.append({'bv': bv, 'label': label[:300]})

# Step 2: 对每个 BVID 调 B站 /view API 拿精确数据
import urllib.request, json
def fetch_bv(bv):
    req = urllib.request.Request(
        f"https://api.bilibili.com/x/web-interface/view?bvid={bv}",
        headers={
            'User-Agent': 'Mozilla/5.0 ...',
            'Referer': 'https://www.bilibili.com/',
            'Accept-Encoding': 'identity',  # 关掉 gzip 避免手动解码
        })
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())['data']
    return {
        'title': d['title'],
        'owner': d['owner']['name'],
        'view': d['stat']['view'],
        'duration': d['duration'],  # 秒
        'pubdate': d['pubdate'],   # unix ts
    }
```

**关键发现**：
- Bing 视频搜索中文出口下基本是 bilibili 镜像（数据真实、播放量真实、UP主真实）
- 通过 BVID 走 `/x/web-interface/view?bvid=xxx` API 拿的数据是**真实权威数据**（B站官方），不需要担心 Bing 显示的播放量是估算
- **XML 链接直接用 B站 URL**：`https://www.bilibili.com/video/{bv}/`（不要用 Bing search URL，因为视频源就是 B站）
- 2026-06-14 实测 /view API 仍可用（之前笔记说 search 接口已废，**单视频 /view 接口没事**）
- API 速率安全：单条 ~0.3s sleep 串行调用 60 条无问题

---

## ⚠️ 单字 B站 search API query 的假阳性雷区（2026-06-22 早间档实测新增）

`scripts/bing_to_bili.py` 默认会跑 `AI / ChatGPT / AI早报 / Claude / Gemini / DeepSeek` 这些关键词的 B站 search API（`order=pubdate`）。**问题**：

- **`Gemini` 单字 query**（2026-06-22 06:02 CST 实测）：返回大量 **"【Gemini】鹅鸭杀 Goose Goose Duck"** / **"Gemini小游戏"** / **"Gemini狼人杀"** — 这里的 Gemini 是战队名/玩家名/主播名，**不是 AI 模型**。按 `looks_like_ai` 关键词命中能过第一道过滤，但语义完全无关。
- **`AI` 单字 query**：返回 **"05益虫害虫蚂蚁多养蚜虫"**（UP主玫琳儿，57 秒短视频）/ **"6月22日资讯早饭｜多家纸尿裤品牌再回应甲酰胺风波"**（瞬息洞察所）/ **"一诺元射'老农民'装扮 各直播间反应"**（熊熊无聊_）— 标题里"AI"是电视台台标或者干脆无意义，按 `looks_like_ai` 完全没过滤掉。
- **`ChatGPT` query**：相对干净，命中真实 AI 教程（魔法puppy 的 GPT5.5 白嫖系列等），但仍需 `view>=50` 兜底。

**新增显式黑名单**（务必加进 `bing_to_bili.py` 的 `EXCLUDE_KW`，否则 06:00 早间档 news 类会被假阳性淹没）：

```python
EXCLUDE_KW = [
    # AI 产品名/战队名/玩家名假阳性
    '鹅鸭杀', 'Goose', '狼人杀', '王者', '王者荣耀', '魔兽', '星际争霸',
    '外星人', '虫族', 'NBA', 'CBA', 'F1', '赛车', '漫展', 'cos',
    '世界杯', '足球', '篮球', '赌', '押注', '理财',
    '美瞳', '美甲', '减肥', '瘦身', '医美', '植发', '相亲',
    # 直播/电竞/装扮类（不属 AI 视频）
    '偶像', '主播', '直播间', '装扮', '一诺元射', '小乔大王',
    # 06:00 早间档实测的诡异命中（蚂蚁/纸尿裤/野草/鹌鹑等）
    '蚂蚁', '纸尿裤', '野草', '鹌鹑', '幼童', '父扑火', '甲酰胺',
    # AI 工具无关关键词
    '小病', '世界杯预测',
]
```

**早间档 news 严格过滤配方**（2026-06-22 06:02 CST 验证，凑出 3 条真实 AI 当日新发）：

```python
from datetime import datetime, timezone, timedelta
CST = timezone(timedelta(hours=8))
today = datetime.now(CST).strftime("%Y-%m-%d")

AI_KW_STRICT = [
    'AI', 'Gpt', 'gpt', 'ChatGpt', 'chatgpt', 'Claude', 'claude', 'Gemini', 'gemini',
    '大模型', 'LLM', 'llm', '深度学习', 'AGI', 'Sora', 'Midjourney', 'Stable Diffusion',
    'ComfyUI', 'Copilot', 'cursor', 'MCP', 'Agent', '智能体', 'Llama', 'Mistral',
    'DeepSeek', 'deepseek', 'Kimi', 'kimi', 'Grok', 'grok', 'OpenAI', 'Anthropic',
    '文心一言', '通义千问', 'AI日报', 'AI早报', 'AI工具', '编程',
]

def is_ai_real(title):
    return any(k in title for k in AI_KW_STRICT) and not any(k in title for k in EXCLUDE_KW)

news_final = [d for d in all_news
              if datetime.fromtimestamp(d['pubdate'], CST).strftime("%Y-%m-%d") == today
              and d['view'] >= 50
              and is_ai_real(d['title'])]
```

**实测 06:00 早间档 news 数量**：3 条真实 AI 当日新发（江枫_AI 的 AI日报 / 菠萝没有蜜丶 的 Grok 教程 / 干嘛wjndj 的 DeepSeek 小游戏娱乐）。不要强行凑 TOP 10 — skill 已明确"早间档发视频少，不要强行凑数"。

---

## 06:00 CST 早间档 推荐流程（2026-06-14 综合，2026-06-20 早间档修正，**2026-06-22 早间档修正单字 query 黑名单**）

确认 YouTube HTTP 000 后：

1. **检测 + 跳过 YouTube 浏览器**（`curl` 一下确认，不要 60s 反复试浏览器）
2. **curl Bing 视频搜索**（1-2 个 query）→ `grep -oE '/video/BV[A-Za-z0-9]{10}'` 提取 BVID（**不依赖 aria-label 语言**）
3. ~~**Bilibili search API**（`urllib.parse.quote` 编码关键词）→ 获取更多 BVID~~ — ⚠️ **2026-06-20 实测：早间档 06:00 CST 不要走 `/x/web-interface/search/type?order=pubdate` 补量！** 见下文"B站 search API by-date 早间档垃圾坑"。直接用 Bing 数据按 view 排序就够了
4. **对所有 BVID 批量调 `/x/web-interface/view` API**（Bing 30-40 条足够，串行 ~0.3s sleep）→ 拿标题/播放量/时长/UP主/上传时间
5. **Python 内 classify + sort**：按 `duration` 切长短（阈值 180s），按 `view` 排热度，按 `pubdate` 排新发
6. **写 XML**（DocxXML 模板，**忽略 prompt 里的 `<YouTubeTrending>` 误导**）
7. **lark-cli 上传**（`+update --command overwrite --doc-format xml`），期望 `ok: true` + 2 个 `degrade_code=4007` warnings（无害）

**总耗时**：~1-2 分钟

### ⚠️ B站 search API by-date 早间档垃圾坑（2026-06-20 早间档实测新增，2026-06-22 黑名单扩展）

**反例**：2026-06-20 06:02 CST 跑 `https://api.bilibili.com/x/web-interface/search/type?keyword=AI&order=pubdate&page=1`，**前 10 条全是垃圾**：

| 标题 | 频道 | 播放量 | 类型 |
|------|------|--------|------|
| ETCSP2026款隐藏式AI屏幕语音无卡etc设备 | 好物推荐 | 0 | ETC 设备广告 |
| 国产大模型连续七周霸榜全球｜英首相被自己人逼宫｜食肉蛆虫时隔60年重返美国 | 世界又发生了啥 | 4 | 新闻汇编（非 AI 主题） |
| ai真好玩 | 鹤望兰ZERO米浴 | 0 | 灌水 |
| GPT预测世界杯系列: 复盘，瑞典VS突尼斯（×6 条同样格式） | zerocool40 | 0-4 | 世界杯 AI 预测灌水 |

**2026-06-22 06:02 CST 进一步发现**：跑 `Gemini` 和 `AI` 单字 query 时，假阳性更离谱 — 返回鹅鸭杀战队名 "Gemini"、纸尿裤新闻、蚂蚁害虫科普、王者荣耀装扮直播等。**所有跑 search API by-pubdate 的代码路径必须配 `EXCLUDE_KW` 黑名单 + `AI_KW_STRICT` 白名单双过滤**，否则 06:00 早间档 news 完全无法凑出 5 条真实 AI 内容。

**关键观察**：
- 早间档 06:00 CST 触发时，B站按 pubdate 排序返回的是**当日 0-6 小时内上传的所有内容**，里面 AI 早报没发（07:00+），剩下全是低质刷量或蹭 AI 关键词的灌水
- 这些 0-view 内容调 `/view` API 后 `stat.view = 0` 仍然入库，污染整个 TOP 10
- B站热门榜（`/x/web-interface/popular`）+ 多关键词 search-hot 路径**也只能补充 ~150 条候选**，**全部走 `/view` 后 AI 关键词过滤后**还是 Bing 的 40 条更干净

**正确做法**（更新后的早间档流程）：
1. **只用 Bing 一个数据源**（1-2 个 query → 40 个 BVID → 37 条 AI-relevant）
2. **不要**用 B站 search API by-date 补"当日新发"——会被 0-view 灌水淹没
3. **News 类用 Bing 的现有数据按 pubdate 倒序排**，接受时间范围 5月-6月（最新条目通常是 5月18日），在飞书文档顶部加一行说明：

```xml
<p>06:00 CST 早间档触发，中文 AI 早报生态（橘鸦Juya / 阿梨等）07:00-10:00 CST 才发布当日内容，Bing 视频搜索也未及时收录当日新发，"最近上传"列表反映 1-2 周内的 AI 热门视频，按上传时间倒序排列。</p>
```

4. **晚间档 20:00 CST 才用 B站 search API by-date 补"当日新发"**——此时 B 站 AI 早报生态已发完，按 pubdate 排序才有真正的当日 AI 内容
5. **如果一定要在 06:00 CST 补 news**：用上面"单字 query 假阳性雷区"小节里的 `EXCLUDE_KW` + `AI_KW_STRICT` 组合过滤，预期只能拿到 3-4 条真实结果，不要凑 TOP 10

### ⚠️ Bing 数据时间范围偏旧（2026-06-20 早间档实测新增）

**反例**：2026-06-20 06:02 CST Bing 视频搜索返回的 40 条 BVID 中，**最"新"的条目是 2026-05-18**（1 个月前），没有任何 24-48 小时内的"今日热门"。

**原因**：
- Bing 视频搜索在中文网络出口下聚合的是**已经积累了一定播放量的视频**（质量门槛过滤），新上传 0-view 视频不会冒头
- 即使 Bing 返回"X 小时之前"的视频，aria-label 里的"上传时间"是 Bing 抓取索引的时间，不是视频实际发布时间
- AI 早报生态（橘鸦等）的视频 Bing 索引滞后 1-7 天

**对飞书文档的影响**：
- 长视频/短视频 TOP 10 数据质量 OK（播放量真实、UP主真实、内容真实）
- "当日新发 TOP 10"在 06:00 CST 早间档**永远无法**凑齐真正当日发布的 AI 内容
- **不要为了凑数放宽阈值**（如"最近 30 天"），保持"最近上传"语义清晰即可
- 在文档里**明确标注时间范围**让用户清楚知道这是"近 1-2 周内最热"

### 早间档 vs 晚间档 数据源选择（2026-06-20 综合，**2026-06-20 晚间档实测修正，2026-06-22 单字 query 修正**）

| 时段 | 长视频 TOP 10 | 短视频 TOP 5 | 当日新发 TOP 10 |
|------|---------------|--------------|-----------------|
| **早间档 06:00 CST** | Bing (按 view) | Bing (duration ≤ 180s, 按 view) | Bing (按 pubdate 倒序，**仅作为最近参考**，加时间范围说明)。如需补量用 `EXCLUDE_KW`+`AI_KW_STRICT` 严格过滤，预期 3-4 条 |
| **晚间档 20:00 CST** | Bing + B站 hot | Bing + B站 hot | **B站 search API `order=pubdate`（此时 AI 早报已发完） + 4 维质量过滤后按 view 排序** |

> **2026-06-20 20:00 CST 晚间档实测**：B站 search API 在 7 个 query 中有 5 个被 412 节流拒绝，**只有 `AI日报` 和 `ChatGPT` 返回 200 OK**（每个 20 条）。Bing 一如既往 38 个 BVID。**当日新发 21 条 2026-06-20 上传 → 19 条通过质量过滤 → 0-view / 1 词标题 / 1 字用户名垃圾被剔除**。完整 4 维质量过滤配方见下文"晚间档 4 维质量过滤"小节。

### 晚间档 4 维质量过滤（2026-06-20 实测，剔除 0-view 灌水的关键）

B站 search API `order=pubdate` 在 20:00 CST 触发时返回的内容**仍然有 30-50% 是低质刷量或蹭 AI 关键词的灌水**（0-view、1 词标题、1 字用户名、UP主无头像），必须用 4 维过滤才能凑出干净的 TOP 10：

```python
def is_ai_relevant(title):
    t = title.lower()
    if 'illustrator' in t: return False
    bad = ['赌', '押注', '理财', '赌狗', '赌资', '赌场', '彩票', '美瞳', '美甲',
           '减肥', '瘦身', '按摩', '养生', '医美', '植发', '隆胸', '相亲']
    if any(k in title for k in bad): return False
    bad_ent = ['星际争霸', '外星人', '虫族', '俘虏', '波兰球', 'NBA', '小病',
               '成为虫族', '世界杯', '足球', '篮球', 'CBA', 'F1', '赛车', '漫展', 'cos']
    if any(k in title for k in bad_ent): return False
    return True

# 强 AI 关键词白名单（大小写不敏感）
AI_KW = ['AI', 'Gpt', 'gpt', 'ChatGpt', 'chatgpt', 'Claude', 'claude', 'Gemini', 'gemini',
         '大模型', '大语言', 'LLM', 'llm', '深度学习', '神经网络', '机器学习', 'AGI', 'agi',
         'Sora', 'Midjourney', 'Stable Diffusion', 'Diffusion', 'ComfyUI', 'Copilot', 'cursor',
         'MCP', 'Agent', '智能体', 'Llama', 'llama', 'Mistral', 'mistral', 'DeepSeek', 'deepseek',
         '文心一言', '通义千问', '盘古', '混元', 'Kimi', 'kimi', 'Grok', 'grok',
         'AI日报', 'AI早报', 'AI周报', 'AI工具', 'OpenAI', 'openai', 'Anthropic', 'anthropic',
         'Prompt', '提示词', 'Transformer', 'transformer', 'MoE', 'Mamba', 'mamba',
         'RAG', 'rag', 'Embedding', 'embedding', 'Token', 'token', 'LangChain', 'langchain',
         'Hugging Face', 'HuggingFace', 'GitHub Copilot', 'DALL', 'Whisper', 'Runway', 'Pika', 'Suno', 'Udio',
         'Robot', '机器狗', '波士顿动力', '具身智能', '自动驾驶', 'FSD',
         '图像生成', '视频生成', '语音合成', 'TTS', 'ASR', 'NLP', '强化学习', 'RLHF', 'DPO',
         'AI编程', 'Cursor', 'Codeium', 'Cline', 'Continue', 'GenAI', 'AIGC', '超级智能']

def looks_like_ai(title):
    return any(k in title for k in AI_KW)

def is_quality_news(d):
    """4 维质量门 — 任何一维不过就丢"""
    if d['view'] < 5: return False          # 维度1: 播放量门槛（拒 0-view 灌水）
    if d['duration'] <= 0: return False     # 维度2: 时长合法
    t = d.get('title', '').strip()
    if len(t) < 4: return False             # 维度3: 标题非单字（拒"chatgpt" "AI" "GPT"）
    o = d.get('owner', '').strip()
    if len(o) < 2: return False             # 维度4: UP主名非 1 字（拒"user_xxx"自动账号）
    return True

# 组合调用
news_top10 = sorted(
    [d for d in today_pool if looks_like_ai(d['title'])
                              and is_ai_relevant(d['title'])
                              and is_quality_news(d)],
    key=lambda x: (-x['view'], -x['pubdate'])
)[:10]
```

**实测 4 维过滤效果**（2026-06-20 21:00 CST）：

| 阶段 | 数量 | 例子 |
|------|------|------|
| 原始 API 返回 | 40 | 含 "chatgpt"(0view), "AI"(0view), ETC 设备 |
| AI 关键词白名单 | 28 | 滤掉 12 条无关 |
| `is_ai_relevant` 黑名单 | 28 | 暂无娱乐/赌博项 |
| 4 维质量门 | 19 | 滤掉 9 条 0-view / 单字标题 / 单字用户名 |
| **最终 TOP 10** | **10** | infinite灵感港 / 阿梨Aria / _AI风向标_ / 硅基考古队 / 江枫_AI 等真实 AI 日报 |

### B站 search API 412 节流模式（2026-06-20 晚间档实测）

`/x/web-interface/search/type?keyword=...&order=...` 端点对**单 IP 短时间内大量 query**触发 412 Precondition Failed 节流。2026-06-20 20:05 CST 实测 7 个 query：

| Keyword | Order | Status | 备注 |
|---------|-------|--------|------|
| `AI早报` | pubdate | **412** | 高频词先被限流 |
| `AI日报` | pubdate | **200** | ✅ 20 条 |
| `ChatGPT` | pubdate | **200** | ✅ 20 条 |
| `Claude` | pubdate | **412** | |
| `Gemini` | pubdate | **412** | |
| `AI 人工智能` | hot | **412** | |
| `AI 2026` | hot | **412** | |

**结论**：
- 7 个 query 只命中 2 个（28.5%），节流很激进
- **不要一次性发 7 个 query** —— 间隔太短都会 412。建议每 query 间隔 0.4-0.5s，且总 query 数 ≤ 3
- 命中的 2 个 query 足够凑出 40 条候选 → 4 维过滤 → 10 条 TOP
- **备选降级**：如果 7 个 query 全 412，回退到 Bing 视频搜索的"按时间排序"（虽然数据偏旧，1-2 周前）

---

## 背景

YouTube 在国内数据中心网络环境下可能被完全封锁（curl 返回 HTTP 000，连接被重置）。
此时需使用替代数据源填充 AI 热门视频报告。

## 数据源1：Bing 视频搜索

### 优势
- 覆盖全球 YouTube、Vimeo、Dailymotion 等平台视频
- 在国内网络稳定可达
- 搜索结果包含：标题、来源、时长、上传日期、估算播放量

### 搜索 URL 模板

```
# 全球 AI 新闻（英文）
https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+OpenAI+Gemini+trending+2026

# 特定事件（如 Google I/O）
https://www.bing.com/videos/search?q=Google+I%2FO+2026+recap+AI+agents+Gemini

# AI 短视频/快速评测
https://www.bing.com/videos/search?q=AI+shorts+GPT+Claude+Gemini+2026+viral

# 中文 AI 内容
https://www.bing.com/videos/search?q=AI+大模型+热门+2026
```

### 关键词选择决定返回结果语言（2026-06-11 晚间档实测）

⚠️ **Bing 视频搜索会根据关键词语言自动地域化结果**。泛英文关键词 `AI LLM GPT Claude OpenAI Gemini trending 2026 June` 在中文网络出口下返回的 30 条结果里**约 50-60% 是日文频道**（3分でわかる海外AI / AI大学 / いまにゅのAIプログラミング塾 / 風花のAI活用ログ 等），剩下 30% 中文假货/无关 + 20% 英文优质结果。直接拿这些当"全球热门"会大幅拉低质量。

**修正策略 — 用具体英文主题词而非泛关键词**：

| 想拿到的内容 | 关键词模板 | 2026-06-11 实测命中率 |
|---|---|---|
| 英文高质量 AI 视频 | `WWDC 2026 Apple Intelligence Siri review` / `Claude Opus review` / `GPT news AI trending` 等**具体事件+产品**词 | 30 条里 25+ 条英文优质 |
| 日文 AI 频道 | `AI 最新 ニュース 2026` / `ChatGPT 活用術` | 几乎全是日文 |
| 中文 AI 内容 | `AI 大模型 热门 2026` | 几乎全是中文 |
| 泛英文 AI 趋势 | `AI LLM GPT Claude trending` | **命中率不可控**，不推荐 |

### Bing 关键词实际差异比预期小（2026-06-12 早间档实测修正）

> ⚠️ **2026-06-12 早间档实测反例**：连续 3 个不同关键词的 Bing 视频搜索结果**前 10 条几乎完全相同**（同一批视频卡片，仅排序微调）：
>
> | 关键词 | 前 5 条命中重合度 |
> |---|---|
> | `AI+LLM+GPT+Claude+Gemini+trending+2026+June` | Inside Anthropic / The dark side of AI / Top 3 AI platform updates / What Is AI? / Getting Real about WWDC |
> | `AI+agent+latest+demo+GPT+Claude+viral` | 同样的 5 条 |
> | `AI+trending+June+12+2026` | 同样的 5 条 |
>
> Bing 视频搜索在中文网络出口下对"AI 热门"语义做了高度聚类，前 10 条几乎是固定池。这**反驳了上面"换关键词拿更多结果"的说法**。
>
> **真实能扩量的方式**：
> - **访问第二页**：`&first=31` 偏移参数（**经验证有效**，2026-06-11 笔记也提到，但 2026-06-12 实测第二页 14 条几乎全是无关杂项 / Apple Watch 老视频，性价比低）
> - **换完全不同主题的具体事件词**（如 `Anthropic+Claude+Gemini+AI+news+today`、`Apple+WWDC+2026+keynote+Siri+AI`、`OpenAI+GPT-5+latest+news`）— 但**注意这类查询可能返回 1 个月前 / 1 年前的旧视频**（Anthropic 3 个月前、OpenAI 2024 年 GPT-4o demo），要按"上传时间"过滤，否则会拿到假新发
> - **跨平台拼**：Bing 凑长视频 + Bilibili 凑当日新发（已推荐过的方案仍然最稳）
>
> **早间档 06:00 CST 的可行策略**：
> 1. 1 次泛 Bing 查询（`AI+LLM+GPT+Claude+OpenAI+Gemini+trending+2026`）→ 凑齐长视频 TOP 10 + 短视频 TOP 5
> 2. 1 次 Bilibili `AI早报` 按发布日期搜索 → 凑齐当日新发 TOP 10
> 3. **不再尝试第二组 Bing 关键词**（浪费时间且结果重复）
> 4. Bing 视频"上传时间"含"X 小时之前"或"X 天之前"都算"近期"，不要严格卡"今天/昨天"

### ⚠️ 06:00 CST 早报空窗（2026-06-13 早间档实测修正）

> **反例**：2026-06-13 06:01 CST 实测，Bilibili 搜 `AI 2026-06-13` 按 pubdate 排序时，**当天完全没有 AI 早报类视频**。中文 AI 早报生态（橘鸦Juya / 阿梨Aria早鸟报 / 苍痕Luca / 猫鱼论AI / AutoDove）的实际发布时间是 **07:00-10:00 CST**。早间档 cron 在 06:00 CST 触发时，当天 B 站早报**还没发布**，搜出来的是 6.12 早上的 5 条（20-22 小时前）+ 一堆不相关杂项（YOLO 教程 / 英语听力 / 信息差等）。
>
> **正确处理**（按"按最新排序"+"最近上传"的宽泛解释）：
> 1. **不要等**——cron 触发就执行，没有"当日 6.13 B 站早报"是正常的
> 2. **B 站 5 条 = 昨天 6.12 早上的早报**（6.12 07:00-10:00 发的，距今 20-23 小时），标 `上传：06-12 HH:MM` 让用户清楚时间
> 3. **Bing 凑剩下 5 条**：用 "X 小时之前" / "1 天前" 的近期 AI 视频（与 B 站 5 条拼成 TOP 10）
> 4. **按"上传时间"倒序排**（不是"按播放量排"）：Bing 5h > Bing 7h > Bing 10h > Bing 16h > B 站 6.12 09:45 > ... > B 站 6.12 07:10
> 5. **晚间档 20:00 CST 才是第一个能拿到"完整当日"数据的 session**——B 站 6.13 早报基本都发完了
>
> **早间档不要强行只取"今天发布的"**——会只拿到 1-2 条或 0 条，远低于 TOP 10 目标。宽泛解释"最近上传" = 24-48h 内即可。

### 拿更多结果的正确方式

- **直接访问第二页**：`&first=31` 偏移参数
- **跨平台补量**：Bing 凑长视频，Bilibili 凑当日新发（最稳）
- **不要**靠点"展开"按钮扩量

### Bing 展开按钮对虚拟列表无效（2026-06-11 实测）

点页面底部"展开"按钮后再抓 `aria-label` 列表，**返回的结果与点击前完全一致**（同 30 条，无新增）。Bing 视频结果用虚拟列表 + 滚动加载，按钮只是滚动到下一页锚点，DOM 中不新增 `<a>` 节点。
### 拿更多结果的正确方式

- **直接访问第二页**：`&first=31` 偏移参数
- **跨平台补量**：Bing 凑长视频，Bilibili 凑当日新发（最稳）
- **不要**靠点"展开"按钮扩量

### 数据提取方式（2026-06-16 更新：BVID 直取为首选）

⚠️ **aria-label 格式随网络出口语言变化**（2026-06-16 晚间档实测）：

- **中文出口**（2026-06-14）：`aria-label="标题...来源: bilibili · 时长: ... · 已浏览 ... 次 · 上传时间: ... · 上传人: ... · 单击以播放。"` → `aria-label*="来源"` 可匹配
- **英文出口**（2026-06-16）：`aria-label="7 Best ChatGPT Alternatives to Try in 2026 from eweek.com · uploaded on 1 month ago · Click to play."` → **`aria-label*="来源"` 匹配 0 条**

**首选方案 — BVID 直取 + B站 /view API**（不依赖 aria-label 语言）：

```python
import re, urllib.request, json

html = open('/tmp/bing1.html').read()
bvs = list(set(re.findall(r'/video/(BV[A-Za-z0-9]{10})', html)))

for bv in bvs:
    req = urllib.request.Request(
        f"https://api.bilibili.com/x/web-interface/view?bvid={bv}",
        headers={
            'User-Agent': 'Mozilla/5.0 ...',
            'Referer': 'https://www.bilibili.com/',
            'Accept-Encoding': 'identity',
        })
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read())['data']
    # d['title'], d['owner']['name'], d['stat']['view'], d['duration'], d['pubdate']
```

**为什么 BVID 直取比 aria-label 更稳**：
- BVID 链接（`/video/BVxxx`）格式固定，不随语言/地区变化
- B站 `/view` API 返回权威数据（精确播放量、真实标题），比 Bing aria-label 估算值更准
- 2026-06-16 实测：两个 Bing query 拿到 34 个唯一 BVID，全部 /view API 成功
- **XML 链接直接用 B站 URL**：`https://www.bilibili.com/video/{bv}/`

**降级方案 — aria-label 路径**（仅中文出口有效）：

```javascript
// 仅当确认 Bing 返回中文 aria-label（含"来源"）时使用
Array.from(document.querySelectorAll('a[aria-label*="来源"]')).slice(0, 30).map(a => {
  const parts = a.getAttribute('aria-label').split('·').map(s => s.trim());
  return {
    title: parts[0],
    source: (parts.find(p=>p.startsWith('来源:'))||'').replace('来源:','').trim(),
    duration: (parts.find(p=>p.startsWith('时长:'))||'').replace('时长:','').trim(),
    views: (parts.find(p=>p.startsWith('已浏览'))||'').replace('已浏览','').trim(),
    uploaded: (parts.find(p=>p.startsWith('上传时间:'))||'').replace('上传时间:','').trim(),
    uploader: (parts.find(p=>p.startsWith('上传人:'))||'').replace('上传人:','').trim()
  };
}).filter(v => v.title);
```

### 数据提取方式（snapshot 路径，已被 aria-label 取代，保留作降级）

直接读 `browser_snapshot` 输出的可访问性树文本，再正则解析：

1. `browser_navigate` 打开搜索页
2. `browser_snapshot full=true` 拿到完整可访问性树（含中文 "已浏览 X 次"、"上传人: XXX"、"上传时间: XXX" 等结构化文本）
3. 按 link "..." 段解析，正则提取 `已浏览 ([0-9.]+[万亿]?) 次` / `时长: ([^·]+?) ·` / `上传人: ([^·]+?) ·` / `上传时间: ([^·]+?) ·`

**解析代码模板**（Python）：

```python
import re

def parse_dur(s):
    # "44 分钟29 秒" -> "44:29", "1 分钟26 秒" -> "1:26"
    s = s.replace(" 分钟", ":").replace(" 秒", "").strip()
    parts = s.split(":")
    if len(parts) == 2:
        return f"{parts[0]}:{parts[1].zfill(2)}"
    return s

# ⚠️ 短视频判定陷阱（2026-06-13 实测）：
# 解析后的 "47:40".split(":") 长度 = 2，跟 "1:26" 一样都是 2 段。
# 简单用 `len(parts) == 2` 判 short 会把 47 分钟视频也判成 short。
# 正确做法：转秒后用 `dur_to_seconds <= 180` 判：
#   def dur_to_seconds(s):
#       parts = [int(p) for p in s.split(":")]
#       if len(parts) == 2: return parts[0]*60 + parts[1]
#       if len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
#   is_short = dur_to_seconds(duration) <= 180

# 每条 link 的文本格式：
#   标题
#   来源: YouTube · 时长: 44 分钟29 秒 · 已浏览 7.1万 次 · 上传时间: 2 天之前 · 上传人: ABC News In-depth · 单击以播放。

for block in blocks:
    lines = block.split("\n")
    if len(lines) < 2: continue
    title = lines[0].strip()
    info = " ".join(lines[1:])
    m_views = re.search(r"已浏览\s*([\d.]+\s*[万亿]?)\s*次", info)
    m_dur = re.search(r"时长:\s*([^·]+?)\s*·", info)
    m_chan = re.search(r"上传人:\s*([^\s][^·]+?)\s*·\s*单击以播放", info)
    m_time = re.search(r"上传时间:\s*([^·]+?)\s*·", info)
```

**注意**：snapshot 默认会截断到约 30 行完整内容；如需更多，调用 `browser_snapshot full=true`，或滚动页面后再次 snapshot 增量。Bing 单页通常 12-20 条结果，够用。

### 局限性
- 部分条目无精确播放量（无 → 用 `—` 占位，不要编造）
- 搜索结果以相关性排序，非播放量排序
- 链接可能是 Bing 重定向链接，需提取实际 URL

### 死路：RSS feed 不要尝试

`https://www.bing.com/videos/feed?count=30&q=...&format=rss` 会 301 重定向到 `https://cn.bing.com/videos/feed?...`，而 cn.bing.com 端点**无视 `format=rss` 直接返回 HTML 搜索页**。浪费时间，绕开。

## 数据源2：Bilibili 搜索页

### 优势
- 中文 AI 内容覆盖全面
- 包含精确播放量、UP主信息
- AI 早报系列（橘鸦Juya、阿梨Aria早鸟报等）每日更新，质量稳定

### 搜索 URL 模板

```
# AI 早报（按发布日期排序，获取最新）
https://search.bilibili.com/all?keyword=AI早报&search_type=video&order=pubdate

# AI 热门（按播放量排序）
https://search.bilibili.com/all?keyword=AI+人工智能&search_type=video&order=hot

# 特定日期
https://search.bilibili.com/all?keyword=AI+2026-06-01&search_type=video&order=pubdate
```

### 数据提取方式（2026-06-09 实测修正）

⚠️ **Bilibili 搜索页所有视频卡片标题都被前端遮盖为"稍后再看"** —— 即使用 JS 抓 `<h3>.textContent` 拿到的也是 `稍后再看{播放量}{时长}`，不是真实标题。原版 JS 过滤 `!title.includes('稍后再看')` 会过滤掉所有条目。

**正确流程**：

1. `browser_navigate` 打开搜索页（按 `pubdate` 或 `hot` 排序均可）→ `browser_console` 抓 BVID 列表（不读 title）：
   ```javascript
   var bvids = [];
   document.querySelectorAll('a[href*="/video/BV"]').forEach(a => {
     var m = a.href.match(/\/video\/(BV[A-Za-z0-9]+)/);
     if (m && !bvids.includes(m[1])) bvids.push(m[1]);
   });
   JSON.stringify(bvids.slice(0, 25));
   ```

2. ~~对每个 BVID 调用 `https://api.bilibili.com/x/web-interface/view?bvid=xxx` 拿真实标题~~ — **2026-06-10 实测：`/x/web-interface/search/type` 和 `/search/all/v2` 端点即使带 `Referer: https://search.bilibili.com/` 头也直接返回 HTML 搜索页**（被反爬拦截，不返回 JSON）。`/x/web-interface/view?bvid=xxx` 单视频接口当前仍可用但 search 接口已废。

   **修正后的真实数据来源**：直接读 `browser_snapshot` 输出的 Bilibili 搜索页可访问性树。Snapshot 里 B 站视频卡片**保留了真实标题**（不像 YouTube 那种被遮盖的情况），格式如：
   ```
   - link "Anthropic 推出 Claude Fable 5 及 Claude Mythos 5【AI 早报 2026-06-10】 3.7万 45 04:17"
       - link "Anthropic 推出 Claude Fable 5 及 Claude Mythos 5【AI 早报 2026-06-10】"
       - link "橘鸦Juya · 10小时前"
   ```
   解析规则：标题在 link 文本前面，数字串是 `{播放量} {弹幕数} {时长}`，频道和上传时间在第二个 link 里。

3. 按 `pubdate` 降序得到"当日新发"，按 `stat.view` 降序得到"最热门"。

> **2026-06-11 实测修正**：当 B 站搜索 URL 带 `&search_type=video` 时，**`browser_console` 走 `a[href*="/video/BV"]` 路径可同时拿到真实 BVID 和真实标题**（h3.textContent 是干净的），不再需要 snapshot 解析：
> ```javascript
> Array.from(document.querySelectorAll('a[href*="/video/BV"]')).slice(0, 15).map(a => ({
>   href: a.href,
>   title: (a.querySelector('h3')?.textContent || '').trim()
> }));
> ```
> 这一结论只对 `?search_type=video&...` 路径有效；`/all?...` 通用搜索页仍被遮盖（h3 是 "稍后再看{播放量}{时长}"），需用上面 snapshot 方案。

> **不要尝试 Bing 视频搜索的 RSS feed**：`/videos/feed?format=rss` 会 301 到 `cn.bing.com` 然后被改写成 HTML 搜索页，不会返回 RSS。用 `browser_navigate` + `browser_console` 走 HTML 路径。

> **2026-06-13 晚间档实测补充**：B 站搜索页 `a[href*="/video/BV"]` 路径返回的是**成对的重复条目**（每个视频卡片 2 个 `<a>` 节点指向同一 BVID）—— 第 1 个是带"稍后再看{播放量}{时长}"占位标题的缩略图链接，第 2 个是真实标题的标题链接。`Array.from(...).slice(0, N)` 会拿到 2N 条记录，去重时按 BVID 去重即可。同时需要挑出 title 包含真实视频名（不是"稍后再看"）的那一条用。**更稳的提取方式**：
> ```javascript
> var seen = {}; var out = [];
> document.querySelectorAll('a[href*="/video/BV"]').forEach(a => {
>   var m = a.href.match(/\/video\/(BV[A-Za-z0-9]+)/);
>   if (!m) return;
>   var bv = m[1];
>   var t = (a.querySelector('h3')?.textContent || a.textContent || '').trim();
>   if (!seen[bv]) { seen[bv] = t; out.push({bv, title: t}); }
>   else if (t && !t.includes('稍后再看') && seen[bv].includes('稍后再看')) {
>     // 升级为真实标题
>     var idx = out.findIndex(x => x.bv === bv);
>     if (idx >= 0) out[idx].title = t;
>   }
> });
> JSON.stringify(out.slice(0, 15));
> ```

> **2026-06-13 实测：`browser_console` 上重 JS 链超时（30s）陷阱**。复杂的 `JSON.stringify(Array.from(document.querySelectorAll('a[aria-label*="来源"]')).filter(...).slice(0,25).map(a => { ... return {...} }), null, 2)` 链（DOM 过滤 + 切片 + map + JSON 序列化）经常会超时返回 `Command timed out after 30 seconds`。但简单的 `Array.from(...).map(...).slice(0, N).join('\n---\n')` 不超时（只提取 aria-label 字符串拼起来）。**经验法则**：console expression 避免 4 层以上链式调用 + 大对象序列化，单行控制在 200 字符内。

### ⚠️ Bilibili search API 必须 URL 编码（2026-06-16 晚间档实测）

`/x/web-interface/search/type?keyword=` 参数含中文或空格时必须 URL 编码，否则 Python `urllib.request` 报错 `'ascii' codec can't encode characters` 或 `URL can't contain control characters`。

```python
import urllib.parse
encoded_q = urllib.parse.quote("AI早报 ChatGPT Claude")
url = f"https://api.bilibili.com/x/web-interface/search/type?keyword={encoded_q}&search_type=video&order=pubdate&page=1"
```

### 高价值频道（AI 早报系列）

| 频道 | 内容 | 典型播放量 |
|------|------|-----------|
| 橘鸦Juya | 每日 AI 早报，覆盖国内外 AI 新闻 | 2-7万 |
| 阿梨Aria早鸟报 | AI 周报/日报，覆盖开源工具和模型 | 1000-3000 |

## 数据合并策略

当 YouTube 不可达时，按以下优先级填充报告：

1. **长视频 TOP 10**：Bing 英文搜索结果（6-8条）+ Bilibili AI 热门（2-4条）
2. **短视频 TOP 5**：Bing 短视频搜索 + Bilibili 短时长内容
3. **当日新发 TOP 10**：Bilibili AI早报（最新日期）+ Bing 最新搜索结果

合并后去重（按标题相似度），按可用数据排序（有播放量的优先）。

## XML 中标注数据来源

```xml
<p>数据来源：Bing视频搜索 + Bilibili（YouTube网络不可达，HTTP 000）</p>
```

在文档底部添加时间戳：
```xml
<text color="gray">⚠️ 数据获取时间：YYYY-MM-DD HH:MM | 数据来源：Bing视频搜索 + Bilibili（YouTube网络不可达，HTTP 000）</text>
```

---

## ⚠️ 晚间档 20:00 CST 实测增量（2026-06-22 20:02 CST 新增）

### 1. 重试被 412 节流的 query 模式（晚间档补量关键）

**反例**：`scripts/bing_to_bili.py` 默认串行跑 `ChatGPT` → `AI%E6%97%A5%E6%8A%A5` (AI日报) → `AI%E6%97%A9%E6%8A%A5` (AI早报) 三个 query，**实测 2/3 触发 412**（2026-06-20 + 2026-06-22 两次晚间档都中），导致当晚候选 BVID 仅 20-40 条，凑不齐 news TOP 10。

**关键发现**：412 节流**不是永久的**。等 2.5 秒后**重新跑同样的 query** 通常会 200 OK。2026-06-22 实测重试模式：

| Query | 第一次 | 重试（2.5s 后） |
|-------|--------|----------------|
| `AI早报` | 412 | 200 ✅ 20 条 |
| `AI日报` | 412 | 412（持续） |
| `Claude` | 412 | 200 ✅ 20 条 |
| `Gemini` | 412 | 200 ✅ 20 条 |
| `AI` | 200 ✅ | — |
| `DeepSeek` | 200 ✅ | — |
| `GPT` | 200 ✅ | — |
| `Sonnet` | 200 ✅ | — |

**正确做法**（晚间档 cron 必跑）：
```python
queries = ["AI早报", "Claude", "Gemini", "AI", "DeepSeek", "GPT", "Sonnet",
           "AI日报"]
import urllib.parse, time, urllib.request, json
for kw in queries:
    encoded = urllib.parse.quote(kw)
    time.sleep(2.5)  # 慢！避免 412
    url = f"https://api.bilibili.com/x/web-interface/search/type?keyword={encoded}&search_type=video&order=pubdate&page=1&page_size=20"
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Referer': 'https://search.bilibili.com/',
        'Accept-Encoding': 'identity',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read()).get('data', {}).get('result', []) or []
        # 收集...
    except urllib.error.HTTPError as e:
        if e.code == 412:
            print(f"  ❌ {kw} 412 throttled")
            continue
```

**实测 2026-06-22 晚间档效果**：8 个 query 命中 6 个 → **120 条候选 BVID → 68 条 /view 权威数据 → 14 条今日发布 → 8 条最终通过质量过滤**。够 news TOP 10 凑齐（凑齐 10 不强求，8 已可接受）。

### 2. 晚间档专属假阳性黑名单（新增必加项）

2026-06-22 06:02 早间档的 `EXCLUDE_KW` 黑名单**不够用**。晚间档 19-22 点发布的内容里有新的假阳性模式：

**游戏角色 / 战队假阳性**（晚间档高发）：
```python
'五杀', 'CG', '新皮肤', '小乔', '长生', '大侠', '狼人杀', '蛋仔', '鸭鸭',
'勇者', '副本', '夏季赛', '常规赛', '锦标赛', '卡组', '水人',
```
- 实测命中：「Gemini看新皮肤CG《一拜二拜三拜》」「Gemini:五杀」（UP 主织梦神 — 显然是游戏玩家视角）「长生小乔吹三个，Gemini大喊"妈妈"」

**AI 教程 / 广告灌水**（晚间档高发）：
```python
'充值', '升级订阅', '解除限制', '小白萌新', '小白无脑',
'无需礼品卡', '一键升级',
```
- 实测命中：「6月22最新 Grok 4.3解除限制！手机＋PC免费教程！小白无脑入手！100％成功！」(view=197)、「手把手教你3折拿下Super Grok」(view=200)、「(最新优惠，自己充GPT 会员chatgpt） plus/pro 国内充值教程」(view=189)

**完整 EXCLUDE_KW（晚间档版）**：
```python
EXCLUDE_KW_EVENING = EXCLUDE_KW + [
    # 游戏角色/战队（晚间档高发）
    '五杀', 'CG', '新皮肤', '小乔', '长生', '大侠', '狼人杀', '蛋仔', '鸭鸭',
    '勇者', '副本', '夏季赛', '常规赛', '锦标赛', '卡组', '水人',
    # AI 教程/广告灌水（晚间档高发）
    '充值', '升级订阅', '解除限制', '小白萌新', '小白无脑',
    '无需礼品卡', '一键升级',
]
```

### 3. News 凑齐策略：14 候选 → 8 干净（接受不凑 10）

**实测晚间档 news 数量漏斗**（2026-06-22 20:02 CST）：
| 阶段 | 数量 |
|------|------|
| 原始 B站 API 返回 | 120 |
| 去重 | 68 |
| /view API 成功 | 68 |
| 今日（2026-06-22）发布 | 40 |
| AI 关键词白名单 + 黑名单 | 14 |
| 4 维质量过滤（view≥100 提高阈值） | **8** |

**结论**：晚间档 20:00 CST cron，**news 凑齐 8 条真实 AI 视频是常态**，不必强行凑 TOP 10。文档里直接写 `<h2>当日新发热门视频 TOP 8</h2>` 而不是 TOP 10。

### 4. lark-cli 写入文件名约定（cron job prompt 强制要求）

**实测**：cron job prompt 经常强制要求 `--content @merged_youtube-ai.xml`（具体文件名）。**正确做法**：
1. 写 `/Users/xiesg/.hermes/cron/output/youtube-ai-pm_YYYY-MM-DD.xml`（**带时戳的真实文件名**，用于 cronjob 历史追溯 + SKILL.md 路径规范）
2. **同时**复制一份到 `/Users/xiesg/.hermes/cron/output/merged_youtube-ai.xml`（**满足 cron job prompt 的固定文件名要求**）
3. lark-cli overwrite 完成后**删除 merged 文件**（不污染下次 cron）

```bash
# 写两份
output_path="/Users/xiesg/.hermes/cron/output/youtube-ai-pm_${today}.xml"
merged_path="/Users/xiesg/.hermes/cron/output/merged_youtube-ai.xml"
echo "$xml" > "$output_path"
echo "$xml" > "$merged_path"

# 写入飞书
cd /Users/xiesg && lark-cli docs +update --api-version v2 \
  --doc "HhyMdusqdoVcW9xLyd2c2Yc2nnf" --command overwrite \
  --content @./.hermes/cron/output/merged_youtube-ai.xml --doc-format xml

# 写入成功（ok: true + revision_id + result: success）后删除 merged
rm -f /Users/xiesg/.hermes/cron/output/merged_youtube-ai.xml
```

**注意**：`--content @` 路径**必须从 HERMES_HOME（`/Users/xiesg/`）用相对路径**（`@./.hermes/...`），`@/absolute/path` 和 `@~/path` 都报错（已有 SKILL.md 顶层 pitfall 1 说明）。

### 5. view 阈值建议（晚间档 vs 早间档）

| 时段 | 推荐 view 阈值 | 原因 |
|------|----------------|------|
| 早间档 06:00 | view ≥ 5（默认） | AI 早报生态未发完，候选稀少 |
| 晚间档 20:00 | **view ≥ 50 或 ≥ 100** | B 站 AI 早报生态已发完，但 19-22 点仍混入 19:00 0-view 新发灌水；view≥50 兜底可剔除大部分 |

**实测**：view ≥ 5 拿到 19 条候选，但里面 5 条是 view=5-50 的边缘灌水（"贴小广告" view=569 这种保留 OK，但 view=129-140 的边缘 AI 日报也可保留）。建议晚间档 **view ≥ 100** 严格过滤。

---

## ⚠️ 晚间档 20:00 CST 实测增量（2026-06-24 20:13 CST 新增 — KPL/电竞赛/硬件/不翻墙广告 四类漏网假阳性）

### 1. KPL/王者荣耀 电竞选手「Gemini」假阳性 — 必须扩展 EXCLUDE_KW

**反例**：2026-06-24 20:13 CST 跑 9 个 B站 search API query（命中 7 个），过滤后 news 候选池里**5/9 = 56% 是 KPL/王者荣耀电竞赛讨论**，里面「Gemini」是 2026 KPL 春季赛/夏季赛的知名电竞选手**（玩家名 / 主播名）**，不是 Google AI 模型。

实测命中：
- `WE3:1虐杀DRG，Gemini直言:子阳来DRG太受罪了呀`（UP：迷尘ん，view=169）
- `Gemini震惊：WE用10分钟就把DRG打爆了！`（UP：KPL二路赛报，view=645）
- `Gemini：我EWC可能要去那个巴黎`（UP：熊熊无聊_，view=959）
- `SYG3∶2腐乳TES，gemini直言：书源真的燃尽了！`（UP：one牢师，view=329-866）

**这些标题既包含 "Gemini"（命中 AI_KW 白名单），又包含真实赛事数据，看似相关但与 AI 完全无关**。B站 412 节流后的 query pool 越宽（AI、Gemini、DeepSeek 等），KPL 选手 "Gemini" 出现的概率越高。

**修复 — 扩展 EXCLUDE_KW_EVENING（必加项）**：
```python
EXCLUDE_KW_EVENING = EXCLUDE_KW + [
    # 2026-06-22 晚间档：游戏角色/战队
    '五杀', 'CG', '新皮肤', '小乔', '长生', '大侠', '狼人杀', '蛋仔', '鸭鸭',
    '勇者', '副本', '夏季赛', '常规赛', '锦标赛', '卡组', '水人',
    '充值', '升级订阅', '解除限制', '小白萌新', '小白无脑',
    '无需礼品卡', '一键升级',
    # 2026-06-24 晚间档新增：KPL/王者荣耀电竞选手 Gemini
    'KPL', 'LPL', 'DRG', 'TES', 'SYG', 'WE', 'EWC', '书源', '子阳', '蓝桉',
    '虞姬', '虞美人', '虐杀', '打爆', '燃尽', '腐乳', '蓝桉虞姬',
]
```

**白名单也需微调** — `looks_like_ai` 不能再无条件匹配 `Gemini`：
```python
def looks_like_ai_strict(title):
    """2026-06-24 实测：单靠 'Gemini' 关键词不够，必须配合 AI 上下文"""
    has_ai_kw = any(k in title for k in AI_KW)
    # 如果标题只有 'Gemini' 没有其他 AI 关键词，且 UP 主/赛事相关，剔除
    ai_context_kw = AI_KW + ['Gemini']
    other_ai = sum(1 for k in ai_context_kw if k in title and k != 'Gemini')
    if 'Gemini' in title and other_ai == 0:
        return False  # 仅 'Gemini' 单关键词的疑似 KPL 选手
    return has_ai_kw
```

**实测效果**：扩展 EXCLUDE_KW 后，2026-06-24 候选池 244 → 225（剔除 19 条 KPL），news TOP 10 不再混入赛事。

### 2. 硬件评测类「AI 鼠标 / AI 耳机」假阳性 — 需要 HARDWARE_KW 黑名单

**反例**：B站 `AI` query 命中 **「星闪低延迟！黑爵T520AI轻量化鼠标实测」**（UP：苹什帽，view=592，时长 62s）。这里的 "AI" 是鼠标型号名（黑爵 T520 AI 鼠标），视频内容是硬件评测，与人工智能无关。

**问题根因**：现有 EXCLUDE_KW 没有硬件产品关键词，命中 AI_KW 白名单通过过滤。

**修复 — 新增 HARDWARE_KW（必加项）**：
```python
HARDWARE_KW = [
    '鼠标', '键盘', '耳机', '音箱', '手表', '手环', '充电宝', '路由器',
    '显示器', '摄像头', '平板', '音响', '麦克风', '扩展坞',
    # 2026-06-24 实测新增：型号带 "AI" 的硬件产品
    'AI鼠标', 'AI耳机', 'AI音箱', 'AI手表', 'AI摄像头', 'AI键盘',
]
```

**用法**：
```python
def is_ai_content_real(title):
    """既不在 EXCLUDE_KW，也不在 HARDWARE_KW"""
    if any(k in title for k in EXCLUDE_KW_EVENING): return False
    if any(k in title for k in HARDWARE_KW): return False
    return True
```

**实测效果**：2026-06-24 news 候选 225 → 211（剔除 14 条硬件评测）。

### 3. 「不翻墙 / 国内免费 / 100%免费」 升级广告灌水 — 现有 EXCLUDE_KW 漏网

**反例**：2026-06-24 候选池第 10 条（按 view）`免费，不翻墙！国内真正的无限制使用ChatGPT-5.5和GPT Image2教程！手机和电脑随便用，100%免费！`（UP：ChatGPT5官方，view=496，时长 124s）。该 UP 主名 `ChatGPT5官方` 看起来权威但实际是**广告/充值引流号**。**命中的关键词 `ChatGPT` 过 AI_KW 白名单**，但实际内容是"国内免费使用教程"类灌水。

**现有 EXCLUDE_KW 漏了什么**：
- `'无需翻墙'` ← 有
- `'不翻墙'` ← **没有**
- `'国内真正的无限制'` ← **没有**
- `'100%免费'` ← **没有**
- `'白嫖'` ← **没有**
- `'免费,', '免费！'` ← **没有**
- `'国内免费'` ← 有但不够

**修复 — 扩展 SPAM_KW（必加项）**：
```python
SPAM_KW = [
    '国内免费', '无需翻墙', '不用翻墙', '不翻墙', '无需礼品卡', '一键升级', '升级订阅',
    '小白萌新', '小白无脑', '解除限制', '充值', '国内快速开通', '两个月超值',
    '低价', '团购', '优惠码', 'super grok国内快速',
    '国内真正的无限制', '100%免费', '100%成功', '白嫖', '免费,', '免费！',
    'VIP', '会员', 'token使用', 'token免费', '优惠',
    '国内使用', '如何注册', '注册教程',
]
```

**用法**（与 EXCLUDE_KW 并联过滤）：
```python
def is_ai_real_news(title):
    if any(k in title for k in EXCLUDE_KW_EVENING): return False
    if any(k in title for k in SPAM_KW): return False
    if any(k in title for k in HARDWARE_KW): return False
    return True
```

**实测效果**：2026-06-24 news 候选 211 → 204（剔除 7 条广告灌水），TOP 10 干净无广告。

### 4. 8 query → 244 候选 BVID：round 2 扩量策略（晚间档 news 凑齐 10 条关键）

**反例**：2026-06-24 20:13 CST round 1（`scripts/bing_to_bili.py` 默认 3 query + Bing 2 page）只拿到 **90 个 BVID → 9 条当日发布 → 4 条通过质量过滤**。**凑不齐 news TOP 10**。

**round 2 修复（晚间档 cron 必跑）**：
1. **Bing 多 query 扩量**：除默认 2 个 query 外，加 3 个不同主题词：
   ```bash
   # 英文主题词
   curl "https://www.bing.com/videos/search?q=GPT-5+Claude+Gemini+OpenAI+AI+trending+2026&FORM=HDRSC6" -o /tmp/bing_gpt5.html
   curl "https://www.bing.com/videos/search?q=AI+agent+LLM+Claude+latest+demo+viral&FORM=HDRSC6" -o /tmp/bing_agent.html
   curl "https://www.bing.com/videos/search?q=AI+tools+tutorial+demo+2026+latest&FORM=HDRSC6" -o /tmp/bing_tools.html
   ```
   → 多 query 共 ~300 个 BVID → 70 条 /view 成功 → 20+ 条今日发布。

2. **B站 search API 加 15 个中文 AI 复合关键词**（避开单字 query 黑名单）：
   ```python
   extra_queries = [
       "AI%E5%B7%A5%E5%85%B7",  # AI工具
       "AI%E6%95%99%E7%A8%8B",  # AI教程
       "AI%E6%B5%8B%E8%AF%84",  # AI测评
       "AI%E5%AE%9E%E6%B5%8B",  # AI实测
       "AI%E6%8A%80%E6%9C%AF",  # AI技术
       "AI%E7%AE%97%E6%B3%95",  # AI算法
       "AI%E5%88%9B%E4%B8%9A",  # AI创业
       "AI%E7%A0%94%E5%8F%91",  # AI研发
       "AI%E5%BC%80%E5%8F%91",  # AI开发
       "AI%E5%9B%BD%E5%86%85",  # AI国内
       "AI%E5%A4%A7%E6%A8%A1%E5%9E%8B",  # AI大模型
       "AI%E6%99%BA%E8%83%BD%E4%BD%93",  # AI智能体
       "AI%E7%BF%BB%E8%AF%91",  # AI翻译
       "AI%E7%BC%96%E7%A8%8B",  # AI编程
   ]
   ```
   - 每个 query 间隔 3.0s（比 round 1 的 2.5s 更稳）
   - 14/15 命中 200 OK（2026-06-24 实测）→ 280 条候选 → 与 Bing 合并后去重

3. **完整 round 2 实测漏斗**（2026-06-24 20:13 CST）：

| 阶段 | 数量 |
|------|------|
| Bing 5 query 命中 BVID | ~360 |
| B站 search API 24 query 命中 BVID | ~480 |
| 去重 | ~550 |
| B站 /view API 成功 | ~470 |
| 2026-06-24 发布 | ~317 |
| AI 关键词白名单 | ~244 |
| EXCLUDE_KW（KPL/广告/硬件）剔除 | **225** |
| 4 维质量门 + AI 严格过滤 | **TOP 10 干净** |

**结论**：晚间档 cron 必须 round 2 扩量（Bing 5 query + B站 24 query），否则 news 凑不齐 TOP 10。**round 1 的 3 query 模式已不够用**。

### 5. view 阈值上调建议（晚间档进一步收紧）

2026-06-22 建议 view ≥ 50/100，2026-06-24 实测发现 **view ≥ 100** 仍不够 — 仍有 view=435 的边缘江枫_AI日报、view=802 的苍痕Luca 早报、view=807 的阿梨Aria 早报通过。**真实有效阈值是 view ≥ 50 但配合 EXCLUDE_KW + HARDWARE_KW + SPAM_KW 三层过滤**，三者缺一不可。

**晚间档完整过滤 pipeline**（2026-06-24 验证）：
```python
news_final = [v for v in today_pool
              if datetime.fromtimestamp(v['pubdate'], CST).strftime("%Y-%m-%d") == today
              and v['view'] >= 50
              and not any(k in v['title'] for k in EXCLUDE_KW_EVENING)
              and not any(k in v['title'] for k in SPAM_KW)
              and not any(k in v['title'] for k in HARDWARE_KW)
              and looks_like_ai_strict(v['title'])]
news_top10 = sorted(news_final, key=lambda x: (-x['view'], -x['pubdate']))[:10]
```

### 6. 飞书文档写入文件名约定的延续（2026-06-24 验证仍必要）

继续遵循 2026-06-22 晚间档的 `#4` 文件名约定：
1. 写 `/Users/xiesg/.hermes/cron/output/youtube-ai-pm_2026-06-24.xml`（带时戳）
2. 同时复制到 `/Users/xiesg/.hermes/cron/output/merged_youtube-ai.xml`
3. lark-cli overwrite 后删除 merged

2026-06-24 实测 ok:true / revision_id:39 / 2 个 degrade_code=4007 warning（无害），流程通畅。

---

## ⚠️ 晚间档 20:00 CST 实测增量（2026-06-29 20:07 CST 新增 — `--today-only` 过窄 + 扩展池定型）

### 1. `--today-only` 在晚间档过窄，新闻池坍缩到 2 条

**反例**：2026-06-29 20:07 CST 跑 `scripts/bing_to_bili.py --round-2 --today-only`，最终输出 `[news] today's only: 2 videos`。原因是 B 站 search API `order=pubdate` 返回的"今天发布"内容很多其实是 18:00-23:59 之间上传、距今仅 1-4 小时的视频，**这些视频播放量还在爬坡（往往 100-1000 之间），过 4 维质量门后只剩 2 条**。

**问题诊断**：当日 19:00-20:00 之间上传播放量还在涨（upload 6h → view 通常 50-500），news 池塌缩。

**修复 — round 2 后追加"今天 + 昨天"扩展池（晚间档 cron 必跑）**：

```python
# bing_to_bili.py 输出 news 只有 2 条时，跑下面的扩展（一次性内联脚本即可）
import json, urllib.parse, urllib.request, time
from datetime import datetime, timezone, timedelta

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CST = timezone(timedelta(hours=8))

# 复用 round 2 已用的 14 个中文复合 query（避开单字 query 黑名单）
extra_queries = [
    "AI%E5%A4%A7%E6%A8%A1%E5%9E%8B", "AI%E6%B5%8B%E8%AF%84", "AI%E5%AE%9E%E6%B5%8B",
    "AI%E7%AE%97%E6%B3%95", "AI%E5%88%9B%E4%B8%9A", "AI%E5%BC%80%E5%8F%91",
    "AI%E7%BF%BB%E8%AF%91", "ChatGPT",
    "AI%E6%99%BA%E8%83%BD%E4%BD%93", "AI%E5%B7%A5%E5%85%B7", "AI%E6%8A%80%E6%9C%AF",
    "AI%E7%A0%94%E5%8F%91", "AI%E5%9B%BD%E5%86%85", "AI%E7%BC%96%E7%A8%8B",
]

# 重试被 412 节流的 query —— 2.5s 间隔，遇到 412 跳过到下一个
all_bvs, fetched = set(), []
for q in extra_queries:
    time.sleep(2.5)
    try:
        url = f"https://api.bilibili.com/x/web-interface/search/type?keyword={q}&search_type=video&order=pubdate&page=1&page_size=20"
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': 'https://search.bilibili.com/', 'Accept-Encoding': 'identity'})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read()).get('data', {}).get('result', []) or []
        for v in data:
            bv = v.get('bvid')
            if bv and bv not in all_bvs:
                all_bvs.add(bv)
    except urllib.error.HTTPError as e:
        if e.code == 412: continue
        else: continue

# 批量 /view API（0.3s sleep）
for bv in all_bvs:
    time.sleep(0.3)
    try:
        req = urllib.request.Request(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bv}",
            headers={'User-Agent': UA, 'Referer': 'https://www.bilibili.com/', 'Accept-Encoding': 'identity'})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read()).get('data', {})
        if d:
            fetched.append({'bv': bv, 'title': d.get('title',''),
                           'owner': d.get('owner',{}).get('name',''),
                           'view': d.get('stat',{}).get('view',0),
                           'duration': d.get('duration',0),
                           'pubdate': d.get('pubdate',0)})
    except: pass

# 时间窗口：今天 + 昨天
today = datetime.now(CST).strftime("%Y-%m-%d")
yesterday = (datetime.now(CST) - timedelta(days=1)).strftime("%Y-%m-%d")

# 4 层过滤（EXCLUDE_KW + SPAM_KW + HARDWARE_KW + AI_KW 白名单 + view ≥ 50）
# EXCLUDE_KW_EVENING / SPAM_KW / HARDWARE_KW / AI_KW —— 复用 2026-06-24 节

def is_ai_real(title):
    if any(k in title for k in EXCLUDE_KW_EVENING): return False
    if any(k in title for k in SPAM_KW): return False
    if any(k in title for k in HARDWARE_KW): return False
    if 'illustrator' in title.lower(): return False
    return any(k in title for k in AI_KW)

recent = []
for d in fetched:
    pd_str = datetime.fromtimestamp(d['pubdate'], CST).strftime("%Y-%m-%d")
    if pd_str in (today, yesterday) and d['view'] >= 50 and is_ai_real(d['title']):
        recent.append(d)

# 去重（按标题前 20 字）+ 排序
seen = set(); unique_recent = []
for d in sorted(recent, key=lambda x: (-x['view'], -x['pubdate'])):
    key = d['title'][:20]
    if key not in seen:
        seen.add(key); unique_recent.append(d)

news_top10 = unique_recent[:10]
```

**2026-06-29 实测漏斗**：

| 阶段 | 数量 |
|------|------|
| 14 个 round-2 复合 query 重试 | 6 个命中（8 个 412）|
| 候选 BVID 去重 | 98 |
| /view API 成功 | 98 |
| 今天 + 昨天发布 | 39 |
| 4 层过滤后 | **21** |
| 去重 + 取 TOP 10 | **10** ✅ |

**结论**：晚间档 cron 在 `bing_to_bili.py --round-2` 之后**必须再跑一次扩展池脚本**，时间窗口从"今天"放宽到"今天 + 昨天"，4 层过滤后从 2 条 → 21 条。**`--today-only` flag 在晚间档已经不够用，应视为过窄默认**。

### 2. News 标题质量二次过滤建议（晚间档补充）

即使过了 4 层过滤（EXCLUDE_KW + SPAM_KW + HARDWARE_KW + AI_KW + view ≥ 50），仍有标题内容过于单薄的视频被收录，例如：

- 「AI将会取代90%的app。」（view=286，时长 5:06，UP 晓舟报告）— 标题完整但内容浅
- 「离谱！我的设计师被开了，全能AI：一个网站全包了」（view=547，UP 花生工具箱）— 标题像软广

**建议新增质量微过滤**（可选，慎用 — 太严会过滤真实内容）：

```python
def is_substantive(title, duration):
    """标题长度 + 时长门槛 — 滤掉太短或标题过浅的视频"""
    if len(title.strip()) < 8: return False
    if duration < 60: return False
    return True
```

**但要谨慎**：`is_substantive` 太严会误杀真实 AI 日报（部分标题简短但内容扎实）。**默认不开**这层过滤；仅当 news 池 ≥ 15 且前 10 名包含明显低质内容时手动启用。

### 3. 完整晚间档 cron 流程（2026-06-29 定型）

```bash
# Step 1: round-2 跑 bing_to_bili.py（bing 5 query + bili 24 query）
python3 ~/.hermes/skills/media/video-content-workflow/scripts/bing_to_bili.py \
  --out /Users/xiesg/.hermes/cron/output/bing_to_bili.json \
  --round-2

# Step 2: 检查 news 数量（< 5 跑扩展）
python3 -c "
import json
with open('/Users/xiesg/.hermes/cron/output/bing_to_bili.json') as f:
    d = json.load(f)
print(f'round-2 news: {len(d.get(\"news\", []))}')
"

# Step 3: 若 news < 5，跑扩展池脚本（today + yesterday, view ≥ 50）
# （直接 inline execute_code 即可，每次 query 不同）

# Step 4: 用 youtube-ai-xml-build.py 生成 XML
python3 -c "
import sys, os, json
sys.path.insert(0, '~/.hermes/skills/media/video-content-workflow/templates')
from youtube_ai_xml_build import write
from datetime import datetime, timezone, timedelta
CST = timezone(timedelta(hours=8))
with open('/Users/xiesg/.hermes/cron/output/bing_to_bili.json') as f:
    data = json.load(f)
today = datetime.now(CST).strftime('%Y-%m-%d')
write(today, 'pm', long_top10=data['longs'], short_top5=data['shorts'], recent_top10=data['news'])
"

# Step 5: lark-cli 上传（同名双文件 + 写后删 merged）
cd /Users/xiesg && lark-cli docs +update --api-version v2 \
  --doc "HhyMdusqdoVcW9xLyd2c2Yc2nnf" --command overwrite \
  --content @./.hermes/cron/output/merged_youtube-ai.xml --doc-format xml
# 写后 rm merged_youtube-ai.xml

# 2026-06-29 实测：ok:true / revision_id:47 / 3 个 warning（2×4007 + 1×1017，全部无害）
```

### 4. 飞书文档写入 1017 warning 持续无害（2026-06-29 验证）

本次晚间档 cron 写入返回 3 个 warning：

```
degrade_code=4007: <docx> was escaped (×2)  ← <docx> + <body> 包装标签被 escape
degrade_code=1017: Duplicate document title was filtered  ← 多个 <title> 标签去重
```

**实测确认 1017 也是无害的**：lark-cli 自动保留第一个 `<title>` 标签，文档标题正确显示。**判断标准仍是 `ok: true` 即成功**，warning 数量从 2 个（06-24）变 3 个（06-29）不影响内容渲染。详见 SKILL.md 顶层"飞书文档写入" pitfall 1b。