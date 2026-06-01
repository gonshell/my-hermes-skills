# bilibili-ai-trending 参考（2026年5月实测）

## 数据源方案（已确认）

### search/type API — **完全废弃，返回 HTTP 412**

> ⚠️ **结论（2026-05-30 实测）**：`https://api.bilibili.com/x/web-interface/search/type` 对**所有关键词**均返回 HTTP 412，无论英文/中文/长/短。
>
> 旧版参考文档（称部分关键词可用）**已过时**，不要依赖 search API。

### 替代方案：从排行榜 API + AI 关键词过滤

```bash
GET https://api.bilibili.com/x/web-interface/ranking/v2?type=all
```
- 返回 `data.list`，100条，按综合得分排序
- **按 AI 关键词过滤**后取 TOP 15 长视频 + TOP 7 小视频

### 排行榜 API 注意事项

- API endpoint 为 `https://api.bilibili.com/x/web-interface/ranking/v2?type=all`，**不带 `order` 参数**（`order` 仅用于 search API，ranking v2 按内置综合算法排序）
- `owner.name` / `owner.uname` 可能同时为空，需批量调用 `/x/web-interface/view?bvid=xxx` 补全
- 小视频阈值用 `duration ≤ 60`（秒），长视频取剩余部分按综合评分排序

### AI 关键词列表（过滤用）

```
AI, 人工智能, 大模型, ChatGPT, Deepseek, Claude, GPT, 机器学习,
神经网络, LLM, Qwen, Kimi, Gemini, 文心, 通义, 智谱, AIGC,
Agent, 智能体, Chatbot, BOT, 语言模型, 深度学习
```

过滤逻辑：视频标题含任一关键词 → 进入 AI 热门候选列表。

## 综合评分算法（排行榜 API 用）

```
score = play × 0.01 + like × 0.5 + favourite × 0.8 + danmu × 0.3
```

| 字段 | 排行榜 API 路径 |
|------|--------------|
| 播放量 | `stat.view` |
| 点赞 | `stat.like` |
| 收藏 | `stat.favourite` |
| 弹幕 | `stat.danmu` |
| 时长（秒） | `duration` |
| 发布日期 | `pubdate`（Unix 时间戳） |
| UP主 | `owner.name` 或 `owner.uname` |
| bvid | `bvid` |

> ⚠️ `owner.name` 在排行榜 API 中可能为空，需调用 `/x/web-interface/view?bvid=xxx` 批量补全。

## 小视频处理

Bilibili **没有独立的小视频 API**，`type=small_video` 参数返回空数组。

**正确方法**：从 `type=all` 排行榜中**按视频时长过滤**，取 `duration ≤ 60` 秒的前7条。

```python
videos = [v for v in all_list if v.get('duration', 9999) <= 60]
```

> **阈值修正（2026-05-31）**：实测 `duration ≤ 60` 更准确地识别"小视频"（短视频/竖屏内容），旧值 `< 120` 可能混入中等时长视频。

## 热门榜单获取方法（2026-05-31 实测）

### 方法1：Bilibili 排行榜 API（⚠️ 已废弃，返回 -352）

```bash
curl -s "https://api.bilibili.com/x/web-interface/ranking/v2?type=all" \
  -H "User-Agent: Mozilla/5.0"
```
- **返回 HTTP -352（timestamp expired）**：排行榜 API 目前需要登录态或新鲜 timestamp，直接 curl 已废弃
- 旧文档称可用的 endpoint `type=all` + `order=hot` 等参数**均已失效**
- **不要依赖此 API**，改用下方方法2/3

### 方法2：Bilibili 搜索页抓取（主用，2026-05-31 实测可用）

**长视频（>10分钟）**：
```
https://search.bilibili.com/all?keyword=AI人工智能&search_type=video&order=hot&duration=4
```
- `duration=4` = 10分钟以上
- `order=hot` =最多播放
- 数据提取：用 `browser_console` JavaScript 提取：
```javascript
var links = [];
document.querySelectorAll('a[href*="/video/BV"]').forEach(a => {
  var href = a.href;
  var title = a.textContent.trim();
  if (title && href && !title.includes('稍后再看')) {
    links.push({href, title});
  }
});
JSON.stringify(links.slice(0, 20));
```

**小视频（<10分钟）**：
```
https://search.bilibili.com/all?keyword=AI人工智能&search_type=video&order=hot&duration=1
```
- `duration=1` = 10分钟以下
- 同上 JS 提取，去重后取前7条

> ⚠️ `browser_snapshot` 会被截断（~310行），**不要用 snapshot 提取10+条数据**，必须用 `browser_console` JS 提取。

> ⚠️ 搜索结果只显示播放量（万为单位）和点赞数，不显示精确值。

### 方法3：Web 搜索（备用/补充）

当 API 不可用或需快速概览时，用 `mcp_minimax_web_search` 搜索关键词：
```
bilibili热门视频 AI人工智能 大模型 2025 site:bilibili.com
```

搜索结果 snippet 中可提取：标题、播放量（万为单位）、UP主、发布日期。

> **注意事项**：
> - 搜索结果中的播放量为估算值（"xx万"），精确数据需调 API
> - 部分视频链接为外部镜像（如 `snm0516.aisee.tv`），需手动替换为 `bilibili.com/video/BVxxx`
> - BV号在搜索结果中可能缺失，需从视频详情页获取

## 文档结构（写入飞书格式）

```xml
<title>Bilibili AI热门推送 · 晚间档</title>
<h1>每日Bilibili AI热门推送 · {日期} · 晚间档</h1>
<h2>最热门长视频 TOP 15</h2>
<p>AI相关热门视频排序（播放×0.01+点赞×0.5+收藏×0.8+弹幕×0.3）</p>
<ol>
  <li seq="1">
    <a href="https://www.bilibili.com/video/BVxxx">标题</a><br/>
    播放：xxx万｜点赞：xx万｜收藏：xx万｜弹幕：xx万<br/>
    UP主：xxx｜发布日期：yyyy-mm-dd｜时长：HH:MM:SS<br/>
    综合评分：xxxxx
  </li>
  ...
</ol>
<h2>最热门小视频 TOP 7</h2>
<p>时长60秒以内的AI相关热门视频</p>
<ol>...</ol>
```

## cronjob 设计要点

### doc_id 独立
每个 cronjob 对应独立飞书文档，不要共享：
- AI热门 job → `Virbd3YyBoYK9XxqaZOccEGRnio`
- 全站热门 job → `TcjbdsX0ToprvCxXPbQcbLqknTq`

### cronjob 路径
```python
output_dir = "/Users/xiesg/.hermes/cron/output/"
```
不要用 `os.path.expanduser("~/.hermes/cron/output/")`。

### 触发命令
```bash
# 触发单个 cronjob（job_id 从上面表格查）
lark-cli cron run --job-id <job_id>
```
