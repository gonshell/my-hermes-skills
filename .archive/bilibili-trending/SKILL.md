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

### 方案A（首选）：热门接口 `popular` — 稳定可用

排行榜 API (`ranking/v2`) 在 cron/自动化环境中频繁返回 **-352 限流**，且等待后难以恢复。**热门接口更稳定**：

```bash
# 每页20条，1-5页共100条（与ranking API数量一致）
curl -s "https://api.bilibili.com/x/web-interface/popular?pn=1&ps=20&type=hot" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  -H "Referer: https://www.bilibili.com/"
```

**用法**：翻1-5页取100条，URL参数 `pn={页码}&ps=20`。
返回字段与 ranking API 相同：title、bvid、duration、pubdate、owner(name)、stat(view/danmaku/like)。

### 方案B（备选）：排行榜接口 `ranking/v2`

```bash
curl -s "https://api.bilibili.com/x/web-interface/ranking/v2?type=all" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  -H "Referer: https://www.bilibili.com/" \
  -H "Origin: https://www.bilibili.com"
```

⚠️ 注意：该 API 存在严格频率限制，连续请求或 cron 场景下返回 **-352 错误**。实测等待20秒仍无法恢复，不建议作为主要数据源。

**最佳实践：**
1. 每次任务优先用 `popular` 接口取5页（100条）
2. 若 `popular` 也失败，再用 `ranking/v2` 作为兜底
3. 请求间隔 1 秒/页，避免触发限流
4. 两个接口返回字段一致，处理逻辑可共用

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
import subprocess, json, datetime, math, time

def fetch_bilibili_hot():
    """获取B站热门视频（popular接口，稳定可用）"""
    all_items = []
    for page in range(1, 6):  # 5页共100条
        cmd = f'curl -s "https://api.bilibili.com/x/web-interface/popular?pn={page}&ps=20&type=hot" \
          -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
          -H "Referer: https://www.bilibili.com/"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        if data.get('code') == 0:
            all_items.extend(data['data']['list'])
        time.sleep(1)  # 避免限流
    # 去重
    seen, items = set(), []
    for v in all_items:
        if v['bvid'] not in seen:
            seen.add(v['bvid']); items.append(v)
    return items

items = fetch_bilibili_hot()
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

# 输出长视频TOP15
for i, v in enumerate(long_v[:15]):
    pub_time = datetime.datetime.fromtimestamp(v['pubdate']).strftime('%m-%d %H:%M')
    print(f"{i+1}. {v['title']}")
    print(f"   播放量：{fmt_view(v['stat']['view'])} | 弹幕数：{v['stat']['danmaku']} | UP主：{v['owner']['name']} | 综合评分：{v['_s']:.4f}")
    print(f"   https://www.bilibili.com/video/{v['bvid']}")

# 输出小视频TOP7
for i, v in enumerate(short_v[:7]):
    pub_time = datetime.datetime.fromtimestamp(v['pubdate']).strftime('%m-%d %H:%M')
    print(f"{i+1}. {v['title']}")
    print(f"   播放量：{fmt_view(v['stat']['view'])} | UP主：{v['owner']['name']} | 综合评分：{v['_s']:.4f}")
    print(f"   https://www.bilibili.com/video/{v['bvid']}")
```

## 飞书推送工作流

定时任务场景下，将数据写入飞书文档并发送通知的完整流程见：
[`references/bilibili-trending-feishu-workflow.md`](references/bilibili-trending-feishu-workflow.md)

**当前实现逻辑（2026-05 改造）**：
1. 读取文档现有内容（`lark-cli docs +fetch --api-version v2 --doc "token"`）
2. 过滤 >7 天的旧段落，保留最近 7 天内容
3. 拼接：保留内容 + 今日新内容
4. 整体 overwrite 写入文档
5. **成功时**：输出单独一行 `[SILENT]`，不输出其他任何内容（cron 自动抑制送达）
6. **失败时**：输出告警格式（cron 自动送达本聊天窗口）

**统一告警格式**：
```
🚨 定时任务执行出错

📌 任务：<任务名>
⏰ 时间：<YYYY-MM-DD HH:MM:SS>
❌ 阶段：<获取数据/读取文档/写入文档/未知>
📝 错误：<具体错误描述>
```

## 已知问题

### 1. API 频率限制

| 接口 | 路径 | 限流严重程度 | 表现 |
|------|------|-------------|------|
| 排行榜 | `/x/web-interface/ranking/v2` | **严重** | cron/自动化场景几乎必返回 -352，等待20秒仍无法恢复 |
| 热门 | `/x/web-interface/popular?type=hot` | 轻微 | 每页间隔1秒翻5页可稳定获取100条数据 |

**结论**：优先使用热门接口作为主要数据源，排行榜接口作为兜底。

### 2. 浏览器抓取效果有限
- B站页面严重依赖 JavaScript 动态渲染，browser_snapshot 通常只返回页头/页脚等静态元素
- 热门视频列表通过异步加载，browser_console JavaScript 提取也经常失败
- 滚动页面后 accessibility tree 仍可能不包含视频数据
- **结论：优先使用 API 方案，浏览器仅作备选**

### 3. 小视频数据
- 小视频（≤60秒）在 API 中可通过 `duration <= 60` 筛选
- 热门接口返回的小视频数量较少（实测约4条/100条），如需更多小视频需额外从 `tids=124` 搜索接口获取

### 4. 播放量显示格式
- B站常用单位：万（1.2万），需按 `×10000` 解析

## 摘要生成
根据视频标题和当前热门话题生成2-3句话的简单摘要，说明主要内容趋势。

## ⚠️ Bilibili 不可用时的备选方案

**备选：Bing视频搜索**
```
URL: https://www.bing.com/videos/search?q=Bilibili+trending+2026+popular+video
```
