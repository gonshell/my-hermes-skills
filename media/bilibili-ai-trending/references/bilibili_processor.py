"""
Bilibili AI Trending — Python Processor
Validated 2026-05-10. Handles: views+duration parsing, date parsing, score calculation.

Usage:
    from bilibili_processor import parse_video_data, calc_score, NOW
    videos = parse_video_data(raw_list, current_date=NOW)
    videos.sort(key=lambda x: x['score'], reverse=True)
"""
import math, re
from datetime import datetime, timedelta

NOW = datetime(2026, 5, 10)  # Update to current date in cron job


def parse_views_and_duration(text):
    """解析粘连的 '1.3万250932' → views=13000, duration='25:09:32'
    
    B站 DOM 格式: "1.3万250932" = 播放量 + HHMMSS时长（无分隔符）
    也有可能是 "4万70721" = 播放量 + MMDDSS
    """
    if not text:
        return 0, ''
    text = text.strip()
    
    # 匹配 HH:MM:SS 或 MM:SS (从末尾)
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
            num_part = text
    
    num_part = re.sub(r'[^\d.万]', '', num_part)
    if '万' in num_part:
        views = float(num_part.replace('万', '')) * 10000
    else:
        views = int(num_part) if num_part.isdigit() else 0
    return views, duration


def parse_duration_seconds(dur_str):
    """'25:09:32' → 90422秒; '09:32' → 572秒"""
    if not dur_str:
        return 0
    parts = dur_str.split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0


def parse_bilibili_date(date_str, current_date=None):
    """解析B站相对日期 → datetime对象 + 原始字符串
    返回 (datetime_obj, display_str)
    """
    if current_date is None:
        current_date = NOW
    if not date_str:
        return None, None
    date_str = date_str.strip()
    
    if '小时前' in date_str or date_str == '刚刚':
        hours = 0
        if '小时前' in date_str:
            m = re.search(r'(\d+)', date_str)
            if m:
                hours = int(m.group(1))
        pub_date = current_date - timedelta(hours=hours)
        return pub_date, pub_date.strftime('%m-%d')
    
    if date_str == '昨天':
        return current_date - timedelta(days=1), '昨天'
    if date_str == '前天':
        return current_date - timedelta(days=2), '前天'
    
    if '-' in date_str and len(date_str) == 5:  # MM-DD
        try:
            m, d = map(int, date_str.split('-'))
            year = current_date.year if m <= current_date.month else current_date.year - 1
            return datetime(year, m, d), date_str
        except:
            return None, date_str
    
    if '-' in date_str and len(date_str) == 10:  # YYYY-MM-DD
        try:
            return datetime.strptime(date_str, '%Y-%m-%d'), date_str
        except:
            return None, date_str
    
    return None, date_str


def calc_score(views, pub_date, current_date=None, max_views=10_000_000):
    """综合评分: 播放量对数(50%) + 互动率(35%) + 新鲜度(15%)
    
    无点赞数据时互动率为0。
    新鲜度7天衰减至0。
    """
    if current_date is None:
        current_date = NOW
    if pub_date is None:
        return 0
    
    hours_old = (current_date - pub_date).total_seconds() / 3600
    if hours_old < 0:
        hours_old = 0
    
    freshness = max(1 - hours_old / 168, 0)
    log_score = math.log10(views + 1) / math.log10(max_views)
    # Interaction = 0 when likes unavailable
    score = 0.5 * log_score + 0.15 * freshness
    return score


def parse_video_data(raw_list, current_date=None):
    """
    将原始视频数据列表处理为含评分的有序列表。
    
    raw_list: [{"title": ..., "author": ..., "views_raw": ..., "date_raw": ..., "link": ...}, ...]
    views_raw: 原始字符串如 "1.3万250932"
    date_raw: B站相对日期字符串
    
    返回: [{"title": ..., "author": ..., "views": int, "views_raw": str,
            "duration": str, "dur_sec": int, "pub_date": datetime,
            "date_raw": str, "hours_old": float, "score": float, "link": str}, ...]
    """
    if current_date is None:
        current_date = NOW
    seen = set()
    videos = []
    
    for v in raw_list:
        bv_match = re.search(r'BV\w+', v.get('link', ''))
        if not bv_match:
            continue
        bv = bv_match.group(0)
        if bv in seen:
            continue
        seen.add(bv)
        
        views, duration = parse_views_and_duration(v.get('views_raw', ''))
        pub_date, date_raw = parse_bilibili_date(v.get('date_raw', ''), current_date)
        score = calc_score(views, pub_date, current_date)
        hours_old = (current_date - pub_date).total_seconds() / 3600 if pub_date else 999
        dur_sec = parse_duration_seconds(duration)
        
        videos.append({
            'title': v.get('title', ''),
            'author': v.get('author', ''),
            'views': views,
            'views_raw': v.get('views_raw', ''),
            'duration': duration,
            'dur_sec': dur_sec,
            'pub_date': pub_date,
            'date_raw': date_raw,
            'hours_old': hours_old,
            'score': score,
            'link': v.get('link', ''),
            'is_short': dur_sec <= 300 if dur_sec > 0 else False,
        })
    
    return videos


def fmt_views(v):
    if v >= 10000:
        return f"{v/10000:.1f}万"
    return str(int(v))


def filter_fresh(videos, hours=168):
    """只保留7天内（可配置）的内容"""
    return [v for v in videos if v['hours_old'] <= hours]


def sort_and_classify(videos):
    """返回 (long_videos, short_videos)，各自按score降序"""
    videos.sort(key=lambda x: x['score'], reverse=True)
    long_videos = [v for v in videos if not v['is_short']]
    short_videos = [v for v in videos if v['is_short']]
    return long_videos, short_videos


if __name__ == '__main__':
    # 演示用法
    test = [
        {"title": "测试", "author": "UP", "views_raw": "1.3万250932", "date_raw": "05-05", "link": "https://www.bilibili.com/video/BV1HJRnBaEsd/"},
        {"title": "测试2", "author": "UP2", "views_raw": "36400138", "date_raw": "3小时前", "link": "https://www.bilibili.com/video/BV1rc5E6xEuX/"},
    ]
    parsed = parse_video_data(test)
    for v in parsed:
        print(f"[{v['score']:.4f}] {fmt_views(v['views']):>8s} | {v['date_raw']} | {v['duration']} | {v['title']}")
