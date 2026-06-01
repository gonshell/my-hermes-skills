# youtube-ai-trending 参考（2026-05-31 更新）

## 搜索URL模板

```bash
# 最热门长视频（本周上传，长视频过滤器）
https://www.youtube.com/results?search_query=AI+news+OR+LLM+OR+GPT+OR+ChatGPT+OR+Claude&sp=CAE%253D

# 最热门短视频（混合流，不加过滤器）
https://www.youtube.com/results?search_query=AI+news+OR+LLM+OR+GPT+OR+ChatGPT+OR+Claude
```

## 已失效URL（不要使用）

- `sp=CAI%253D`（按最新排序）— 无法通过 URL 直接访问
- `@AIDailyBrief/videos` 频道页 — `titleEl.href` 返回空字符串

## 数据提取 JS（长视频）

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
}).filter(v => v.title && v.link && !v.isShort)
```

## 数据提取 JS（短视频）

必须从 Shorts 标签页提取，使用 `ytd-video-renderer`：

```javascript
Array.from(document.querySelectorAll('ytd-video-renderer'))
  .map(v => {
    const titleEl = v.querySelector('#video-title');
    const link = titleEl?.href || '';
    return {
      title: titleEl?.textContent?.trim() || '',
      link,
      isShort: link.includes('/shorts/'),
      metadata: Array.from(v.querySelectorAll('#metadata-line span')).map(s => s.textContent).join(' · '),
      channel: v.querySelector('#channel-name a')?.textContent?.trim() || ''
    };
  })
  .filter(v => v.title && v.isShort)
  .slice(0, 10)
```

> ⚠️ Shorts 渲染器中 `channel-name` 可能为空（本 session 实测短视频均无频道名），写入 XML 时留空。

## isShort 过滤规则

```javascript
// 正确 ✅
.filter(v => v.title && v.link && !v.isShort)

// 错误 ❌
.filter(v => v.title && v.link && !v.link.includes('/shorts/'))
```

## 标签页切换（2026-05-31 实测）

YouTube 搜索页有三个关键标签：
- `全部`（默认）→ 执行长视频 JS，过滤 `!v.isShort`
- `Shorts`（ref=e132）→ 执行短视频 JS，过滤 `v.isShort`
- `最近上传`（ref=e136）→ 执行长视频 JS，过滤时间戳含"分钟"或"小时"

**切换标签页后必须重新执行 JS**，不能复用上一个标签页的数据。

## 新发布视频获取策略（2026-05-31 更新）

`最近上传` 标签页配合 `sp=CAE%253D`（长视频过滤器）URL 效果更好，可发现"全部"标签页未出现的最新长视频：

```bash
# 正确：用长视频过滤器 URL 打开搜索，再切换"最近上传"标签
https://www.youtube.com/results?search_query=AI+news+OR+LLM+OR+GPT+OR+ChatGPT+OR+Claude&sp=CAE%253D
```

切换到"最近上传"标签后执行长视频 JS，再过滤含"分钟"或"小时"的条目。
`全部` 标签页使用同样 URL，执行长视频 JS 过滤 `!v.isShort`，从中筛选时间戳含"分钟/小时"的条目作为补充。

## 新发布视频数量预期

注意：YouTube 本周新发 AI 视频实际数量很少，"最近上传"标签通常只返回 4-6 条，
即使配合"全部"标签页补充也难以凑满 10 条。**不要强行凑数**，以实际获取量为准，
标注当日新发视频实际条目数即可。

## 页面滚动与渲染注意事项

YouTube 搜索结果为懒加载（lazy render），但 `ytd-video-renderer` 在 DOM 中数量有限（20-30条）。
滚动页面**不会触发更多视频渲染器加载**——已加载的渲染器数量在首次 JS 执行时已固定。
如需获取更多结果，需访问第二页或使用其他搜索词。

## 最近上传时间过滤

```javascript
// 在长视频 JS 结果上追加过滤
.filter(v => v.metadata.match(/分钟|小时/))
```

时间戳示例：`"4.4万次观看 · 1天前"`（不含分钟/小时）不匹配，`"2415次观看 · 15小时前"` 匹配。

注意：该标签页通常只返回 4-6 条，是获取当日最新视频的补充方式。如需凑满 TOP 10，需配合 "全部" 标签页中时间戳含"分钟"或"小时"的条目补充。

## 飞书文档写入

```bash
cd /Users/xiesg && lark-cli docs +update --api-version v2 \
  --doc "<doc_id>" --command overwrite \
  --content @./.hermes/cron/output/youtube-ai-am_YYYY-MM-DD.xml --doc-format xml
```

早间档文档 token：`EbHDdKARYo4vEExQiNGc3qiGnSe`

## cronjob 路径偏移

> ⚠️ `os.path.expanduser("~/.hermes/cron/output/")` 在 cronjob 中展开为 `/Users/xiesg/.hermes/home/.hermes/cron/output/`（错误路径）。

**必须使用硬编码绝对路径**：
```python
output_dir = "/Users/xiesg/.hermes/cron/output/"
```

## 文件名约定

- 早间档：`youtube-ai-am_YYYY-MM-DD.xml`（am 前缀）
- 晚间档：`youtube-ai-pm_YYYY-MM-DD.xml`（pm 前缀）
- 下划线连接日期，不用空格

## 网络不可用降级（2026-06-01 更新）

YouTube 在国内网络可能完全不可达：
- `curl` 返回 0 字节（非超时，而是连接被重置）
- `browser_navigate` 超时（60s），浏览器守护进程也可能未启动
- 同步检测：`github.com` 也不可达时，确认是整体出口问题而非 YouTube 单独限制

**降级流程**（优先使用替代数据源，见完整指南）：
1. 快速检测网络：`curl -s --max-time 10 -o /dev/null -w "%{http_code}" "https://www.youtube.com"` → HTTP 000 即不可达
2. **优先**：用 Bing 视频搜索 + Bilibili 搜索获取真实数据填充报告
3. **其次**：查找当日早间档文件复用
4. **最后**：生成「数据获取失败」占位 XML 上传飞书
5. **不要反复重试浏览器访问 YouTube**（每次 60s 超时 × N = 浪费大量时间）

> 完整替代数据源策略见 `<references/youtube-unreachable-fallback.md>`