import math
import re
from datetime import datetime, timedelta

# ===== Bilibili Data Processor =====
# Usage: Run after extracting BV data from 2-3 search URLs via browser_console.
# Pattern: Extract all a[href*="/video/BV"] + all h3 meta in ONE console call per URL,
#          collect raw BV data from all pages, then merge with meta_map by BV.

NOW = datetime.now()

def parse_views_and_duration(text):
    """Parse '稍后再看VV DD HH:MM:SS' into (views_int, duration_str)."""
    if not text: return 0, ''
    text = text.strip().replace('\u7f13\u518d\u770b', '')  # 稍后再看
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
    first_token = re.sub(r'[^\d.\u4e07]', '', tokens[0]) if tokens else ''  # \u4e07 = 万
    if '\u4e07' in first_token:
        views = float(first_token.replace('\u4e07','')) * 10000
    else:
        views = int(float(first_token)) if first_token else 0
    return views, duration

def duration_to_sec(dur):
    if not dur: return 0
    parts = dur.split(':')
    if len(parts) == 3:
        return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0])*60 + int(parts[1])
    return 0

def parse_bilibili_date(date_str, current_date=NOW):
    """Parse Bilibili relative date string to (datetime_obj, display_string)."""
    if not date_str: return None, None
    date_str = date_str.strip()
    # Must check 分钟前 BEFORE 小时前
    if '\u5206\u949f\u524d' in date_str:  # 分钟前
        try:
            mins = int(re.search(r'(\d+)', date_str).group(1))
            return current_date - timedelta(minutes=mins), date_str
        except: pass
    if '\u5c0f\u65f6\u524d' in date_str:  # 小时前
        try:
            hours = int(re.search(r'(\d+)', date_str).group(1))
            return current_date - timedelta(hours=hours), date_str
        except: pass
    if date_str in ('\u521a\u521a', '\u6628\u5929', '\u524d\u5929'):  # 刚刚, 昨天, 前天
        delta = {'\u521a\u521a': 0, '\u6628\u5929': 1, '\u524d\u5929': 2}[date_str]
        return current_date - timedelta(days=delta), date_str
    if re.match(r'^\d{2}-\d{2}$', date_str):
        try:
            m, d = map(int, date_str.split('-'))
            year = current_date.year
            pub_date = datetime(year, m, d)
            if pub_date > current_date:
                pub_date = datetime(year-1, m, d)
            return pub_date, date_str
        except: return None, date_str
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d'), date_str
        except: return None, date_str
    return None, date_str

def calc_score(views, pub_date, current_date=NOW, max_views=10_000_000):
    """Composite score: 0.5*log10(views) + 0.15*freshness. No likes data available."""
    if pub_date is None: return 0
    hours_old = (current_date - pub_date).total_seconds() / 3600
    freshness = max(1 - hours_old / 168, 0)
    log_score = math.log10(views + 1) / math.log10(max_views)
    score = 0.5 * log_score + 0.15 * freshness
    return score

def process_all(raw_bv_list, meta_list, current_date=NOW):
    """
    Merge BV raw data with metadata, filter to 3 days, score and categorize.
    raw_bv_list: list of {"bv": str, "raw": str} from a[href*="/video/BV"] extraction
    meta_list:    list of {"t": title, "bv": str, "a": author, "d": date_str} from h3 extraction
    Returns (long_videos, short_videos, new_long, new_short) sorted by score/pubdate.
    """
    three_days_ago = current_date - timedelta(days=3)

    all_raw = {item['bv']: item['raw'] for item in raw_bv_list}
    meta_map = {m['bv']: m for m in meta_list}

    all_videos = []
    for bv, raw in all_raw.items():
        views, dur = parse_views_and_duration(raw)
        dur_sec = duration_to_sec(dur)
        meta = meta_map.get(bv, {})
        title = meta.get('t', '')
        author = meta.get('a', '')
        date_str = meta.get('d', '')
        pub_date, _ = parse_bilibili_date(date_str, current_date)

        if pub_date and pub_date < three_days_ago:
            continue

        score = calc_score(views, pub_date, current_date)
        all_videos.append({
            'bv': bv,
            'title': title,
            'views': views,
            'duration': dur,
            'dur_sec': dur_sec,
            'author': author,
            'date_str': date_str,
            'pub_date': pub_date,
            'score': score,
        })

    long_videos = [v for v in all_videos if v['dur_sec'] > 300]
    short_videos = [v for v in all_videos if v['dur_sec'] <= 300 and v['dur_sec'] > 0]

    long_videos.sort(key=lambda x: -x['score'])
    short_videos.sort(key=lambda x: -x['score'])

    new_releases = sorted(
        [v for v in all_videos if v['pub_date'] is not None],
        key=lambda x: -x['pub_date'].timestamp()
    )
    new_long = [v for v in new_releases if v['dur_sec'] > 300]
    new_short = [v for v in new_releases if v['dur_sec'] <= 300 and v['dur_sec'] > 0]

    return long_videos, short_videos, new_long, new_short

if __name__ == '__main__':
    # Demo: show the output format
    print("Requires raw_bv_list + meta_list from browser extraction.")
    print("Run browser_console to extract, collect all pages, then call process_all().")