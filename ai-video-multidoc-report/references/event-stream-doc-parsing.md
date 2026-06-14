# 事件流 doc 解析配方（针对 SWLX 类结构化新闻 doc）

## 何时用这个配方

**触发条件**：lark-cli `docs +fetch --scope full` 拿到的 doc 满足以下**全部**特征：
- 没有 `<li>` 有序列表（不是视频清单）
- 用 `<h2>{日期}</h2>` 切分日期段
- 每段内用 `<b>N. 标题</b>` 编号
- 每条事件后跟 `<br/>来源：xxx | 摘要：xxx`

**典型代表**：`SWLXdMOQXoi0WFxML3zcDXuCnTd`（每日 AI 新闻早报，6-7~6-14 共 8 天 130+ 条事件）

## 与视频 doc 解析的关键区别

| 维度 | 视频 doc（Virb/HhyM/EbHD/ZzPa）| 事件流 doc（SWLX）|
|---|---|---|
| XML 结构 | `<ol><li>...</li></ol>` | `<h2>{日期}</h2>` + `<b>{编号}. {标题}</b><br/>来源：xxx` |
| 必填字段 | 频道/UP主 / 播放 / 时长 / 上传 | 日期 / 来源媒体 / 摘要 |
| 数据维度 | 反映"用户看什么"（带播放量）| 反映"行业发生什么"（带来源）|
| 解析后用途 | 主题热度、UP 主矩阵、播放量分布 | 事件链、跨日趋势、媒体来源分布 |

## Python 解析代码（可直接复用）

```python
import re
import json
from collections import defaultdict

def parse_event_stream(content):
    """解析 SWLX 类事件流 doc。返回按日期分组的事件列表。"""
    # 1. 按 <h2>{日期}</h2> 切分日期段
    date_pattern = re.compile(r'<h2>(\d{4}年\d{2}月\d{2}日[^<]*)</h2>')
    date_matches = list(date_pattern.finditer(content))
    
    events_by_date = {}
    for i, m in enumerate(date_matches):
        date_str = m.group(1).strip()
        # 该日期段从 m.end() 到下一个日期段开始（或文档末尾）
        segment_end = date_matches[i+1].start() if i+1 < len(date_matches) else len(content)
        segment = content[m.end():segment_end]
        
        # 2. 在该段内解析 <b>N. 标题</b><br/>来源：xxx | 摘要：xxx
        item_pattern = re.compile(
            r'<b>(\d+)\.\s*([^<]+)</b>'
            r'(?:<br/>)?'
            r'来源：([^<|]+)'
            r'(?:\s*\|\s*)?'
            r'摘要：([^<]+)'
        )
        events = []
        for im in item_pattern.finditer(segment):
            events.append({
                'date': date_str,
                'index': int(im.group(1)),
                'title': im.group(2).strip(),
                'source': im.group(3).strip(),
                'summary': im.group(4).strip()[:120]  # 截断到 120 字
            })
        events_by_date[date_str] = events
    
    return events_by_date

# 用法示例
with open('/tmp/swlx_full.xml') as f:
    content = f.read()
events = parse_event_stream(content)
# 输出：{'2026年06月14日（周日）': [...10 events], '2026年06月13日（周六）': [...10 events], ...}
```

## 解析失败的兜底方案

**症状 1**：`<b>` 标签里的标题含 `<a>` 链接（部分新闻标题是带跳转的）
- **症状 2**：来源列表里出现 `|`（如 "来源：36氪/腾讯科技"）
- **症状 3**：摘要后跟额外 `<p>` 标签（如"相关分析"小节）

**解法**：
- 用 `re.DOTALL` 让 `.` 匹配换行
- 来源提取改用 `r'来源：([^<]+?)(?=\s*(?:摘要|$))'` —— 接受任何非 `<` 字符到"摘要"前
- 摘要截断改用 `im.group(4).split('<')[0]` —— 截到第一个 `<`

## 解析后必跑的统计

```python
# 1. 每日事件数（看新闻节奏是否平稳）
for date, evs in events.items():
    print(f'{date}: {len(evs)} events')

# 2. 来源媒体分布（看谁在主导话语）
from collections import Counter
all_sources = []
for evs in events.values():
    for ev in evs:
        # 拆分 "36氪/腾讯科技" 这类
        all_sources.extend(s.strip() for s in ev['source'].split('/'))
print(Counter(all_sources).most_common(10))

# 3. 跨日话题（同一事件在多日出现的次数）
title_keywords = Counter()
for evs in events.values():
    for ev in evs:
        for kw in ['Anthropic', 'OpenAI', 'Kimi', 'DeepSeek', 'MiniMax', '豆包', '网信办', '智源']:
            if kw in ev['title']:
                title_keywords[kw] += 1
print(title_keywords.most_common())
```

## 跟视频 doc 交叉验证（5 doc 体系核心步骤）

**目的**：检测"行业大事是不是用户真正关心"（反之亦然）。

```python
# 步骤 1：从事件流 doc 提取"高优先级事件"（出现 ≥ 3 次 或 多源报道）
high_priority_events = []
for evs in events.values():
    for ev in evs:
        if ev['source'].count('/') >= 2:  # 多源报道
            high_priority_events.append(ev['title'])

# 步骤 2：从视频 doc 提取"高播放视频"（播放 > 50 万）
high_play_videos = []
for doc in ['ebhd', 'hhym', 'virb', 'zzpa']:
    for it in all_items[doc]:
        if parse_views(it['views']) > 500000:
            high_play_videos.append(it['title'])

# 步骤 3：交叉检查
# - 行业大事但用户不关心 → 洞见"行业热度 ≠ 用户兴趣"
# - 用户关心但行业不报道 → 洞见"用户兴趣与行业脱节"
# - 双方都关注 → 确认真热点
overlap = set(high_priority_events) & set(high_play_videos)
only_industry = set(high_priority_events) - set(high_play_videos)
only_user = set(high_play_videos) - set(high_priority_events)
```

## 实战经验教训

- **第 8 天数据可能缺失**：cron 任务是晚 21:00 跑，6-14 晚 21:00 跑的 cron 任务可能漏当天的 6-14 段。报告里要标"6-14 数据可能尚未生成"——不要强行补
- **"摘要"段被截断别慌**：lark-cli 单次只返回 ~10KB，事件流 doc 8 天全量常超 30KB。要么多 fetch 几次拼，要么只取摘要前 80 字
- **来源用 `/` 隔开 vs `、`隔开**：看具体 doc，作者不一定一致。建议先 `Counter(source_pattern)` 看哪种分隔符多，再决定 split 字符
- **`<b>` 内可能含 HTML 转义**：标题里出现 `&amp;` `&quot;` `&lt;` 等，需要 `html.unescape()` 再入库
