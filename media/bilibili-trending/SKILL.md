---
name: bilibili-trending
description: 获取Bilibili全站热门视频和当日新发热门视频，返回标题、URL、播放量、UP主。使用browser工具从B站热门榜单和搜索页面提取数据。
triggers:
  - 获取B站今日热门视频
  - Bilibili热门视频排行
  - B站全站热门长视频/短视频
  - 当天新发热门视频
---

# Bilibili 全站热门视频获取

## 功能说明
获取Bilibili全站热门视频和当日新发视频，返回标题、URL、播放量、UP主。

## 数据分类

### 1. 最热门长视频 TOP 15
- 来源：B站排行榜（综合热门）
- 过滤器：视频（非小视频）
- **时间范围：3天内发布**
- **综合评分排序**

### 2. 最热门小视频 TOP 7
- 来源：B站小视频频道
- **时间范围：3天内发布**
- **综合评分排序**

## 综合评分算法

```
score = 0.5 × log₁₀(播放量)/10
      + 0.35 × min(点赞/播放 × 10, 1.0)
      + 0.15 × 新鲜度
```

### 计算公式说明

| 权重 | 指标 | 计算方式 |
|------|------|----------|
| 50% | 播放量 | `0.5 × log₁₀(播放量) / 10` — 对数归一化，避免头部视频垄断 |
| 35% | 互动率 | `0.35 × min(点赞/播放 × 10, 1.0)` — 点赞/播放比，cap at 1.0 |
| 15% | 新鲜度 | `0.15 × max(1 - 发帖小时数/72, 0)` — 3天内线性衰减（3天=72小时） |

### 数据提取字段要求
必须提取以下字段用于评分：
- `播放量`（views）
- `点赞数`（likes）
- `发布时间`（publish time，用于计算新鲜度）
- `标题`（title）

### 评分计算实现
```javascript
function calculateScore(video) {
  // 播放量归一化（假设最大播放量1000万）
  const maxViews = 10000000;
  const logScore = Math.log10(video.views + 1) / Math.log10(maxViews);

  // 互动率得分
  const likeRate = video.likes / video.views;
  const interactionScore = Math.min(likeRate * 10, 1.0);

  // 新鲜度得分（72小时=3天）
  const hoursAgo = (Date.now() - new Date(video.pubDate).getTime()) / 3600000;
  const freshnessScore = max(1 - hoursAgo / 72, 0);

  // 综合得分
  const score = 0.5 * logScore + 0.35 * interactionScore + 0.15 * freshnessScore;
  return score;
}
```

### 注意事项
- B站排行榜页面通常不直接显示点赞数，需要进入视频详情页获取
- 如果无法获取点赞数，则只使用播放量和新鲜度计算（归一化为满分1.0）
- 新鲜度基准：发布时间在3天以内，之外则为0

## 推荐：API 直接获取（首选方案）

B站提供公开排行榜 API，可通过 curl 直接获取完整结构化数据，比浏览器抓取更可靠：

```
curl -s "https://api.bilibili.com/x/web-interface/ranking/v2?type=all" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  -H "Referer: https://www.bilibili.com/"
```

返回字段包括：title、bvid、duration、pubdate、owner(name)、stat(view/danmaku/like)。

⚠️ 注意：该 API 存在严格频率限制，连续请求会返回 -352 错误。

**最佳实践：**
1. 每次任务只调用一次 API，解析后缓存在 Python 脚本中处理
2. 若遇 -352，等待 5 秒后重试一次（通常可恢复）
3. 请求时附带完整 headers（含 `Origin` 字段）可降低被限流概率：
```bash
curl -s "https://api.bilibili.com/x/web-interface/ranking/v2?type=all" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  -H "Referer: https://www.bilibili.com/" \
  -H "Origin: https://www.bilibili.com"
```
4. API 返回 100 条数据，足够覆盖 TOP 15 + TOP 7 需求，无需翻页

## 备选：页面URL（浏览器方式，优先级较低）

```
# B站综合热门排行榜（最多取TOP 20）
https://www.bilibili.com/v/policy/ranking

# B站小视频热门
https://www.bilibili.com/v/popular/history?tab=2

# 搜索最新发布视频
https://search.bilibili.com/video?keyword=热门&order=pubdate

# 小视频最新发布
https://search.bilibili.com/video?keyword=热门&order=pubdate&tids=124
```

## 输出格式

```
📺 一、最热门长视频 TOP 10

1. 视频标题
   播放量：XXX | 弹幕数 | 评论数 | UP主
   https://www.bilibili.com/video/BVxxxxxx

...

📺 二、最热门小视频 TOP 5

1. 视频标题
   播放量：XXX | UP主
   https://www.bilibili.com/video/BVxxxxxx

...

📺 三、当日新发热门视频

### 长视频 TOP 5
1. 视频标题
   播放量：XXX | 发布时间 | UP主
   https://www.bilibili.com/video/BVxxxxxx

### 小视频 TOP 3
1. 视频标题
   播放量：XXX | 发布时间 | UP主
   https://www.bilibili.com/video/BVxxxxxx

---

📝 摘要说明
- 当前热门主题分析
- 关键趋势总结
```

## 链接显示注意事项
⚠️ 飞书消息中Markdown表格格式会导致链接无法点击显示，必须使用纯文本格式发送链接。

## 数据处理参考实现（Python）

```python
import subprocess, json, datetime, math

cmd = 'curl -s "https://api.bilibili.com/x/web-interface/ranking/v2?type=all" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  -H "Referer: https://www.bilibili.com/" -H "Origin: https://www.bilibili.com"'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
data = json.loads(result.stdout)
items = data['data']['list']

now_ts = datetime.datetime.now().timestamp()
three_days_ago = now_ts - 3 * 24 * 3600

def calc_score(v, now_ts):
    views = v['stat']['view']
    likes = v['stat'].get('like', 0)
    pubdate = v['pubdate']
    max_views = 10000000
    log_score = math.log10(views + 1) / math.log10(max_views)
    like_rate = likes / views if views > 0 else 0
    interaction = min(like_rate * 10, 1.0)
    hours_ago = (now_ts - pubdate) / 3600
    freshness = max(1 - hours_ago / 72, 0)  # 3天内衰减
    return 0.5 * log_score + 0.35 * interaction + 0.15 * freshness

long_v, short_v = [], []
for v in items:
    if v['pubdate'] >= three_days_ago:
        (long_v if v['duration'] > 60 else short_v).append(v)

for v in long_v + short_v:
    v['_s'] = calc_score(v, now_ts)
long_v.sort(key=lambda x: x['_s'], reverse=True)
short_v.sort(key=lambda x: x['_s'], reverse=True)

def fmt_view(n): return f"{n//10000}万" if n >= 10000 else str(n)

for i, v in enumerate(long_v[:15]):
    print(f"{i+1}. {v['title']}")
    print(f"   播放量：{fmt_view(v['stat']['view'])} | 弹幕数：{v['stat']['danmaku']} | UP主：{v['owner']['name']} | 综合评分：{v['_s']:.4f}")
    print(f"   https://www.bilibili.com/video/{v['bvid']}")

for i, v in enumerate(short_v[:7]):
    print(f"{i+1}. {v['title']}")
    print(f"   播放量：{fmt_view(v['stat']['view'])} | UP主：{v['owner']['name']} | 综合评分：{v['_s']:.4f}")
    print(f"   https://www.bilibili.com/video/{v['bvid']}")
```

## 已知问题

### 1. API 频率限制
- Bilibili 排行榜 API 存在严格限流，连续请求返回 -352
- 解决：每次任务只调用一次 API；失败则等待数秒后重试
- 备选：使用 Python 脚本解析页面内容作为兜底

### 2. 浏览器抓取效果有限
- B站页面严重依赖 JavaScript 动态渲染，browser_snapshot 通常只返回页头/页脚等静态元素
- 热门视频列表通过异步加载，browser_console JavaScript 提取也经常失败
- 滚动页面后 accessibility tree 仍可能不包含视频数据
- **结论：优先使用 API 方案，浏览器仅作备选**

### 3. 小视频数据
- 小视频（≤60秒）在 API 中可通过 `duration <= 60` 筛选
- 主排行榜 API 数据足够完整，无需额外请求小视频频道

### 4. 播放量显示格式
- B站常用单位：万（1.2万），需按 `×10000` 解析

## 摘要生成
根据视频标题和当前热门话题生成2-3句话的简单摘要，说明主要内容趋势。

## ⚠️ Bilibili 不可用时的备选方案

**备选：Bing视频搜索**
```
URL: https://www.bing.com/videos/search?q=Bilibili+trending+2026+popular+video
```
