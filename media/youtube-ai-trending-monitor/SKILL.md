---
name: youtube-ai-trending-monitor
description: >
  Monitor YouTube AI content hotness by two dimensions: total views (current popularity)
  and daily view velocity (incremental growth rate). Use when the user wants to track
  AI-related YouTube videos, discover trending content, or rank videos by freshness vs accumulated popularity.
---

# YouTube AI内容热度监控方案

## 两个维度的排序方法

### 维度1：当前热度（按总播放量排序）
侧重历史积累，大频道和长期热门视频占优

### 维度2：当日增量（按播放量/发布小时数排序）
侧重上升速度，新发布和突发事件占优

**公式：**
```
每小时增量 = 当前播放量 ÷ 发布小时数
```

## YouTube搜索URL参数

```
基础搜索词：AI news OR AI update OR artificial intelligence
```

| 过滤器 | URL参数 | 含义 |
|--------|---------|------|
| 本周上传 | `sp=CAE%253D` | 获取本周视频 |
| 今日上传 | `sp=CAMSAhAB` | 获取今日视频（精度有限） |
| 视频类型 | `sp=CAESABobCAE%3D` | 仅视频 |

**完整URL示例：**
```
https://www.youtube.com/results?search_query=AI+news&sp=CAE%253D
```

## 页面数据提取字段

从YouTube搜索结果页面提取：
```
标题 | 频道名 | 播放量（如"96K views"）| 发布时间（如"3天前"）
```

**播放量格式：** K（千）、M（百万）
**发布时间格式：** X分钟前、X小时前、X天前

## 增量计算示例

| 视频 | 当前播放 | 发布时间 | 每小时增量 | 评估 |
|------|---------|----------|-----------|------|
| A | 24K | 9小时前 | 2,667/h | 极高 |
| B | 6.7K | 4小时前 | 1,675/h | 高 |
| C | 23K | 1天前 | ~958/h | 中高 |
| D | 96K | 3天前 | ~1,333/天 | 长尾稳定 |

## 搜索词扩展

```
AI news OR AI update OR artificial intelligence
LLM OR GPT OR ChatGPT OR Claude
machine learning OR deep learning OR neural network
```

## 注意事项

1. **反爬限制**：YouTube有反爬机制，频繁访问可能触发CAPTCHA验证
2. **过滤器精度**：`今日上传`参数精度有限，需结合发布时间字段人工筛选
3. **API方案**：如需精确数据，使用YouTube Data API v3获取 `statistics.viewCount` 和 `snippet.publishedAt`
4. **数据延迟**：页面播放量为近似值，可能有几分钟延迟

## 快速验证流程

1. 打开浏览器访问：
   ```
   https://www.youtube.com/results?search_query=AI+news&sp=CAE%253D
   ```
2. 提取前10条的：标题、频道名、播放量、发布时间
3. 按两个维度分别排序
4. 对比两个排名的差异

## 高效抓取方案：并行Subagent（推荐）

单页顺序浏览效率低，**使用并行subagent同时抓取多个数据源**：

### 并行抓取策略
用 `delegate_task` 同时发起3个浏览器任务：

```
任务1: YouTube搜索页 → 获取热门长视频TOP10
任务2: YouTube搜索页(Shorts标签) → 获取热门短视频TOP5  
任务3: AI Daily Brief频道页 → 获取最新发布视频
```

### 推荐URL组合
```
# 热门长视频搜索（本周）
https://www.youtube.com/results?search_query=AI+news+OR+LLM+OR+GPT+OR+ChatGPT+OR+Claude&sp=CAE%253D

# 热门短视频（搜索+Shorts标签）
https://www.youtube.com/results?search_query=AI+OR+artificial+intelligence

# 今日新发视频（频道页+Latest标签）
https://www.youtube.com/@AIDailyBrief/videos
```

### delegate_task 配置
```python
delegate_task(
    goal="访问YouTube页面，提取：标题、URL、播放量、发布时间、频道名",
    toolsets=["browser"]
)
```

### 数据提取字段
从页面snapshot提取：
- 标题 → 从heading或link text
- URL → 从link元素的url属性（格式：`/watch?v=VIDEO_ID`）
- 播放量 → text中的 "XXK views" 或 "XXM views"
- 发布时间 → text中的 "X分钟前"、"X小时前"、"X天前"
- 频道名 → 从link text（如 "Matt Wolfe"）

### 输出格式模板
```
序号 | 标题 | URL | 播放量 | 发布时间 | 频道名
```

### 为什么更有效
- 顺序浏览每页耗时2-5分钟，并行任务总耗时约等于最慢的那个任务
- 搜索结果页广告多，频道页纯净度高
- 频道页自带时间排序，发布时间清晰可见

### 搜索词扩展
```
AI news OR AI update OR artificial intelligence
LLM OR GPT OR ChatGPT OR Claude
machine learning OR deep learning OR neural network
OpenAI OR Anthropic OR Google AI
```

### 高质量AI新闻频道
```
@AIDailyBrief/videos          ← 每日AI新闻，发布时间精确
@WorldofAI/videos            ← 模型泄露热点
@Two-MinutePapers            ← 论文速读
@MattWolfe/videos            ← AI工具和新闻周报
@mreflow/videos              ← Matt Wolfe主频道
```

### 工作流
1. 确定数据需求：热门总榜 / 当日新增 / 分类别
2. 选择对应的URL和搜索词组合
3. 并行发起3个subagent任务
4. 汇总结果，按播放量排序（热门）或发布时间排序（新增）
5. 过滤发布时间<24小时的数据作为"今日新发"

### 飞书消息格式要求
⚠️ **重要**：飞书消息中Markdown表格格式会导致链接无法点击显示！
- 链接必须用纯文本格式发送
- 每条视频信息单独一行：标题 + 播放量 + 发布时间 + URL

## 局限性发现（经验总结）

1. 维度1中，279K播放的Bloomberg视频因发布超过本周而不出现在本周结果中
2. 维度2中，极新发布（51分钟前）的视频虽然增量高但绝对播放量低
3. 建议结合使用：维度2发现新热点 → 维度1确认持续影响力
