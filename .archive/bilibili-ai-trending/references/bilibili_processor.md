# Bilibili AI Trending — 数据处理参考实现

## 概述
`bilibili_processor.py` 是 `bilibili-ai-trending` skill 的核心数据处理模块，包含从原始 BV 提取到最终分组的完整处理链。

**状态**：2026-05-28 实测验证通过。本文件是从实际 cron job session 中提取的运行代码，确保可复现。

---

## 核心函数

### parse_views_and_duration(text)
解析 B站 链接文本中的播放量 + 时长。

**输入格式**：`"稍后再看VV DD HH:MM:SS"` 或 `"稍后再看VV DD MM:SS"`
- VV = 播放量（可能为 `1.3万` 或纯数字）
- DD = 弹幕数
- HH:MM:SS 或 MM:SS = 视频时长

**关键逻辑**：必须用 `split()` 取第一个 token 作为播放量（不能把 "67 15" 当成 6715）。

```python
def parse_views_and_duration(text):
    if not text: return 0, ''
    text = text.strip().replace('稍后再看', '')
    m = re.search(r'(\d{1,2}):(\d{2}):(\d{2})\s*$', text)
    if m:
        h, mn, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
        duration = f"{h}:{mn:02d}:{s:02d}"
        num_part = text[:m.start()].strip()
    else:
        m2 = re.search(r'(\d{1,2}):(\d{2})\s*$', text)
        if m2:
            mn, s = int(m2.group(1)), int(m2.group(2))
            duration = f"{mn}:{s:02d}"
            num_part = text[:m2.start()].strip()
        else:
            duration = ''
            num_part = text.strip()
    tokens = num_part.strip().split()
    first_token = re.sub(r'[^\d.万]', '', tokens[0]) if tokens else ''
    if '万' in first_token:
        views = float(first_token.replace('万','')) * 10000
    else:
        views = int(float(first_token)) if first_token else 0
    return views, duration
```

### parse_bilibili_date(date_str, current_date=NOW)
将 B站相对日期解析为 datetime 对象。

**⚠️ 关键：`分钟前` 判断必须在 `小时前` 之前！**

```python
def parse_bilibili_date(date_str, current_date=NOW):
    if not date_str: return None, None
    date_str = date_str.strip()

    if '分钟前' in date_str:
        try:
            mins = int(re.search(r'(\d+)', date_str).group(1))
            pub_date = current_date - timedelta(minutes=mins)
            return pub_date, date_str
        except: pass

    if '小时前' in date_str:
        try:
            hours = int(re.search(r'(\d+)', date_str).group(1))
            pub_date = current_date - timedelta(hours=hours)
            return pub_date, date_str
        except: pass

    if date_str == '刚刚':
        return current_date, '刚刚'
    if date_str == '昨天':
        return current_date - timedelta(days=1), '昨天'
    if date_str == '前天':
        return current_date - timedelta(days=2), '前天'

    if re.match(r'^\d{2}-\d{2}$', date_str):
        try:
            m, d = map(int, date_str.split('-'))
            return datetime(current_date.year, m, d), date_str
        except: return None, date_str

    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d'), date_str
        except: return None, date_str

    return None, date_str
```

### calc_score(views, pub_date, current_date=NOW)
综合评分：B站搜索页无点赞数，真实公式为 `0.5×log + 0.15×freshness`。

```python
def calc_score(views, pub_date, current_date=NOW, max_views=10_000_000):
    if pub_date is None: return 0
    hours_old = (current_date - pub_date).total_seconds() / 3600
    freshness = max(1 - hours_old / 168, 0)
    log_score = math.log10(views + 1) / math.log10(max_views)
    score = 0.5 * log_score + 0.15 * freshness
    return score
```

### duration_to_sec(dur) → int
将 B站时长字符串转为秒数（用于长视频/短视频分类）。

```python
def duration_to_sec(dur):
    if not dur: return 0
    parts = dur.split(':')
    if len(parts) == 3:
        h, m, s = map(int, parts)
        return h*3600 + m*60 + s
    elif len(parts) == 2:
        m, s = map(int, parts)
        return m*60 + s
    return 0
```

---

## 完整处理流程（cron job 推荐）

```python
import math, re, json
from datetime import datetime, timedelta

NOW = datetime.now()  # ⚠️ 必须是 datetime.now()，不能硬编码日期

# Step 1: 从两个搜索页面提取 BV raw + meta
#   页面1: keyword=AI 人工智能&order=pubdate
#   页面2: keyword=AI 人工智能 大模型 深度学习&order=pubdate
#   每次提取两次（初始快照 + 滚动后）

meta_map = {m['bv']: m for m in meta_list_1 + meta_list_2}
raw_map  = {r['bv']: r for r in raw_bv_list_1 + raw_bv_list_2}

# Step 2: 合并、去重、解析
processed = []
for bv in set(list(meta_map.keys()) + list(raw_map.keys())):
    meta = meta_map.get(bv, {})
    raw = raw_map.get(bv, {})
    views, duration = parse_views_and_duration(raw.get('raw', ''))
    pub_date, date_display = parse_bilibili_date(meta.get('d', ''))
    dur_sec = duration_to_sec(duration)
    score = calc_score(views, pub_date)
    is_short = dur_sec > 0 and dur_sec <= 300
    processed.append({bv, title, author, date_display, pub_date, views, duration, dur_sec, is_short, score, url})

# Step 3: 过滤3天内 + 按评分排序
three_days_ago = NOW - timedelta(days=3)
recent = [v for v in processed if v['pub_date'] and v['pub_date'] >= three_days_ago]
recent.sort(key=lambda x: -x['score'])

long_videos  = [v for v in recent if not v['is_short']]
short_videos = [v for v in recent if v['is_short']]
```

---

## 长视频/小视频分类阈值
- **小视频**：duration_sec ≤ 300（≤5分钟）
- **长视频**：duration_sec > 300

⚠️ `tids=124` 参数不可靠，不要依赖。

---

## 播放量 raw 字段格式（2026-05 实测）

| 原始文本 | 解析结果 |
|---------|---------|
| `"稍后再看0000:06"` | views=0, dur="0:06" |
| `"稍后再看5021:42"` | views=50, dur="21:42" |
| `"稍后再看42001:43"` | views=42, dur="01:43" |
| `"稍后再看145023:57"` | views=145, dur="23:57" |
| `"稍后再看2901403:53:11"` | views=29014, dur="3:53:11" |
| `"稍后再看666003:42"` | views=666, dur="3:42" |

⚠️ 有些播放量是 "50"（50播放）不是 "50万"。`parse_views_and_duration` 的 `split()` + 万单位检测可正确处理。

---

## 飞书写入路径要点（纠错）

```bash
# ❌ 错误：绝对路径
lark-cli docs +update --doc "token" --command overwrite --content @/tmp/output.xml

# ✅ 正确：相对路径（当前工作目录下）
lark-cli docs +update --doc "token" --command overwrite --content @./output.xml
```

**常见错误**：`--content @/tmp/xxx` → lark-cli 报错 `--file must be a relative path within the current directory`。

**解决方案**：写入 `/tmp/` 后 `cp` 到 `~/.hermes/hermes-agent/` 下，再用 `@./filename` 引用。