# youtube-ai-trending-monitor 参考

## 两个维度的排序方法

### 维度1：当前热度（按总播放量排序）
侧重历史积累，大频道和长期热门视频占优

### 维度2：当日增量（按播放量/发布小时数排序）
侧重上升速度，新发布和突发事件占优

**公式：**
```
每小时增量 = 当前播放量 ÷ 发布小时数
```

## YouTube 搜索 URL 参数

| 过滤器 | URL参数 | 含义 |
|--------|---------|------|
| 本周上传 | `sp=CAE%253D` | 获取本周视频 |
| 今日上传 | `sp=CAMSAhAB` | 获取今日视频 |
| 视频类型 | `sp=CAESABobCAE%3D` | 仅视频 |

```bash
https://www.youtube.com/results?search_query=AI+news&sp=CAE%253D
```

## 增量计算示例

| 视频 | 当前播放 | 发布时间 | 每小时增量 | 评估 |
|------|---------|----------|-----------|------|
| A | 24K | 9小时前 | 2,667/h | 极高 |
| B | 6.7K | 4小时前 | 1,675/h | 高 |
| C | 23K | 1天前 | ~958/h | 中高 |
| D | 96K | 3天前 | ~1,333/天 | 长尾稳定 |

## 推荐 URL 组合

```bash
# 热门长视频搜索（本周）
https://www.youtube.com/results?search_query=AI+news+OR+LLM+OR+GPT+OR+ChatGPT+OR+Claude&sp=CAE%253D

# 热门短视频
https://www.youtube.com/results?search_query=AI+OR+artificial+intelligence

# 今日新发视频（频道页）
https://www.youtube.com/@AIDailyBrief/videos
```

## 高质量 AI 新闻频道

```
@AIDailyBrief/videos   ← 每日AI新闻
@WorldofAI/videos      ← 模型泄露热点
@Two-MinutePapers     ← 论文速读
@MattWolfe/videos      ← AI工具和新闻周报
```