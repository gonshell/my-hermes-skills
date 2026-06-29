# 2026-06-29 cron: known-good working script
# 关键变更（vs 2026-06-24）：
# 1. search/all/v2 → search/type?search_type=video（见 SKILL §10.1）
# 2. tier 判定用 main_title（取第一个 | 之前），剔除 |tag 后缀（见 SKILL §10.2）
# 3. /view 补全（必做，见 SKILL §4）
# 4. lark-cli 必须相对路径（见 SKILL §13）：复制 XML 到 cwd 再传 @relative

import subprocess, json, urllib.parse, time, os, re, html
from datetime import datetime, timezone, timedelta

# ============== KEYWORDS ==============
TIER1 = [
    r'ChatGPT', r'GPT-4', r'GPT-5', r'GPT-image', r'GPT Image', r'GPT-Image',
    r'GPT-4o', r'OpenAI', r'DeepSeek', r'Claude', r'Gemini', r'Grok',
    r'Cursor', r'Copilot', r'Trae', r'Dify', r'Coze', r'扣子', r'Manus',
    r'Midjourney', r'Stable Diffusion', r'ComfyUI', r'Sora', r'Vidu',
    r'Pika', r'Runway', r'Suno', r'可灵', r'即梦', r'Hailuo',
    r'Seedance', r'Seedream', r'LoRA', r'Qwen', r'Kimi',
    r'人工智能', r'大模型', r'大语言模型', r'机器学习', r'深度学习',
    r'神经网络', r'LLM', r'RAG', r'智能体', r'AIGC', r'AGI',
    r'提示词', r'Embedding', r'Transformer', r'文生视频', r'图生视频',
    r'具身智能', r'强化学习', r'AI Agent',
    r'AI编程', r'AI画图', r'AI绘画', r'AI工具', r'AI视频', r'AI生成',
    r'AI教程', r'AI数字人',
]
TIER2 = [r'\bAI\b', r'GPT', r'豆包', r'Prompt', r'Agent', r'数字人', r'Diffusion']
BLACKLIST = [
    r'Adobe Illustrator', r'Illustrator',
    r'远嫁', r'受虐', r'非洲',
    r'小豆包', r'豆包姐姐',
    r'进入MC', r'进入我的世界', r'傲娇粪', r'人森',
    r'玩MC', r'在MC', r'弱智吧', r'回复',
]
tier1_compiled = [re.compile(p) for p in TIER1]
blacklist_compiled = [re.compile(p, re.IGNORECASE) for p in BLACKLIST]

# ============== HELPERS ==============
def get_main_title(t):
    """取第一个 | 之前的主标题，剔除 |tag|tag 后缀（见 SKILL §10.2）"""
    if not t: return t
    if '|' not in t: return t.strip()
    return t.split('|', 1)[0].strip()

def strip_html(s):
    if not s: return ''
    return re.sub(r'<[^>]+>', '', s).strip()

def is_ai_main_title(main_title):
    if not main_title: return False
    for p in blacklist_compiled:
        if p.search(main_title): return False
    for p in tier1_compiled:
        if p.search(main_title): return True
    return False

def fmt_dur(d):
    if isinstance(d, str) and ':' in d: return d
    if isinstance(d, (int, float)):
        s = int(d)
        if s >= 3600:
            h, rem = divmod(s, 3600); m, sec = divmod(rem, 60)
            return f"{h}:{m:02d}:{sec:02d}"
        return f"{s//60}:{s%60:02d}"
    return "?"

def fmt_play(p):
    if p >= 100000000: return f"{p/100000000:.1f}亿"
    if p >= 10000: return f"{p/10000:.1f}万"
    return str(p)

def dur_secs(v):
    d = v['duration']
    if isinstance(d, (int, float)): return int(d)
    if isinstance(d, str) and ':' in d:
        try: return sum(int(x) * (60**i) for i, x in enumerate(reversed(d.split(':'))))
        except: return 0
    return 0

def curl_json(url, retries=3):
    for i in range(retries):
        try:
            r = subprocess.run(
                ['curl', '-sS', '--max-time', '15',
                 '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 13_7_8) AppleWebKit/537.36',
                 url],
                capture_output=True, text=True, timeout=20)
            if r.returncode == 0 and r.stdout:
                return json.loads(r.stdout, strict=False)
        except Exception:
            time.sleep(1)
    return None

# ============== 1. POPULAR ==============
candidates = {}
for pn in [1, 2]:
    data = curl_json(f"https://api.bilibili.com/x/web-interface/popular?ps=50&pn={pn}")
    if not data or data.get('code') != 0: continue
    for v in (data.get('data', {}).get('list') or []):
        bvid = v.get('bvid')
        if not bvid: continue
        candidates[bvid] = {
            'bvid': bvid,
            'title': v.get('title', ''),
            'desc': v.get('desc', ''),
            'author': v.get('owner', {}).get('name', ''),
            'play': v.get('stat', {}).get('view', 0) or 0,
            'like': v.get('stat', {}).get('like', 0) or 0,
            'duration': v.get('duration', 0) or 0,
            'source': 'popular',
        }
    time.sleep(0.2)

# ============== 2. SEARCH/TYPE?search_type=video（NOT all/v2） ==============
keywords = ['AI', 'ChatGPT', 'DeepSeek', 'Claude', '大模型', '人工智能',
            '机器学习', '深度学习', '神经网络', 'AIGC', 'AI编程', 'AI绘画', 'AI视频']
for kw in keywords:
    for order in ['click', 'pubdate']:
        for page in [1, 2]:
            url = (f"https://api.bilibili.com/x/web-interface/search/type"
                   f"?search_type=video&keyword={urllib.parse.quote(kw)}"
                   f"&order={order}&page={page}&pagesize=20")
            data = curl_json(url)
            if not data or data.get('code') != 0: continue
            for item in (data.get('data', {}).get('result') or []):
                if item.get('type') != 'video': continue
                bvid = item.get('bvid')
                if not bvid or bvid in candidates: continue
                candidates[bvid] = {
                    'bvid': bvid,
                    'title': item.get('title', ''),
                    'desc': item.get('description', ''),
                    'author': item.get('author', ''),
                    'play': item.get('play', 0) or 0,
                    'like': item.get('like', 0) or 0,
                    'duration': item.get('duration', '0:00') or '0:00',
                    'source': 'search',
                }
            time.sleep(0.2)

# ============== 3. /view ENRICHMENT ==============
need = [v for v in candidates.values() if v['source'] == 'search' or v['play'] == 0]
for v in need:
    data = curl_json(f"https://api.bilibili.com/x/web-interface/view?bvid={v['bvid']}")
    if data and data.get('code') == 0:
        d = data['data']
        stat = d.get('stat', {})
        v['play'] = stat.get('view', 0) or v['play']
        v['like'] = stat.get('like', 0) or 0
        v['duration'] = d.get('duration', v['duration'])
        v['author'] = d.get('owner', {}).get('name', v['author'])
        v['title_real'] = d.get('title', v['title'])  # 干净的实际标题
        v['desc'] = d.get('desc', '') or v['desc']
    time.sleep(0.08)

# ============== 4. AI FILTER（用 main_title，见 SKILL §10.2） ==============
ai = []
for v in candidates.values():
    raw_title = v.get('title_real', v.get('title', ''))
    main = get_main_title(strip_html(raw_title))
    v['title_main'] = main
    if is_ai_main_title(main):
        ai.append(v)

# ============== 5. PLAY >= 5000 ==============
filtered = [v for v in ai if v['play'] >= 5000]

# ============== 6. SPLIT + RANK ==============
long_v  = sorted([v for v in filtered if dur_secs(v) > 180],  key=lambda x: x['play'], reverse=True)[:15]
short_v = sorted([v for v in filtered if dur_secs(v) <= 180], key=lambda x: x['play'], reverse=True)[:7]

# ============== 7. BUILD XML ==============
bj = timezone(timedelta(hours=8))
today = datetime.now(bj).strftime('%Y-%m-%d')

def xml_escape(s):
    if not s: return ''
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;'))

def build_link(bv): return f"https://www.bilibili.com/video/{bv}"

L = []
L.append('<?xml version="1.0" encoding="UTF-8"?>')
L.append('<docx>')
L.append('  <title>Bilibili AI热门视频</title>')
L.append('  <body>')
L.append(f'    <h1>Bilibili AI热门视频 · {today}</h1>')
L.append('')
L.append('    <h2>热门长视频 TOP 15</h2>')
L.append('    <p>按播放量排序</p>')
L.append('    <ol>')
for v in long_v:
    L.append(f'      <li seq="auto"><a href="{build_link(v["bvid"])}">{xml_escape(v["title_main"])}</a> ｜UP主：{xml_escape(v.get("author",""))} ｜播放：{fmt_play(v["play"])} ｜点赞：{fmt_play(v.get("like",0))} ｜时长：{fmt_dur(v["duration"])}</li>')
L.append('    </ol>')
L.append('')
L.append('    <h2>热门小视频 TOP 7</h2>')
L.append('    <p>按播放量排序</p>')
L.append('    <ol>')
for v in short_v:
    L.append(f'      <li seq="auto"><a href="{build_link(v["bvid"])}">{xml_escape(v["title_main"])}</a> ｜UP主：{xml_escape(v.get("author",""))} ｜播放：{fmt_play(v["play"])} ｜点赞：{fmt_play(v.get("like",0))} ｜时长：{fmt_dur(v["duration"])}</li>')
L.append('    </ol>')
L.append('')
L.append('  </body>')
L.append('</docx>')
xml = '\n'.join(L)

# ============== 8. WRITE FILES (timestamped + canonical) ==============
ts = datetime.now(bj).strftime('%Y%m%d_%H%M%S')
with open(f'/tmp/merged_bilibili-ai_{ts}.xml', 'w', encoding='utf-8') as f:
    f.write(xml)
with open('/tmp/merged_bilibili-ai.xml', 'w', encoding='utf-8') as f:
    f.write(xml)
import shutil
shutil.copy('/tmp/merged_bilibili-ai.xml', os.path.expanduser('~/merged_bilibili-ai.xml'))

# ============== 9. LARK-CLI UPLOAD (relative path, 见 SKILL §13) ==============
result = subprocess.run(
    ['lark-cli', 'docs', '+update', '--api-version', 'v2',
     '--doc', 'Virbd3YyBoYK9XxqaZOccEGRnio',
     '--command', 'overwrite',
     '--content', '@merged_bilibili-ai.xml',
     '--doc-format', 'xml'],
    cwd=os.path.expanduser('~'),
    capture_output=True, text=True, timeout=60)
print(result.stdout)
print(result.stderr)
