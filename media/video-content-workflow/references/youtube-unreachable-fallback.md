# YouTube 不可达时的替代数据源（2026-06-01 实测，2026-06-09 修正，2026-06-10 更新，2026-06-11 晚间档修正关键词与展开按钮，2026-06-12 早间档修正 Bing 关键词实际差异，2026-06-13 早间档修正 06:00 CST 早报空窗）

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

### 数据提取方式（2026-06-11 实测修正：aria-label 路径最优）

✅ **2026-06-11 实测**：`browser_console` 走 `aria-label` 路径完全可用且最稳定。每条视频卡片是一个带 `aria-label` 的 `<a>`，标签文本用 `·` 分隔，结构固定：

```javascript
// 抓所有视频卡片（约 20-30 条 / 页）
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

**关键发现**：
- `a.textContent` 仍可能为空（Bing 用 Shadow DOM / 虚拟列表），**但 `aria-label` 是真实的**——无障碍标签不会被覆盖。
- `a.href` 是 `https://www.bing.com/videos/riverview/relatedvideo?q=...`（Bing 相关视频查看器），**无法跳到 YouTube 原页**。
- **XML 链接用 Bing search URL 替代**：`https://www.bing.com/videos/search?q={urlquote(title)}`（与 2026-06-10 早间档格式一致），用户点击后在 Bing 搜到原视频。

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
