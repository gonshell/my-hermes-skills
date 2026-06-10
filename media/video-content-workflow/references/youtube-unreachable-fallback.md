# YouTube 不可达时的替代数据源（2026-06-01 实测，2026-06-09 修正，2026-06-10 更新）

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

### 数据提取方式（2026-06-10 实测修正）

⚠️ **Bing 视频搜索页 `a.textContent` 返回空字符串** — 即使用 `browser_console` 抓 `document.querySelectorAll('main a')` 拿到的 `textContent` 字段全部是空，无法通过 JS 提取出标题/播放量/时长/频道。可能是 Bing 用 Shadow DOM 或动态渲染注入文本。`browser_console` 走 JS 路径行不通。

**正确流程**：直接读 `browser_snapshot` 输出的可访问性树文本，再正则解析：

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

> **不要尝试 Bing 视频搜索的 RSS feed**：`/videos/feed?format=rss` 会 301 到 `cn.bing.com` 然后被改写成 HTML 搜索页，不会返回 RSS。用 `browser_navigate` + `browser_console` 走 HTML 路径。

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
