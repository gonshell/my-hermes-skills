#!/usr/bin/env python3
"""
bing_to_bili.py — YouTube 不可达时的 YouTube-AI 早间档/晚间档 cron 数据获取脚本

当 YouTube 返回 HTTP 000 时，用这个脚本：
  1. curl Bing 视频搜索 1-2 个 query
  2. **BVID 直取**（不依赖 aria-label 语言，2026-06-16 实测首选方案）
  3. curl B站 search API `/x/web-interface/search/type?keyword=...&order=pubdate`
     — 2026-06-20 晚间档实测：5/7 query 触发 412 节流，命中 2-3 个即可
  4. 批量调 B站 /x/web-interface/view?bvid= API 拿真实标题/播放量/时长
  5. 4 维质量过滤（view >= 5 / duration > 0 / title len >= 4 / owner len >= 2）
  6. 输出 longs / shorts / news 三个 JSON 列表供 XML 生成使用

实测：2026-06-14 06:01 CST 跑通，~2 分钟拿到 60+ 条候选 -> 取 TOP 25
      2026-06-20 20:05 CST 升级：BVID 直取 + 4 维质量过滤 + B站 search API 节流策略

用法：
  python3 bing_to_bili.py                       # 写 /tmp/curated.json
  python3 bing_to_bili.py --today-only          # news 仅保留今天发布的（晚间档建议）
  python3 bing_to_bili.py --out /tmp/x.json

依赖：仅 stdlib（urllib, json, re, subprocess, time, datetime）
"""
# 旧版本（本文件 2026-06-20 之前）依赖 aria-label*="来源" 提取，**已被废弃**：
#   - aria-label 格式随网络出口语言变化（中文含"来源"、英文不含）
#   - 英文出口下 `aria-label*="来源"` 匹配 0 条
# 现版本改用 BVID 直取（`/video/BV[A-Za-z0-9]{10}`），对出口语言无依赖。
# 详见 references/youtube-unreachable-fallback.md "BVID 直取为首选" 一节。

import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
BILI_REF = "https://www.bilibili.com/"
CST = timezone(timedelta(hours=8))

# Bing query 列表：1 个泛 query 拿长视频/短视频，第 2 个偏新闻拿新发
BING_QUERIES = [
    "https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+OpenAI+Gemini+trending+2026&FORM=HDRSC6",
    "https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+trending+2026&FORM=HDRSC6&first=31",
]
# B站 search API query 列表 — 2026-06-20 实测 5/7 触发 412 节流，命中 2-3 个即可
# 关键词按命中率从高到低排：AI日报 > ChatGPT > AI早报 > Claude/Gemini(412 概率高)
BILI_API_QUERIES = [
    ("AI%E6%97%A5%E6%8A%A5", "pubdate"),   # AI日报
    ("ChatGPT", "pubdate"),
    ("AI%E6%97%A9%E6%8A%A5", "pubdate"),   # AI早报
]


def curl(url, dest):
    """curl -sL with chrome UA. Returns True on success."""
    try:
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "30", "-A", UA, url, "-o", dest],
            check=True, capture_output=True, timeout=35,
        )
        return True
    except Exception as e:
        print(f"[curl] FAIL {url}: {e}")
        return False


def extract_bvids_from_bing(html):
    """从 Bing HTML 提取 BVID（不依赖 aria-label 语言，2026-06-16 首选方案）"""
    return list(set(re.findall(r'/video/(BV[A-Za-z0-9]{10})', html)))


def fetch_bili_api(keyword_enc, order, page=1):
    """调 B站 search API `/x/web-interface/search/type`（晚间档新发主要来源）

    2026-06-20 实测 5/7 query 触发 412 节流；调用方需做好重试/降级
    返回 [(bvid, title, author, play), ...]
    """
    url = (f"https://api.bilibili.com/x/web-interface/search/type"
           f"?keyword={keyword_enc}&search_type=video&order={order}"
           f"&page={page}&page_size=20")
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Referer': 'https://search.bilibili.com/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'identity',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 412:
            print(f"[bili-api] {keyword_enc}|{order}: 412 throttled")
            return []
        raise
    results = data.get('data', {}).get('result', []) or []
    out = []
    for x in results:
        if x.get('bvid'):
            out.append((x['bvid'], x.get('title', ''), x.get('author', ''), int(x.get('play', 0) or 0)))
    print(f"[bili-api] {keyword_enc}|{order}: {len(out)} bvs (code={data.get('code')})")
    return out


def fetch_bili_view(bv):
    """调 B站 /x/web-interface/view?bvid= 拿真实数据。"""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bv}"
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Referer': BILI_REF,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'identity',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {'bv': bv, 'error': str(e)}
    d = data.get('data', {})
    if not d:
        return {'bv': bv, 'error': 'no_data'}
    return {
        'bv': bv,
        'title': d.get('title', ''),
        'owner': d.get('owner', {}).get('name', ''),
        'view': int(d.get('stat', {}).get('view', 0)),
        'duration': int(d.get('duration', 0)),  # 秒
        'pubdate': int(d.get('pubdate', 0)),     # unix ts
    }


# 强 AI 关键词白名单（晚间档 4 维质量过滤维度之一）
AI_KW = [
    'AI', 'Gpt', 'gpt', 'ChatGpt', 'chatgpt', 'Claude', 'claude', 'Gemini', 'gemini',
    '大模型', '大语言', 'LLM', 'llm', '深度学习', '神经网络', '机器学习', 'AGI', 'agi',
    'Sora', 'Midjourney', 'Stable Diffusion', 'Diffusion', 'ComfyUI', 'Copilot', 'cursor',
    'MCP', 'Agent', '智能体', 'Llama', 'llama', 'Mistral', 'mistral', 'DeepSeek', 'deepseek',
    '文心一言', '通义千问', '盘古', '混元', 'Kimi', 'kimi', 'Grok', 'grok',
    'AI日报', 'AI早报', 'AI周报', 'AI工具', 'OpenAI', 'openai', 'Anthropic', 'anthropic',
    'Prompt', '提示词', 'Transformer', 'transformer', 'MoE', 'Mamba', 'mamba',
    'RAG', 'rag', 'Embedding', 'embedding', 'Token', 'token', 'LangChain', 'langchain',
    'Hugging Face', 'HuggingFace', 'GitHub Copilot', 'DALL', 'Whisper', 'Runway', 'Pika', 'Suno', 'Udio',
    'Robot', '机器狗', '波士顿动力', '具身智能', '自动驾驶', 'FSD',
    '图像生成', '视频生成', '语音合成', 'TTS', 'ASR', 'NLP', '强化学习', 'RLHF', 'DPO',
    'AI编程', 'Cursor', 'Codeium', 'Cline', 'Continue', 'GenAI', 'AIGC', '超级智能',
]


def is_ai_relevant(title):
    """粗过滤 Adobe Illustrator / 赌博 / 武器 / 纯娱乐等假阳性"""
    t = title.lower()
    if 'illustrator' in t:
        return False
    bad = ['赌', '押注', '理财', '赌狗', '赌资', '赌场', '彩票',
           '美瞳', '美甲', '减肥', '瘦身', '按摩', '养生', '医美', '植发', '隆胸', '相亲']
    if any(k in title for k in bad):
        return False
    bad_ent = ['星际争霸', '外星人', '虫族', '俘虏', '波兰球', 'NBA', '小病',
               '成为虫族', '世界杯', '足球', '篮球', 'CBA', 'F1', '赛车', '漫展', 'cos']
    if any(k in title for k in bad_ent):
        return False
    return True


def looks_like_ai(title):
    return any(k in title for k in AI_KW)


def is_quality(d, min_view=5, min_title_len=4, min_owner_len=2):
    """4 维质量门（2026-06-20 晚间档实测）：
    维度1: view >= min_view (拒 0-view 灌水)
    维度2: duration > 0 (拒异常条目)
    维度3: title len >= min_title_len (拒"chatgpt"/"AI"单字)
    维度4: owner len >= min_owner_len (拒"user_xxx"自动账号)
    """
    if d.get('view', 0) < min_view:
        return False
    if d.get('duration', 0) <= 0:
        return False
    t = (d.get('title', '') or '').strip()
    if len(t) < min_title_len:
        return False
    o = (d.get('owner', '') or '').strip()
    if len(o) < min_owner_len:
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/curated.json')
    ap.add_argument('--keep-n', type=int, default=70, help='最多保留多少 BVID 去查 API')
    ap.add_argument('--today-only', action='store_true',
                    help='当日新发仅保留今天发布的（晚间档建议开启）')
    args = ap.parse_args()

    all_bvids = []

    # Step 1: curl Bing -> BVID 直取
    for i, q in enumerate(BING_QUERIES):
        path = f"/tmp/bing_{i}.html"
        if curl(q, path):
            try:
                with open(path) as f:
                    html = f.read()
                bvs = extract_bvids_from_bing(html)
                print(f"[bing] {q[:60]}... -> {len(bvs)} bvids")
                for b in bvs:
                    all_bvids.append((b, 'bing'))
            except Exception as e:
                print(f"[bing] read FAIL: {e}")

    # Step 2: B站 search API -> 拿当日新发 BVID（晚间档主路径，2026-06-20 升级）
    for kw, order in BILI_API_QUERIES:
        try:
            api_bvs = fetch_bili_api(kw, order)
            for bv, _t, _a, _p in api_bvs:
                all_bvids.append((bv, 'bili'))
        except Exception as e:
            print(f"[bili-api] FAIL {kw}|{order}: {e}")
        time.sleep(0.4)  # 限速避免 412

    # 去重
    seen = set()
    deduped = []
    for bv, src in all_bvids:
        if bv in seen:
            continue
        seen.add(bv)
        deduped.append((bv, src))
    print(f"[total] {len(deduped)} unique bvids, fetching top {args.keep_n}")

    # Step 3: 批量调 B站 /view API 拿权威数据
    enriched = []
    for i, (bv, src) in enumerate(deduped[:args.keep_n]):
        d = fetch_bili_view(bv)
        if d and 'title' in d:
            d['source'] = src
            enriched.append(d)
        if i % 20 == 0:
            print(f"  [{i+1}/{min(args.keep_n, len(deduped))}] {bv} {(d or {}).get('title','')[:40]}")
        time.sleep(0.25)

    # Step 4: 过滤 + 分类
    valid = [d for d in enriched
             if is_ai_relevant(d.get('title', '')) and looks_like_ai(d.get('title', ''))]
    print(f"[valid] {len(valid)} AI-relevant videos")

    longs_pool = [d for d in valid if d['duration'] > 180]
    shorts_pool = [d for d in valid if 0 < d['duration'] <= 180]

    def by_view(ds):
        return sorted(ds, key=lambda x: -x['view'])

    def by_pub(ds):
        return sorted(ds, key=lambda x: -x['pubdate'])

    # news 走 4 维质量过滤
    news_pool = [d for d in valid if is_quality(d)]
    if args.today_only:
        today = datetime.now(CST).strftime("%Y-%m-%d")
        news_pool = [d for d in news_pool
                     if datetime.fromtimestamp(d['pubdate'], CST).strftime("%Y-%m-%d") == today]
        print(f"[news] today's only: {len(news_pool)} videos (from {len(valid)} AI-relevant)")

    result = {
        'longs': by_view(longs_pool)[:10],
        'shorts': by_view(shorts_pool)[:5],
        'news': by_pub(news_pool)[:10],
    }

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[done] wrote {args.out}: {len(result['longs'])} longs, "
          f"{len(result['shorts'])} shorts, {len(result['news'])} news")


if __name__ == '__main__':
    main()
