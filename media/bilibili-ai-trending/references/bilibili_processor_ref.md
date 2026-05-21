# Bilibili AI Trending — Processor Reference

## 完整处理脚本模板

```python
import math, re
from datetime import datetime, timedelta

# ⚠️ CRITICAL: 必须使用 datetime.now() 而非硬编码日期
# cron job 以 UTC 执行，而 B站 使用 CST(UTC+8)
# datetime.now() 会自动使用系统时区（Mac 上为 CST）
NOW = datetime.now()
THREE_DAYS = timedelta(hours=72)

def parse_views_and_duration(text):
    """解析 '0002:19' → views=0, duration='02:19' (注意：raw可能含'稍后再看'前缀)
    格式: [稍后再看]VV [DD] HH:MM:SS 或 [稍后再看]VV [DD] MM:SS
    """
    if not text: return 0, ''
    text = text.strip().replace('稍后再看', '')
    m = re.search(r'(\d{1,2}):(\d{2}):(\d{2})\s*$', text)
    if m:
        h, mn, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
        duration = f'{h}:{mn:02d}:{s:02d}'
        num_part = text[:m.start()].strip()
    else:
        m2 = re.search(r'(\d{1,2}):(\d{2})\s*$', text)
        if m2:
            mn, s = int(m2.group(1)), int(m2.group(2))
            duration = f'{mn}:{s:02d}'
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

def duration_to_sec(dur):
    """HH:MM:SS or MM:SS → seconds"""
    if not dur: return 0
    parts = dur.split(':')
    if len(parts) == 3:
        return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0])*60 + int(parts[1])
    return 0

def parse_bilibili_date(date_str, current_date=NOW):
    """B站相对日期 → datetime_obj, display_str
    ⚠️ '分钟前' 必须在 '小时前' 之前检查！
    """
    if not date_str: return None, None
    date_str = date_str.strip()
    if '分钟前' in date_str:
        try:
            mins = int(re.search(r'(\d+)', date_str).group(1))
            return current_date - timedelta(minutes=mins), date_str
        except: pass
    if '小时前' in date_str:
        try:
            hours = int(re.search(r'(\d+)', date_str).group(1))
            return current_date - timedelta(hours=hours), date_str
        except: pass
    if date_str == '刚刚': return current_date, '刚刚'
    if date_str == '昨天': return current_date - timedelta(days=1), '昨天'
    if date_str == '前天': return current_date - timedelta(days=2), '前天'
    if re.match(r'^\d{2}-\d{2}$', date_str):
        try:
            m, d = map(int, date_str.split('-'))
            return datetime(current_date.year, m, d), date_str
        except: pass
    return None, date_str

def calc_score(views, pub_date, current_date=NOW, max_views=10_000_000):
    """score = 0.5*log10(views) + 0.15*freshness (点赞=0)"""
    if pub_date is None or views == 0: return 0
    hours_old = (current_date - pub_date).total_seconds() / 3600
    freshness = max(1 - hours_old / 168, 0)
    log_score = math.log10(views + 1) / math.log10(max_views)
    return 0.5 * log_score + 0.15 * freshness

# === 合并两步提取的数据 ===
# raw_data: [{'bv': 'BVxxx', 'raw': '0002:19', 't': 'title', 'a': 'author', 'd': '1分钟前'}, ...]

processed = []
for item in raw_data:
    views, duration = parse_views_and_duration(item['raw'])
    pub_dt, date_display = parse_bilibili_date(item['d'])
    dur_sec = duration_to_sec(duration)
    score = calc_score(views, pub_dt)
    is_short = dur_sec <= 300  # <=5min = 小视频
    processed.append({
        'bv': item['bv'], 'title': item['t'], 'author': item['a'],
        'date': date_display, 'pub_dt': pub_dt,
        'views': views, 'duration': duration, 'dur_sec': dur_sec,
        'score': score, 'is_short': is_short,
        'link': f'https://www.bilibili.com/video/{item["bv"]}'
    })

# 3天内过滤
recent = [p for p in processed if p['pub_dt'] and p['pub_dt'] >= NOW - THREE_DAYS]

long_videos = sorted([p for p in recent if not p['is_short']], key=lambda x: -x['score'])
short_videos = sorted([p for p in recent if p['is_short']], key=lambda x: -x['score'])

# 当日新发 = 3天内，按发布时间倒序
new_long = sorted([p for p in recent if not p['is_short']], key=lambda x: x['pub_dt'] or NOW, reverse=True)
```

## 本次 session 关键发现 (2026-05-21)

### 关键词 vs 结果新鲜度矛盾
- `DeepSeek GPT Claude Qwen LLM 大模型` → 大量 2025 年视频（标题长期匹配这些词）
- `AI 人工智能` → 返回真正分钟级最新的视频
- **结论**：关键词越宽泛+order=pubdate，结果越新鲜

### 时区问题导致 "当日新发" 只有1条
- cron 以 UTC 执行
- `datetime.now()` 在 Mac 本地返回 CST（UTC+8）时间
- 当 `NOW=datetime(UTC)` 时，"1分钟前" 被解析为昨天 → 被 three_days_ago 过滤掉
- **修复**：处理器中始终用 `datetime.now()`，不依赖 skill 硬编码的 NOW

### raw 字段格式（2026-05-21 确认）
- `a[href*="/video/BV"]` 的 textContent = `"稍后再看VV DD HH:MM:SS"` 或 `"VV DD MM:SS"`
- VV = 播放量（万单位直接写"万"），DD = 弹幕数，HH:MM:SS = 总时长
- **必须先 `.replace('稍后再看', '')` 再解析**
