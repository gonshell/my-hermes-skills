# YouTube 搜索 sp 参数速查（2026-06-17）

## 已验证的 sp 值

| sp 值 | 用途 | 适用场景 |
|--------|------|----------|
| `CAMSAhAB` | 按播放量排序（最热门） | 获取"最热门长视频 TOP 10" |
| `CAISBAgCEAE%3D` | 本周上传 + 仅视频（排除频道/播放列表） | 补充本周热门 |
| `EgIYAg%3D%3D` | 仅 Shorts | 获取"最热门短视频 TOP 5" |
| `CAE%253D` | 长视频过滤（>20分钟） | 过滤长视频 |
| `CAMSBAgEEAE%253D` | 本周上传（按日期排序） | 获取本周新发视频 |

## 推荐搜索组合

### 获取"最热门长视频 TOP 10"
```
URL: https://www.youtube.com/results?search_query=artificial+intelligence+2026&sp=CAMSAhAB
关键词: artificial intelligence 2026
```
- 按播放量全局排序，取前 10 条长视频
- 用 `browser_console` 提取，过滤掉 `/shorts/` 链接

### 获取"最热门短视频 TOP 5"
```
URL: https://www.youtube.com/results?search_query=AI+artificial+intelligence+2026&sp=EgIYAg%3D%3D
关键词: AI artificial intelligence 2026
```
- Shorts 标签页，取前 5 条
- 注意：Shorts 渲染器中 channel-name 可能为空

### 获取"当日新发热门视频 TOP 10"
```
URL: https://www.youtube.com/results?search_query=artificial+intelligence+2026&sp=CAISBAgCEAE%3D
关键词: artificial intelligence 2026
```
- 本周上传 + 仅视频，按相关性排序
- 再按时间戳过滤（含"分钟"或"小时"的条目）

## 备用关键词

当主关键词结果不足时，补充搜索：
- `ChatGPT Claude GPT LLM Gemini AI 2026`
- `AI agent tools machine learning 2026`
- `Google I/O Apple WWDC Microsoft Build AI 2026`

## Web 搜索工具降级策略

当 web_search / SearXNG / GLM 等搜索工具全部失败（rate limit、502、API key 未配置）时：
1. **直接用 `browser_navigate` 打开 YouTube 搜索页**，不依赖外部搜索 API
2. 用 `browser_console` 执行 JS 提取数据
3. 多次搜索不同关键词 + `sp` 参数组合来覆盖三个分类
4. 合并去重后按播放量排序

## 数据提取 JS（2026-06-17 优化版）

比旧版多提取 duration 和 upload 字段，结构更清晰：

```javascript
const videos = [];
const videoElements = document.querySelectorAll('ytd-video-renderer');
videoElements.forEach(el => {
  const titleEl = el.querySelector('#video-title');
  const viewCountEl = el.querySelector('#metadata-line span:first-child');
  const channelEl = el.querySelector('#channel-name a');
  const durationEl = el.querySelector('#text.ytd-thumbnail-overlay-time-status-renderer');
  const uploadEl = el.querySelector('#metadata-line span:nth-child(2)');
  
  if (titleEl) {
    videos.push({
      title: titleEl.textContent?.trim(),
      href: titleEl.href,
      views: viewCountEl?.textContent?.trim(),
      channel: channelEl?.textContent?.trim(),
      duration: durationEl?.textContent?.trim(),
      upload: uploadEl?.textContent?.trim()
    });
  }
});
JSON.stringify(videos.slice(0, 20), null, 2);
```

> **字段说明**：
> - `views`: 如 "3593万次观看" 或 "6.1万次观看"
> - `duration`: 如 "13:33" 或 "2:18:00"（从缩略图覆盖层提取，比 metadata 更可靠）
> - `upload`: 如 "23小时前" 或 "3周前"（从 metadata-line 第二个 span 提取）
> - `channel`: 如 "NVIDIA" 或 "AI Revolution"

## 注意事项

1. **`browser_snapshot` 截断问题**：snapshot 超过 ~310 行会被截断，不适用于提取 10+ 条数据。**必须用 `browser_console` 执行 JS**。
2. **页面懒加载**：YouTube 搜索结果为懒加载，`ytd-video-renderer` 数量在首次 JS 执行时已固定（20-30 条）。滚动不会加载更多。
3. **views 字段清洗**：`viewCountEl?.textContent?.trim()` 可能包含频道名等噪声（如 "NVIDIA\n  \n  \n    NVIDIA\n  \n\n\n\n\n\n    •\n    \n  \n  \n    \n    \n    •\n    \n      3593万次观看"），需要在后续处理中用正则提取纯播放量数字。
4. **Shorts 无频道名**：Shorts 渲染器中 `#channel-name a` 通常为空，写入 XML 时可留空或用频道 URL 推断。
