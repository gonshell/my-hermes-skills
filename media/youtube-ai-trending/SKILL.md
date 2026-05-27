---
name: youtube-ai-trending
description: 获取YouTube上AI领域的热门视频和当日新发视频，返回标题、URL、播放量、简单摘要。使用browser工具从YouTube搜索页面和频道页面提取数据。
triggers:
  - 获取今日热门AI视频
  - YouTube AI视频排行
  - AI领域热门长视频/短视频
  - 当天新发AI视频
---

# YouTube AI 热门视频获取

## 功能说明
获取YouTube上AI领域的热门视频和当日新发视频，返回标题、URL、播放量、简单摘要。

## 数据分类

### 1. 最热门长视频 TOP 10
- 搜索词：`AI news OR LLM OR GPT OR ChatGPT OR Claude`
- 过滤器：长视频（sp=CAE%253D）
- 按播放量排序

### 2. 最热门短视频 TOP 5
- 搜索词：`AI OR artificial intelligence`
- 点击"Shorts"标签
- 按播放量排序

### 3. 当日新发热门视频
**实际做法**：使用同一最热门长视频搜索页（`sp=CAE%253D`），通过 JS 提取后**按发布时间过滤**（如 "7小时前"、"19小时前"），无需切换 tab 或重新加载页面。YouTube 的搜索结果默认混合了热门和较新视频，7小时内上传的视频也会出现在其中。

- **长视频 TOP 5**：从最热门搜索结果中过滤发布时间在24小时内的视频，按播放量排序
- **短视频 TOP 3**：从混合搜索页「すべて」标签过滤 `/shorts/` 链接，按播放量排序
- 参考搜索页：`https://www.youtube.com/results?search_query=AI+news+OR+LLM+OR+GPT+OR+ChatGPT+OR+Claude&sp=CAE%253D`

**注意**：
- `sp=CAI%253D`（按最新排序）在浏览器中**无法通过 URL 直接访问**，会停留在默认排序，无法作为备选
- 直接访问 `@AIDailyBrief/videos` 频道页时，`titleEl.href` 返回空字符串（链接丢失），不要使用频道页提取新上传视频
- 推荐做法：对最热门搜索页的 JS 提取结果按 `metadata` 中的时间字符串（如 "7小时前"）筛选即可获得新发布视频

## 搜索URL模板

```
# 最热门长视频（本周上传）
https://www.youtube.com/results?search_query=AI+news+OR+LLM+OR+GPT+OR+ChatGPT+OR+Claude&sp=CAE%253D

# 最热门短视频（混合流，不过滤Shorts，同一页面提取长+短）
https://www.youtube.com/results?search_query=AI+news+OR+LLM+OR+GPT+OR+ChatGPT+OR+Claude
```

**⚠️ 已失效的 URL（不要使用）：**
- `sp=CAI%253D`（按最新排序）— 无法通过 URL 直接访问，会停留在默认热门排序
- `@AIDailyBrief/videos` 频道页 — `titleEl.href` 返回空字符串，导致所有 watch URL 全部丢失

**JS 过滤长视频的正确写法（重要）：**
从混合搜索页同时提取长视频+短视频时，必须用 `!isShort` 布尔标志过滤，不能只依赖 `!link.includes('/shorts/')`：
```javascript
// 错误 ❌ — 可能在某些YouTube变体下误判
.filter(v => v.title && v.link && !v.link.includes('/shorts/'))

// 正确 ✅ — 使用明确的 isShort 标志
.filter(v => v.title && v.link && !v.isShort)
```

## 输出格式

```
📊 一、最热门长视频 TOP 10

1. 视频标题
   播放量：XXX | 发布时间 | 频道名
   https://youtube.com/watch?v=VIDEO_ID

...

📊 二、最热门短视频 TOP 5

1. 视频标题
   播放量：XXX
   https://youtube.com/shorts/VIDEO_ID

...

📊 三、当天新发热门视频

### 长视频 TOP 5
1. 视频标题
   播放量：XXX | 发布时间 | 频道名
   https://youtube.com/watch?v=VIDEO_ID

### 短视频 TOP 3
1. 视频标题
   播放量：XXX
   https://youtube.com/shorts/VIDEO_ID

---

📝 摘要说明
- 当前热门主题分析
- 关键趋势总结
```

## 链接显示注意事项
⚠️ 飞书消息中Markdown表格格式会导致链接无法点击显示，必须使用纯文本格式发送链接。

## 数据提取方法（重要）

⚠️ `browser_snapshot` 和 `browser_snapshot(full=true)` 会因页面内容过长而被截断（通常在 ~310 行处），不适合用于提取 10+ 条视频数据。

**推荐方法：使用 `browser_console` 执行 JavaScript 提取**

长视频数据提取（同时产出 isShort 标志，供后续过滤复用）：
```javascript
Array.from(document.querySelectorAll('ytd-video-renderer')).slice(0, 20).map((v, i) => {
  const titleEl = v.querySelector('#video-title');
  const title = titleEl?.textContent?.trim() || '';
  const link = titleEl?.href || '';
  const isShort = link.includes('/shorts/');
  const spans = v.querySelectorAll('#metadata-line span');
  const metadata = Array.from(spans).map(s => s.textContent).join(' · ');
  const channel = v.querySelector('#channel-name a')?.textContent?.trim() || '';
  return {i, title, link, isShort, metadata, channel};
}).filter(v => v.title && v.link && !v.isShort)  // 过滤掉短视频
```

短视频数据提取：
⚠️ `ytd-rich-item-renderer` 在搜索结果页的 Shorts 标签下返回空数组（2026年4月亲测）。必须使用下面的方案1或方案2。

短视频数据仍可用同一搜索页「すべて」标签的JS提取（过滤 `/shorts/` 链接即可），无需切换到「ショート」tab。示例JS：
```javascript
Array.from(document.querySelectorAll('ytd-video-renderer'))
  .map(v => {
    const titleEl = v.querySelector('#video-title');
    const link = titleEl?.href || '';
    const isShort = link.includes('/shorts/');
    return {
      title: titleEl?.textContent?.trim() || '',
      link,
      isShort,
      metadata: Array.from(v.querySelectorAll('#metadata-line span')).map(s => s.textContent).join(' · ')
    };
  })
  .filter(v => v.title && v.isShort)
  .slice(0, 10)
```

## 提取字段
- 标题（title）
- URL（完整watch链接）
- 播放量（viewCount，格式如3.1M、104K）
- 发布时间（relative time，如23小时前、3天前）
- 频道名（channel name）

## 短视频数据提取 - 技术注意事项

⚠️ **已知问题（重要）**：YouTube Shorts 页面的 `ytd-rich-item-renderer` 元素在 DOM 中存在，但 `browser_console` 执行 JS 时，`#video-title`、`yt-formatted-string#title` 等选择器可能返回空字符串（YouTube 对 Shorts 使用了不同的渲染机制）。

**更严重的问题**：`a[href*="/shorts/"]` 配合 `img.alt` 在 Shorts 页面会返回 `"true"` 字符串而非真实标题，因为 YouTube Shorts 的 img 标签 `alt` 属性值就是 `"true"`。

**已验证可用的备选方案（按可靠性排序）**：

1. **搜索结果页「ショート」tab（最可靠）** ✅
   - 点击页面内 tab 区域的「ショート」tab（ref=e11 附近），而不是顶部导航的「ショート」链接
   - 点击后会加载 Shorts 内容，仍使用 `ytd-video-renderer` 渲染，可正常提取
   - 提取JS：
```javascript
Array.from(document.querySelectorAll('ytd-video-renderer'))
  .map(v => {
    const titleEl = v.querySelector('#video-title');
    const link = titleEl?.href || '';
    const isShort = link.includes('/shorts/');
    return {
      title: titleEl?.textContent?.trim() || '',
      link,
      isShort,
      metadata: Array.from(v.querySelectorAll('#metadata-line span')).map(s => s.textContent).join(' · ')
    };
  })
  .filter(v => v.title && v.isShort)
  .slice(0, 10)
```

1. **搜索结果页「ショート」tab（最可靠）** ✅
   - 点击页面内 tab 区域的「ショート」tab（ref=e11 附近），而不是顶部导航的「ショート」链接
   - 点击后会加载 Shorts 内容，仍使用 `ytd-video-renderer` 渲染，可正常提取
   - 提取JS：
```javascript
Array.from(document.querySelectorAll('ytd-video-renderer'))
  .map(v => {
    const titleEl = v.querySelector('#video-title');
    const link = titleEl?.href || '';
    const isShort = link.includes('/shorts/');
    return {
      title: titleEl?.textContent?.trim() || '',
      link,
      isShort,
      metadata: Array.from(v.querySelectorAll('#metadata-line span')).map(s => s.textContent).join(' · ')
    };
  })
  .filter(v => v.title && v.isShort)
  .slice(0, 10)
```

2. **从搜索结果「すべて」标签过滤 Shorts（次选，有时为空）** ⚠️
   - 使用主搜索结果页（不过滤Shorts）提取所有 `ytd-video-renderer`
   - 过滤出 `/shorts/` 链接的视频
   - **2026-05 实测**：有时「すべて」页面的 `ytd-video-renderer` 元素中完全不包含 `/shorts/` 链接，导致过滤结果为空。此时必须回退到方案1（点击 Shorts tab）
   - **但若返回非空结果，则此方案效率最高** — 可在同一次 JS 提取中同时获得长视频（`!isShort`）和短视频（`isShort`），无需切换 tab
   - 验证方法：运行 JS 后检查 `filter(v => v.isShort)` 是否返回 ≥3 条；若少于 3 条立即切换方案1
   - 提取JS：
```javascript
Array.from(document.querySelectorAll('ytd-video-renderer'))
  .map(v => {
    const titleEl = v.querySelector('#video-title');
    const link = titleEl?.href || '';
    const isShort = link.includes('/shorts/');
    return {
      title: titleEl?.textContent?.trim() || '',
      link,
      isShort,
      metadata: Array.from(v.querySelectorAll('#metadata-line span')).map(s => s.textContent).join(' · ')
    };
  })
  .filter(v => v.title && v.isShort)
  .slice(0, 10)
```

3. **从搜索结果「すべて」标签过滤 Shorts（已不可靠）** ⚠️
   - 使用主搜索结果页提取所有 `ytd-video-renderer`，过滤 `/shorts/` 链接
   - **2026年5月实测**：热门排序页（`sp=CAE%253D`）和默认排序页均可能返回 0 条 shorts。YouTube 可能已调整搜索结果渲染逻辑
   - 提取JS见上方「短视频数据提取」部分，但务必准备回退到方案1

4. **Shorts 页面备选方案**（数据质量较低）：
   - 滚动触发懒加载后，使用 `a[href*="/shorts/"]` 提取链接
   - 标题只能依赖 DOM 中可见文本或截断显示，无法获取完整标题
   - 备选JS：
```javascript
Array.from(document.querySelectorAll('a[href*="/shorts/"]'))
  .filter(a => {
    const href = a.href;
    return href.includes('/shorts/') && href.length > 30 && !href.includes('&list=');
  })
  .map(a => ({
    link: a.href.split('&')[0],
    text: a.textContent?.trim() || a.innerText?.trim() || 'Shorts'
  }))
```

**已知失效方案（2026年4月亲测）**：
- `ytd-rich-item-renderer` 在搜索结果页的 Shorts 标签下返回空数组
- `a[href*="/shorts/"]` 配合 `img.alt` 在 Shorts 页面返回 `"true"` 而非真实标题
- 顶部导航的「ショート」链接会跳转到独立的 Shorts 主页，体验不同于搜索结果内的 Shorts 标签
- 直接访问 YouTube 频道页（如 `@AIDailyBrief/videos`）时，`titleEl.href` 返回空字符串，导致提取的 watch URL 全部丢失

## 摘要生成
根据视频标题和描述生成2-3句话的简单摘要，说明视频主要内容。

## ⚠️ YouTube 不可用时的备选方案

**问题**：YouTube 在某些网络环境下会完全无法访问，此时需要切换到备选数据源。

**触发条件**：任何导致 YouTube 搜索页无法加载的网络错误都应触发 fallback，包括但不限于 `ERR_CONNECTION_TIMED_OUT`、`ERR_EMPTY_RESPONSE`（本 session 实测）、`ERR_NETWORK_CHANGED` 等。判断标准是 `browser_navigate` 返回 `false`，而不是特定的错误字符串。

**备选方案：Bing视频搜索 + Bilibili 搜索结果页 + Bilibili AI早报**

### 备选方案：Bilibili 搜索结果页（首选） + Bing视频搜索（次选）

#### Bilibili 搜索结果页（首选备选）✅
Bilibili 搜索列表页**渲染完整、结构清晰**，是 YouTube 不可用时的最佳数据源。

**关键发现（2026-05 实测）**：
- `browser_console` JS 提取在 Bilibili 搜索页**部分有效** — `a[href*="/video/BV"]` 选择器可提取 BV URL 和文本
- `browser_click` 在 Bilibili 搜索页**不会真正导航**（点击成功但快照仍停留在搜索页）
- `browser_snapshot`（compact 模式）的快照中**已包含完整结构化数据**（标题、频道名、播放量、相对时间）
- 从快照中配合 BV 链接 JS 提取是**最可靠方式**

URL：`https://search.bilibili.com/video?keyword=AI+LLM+GPT+Claude+OpenAI+trending+2026`

**BV URL + 标题 JS 提取（实测有效）**：
```javascript
Array.from(document.querySelectorAll('a[href*="/video/BV"]'))
  .map(a => ({href: a.href.split('?')[0], text: a.innerText?.trim() || a.textContent?.trim()}))
  .filter(v => v.href && v.text && v.text.length > 5 && !v.text.includes('万') && !v.text.includes('://'))
```

#### Bing视频搜索（次选）⚠️
Bing视频搜索的 `browser_console` JS 提取几乎无法获取结构化数据（视频项），Bing的视频链接指向外部平台而非站内播放页。**此源数据有限**，主要价值是确认热门话题方向。

```
URL: https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+OpenAI+trending+May+2026
```

#### 步骤3：直接从Bilibili AI早报视频描述提取完整新闻（可选增强）
如果需要更完整的新闻列表，可以尝试进入 AI早报 视频详情页：
- 搜索：`https://search.bilibili.com/video?keyword=AI早报+YYYY-MM-DD`
- 从结果列表中找对应日期的视频（如 `苍痕Luca · 05-22`）
- 点击进入详情页，从页面描述提取完整新闻列表

⚠️ **已知问题**：直接 `browser_navigate` 到 bilibili 视频 URL 有时返回"出错啦!"页面，但从搜索结果点击进入则正常。这是因为 bilibili 对直接URL访问有登录态检查，而搜索来源的点击带 referrer 头。
推荐订阅的AI早报UP主（每日更新，质量高）：
- **苍痕Luca** — AI早报系列，每日更新，覆盖OpenAI/Claude/DeepSeek等全领域
  - https://space.bilibili.com/3546884010412559/channel/collectiondetail?sid=7968947
- 典型视频标题格式：`【AI早报 2026-04-25】DeepSeek 开源 1.6T 参数｜OpenAI 发布 GPT-5.5｜Claude Code 质量翻身`

⚠️ **已知问题**：`browser_navigate` 直接访问频道合集页（collectiondetail）无法正确渲染视频列表（返回空内容）。**解决方案**：改用已知有效的最新一期AI早报直接视频URL（如 `https://www.bilibili.com/video/BV1BLoSByEoU/`），页面可正常加载并显示视频描述中的完整新闻列表。

### 步骤4：直接从Bilibili AI早报视频描述提取完整新闻（需视频页可播放）
Bilibili AI早报视频描述包含完整的新闻列表，格式例如：
```
📰 新闻：
00:04 Google 官方披露：公司 75% 的新代码由 AI 生成
00:42 Moonshot Kimi K2.6 开源并登陆 Perplexity
01:23 GPT-5.5 "Spud" 从 Codex CLI dropdown 意外泄露
...
🎙 播客推荐：
09:31 How Anthropic's product team moves faster than anyone else
```

### 备选数据源优先级
1. YouTube（优先，数据最全面）
2. Bilibili 搜索结果页（YouTube不可用时的首选 — 列表页可正常渲染，数据完整）
3. Bing视频搜索（次选，混合多平台，质量参差）
4. Bilibili AI早报（新闻最完整，但依赖视频页可播放）

### 已知有效备选URL
```
# Bilibili 搜索结果页（推荐首选备选）
https://search.bilibili.com/video?keyword=AI%E6%97%A9%E6%8A%A5+YYYY-MM-DD

# Bing视频搜索（推荐加 May/2026 等时间词提高相关性）
https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+OpenAI+trending+May+2026

# ⚠️ 频道合集页已失效 — 直接访问返回空内容，不要使用
https://space.bilibili.com/3546884010412559/channel/collectiondetail?sid=7968947
```

**获取当日期号AI早报的正确方法（重要）**：

⚠️ AI早报视频的 BV号 不是固定的，每期不同。**不要 hardcode BV号**，必须通过搜索获取：

1. 搜索：`https://search.bilibili.com/video?keyword=AI早报+YYYY-MM-DD`（URL编码中文）
2. 从搜索结果列表中找到对应日期的视频（如 `苍痕Luca · 05-18`）
3. 点击链接进入视频页面，从页面右侧推荐列表可获取更多当期内容

**备选**：如果知道UP主名称（如 `苍痕Luca`），也可直接搜索 `site:bilibili.com 苍痕Luca AI早报 2026-05-18`

⚠️ **已知问题**：直接 `browser_navigate` 到 bilibili 视频 URL 有时返回"出错啦!"页面，但从搜索结果点击进入则正常。这是因为 bilibili 对直接URL访问有登录态检查，而搜索来源的点击带 referrer 头。

## 飞书推送工作流

定时任务场景下，将数据写入飞书文档并发送通知的完整流程见：
[`references/youtube-ai-trending-feishu-workflow.md`](references/youtube-ai-trending-feishu-workflow.md)

### 飞书消息发送要点（关键Pitfall）

发送文本消息到群聊时，**必须用 `--text` 而非 `--content`**：
```bash
# 错误 ❌ — --content 要求 JSON 格式 {"text":"..."}
lark-cli im +messages-send --chat-id "oc_xxx" --content "纯文本消息" --msg-type text

# 正确 ✅ — --text 直接接收纯文本
lark-cli im +messages-send --chat-id "oc_xxx" --text "纯文本消息" --msg-type text
```

查询群ID：先 `lark-cli im chats list` 获取 bot 所在群列表，取 `chat_id` 字段。

### lark-cli docs +update 参数说明

```bash
# 正确 ✅
lark-cli docs +update --api-version v2 \
  --doc "TBEddfdvQogBTxx9HArceKmlnYd" \
  --command append \          # 注意是 --command，不是 --mode
  --content @./lark_content.xml

# --mode append 是旧版 v1 参数；v2 API 必须用 --command
```

⚠️ **已知问题（2026-05 亲测）**：`--mode append` 在 v2 API 下报错 `unknown flag`，必须用 `--command append`。

### Shorts 排名说明

⚠️ Shorts 标签页的 `ytd-video-renderer` 渲染结果**按总播放量排序，而非发布时间**。提取的 Shorts TOP 5 通常是发布数月前的爆款内容（如 7-9 个月前的视频仍排第一），不代表近期新发。内容新鲜度参考价值有限。真正的"当天新发热门短视频"建议从长视频搜索页的混合流中过滤 `/shorts/` 链接获取（见 SKILL.md 主文方案 2/3）。
