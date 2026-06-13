# bilibili-ai-trending — 2026-06-13 实测增量

> 本文是对 `bilibili-ai-trending-pitfalls-2026-06-12.md` 的补充。
> **旧文件保留为历史记录**，不要删；本节是当前推荐做法。

## 1. /view 的 `tag` 字段可能整批返回空字符串（2026-06-13 实测）

实测 100 条 bvid 调 `https://api.bilibili.com/x/web-interface/view?bvid=xxx`：
- `data.tag` 全部返回空字符串（100/100 = 100%）
- 其它字段（`title` / `owner.name` / `stat.view` / `stat.like` / `duration`）正常

**影响**：2026-06-11 引入的 "tag 集合求交" 过滤升级在此场景**完全失效**，必须降级到"标题强关键词"过滤。

**应对策略**（两段式，先 tag 后 title-strong 兜底）：
```python
def is_real_ai(v):
    # 1) tag 求交（首选，2026-06-11 推荐）
    tag_list = [t.strip() for t in v.get("tag", "").replace("，", ",").split(",") if t.strip()]
    if tag_list:  # tag 非空才走这条路
        ai_tags = {x.lower() for x in [...]}  # 见 06-11 pitfall
        for t in tag_list:
            if t.lower() in ai_tags:
                return True, f"tag:{t}"
        for t in tag_list:
            for kw in ai_substrings:
                if kw.lower() in t.lower():
                    return True, f"tag-match:{t}:{kw}"
    # 2) 标题强关键词兜底（tag 为空时唯一依据）
    STRONG_KW = [
        "ChatGPT", "DeepSeek", "deepseek", "Claude", "Sora", "Kimi", "豆包",
        "通义千问", "文心一言", "AIGC", "OpenAI", "Anthropic", "Llama", "LLaMA",
        "Gemini", "Grok", "Copilot", "Midjourney", "Stable Diffusion",
        "英伟达", "NVIDIA", "Prompt", "提示词", "智能体", "大模型", "AGI", "RAG",
        "具身智能", "AI绘画", "AI视频", "Diffusion", "扩散模型",
        "ComfyUI", "人工智能", "机器学习", "深度学习", "神经网络",
        "MCP", "AI工具", "AI生成", "AI应用", "AI模型", "AI配音",
        "AI数字人", "Transformer", "MoE", "Agent", "Mamba", "LangChain",
        "大语言模型", "LLM", "LoRA", "GenAI", "Qwen", "Qwen3", "Deep Learning"
    ]
    for kw in STRONG_KW:
        if kw in v.get("title", ""):
            return True, f"title-strong:{kw}"
    # 3) 单词 "AI"（word-boundary 避免误中 Illustrator/Aim）
    import re
    if re.search(r'(?<![a-zA-Z])AI(?![a-zA-Z])', v.get("title", "")):
        return True, "title-strong:AI"
    return False, "no-match"
```

**根因猜测**：B站 `/view` API 可能对短时间内大批量请求做了节流降级（返回简化版数据），或账号/IP 被识别为爬虫导致 tag 字段被截断。两种缓解方案：
- 在 100 条 /view 请求之间加更长 sleep（0.3s 而不是 0.1s）
- 错峰分批（拆成 25 条 × 4 批，批间 sleep 2s）

## 2. 标题强关键词清单需要补：`Mamba` / `Deepseek`(lowercase s) / `Deep Learning`

2026-06-13 实测漏掉的真实 AI 视频（已修正）：
- **Mamba 模型教程**（B 站 AI 教程频道）—— `Mamba` 是 State Space Model 架构，2024-2026 主流 LLM 架构之一，关键词必须含
- **Deepseek**（lowercase s，驼峰变体）—— 用户标题常用 "Deepseek部署"、"deepseek本地化" 等写法
- **Deep Learning**（带空格）—— 老教程 UP 主（吴恩达等）的英文标题常用

## 3. "AI" 单词用 word-boundary 正则处理，避免 Illustrator/Aim/Mai 误中

旧做法：直接 `if "AI" in title` → 误中 Adobe Illustrator、Aim High、Game AI 等。
**正确做法**（必须配合已有 K-pop/Illustrator 黑名单）：
```python
import re
if re.search(r'(?<![a-zA-Z])AI(?![a-zA-Z])', title):
    return True
```

**关键洞察**：word-boundary 单独**不够**，必须叠加 K-pop/Illustrator 黑名单 —— 因为某些标题（如 "Adobe Illustrator"）中"AI"前后是字母也会被 word-boundary 误判命中（实际上是 Illustrator 字符串里的子串 AI，不是单词 AI，但 regex 不区分）。黑名单过滤是必要的第二道防线。

## 4. 完整工作流（2026-06-13 验证版，含 tag 降级路径）

```python
import json, gzip, urllib.parse, urllib.request, time, re, random

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ..."
def fetch_json(url, retries=2):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Referer": "https://www.bilibili.com",
                "Accept": "application/json, text/plain, */*",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                if data[:2] == b'\x1f\x8b':
                    data = gzip.decompress(data)
                return json.loads(data.decode("utf-8"))
        except Exception:
            time.sleep(0.3 + random.random() * 0.3)
    return None

KEYWORDS = [29 个关键词，见 bilibili-ai-trending-pitfalls-2026-06-12.md]
all_videos = {}
for kw in KEYWORDS:
    for page in [1, 2]:
        url = f"https://api.bilibili.com/x/web-interface/search/all/v2?keyword={urllib.parse.quote(kw)}&page={page}&page_size=20"
        data = fetch_json(url)
        if data and data.get("code") == 0:
            for r in data.get("data", {}).get("result", []):
                if r.get("result_type") == "video":
                    for v in r.get("data", []):
                        bvid = v.get("bvid")
                        if not bvid: continue
                        title_clean = re.sub(r'<[^>]+>', '', v.get("title", ""))
                        existing = all_videos.get(bvid)
                        if not existing or (v.get("play", 0) or 0) > existing.get("view", 0):
                            all_videos[bvid] = {
                                "title": title_clean, "bvid": bvid,
                                "view": v.get("play", 0) or 0,
                                "duration_str": v.get("duration", ""),
                                "author": v.get("author", ""), "keyword": kw,
                            }
        time.sleep(0.25 + random.random() * 0.15)

# 取 top 100 按 play 粗排，/view enrichment
sorted_v = sorted(all_videos.values(), key=lambda x: -x["view"])
top_100 = sorted_v[:100]
enriched = []
for v in top_100:
    d = fetch_json(f"https://api.bilibili.com/x/web-interface/view?bvid={v['bvid']}")
    if d and d.get("code") == 0:
        s = d["data"]
        enriched.append({
            "bvid": v["bvid"],
            "title": s.get("title", v["title"]),
            "owner": s.get("owner", {}).get("name", "") or v.get("author", ""),
            "view": s.get("stat", {}).get("view", 0),
            "like": s.get("stat", {}).get("like", 0),
            "duration": s.get("duration", 0),
            "tag": s.get("tag", ""),  # 注意：可能为空！
            "desc": s.get("desc", "")[:200],
            "keyword": v.get("keyword", ""),
        })
    time.sleep(0.1 + random.random() * 0.05)

# 过滤（黑名单 + is_real_ai，见上面两段式实现）
ai_videos = [v for v in enriched if not is_blacklisted(...) and is_real_ai(v)[0]]

# 切分
LONG_THRESHOLD = 300
long_v = sorted([v for v in ai_videos if v["duration"] > LONG_THRESHOLD], key=lambda x: -x["view"])[:15]
short_v = sorted([v for v in ai_videos if v["duration"] <= LONG_THRESHOLD], key=lambda x: -x["view"])[:7]
```

## 5. 与前次文档的关系

- `bilibili-ai-trending-pitfalls-2026-06-12.md`：仍然准确。
- `bilibili-ai-trending-pitfalls-2026-06-11.md`：tag 求交方法仍然准确，但本节补充了 tag 为空时的降级路径。
- **新发现统一记录到本文档**，旧文件不再修改。

## 6. 输出 XML 模板确认（沿用 2026-06-12）

```xml
<docx><title>Bilibili AI热门视频</title><body>
<BilibiliAITrending>
<h1>Bilibili AI热门视频 · {YYYY年MM月DD日}</h1>
<h2>热门长视频 TOP 15</h2>
<p>按播放量排序</p>
<ol>
<li seq="auto"><a href="...">标题</a> ｜UP主：xxx ｜播放：xxx ｜点赞：xxx ｜时长：xxx</li>
...
</ol>
<h2>热门小视频 TOP 7</h2>
<p>按播放量排序</p>
<ol>
<li seq="auto"><a href="...">标题</a> ｜UP主：xxx ｜播放：xxx ｜点赞：xxx ｜时长：xxx</li>
...
</ol>
</BilibiliAITrending>
</body></docx>
```
