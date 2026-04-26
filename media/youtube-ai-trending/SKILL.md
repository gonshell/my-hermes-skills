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
- **长视频 TOP 5**：从最新发布中按播放量排序
- **短视频 TOP 3**：从最新发布中按播放量排序
- 参考来源频道：`https://www.youtube.com/@AIDailyBrief/videos`

## 搜索URL模板

```
# 最热门长视频（本周上传）
https://www.youtube.com/results?search_query=AI+news+OR+LLM+OR+GPT+OR+ChatGPT+OR+Claude&sp=CAE%253D

# 最热门短视频
https://www.youtube.com/results?search_query=AI+OR+artificial+intelligence

# AI Daily Brief频道（最新视频）
https://www.youtube.com/@AIDailyBrief/videos
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

长视频数据提取：
```javascript
Array.from(document.querySelectorAll('ytd-video-renderer')).slice(0, 20).map((v, i) => {
  const titleEl = v.querySelector('#video-title');
  const title = titleEl?.textContent?.trim() || '';
  const link = titleEl?.href || '';
  const spans = v.querySelectorAll('#metadata-line span');
  const metadata = Array.from(spans).map(s => s.textContent).join(' · ');
  const channel = v.querySelector('#channel-name a')?.textContent?.trim() || '';
  return {i, title, link, metadata, channel};
}).filter(v => v.title && v.link)
```

短视频数据提取：
```javascript
Array.from(document.querySelectorAll('ytd-rich-item-renderer')).slice(0, 15).map((v, i) => {
  const title = v.querySelector('#video-title')?.textContent?.trim() || v.querySelector('a#video-title')?.textContent?.trim() || '';
  const link = v.querySelector('#video-title, a#video-title')?.href || '';
  const views = v.querySelector('#metadata-line span')?.textContent || '';
  const channel = v.querySelector('#channel-name a, ytd-channel-name a')?.textContent?.trim() || '';
  return {i, title, link, views, channel};
}).filter(v => v.title)
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

**已验证可用的备选方案**：

1. **使用 `最近アップロードされた動画` 标签**（推荐）：
   - 在搜索结果页面点击"最近アップロードされた動画"标签获取最新上传
   - 该标签下的视频仍使用 `ytd-video-renderer`，可正常提取
   - Shorts 在这个标签下会显示为 `/shorts/` 链接但仍用 `ytd-video-renderer` 渲染

2. **从搜索结果「すべて」标签提取含Shorts链接的视频**：
   - 使用主搜索结果页（不过滤Shorts）提取所有 `ytd-video-renderer`
   - 过滤出 `/shorts/` 链接的视频，手动记录播放量
   - 示例JS：
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
  .filter(v => v.title && (v.isShort || v.link.includes('/watch?')))
```

3. **Shorts 页面备选方案**（数据质量较低）：
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

3. **滚动加载后提取**：
   - Shorts 页面需要滚动触发懒加载
   - 可用 `browser_scroll(direction='down')` 后等待再提取

## 摘要生成
根据视频标题和描述生成2-3句话的简单摘要，说明视频主要内容。

## ⚠️ YouTube 不可用时的备选方案

**问题**：YouTube 在某些网络环境下会完全无法访问（`ERR_CONNECTION_TIMED_OUT`），此时需要切换到备选数据源。

**备选方案：Bing视频搜索 + Bilibili AI早报**

### 步骤1：Bing视频搜索获取热门AI视频
```
URL: https://www.bing.com/videos/search?q=AI+2026+trending+video+GPT+Claude+OpenAI
```
从搜索结果中提取：
- 视频标题
- 播放量
- 发布平台（Bilibili等）
- 视频URL

### 步骤2：直接从Bilibili AI早报获取完整新闻
推荐订阅的AI早报UP主（每日更新，质量高）：
- **苍痕Luca** — AI早报系列，每日更新，覆盖OpenAI/Claude/DeepSeek等全领域
  - https://space.bilibili.com/3546884010412559/channel/collectiondetail?sid=7968947
- 典型视频标题格式：`【AI早报 2026-04-25】DeepSeek 开源 1.6T 参数｜OpenAI 发布 GPT-5.5｜Claude Code 质量翻身`

### 步骤3：从视频描述提取完整新闻
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
2. Bing视频搜索（YouTube不可用时的次选）
3. Bilibili AI早报（新闻最完整，可直接提取当日热点）

### 已知有效备选URL
```
# Bing视频搜索
https://www.bing.com/videos/search?q=AI+2026+trending+video+GPT+Claude+OpenAI

# Bilibili AI早报合集
https://space.bilibili.com/3546884010412559/channel/collectiondetail?sid=7968947

# 直接获取最新一期AI早报
https://www.bilibili.com/video/BV1BLoSByEoU/  (2026-04-25期)
```
