import math
import re
from datetime import datetime, timedelta

# Usage: copy all functions below into execute_code, set NOW to current time
# then call process_all(raw_data, meta_data) to get scored/sorted results

NOW = datetime(2026, 5, 17, 21, 0)  # SET THIS to current time in cron job


def parse_views_and_duration(text):
    """Parse '稍后再看VV DD HH:MM:SS' → views, duration.
    Handles the粘连 format where play count and duration are fused together.
    CRITICAL: only takes the FIRST space-delimited token as the play count.
    """
    if not text:
        return 0, ''
    text = text.strip().replace('稍后再看', '')
    # Extract duration HH:MM:SS or MM:SS from end
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
    # CRITICAL: only take first token as views
    tokens = num_part.strip().split()
    first_token = re.sub(r'[^\d万]', '', tokens[0]) if tokens else ''
    if '万' in first_token:
        views = float(first_token.replace('万', '')) * 10000
    else:
        views = int(float(first_token)) if first_token else 0
    return views, duration


def parse_bilibili_date(date_str, current_date=NOW):
    """Parse Bilibili relative date string → (datetime_obj, display_string).
    MUST check '分钟前' BEFORE '小时前' — otherwise '1分钟前' matches '1小时前'.
    """
    if not date_str:
        return None, None
    date_str = date_str.strip()

    if '分钟前' in date_str:
        try:
            mins = int(re.search(r'(\d+)', date_str).group(1))
            pub_date = current_date - timedelta(minutes=mins)
            return pub_date, date_str
        except:
            pass

    if '小时前' in date_str:
        try:
            hours = int(re.search(r'(\d+)', date_str).group(1))
            pub_date = current_date - timedelta(hours=hours)
            return pub_date, date_str
        except:
            pass

    if date_str == '刚刚':
        return current_date, '刚刚'
    if date_str == '昨天':
        pub_date = current_date - timedelta(days=1)
        return pub_date, '昨天'
    if date_str == '前天':
        pub_date = current_date - timedelta(days=2)
        return pub_date, '前天'

    # MM-DD format (e.g. "03-17")
    if re.match(r'^\d{2}-\d{2}$', date_str):
        try:
            m, d = map(int, date_str.split('-'))
            year = current_date.year
            pub_date = datetime(year, m, d)
            return pub_date, date_str
        except:
            return None, date_str

    # YYYY-MM-DD format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        try:
            pub_date = datetime.strptime(date_str, '%Y-%m-%d')
            return pub_date, date_str
        except:
            return None, date_str

    return None, date_str


def calc_score(views, pub_date, current_date=NOW, max_views=10_000_000):
    """Composite score: 0.5 × log10(views) + 0.15 × freshness.
    Interaction term (likes) = 0 since B站 search pages don't expose likes.
    Freshness decays linearly over 7 days (168h) to 0.
    """
    if pub_date is None:
        return 0
    hours_old = (current_date - pub_date).total_seconds() / 3600
    freshness = max(1 - hours_old / 168, 0)
    log_score = math.log10(views + 1) / math.log10(max_views)
    score = 0.5 * log_score + 0.15 * freshness
    return score


def duration_to_sec(d):
    """Convert B站 duration string (HH:MM:SS or MM:SS) to seconds."""
    if not d:
        return 0
    parts = d.split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[2])
    return 0


def process_all(raw_data, meta_data, current_date=NOW, hours_limit=72):
    """Process raw BV data + metadata into scored/sorted video list.
    
    raw_data: list of (bv, raw_text) tuples from browser_console a[href*="/video/BV"]
    meta_data: list of (bv, title, author, date_str) tuples from h3 extraction
    hours_limit: only include videos published within this many hours (default 72 = 3 days)
    
    Returns (long_videos, short_videos) sorted by score descending.
    Short video = duration <= 300 seconds (5 minutes).
    """
    raw_lookup = {bv: raw for bv, raw in raw_data}
    meta_lookup = {bv: (title, author, date) for bv, title, author, date in meta_data}

    videos = []
    for bv in raw_lookup:
        raw = raw_lookup[bv]
        if bv not in meta_lookup:
            continue
        title, author, date_str = meta_lookup[bv]
        views, duration = parse_views_and_duration(raw)
        pub_date, date_display = parse_bilibili_date(date_str, current_date)
        if pub_date is None:
            continue
        hours_old = (current_date - pub_date).total_seconds() / 3600
        if hours_old > hours_limit:
            continue
        score = calc_score(views, pub_date, current_date)
        dur_sec = duration_to_sec(duration)
        is_short = dur_sec > 0 and dur_sec <= 300
        videos.append({
            'bv': bv,
            'title': title,
            'author': author,
            'views': int(views),
            'date': date_display,
            'pub_date': pub_date,
            'score': score,
            'duration': duration,
            'is_short': is_short,
            'url': f'https://www.bilibili.com/video/{bv}'
        })

    videos.sort(key=lambda x: x['score'], reverse=True)
    long_videos = [v for v in videos if not v['is_short']]
    short_videos = [v for v in videos if v['is_short']]
    return long_videos, short_videos


def format_report(long_videos, short_videos, top_n_long=15, top_n_short=7, top_n_new_long=5, top_n_new_short=3, current_date=NOW):
    """Format scored video lists into plain-text report string."""
    lines = []

    lines.append("📺 一、最热门长视频 TOP {}（3天内，综合评分）".format(top_n_long))
    lines.append("")
    for i, v in enumerate(long_videos[:top_n_long], 1):
        title = v['title'][:50] + ('...' if len(v['title']) > 50 else '')
        lines.append(f"{i}. {title}")
        lines.append(f"   播放量：{v['views']} | {v['date']} | {v['author']} | 综合评分：{v['score']:.3f} | 时长：{v['duration']}")
        lines.append(f"   {v['url']}")
        lines.append("")

    lines.append("📺 二、最热门小视频 TOP {}（3天内，综合评分）".format(top_n_short))
    lines.append("")
    for i, v in enumerate(short_videos[:top_n_short], 1):
        title = v['title'][:50] + ('...' if len(v['title']) > 50 else '')
        lines.append(f"{i}. {title}")
        lines.append(f"   播放量：{v['views']} | {v['date']} | {v['author']} | 综合评分：{v['score']:.3f} | 时长：{v['duration']}")
        lines.append(f"   {v['url']}")
        lines.append("")

    new_long = sorted(long_videos, key=lambda x: x['pub_date'] or datetime.min, reverse=True)[:top_n_new_long]
    new_short = sorted(short_videos, key=lambda x: x['pub_date'] or datetime.min, reverse=True)[:top_n_new_short]

    lines.append("📺 三、当日新发热门视频（3天内）")
    lines.append("")
    lines.append("### 长视频 TOP {}".format(top_n_new_long))
    for i, v in enumerate(new_long, 1):
        title = v['title'][:50] + ('...' if len(v['title']) > 50 else '')
        lines.append(f"{i}. {title}")
        lines.append(f"   播放量：{v['views']} | {v['date']} | {v['author']} | 时长：{v['duration']}")
        lines.append(f"   {v['url']}")
        lines.append("")

    lines.append("### 短视频 TOP {}".format(top_n_new_short))
    for i, v in enumerate(new_short, 1):
        title = v['title'][:50] + ('...' if len(v['title']) > 50 else '')
        lines.append(f"{i}. {title}")
        lines.append(f"   播放量：{v['views']} | {v['date']} | {v['author']} | 时长：{v['duration']}")
        lines.append(f"   {v['url']}")
        lines.append("")

    return '\n'.join(lines)
