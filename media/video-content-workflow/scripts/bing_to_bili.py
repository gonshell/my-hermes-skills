#!/usr/bin/env python3
"""
bing_to_bili.py — YouTube 不可达时的 YouTube-AI 早间档 cron 数据获取脚本

当 YouTube 返回 HTTP 000 时，用这个脚本：
  1. curl Bing 视频搜索 1-2 个 query
  2. grep aria-label 提取卡片 → 解析 BVID
  3. curl B站搜索 "AI早报" 按 pubdate 排序
  4. 批量调 B站 /x/web-interface/view?bvid= API 拿真实标题/播放量/时长
  5. 输出 longs / shorts / news 三个 JSON 列表供 XML 生成使用

实测：2026-06-14 06:01 CST 跑通，~2 分钟拿到 60+ 条候选 → 取 TOP 25。

用法：
  python3 bing_to_bili.py          # 写 /tmp/curated.json
  python3 bing_to_bili.py --out /tmp/x.json

依赖：仅 stdlib（urllib, json, re, subprocess, time, datetime）
"""

import argparse
import json
import re
import subprocess
import time
import urllib.request
from datetime import datetime

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
BILI_REF = "https://www.bilibili.com/"

# Bing query 列表：1 个泛 query 拿长视频/短视频，第 2 个偏新闻拿新发
BING_QUERIES = [
    "https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+OpenAI+Gemini+trending+2026&FORM=HDRSC6",
    "https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+trending+2026&FORM=HDRSC6&first=31",
]
BILI_QUERIES = [
    "https://search.bilibili.com/all?keyword=AI%E6%97%A9%E6%8A%A5&search_type=video&order=pubdate",
    "https://search.bilibili.com/all?keyword=AI%E6%97%A9%E6%8A%A5&search_type=video&order=pubdate&page=2",
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
    """从 Bing HTML 同时提取 aria-label + BVID"""
    out = []
    seen = set()
    for m in re.finditer(r'aria-label="([^"]*来源[^"]*)"', html):
        label = m.group(1)
        forward = html[m.end():m.end()+5000]
        bvm = re.search(r'/video/(BV[A-Za-z0-9]{10})', forward)
        if not bvm:
            continue
        bv = bvm.group(1)
        if bv in seen:
            continue
        seen.add(bv)
        out.append({'bv': bv, 'bing_label': label[:300]})
    return out


def extract_bvids_from_bili(html):
    """从 B站搜索页提取 BVID（去重）"""
    seen = set()
    out = []
    for m in re.finditer(r'/video/(BV[A-Za-z0-9]{10})', html):
        bv = m.group(1)
        if bv in seen:
            continue
        seen.add(bv)
        out.append(bv)
    return out


def fetch_bili_view(bv):
    """调 B站 /x/web-interface/view?bvid= 拿真实数据。"""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bv}"
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Referer': BILI_REF,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'identity',  # 避免手动 gzip 解码
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


def is_ai_relevant(title):
    """粗过滤 Adobe Illustrator / 赌博 / 武器 / 纯娱乐等假阳性"""
    t = title.lower()
    if 'illustrator' in t:
        return False
    bad = ['赌', '押注', '理财', '赌狗', '赌资', '赌场', '彩票']
    if any(k in title for k in bad):
        return False
    bad_mil = ['无人机空战', '对撞', '网枪', '霰弹', '航母', '军事']
    if any(k in title for k in bad_mil):
        return False
    bad_ent = ['星际', '外星', '虫族', '俘虜', '波兰球', '按摩', 'NBA', '面试时被HR', '小病', '成为虫族']
    if any(k in title for k in bad_ent):
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/curated.json')
    ap.add_argument('--keep-n', type=int, default=70, help='最多保留多少 BVID 去查 API')
    args = ap.parse_args()

    all_bvids = []

    # Step 1: curl Bing → extract BVIDs
    for i, q in enumerate(BING_QUERIES):
        path = f"/tmp/bing_{i}.html"
        if curl(q, path):
            try:
                with open(path) as f:
                    html = f.read()
                bing_results = extract_bvids_from_bing(html)
                print(f"[bing] {q[:60]}... → {len(bing_results)} bvids")
                for r in bing_results:
                    r['source'] = 'bing'
                    all_bvids.append(r)
            except Exception as e:
                print(f"[bing] read FAIL: {e}")

    # Step 2: curl B站 → extract BVIDs
    for i, q in enumerate(BILI_QUERIES):
        path = f"/tmp/bili_{i}.html"
        headers_extra = ['-H', f'Referer: {BILI_REF}']
        try:
            subprocess.run(
                ['curl', '-sL', '--max-time', '30', '-A', UA, *headers_extra, q, '-o', path],
                check=True, capture_output=True, timeout=35,
            )
            with open(path) as f:
                html = f.read()
            bvids = extract_bvids_from_bili(html)
            print(f"[bili] {q[:60]}... → {len(bvids)} bvids")
            for bv in bvids:
                all_bvids.append({'bv': bv, 'source': 'bili'})
        except Exception as e:
            print(f"[bili] FAIL: {e}")

    # 去重 + 限速
    seen = set()
    deduped = []
    for r in all_bvids:
        if r['bv'] in seen:
            continue
        seen.add(r['bv'])
        deduped.append(r)
    print(f"[total] {len(deduped)} unique bvids, fetching top {args.keep_n}")

    # Step 3: 批量调 B站 API
    enriched = []
    for i, r in enumerate(deduped[:args.keep_n]):
        data = fetch_bili_view(r['bv'])
        data['source'] = r['source']
        data['bing_label'] = r.get('bing_label', '')
        enriched.append(data)
        if i % 10 == 0:
            print(f"  [{i+1}/{min(args.keep_n, len(deduped))}] {data.get('bv')} {data.get('title','')[:40]}")
        time.sleep(0.3)  # 限速避免被 ban

    # Step 4: 过滤 + 分类
    valid = [d for d in enriched if 'title' in d and is_ai_relevant(d['title'])]
    print(f"[valid] {len(valid)} AI-relevant videos")

    longs_pool = [d for d in valid if d['duration'] > 180]
    shorts_pool = [d for d in valid if 0 < d['duration'] <= 180]

    def by_view(ds): return sorted(ds, key=lambda x: -x['view'])
    def by_pub(ds):  return sorted(ds, key=lambda x: -x['pubdate'])

    result = {
        'longs': by_view(longs_pool)[:10],
        'shorts': by_view(shorts_pool)[:5],
        'news': by_pub(valid)[:10],
    }

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[done] wrote {args.out}: {len(result['longs'])} longs, "
          f"{len(result['shorts'])} shorts, {len(result['news'])} news")


if __name__ == '__main__':
    main()
