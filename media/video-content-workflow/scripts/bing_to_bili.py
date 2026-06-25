#!/usr/bin/env python3
"""
bing_to_bili.py - YouTube 不可达时的 YouTube-AI 早间档/晚间档 cron 数据获取脚本

当 YouTube 返回 HTTP 000 时，用这个脚本：
  1. curl Bing 视频搜索 1-2 个 query
  2. **BVID 直取**（不依赖 aria-label 语言，2026-06-16 实测首选方案）
  3. curl B站 search API `/x/web-interface/search/type?keyword=...&order=pubdate`
     — 2026-06-20 晚间档实测：5/7 query 触发 412 节流，命中 2-3 个即可
     — 2026-06-24 晚间档实测：round 2 加 15 个中文 AI 复合 query，14/15 命中
  4. 批量调 B站 /x/web-interface/view?bvid= API 拿真实标题/播放量/时长
  5. 4 维质量过滤（view >= 5 / duration > 0 / title len >= 4 / owner len >= 2）
     + AI 关键词白名单 + 单字 query 黑名单（2026-06-22 早间档实测新增）
     + KPL/王者荣耀电竞赛黑名单（2026-06-24 晚间档实测新增）
     + 硬件评测 HARDWARE_KW 黑名单（2026-06-24 晚间档实测新增）
     + 不翻墙广告 SPAM_KW 黑名单（2026-06-24 晚间档实测新增）
  6. 输出 longs / shorts / news 三个 JSON 列表供 XML 生成使用

实测：2026-06-14 06:01 CST 跑通，~2 分钟拿到 60+ 条候选 -> 取 TOP 25
      2026-06-20 20:05 CST 升级：BVID 直取 + 4 维质量过滤 + B站 search API 节流策略
      2026-06-22 06:02 CST 升级：EXCLUDE_KW 黑名单 + AI_KW_STRICT 白名单
                         （剔除 Gemini 战队名/AI 电视台台标/纸尿裤/蚂蚁/鹅鸭杀等假阳性）
      2026-06-24 20:13 CST 升级：KPL电竞赛黑名单 + 硬件评测黑名单 + 不翻墙广告黑名单
                          + round 2 扩量策略（Bing 5 query + B站 24 query）

用法：
  python3 bing_to_bili.py                       # 写 /tmp/curated.json
  python3 bing_to_bili.py --today-only          # news 仅保留今天发布的（晚间档建议）
  python3 bing_to_bili.py --out /tmp/x.json
  python3 bing_to_bili.py --round-2             # 晚间档必加：扩量到 ~24 B站 query + 5 Bing query

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

# Bing query 列表：round 1 默认 2 个 query，round 2 加 3 个不同主题词
# 2026-06-24 实测：round 1 拿到 ~90 BVID，round 2 拿到 ~300 BVID（晚间档 news 凑齐 10 条关键）
BING_QUERIES = [
    "https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+OpenAI+Gemini+trending+2026&FORM=HDRSC6",
    "https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+trending+2026&FORM=HDRSC6&first=31",
]
BING_QUERIES_ROUND2 = [
    "https://www.bing.com/videos/search?q=GPT-5+Claude+Gemini+OpenAI+AI+trending+2026&FORM=HDRSC6",
    "https://www.bing.com/videos/search?q=AI+agent+LLM+Claude+latest+demo+viral&FORM=HDRSC6",
    "https://www.bing.com/videos/search?q=AI+tools+tutorial+demo+2026+latest&FORM=HDRSC6",
]
# B站 search API query 列表 — 2026-06-20 实测 5/7 触发 412 节流，命中 2-3 个即可
# 关键词按命中率从高到低排：ChatGPT > AI日报 > Claude/Gemini(412 概率高)
# 2026-06-22 早间档实测：移除 "AI" 单字（蚂蚁/纸尿裤假阳性严重）和 "Gemini"（战队名假阳性严重）
# 2026-06-22 晚间档实测：扩展至 8 个 query（AI早报/AI日报/Claude/Gemini/AI/DeepSeek/GPT/Sonnet），
#  每个 query 间隔 2.5s，遇到 412 时继续跑下一个，命中率约 6/8 = 75%
# 2026-06-24 晚间档实测：扩到 9 个 query（加 Sonnet），并加 14 个 round 2 中文复合 query
BILI_API_QUERIES = [
    ("ChatGPT", "pubdate"),
    ("AI%E6%97%A5%E6%8A%A5", "pubdate"),   # AI日报
    ("AI%E6%97%A9%E6%8A%A5", "pubdate"),   # AI早报
    ("Claude", "pubdate"),
    ("Gemini", "pubdate"),
    ("AI", "pubdate"),
    ("DeepSeek", "pubdate"),
    ("GPT", "pubdate"),
    ("Sonnet", "pubdate"),
]
# Round 2 中文复合 query — 避开单字 query 黑名单，命中真实 AI 内容（晚间档 cron 必跑）
# 2026-06-24 实测：14/15 命中 200 OK，每个 query 间隔 3.0s
BILI_API_QUERIES_ROUND2 = [
    ("AI%E5%B7%A5%E5%85%B7", "pubdate"),         # AI工具
    ("AI%E6%95%99%E7%A8%8B", "pubdate"),         # AI教程
    ("AI%E6%B5%8B%E8%AF%84", "pubdate"),         # AI测评
    ("AI%E5%AE%9E%E6%B5%8B", "pubdate"),         # AI实测
    ("AI%E6%8A%80%E6%9C%AF", "pubdate"),         # AI技术
    ("AI%E7%AE%97%E6%B3%95", "pubdate"),         # AI算法
    ("AI%E5%88%9B%E4%B8%9A", "pubdate"),         # AI创业
    ("AI%E7%A0%94%E5%8F%91", "pubdate"),         # AI研发
    ("AI%E5%BC%80%E5%8F%91", "pubdate"),         # AI开发
    ("AI%E5%9B%BD%E5%86%85", "pubdate"),         # AI国内
    ("AI%E5%A4%A7%E6%A8%A1%E5%9E%8B", "pubdate"), # AI大模型
    ("AI%E6%99%BA%E8%83%BD%E4%BD%93", "pubdate"), # AI智能体
    ("AI%E7%BF%BB%E8%AF%91", "pubdate"),         # AI翻译
    ("AI%E7%BC%96%E7%A8%8B", "pubdate"),         # AI编程
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

# 显式假阳性黑名单（2026-06-22 早间档实测新增）
# 用于剔除：Gemini 战队名、鹅鸭杀/狼人杀、王者装扮、纸尿裤、蚂蚁害虫等
# 2026-06-22 晚间档实测新增：游戏角色/战队（"五杀"/"新皮肤"/"长生小乔"）+ AI 广告灌水（"充值"/"解除限制"）
# 2026-06-24 晚间档实测新增：KPL/王者荣耀电竞赛选手「Gemini」（书源/子阳/蓝桉/虞姬/DRG/TES 等赛事关键词）
EXCLUDE_KW = [
    # AI 产品名/战队名/玩家名假阳性
    '鹅鸭杀', 'Goose', '狼人杀', '王者', '王者荣耀', '魔兽', '星际争霸',
    '外星人', '虫族', 'NBA', 'CBA', 'F1', '赛车', '漫展', 'cos',
    '世界杯', '足球', '篮球', '赌', '押注', '理财',
    '美瞳', '美甲', '减肥', '瘦身', '医美', '植发', '相亲',
    # 直播/电竞/装扮类（不属 AI 视频）
    '偶像', '主播', '直播间', '装扮', '一诺元射', '小乔大王',
    # 06:00 早间档实测的诡异命中
    '蚂蚁', '纸尿裤', '野草', '鹌鹑', '幼童', '父扑火', '甲酰胺',
    # AI 工具无关关键词
    '小病', '世界杯预测',
    # 20:00 晚间档实测新增：游戏角色/战队假阳性
    '五杀', 'CG', '新皮肤', '小乔', '长生', '大侠', '蛋仔', '鸭鸭',
    '勇者', '副本', '夏季赛', '常规赛', '锦标赛', '卡组', '水人',
    # 20:00 晚间档实测新增：AI 教程/广告灌水（基础）
    '充值', '升级订阅', '解除限制', '小白萌新', '小白无脑',
    '无需礼品卡', '一键升级',
    # 2026-06-24 晚间档实测新增：KPL/王者荣耀电竞赛选手「Gemini」
    # 这些赛事简称 + 选手名 + 比赛用语在 B站 KPL 频道极高频出现，
    # 「Gemini书源」「子阳」「虞姬」都是 2026 KPL 选手/术语
    'KPL', 'LPL', 'DRG', 'TES', 'SYG', 'WE', 'EWC', '书源', '子阳', '蓝桉',
    '虞姬', '虞美人', '虐杀', '打爆', '燃尽', '腐乳', '蓝桉虞姬',
]

# 硬件评测假阳性黑名单（2026-06-24 晚间档实测新增）
# 用于剔除：「黑爵T520AI鼠标」「XX AI 耳机」等型号带 AI 的硬件评测视频，
# 标题含「AI」但内容是鼠标/耳机/键盘/音箱评测，与人工智能无关
HARDWARE_KW = [
    '鼠标', '键盘', '耳机', '音箱', '手表', '手环', '充电宝', '路由器',
    '显示器', '摄像头', '平板', '音响', '麦克风', '扩展坞',
    # 2026-06-24 实测新增：型号带 "AI" 的硬件产品（精确匹配避免误伤 AI 教程视频）
    'AI鼠标', 'AI耳机', 'AI音箱', 'AI手表', 'AI摄像头', 'AI键盘',
]

# 国内免费/不翻墙广告灌水黑名单（2026-06-24 晚间档实测新增）
# 用于剔除：「国内真正无限制使用 ChatGPT-5.5」「100% 免费教程」
# 等看似 AI 教程实则充值引流的 UP 主广告视频
SPAM_KW = [
    # 2026-06-22 晚间档已加（基础）
    '国内免费', '无需翻墙', '不用翻墙', '无需礼品卡', '一键升级', '升级订阅',
    '小白萌新', '小白无脑', '解除限制', '充值', '国内快速开通', '两个月超值',
    '低价', '团购', '优惠码', 'super grok国内快速',
    # 2026-06-24 实测新增（UP主广告文案高频词）
    '国内真正的无限制', '100%免费', '100%成功', '白嫖',
    '免费,', '免费！',  # 标题里带这两个高概率是广告
    'VIP', '会员', 'token使用', 'token免费', '优惠',
    '国内使用', '如何注册', '注册教程',
]


def is_ai_relevant(title):
    """粗过滤 Adobe Illustrator / 赌博 / 武器 / 纯娱乐 / 硬件评测 / 广告灌水 等假阳性

    2026-06-24 实测升级：除 EXCLUDE_KW 外，还检查 HARDWARE_KW（鼠标/耳机等硬件评测）
    和 SPAM_KW（不翻墙广告 / 充值引流）。单看 AI 关键词白名单会漏掉：
    - 「黑爵T520AI鼠标实测」→ 命中 AI 但内容是硬件评测
    - 「国内真正的无限制使用ChatGPT-5.5」→ 命中 ChatGPT 但 UP 是广告号
    """
    t = title.lower()
    if 'illustrator' in t:
        return False
    if any(k in title for k in EXCLUDE_KW):
        return False
    # 2026-06-24 新增：硬件评测 + 不翻墙广告双层过滤
    if any(k in title for k in HARDWARE_KW):
        return False
    if any(k in title for k in SPAM_KW):
        return False
    return True


def looks_like_ai(title):
    """宽松 AI 关键词匹配 — 只要标题含任一 AI 模型/工具/产品/概念关键词

    2026-06-24 实测：单独匹配「Gemini」会被 KPL 选手名命中（书源/子阳/虞姬等上下文）。
    配套 is_ai_relevant 已通过 EXCLUDE_KW 剔除 KPL 内容，所以这里可以保持宽松。
    """
    return any(k in title for k in AI_KW)


def looks_like_ai_strict(title):
    """严格 AI 关键词匹配 — 2026-06-24 实测新增的备用入口

    单靠 'Gemini' 关键词不够，必须配合 AI 上下文。如果只用 Gemini 没有其他 AI 关键词，
    疑似 KPL 选手名（即使 EXCLUDE_KW 没命中）。正常路径用 looks_like_ai + EXCLUDE_KW 即可。
    """
    has_ai_kw = any(k in title for k in AI_KW)
    # 如果标题只有 Gemini 没有其他 AI 关键词，疑似 KPL 选手
    other_ai_count = sum(1 for k in AI_KW if k in title and k != 'Gemini' and k != 'gemini')
    if ('Gemini' in title or 'gemini' in title) and other_ai_count == 0:
        return False
    return has_ai_kw


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
    ap.add_argument('--news-min-view', type=int, default=5,
                    help='news 类最低 view 门槛（默认 5，配合 --today-only 时建议 50+）')
    ap.add_argument('--round-2', action='store_true',
                    help='晚间档必加：扩量到 5 Bing query + 24 B站 query，凑齐 news TOP 10'
                         '（2026-06-24 实测：从 9 候选 → 244 候选）')
    args = ap.parse_args()

    all_bvids = []

    # Step 1: curl Bing -> BVID 直取
    bing_queries = BING_QUERIES + (BING_QUERIES_ROUND2 if args.round_2 else [])
    for i, q in enumerate(bing_queries):
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
    bili_queries = BILI_API_QUERIES + (BILI_API_QUERIES_ROUND2 if args.round_2 else [])
    for kw, order in bili_queries:
        try:
            api_bvs = fetch_bili_api(kw, order)
            for bv, _t, _a, _p in api_bvs:
                all_bvids.append((bv, 'bili'))
        except Exception as e:
            print(f"[bili-api] FAIL {kw}|{order}: {e}")
        time.sleep(3.0 if args.round_2 else 2.5)
        # 2026-06-22 晚间档实测：0.4s 太激进，5/7 触发 412；2.5s 间隔命中率 6/8 = 75%
        # 2026-06-24 实测：3.0s 间隔更稳，14/15 round 2 query 命中 200 OK

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
    # AI 相关性：白名单（looks_like_ai） + 黑名单（is_ai_relevant）
    valid = [d for d in enriched
             if is_ai_relevant(d.get('title', '')) and looks_like_ai(d.get('title', ''))]
    print(f"[valid] {len(valid)} AI-relevant videos")

    longs_pool = [d for d in valid if d['duration'] > 180]
    shorts_pool = [d for d in valid if 0 < d['duration'] <= 180]

    def by_view(ds):
        return sorted(ds, key=lambda x: -x['view'])

    def by_pub(ds):
        return sorted(ds, key=lambda x: -x['pubdate'])

    # news 走 4 维质量过滤（晚间档：min_view=5 默认；早间档建议传 --news-min-view 50）
    news_pool = [d for d in valid if is_quality(d, min_view=args.news_min_view)]
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