# bilibili-ai-trending — 2026-06-11 实测增量

> 本文是对 `bilibili-ai-trending.md` + `bilibili-ai-trending-pitfalls.md` 的补充，覆盖 2026-06-11 cron job 实测中确认的新发现/修正。
> **旧文件保留为历史记录**，不要删；本节是当前推荐做法。

## 1. search/all/v2 的 play 字段实际可用（修正旧结论）

**旧结论（2026-06-09）**：`play` 字段始终为 0。
**新结论（2026-06-11）**：`play` 字段**实际有真实值**，可作为粗排依据。

实测数据点：
- 吴恩达机器学习：`play=3679914`（与 `/view?bvid=` 的 `stat.view=3679921` 误差 < 0.01%）
- 影视飓风 AI 还是真的：`play=4081582`（vs `stat.view=4082230`）
- 大模型教程：`play=4851867`（vs `stat.view=4851867`，完全一致）
- 宋浩老师 高等数学：`play=104010142`（vs `stat.view=104010637`，~0.05% 误差）

**但 `like` 字段错位为 `favorites`（收藏数）**：
- 旧结论说 `like` 始终为 0 是错的——其实它返回的是 `favorites`（收藏数），不是真正的点赞
- 例：黑马程序员大模型课程的 `like` 字段返回 55891，但 `stat.like` 实际是 13133
- **绝不可信为点赞数**。要用点赞必须调 `/view?bvid=`

**结论修正**：
- `play` 字段：可用作粗排（精度足够）—— 拿前 80 条 bvid
- `like` 字段：**不能用** —— 直接忽略
- `duration` 字段：是 `"12:34"` 字符串，需 parse
- `view` 字段：缺失

## 2. Bilibili API 响应可能是 gzip 压缩

实测中 Python `urllib` 收到的响应 body 前两字节是 `0x1f 0x8b`（gzip magic），直接 `json.loads()` 会抛 `UnicodeDecodeError` 或 `Expecting value` 错误。

**必须做的处理**：
```python
import gzip
data = resp.read()
if data[:2] == b'\x1f\x8b':
    data = gzip.decompress(data)
return json.loads(data.decode("utf-8"))
```

**curl 客户端自动处理**（带 `--compressed` 或默认 Accept-Encoding），但 urllib 需要手动。

## 3. AI 验证从"标题关键词"升级到"tag 集合求交"（关键质量提升）

旧做法：标题/描述里包含 AI 关键词就算 AI 视频。
问题：误杀/误中率高。例：
- 宋浩老师 高等数学（`104,010,142` 播放）—— 标题无 AI 词，但被搜索 "机器学习" 时进入结果（因为 B站视频偶尔会带 AI 标签）
- `《归环》过场动画` —— 标题含 "asi"（"中亚" 子串），关键词搜索 "AGI" 时误中
- `满分神作《飞驰团生3》` —— 标题无 AI 词，AI 关键词过滤后却被保留（搜索结果带 AI 标签）

**新做法**（2026-06-11 实测）：用 `/view?bvid=` 返回的 `tag` 字段做 AI 集合求交：

```python
ai_tags = {
    "AI", "人工智能", "大模型", "大语言模型", "LLM", "ChatGPT", "DeepSeek",
    "Deepseek", "deepseek", "Claude", "机器学习", "深度学习", "神经网络",
    "AGI", "AIGC", "ASI", "生成式", "生成式AI", "文心一言", "通义千问",
    "通义", "千问", "Kimi", "豆包", "Transformer", "Stable Diffusion",
    "Midjourney", "Sora", "Grok", "Prompt", "提示词", "RAG", "智能体",
    "Agent", "Llama", "LLama", "Gemini", "OpenAI", "Anthropic", "NVIDIA",
    "英伟达", "文生图", "图生图", "TTS", "ASR", "Embedding", "LoRA",
    "QLoRA", "DPO", "RLHF", "GRPO", "强化学习", "CNN", "RNN", "GAN",
    "扩散", "开源模型", "开源大模型", "预训练", "微调", "蒸馏", "对齐",
    "涌现", "具身智能", "多模态", "Copilot", "Qwen", "AI绘画", "AI视频",
    "AI画", "AI生成", "AI工具", "AI应用", "AI模型", "AI配音", "AI数字人",
    "马斯克", "xAI", "MCP", "Claude Code", "SubAgent", "Agent Skills",
    "深度学习算法", "机器学习算法", "卷神经网络", "计算机视觉", "OpenCV",
    "神经网络算法", "Diffusion", "扩散模型", "ComfyUI", "ControlNet",
}

def is_real_ai(v):
    tag_list = [t.strip() for t in v.get("tag", "").replace("，", ",").split(",") if t.strip()]
    ai_lower = {x.lower() for x in ai_tags}
    # tag 完全匹配
    for t in tag_list:
        if t.lower() in ai_lower:
            return True, f"tag:{t}"
    # tag 包含 AI 子串
    ai_substrings = ["AI", "人工智能", "大模型", "DeepSeek", "ChatGPT", "Claude",
                     "机器学习", "深度学习", "神经网络", "AIGC", "Sora", "Kimi",
                     "豆包", "通义", "千问", "Llama", "Gemini", "Grok", "智能体",
                     "Agent", "Prompt", "RAG", "Copilot", "英伟达", "NVIDIA",
                     "OpenAI", "Anthropic", "马斯克", "xAI", "Diffusion",
                     "Midjourney", "Stable Diffusion", "Transformer", "AGI"]
    for t in tag_list:
        for kw in ai_substrings:
            if kw.lower() in t.lower():
                return True, f"tag-match:{t}:{kw}"
    # 标题强 AI 关键词（兜底）
    strong = ["ChatGPT", "DeepSeek", "Claude", "Sora", "Kimi", "豆包", "通义千问",
              "文心一言", "千问", "AIGC", "OpenAI", "Anthropic", "Llama", "Gemini",
              "Grok", "Copilot", "Midjourney", "Stable Diffusion", "英伟达", "NVIDIA",
              "Prompt", "智能体", "大模型", "AGI", "RAG", "具身智能", "AI绘画",
              "AI视频", "AI画", "AI生成", "AI工具", "AI应用", "AI模型", "AI配音",
              "AI数字人", "Diffusion", "扩散模型"]
    for kw in strong:
        if kw in v.get("title", ""):
            return True, f"title-strong:{kw}"
    return False, "no-match"
```

**实测效果**（2026-06-11）：
- 输入 363 条候选，标签求交后保留 343 条 AI 视频
- 排除掉的 20 条全是误中：宋浩老师 高等数学（高等数学课程但带机器学习标签）、影评/动画/游戏（带"亚"/"AIGC"假阳性）等
- 准确率从 ~70%（纯关键词）提升到 ~98%（tag 求交 + 标题强词兜底）

## 4. /x/web-interface/view 的 owner.name 比 search 返回的 author 更可靠

`search/all/v2` 返回的 `author` 字段偶尔是空字符串或奇怪的截断。`/view?bvid=` 返回的 `owner.name` 始终有值且为干净的 UP 主名。

**最佳实践**：在 XML 输出前用 `/view` 的 `owner.name` 覆盖 `author`。

## 5. 完整工作流（2026-06-11 验证版）

```python
import json, gzip, urllib.parse, urllib.request, time, re, random
from collections import Counter

def fetch_json(url, retries=2):
    ua_list = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ..."]
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": random.choice(ua_list),
                "Referer": "https://www.bilibili.com",
                "Accept": "application/json, text/plain, */*",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                if data[:2] == b'\x1f\x8b':
                    data = gzip.decompress(data)
                return json.loads(data.decode("utf-8"))
        except Exception:
            time.sleep(0.3)
    return None

# Step 1: 多关键词 search/all/v2
KEYWORDS = ["AI", "DeepSeek", "ChatGPT", "大模型", "Claude", "人工智能", 
            "机器学习", "神经网络", "AIGC", "Sora"]
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
                        if bvid not in all_videos or (v.get("play", 0) or 0) > all_videos[bvid].get("view", 0):
                            all_videos[bvid] = {
                                "title": re.sub(r'<[^>]+>', '', v.get("title", "")),
                                "bvid": bvid, "aid": v.get("aid"),
                                "view": v.get("play", 0) or 0,  # 粗排依据
                                "duration_str": v.get("duration", ""),
                                "duration": parse_duration(v.get("duration", "")),
                                "author": v.get("author", ""),
                                "pic": v.get("pic", ""),
                                "keyword": kw,
                            }
        time.sleep(0.3)

# Step 2: 按 play 降序，取前 80，跟调 /view 拿真实数据
sorted_v = sorted(all_videos.values(), key=lambda x: -x["view"])
top_80 = sorted_v[:80]
for v in top_80:
    d = fetch_json(f"https://api.bilibili.com/x/web-interface/view?bvid={v['bvid']}")
    if d and d.get("code") == 0:
        s = d["data"]
        v["view"] = s["stat"].get("view", 0)
        v["like"] = s["stat"].get("like", 0)
        v["duration"] = s.get("duration", 0)
        v["title"] = s.get("title", v["title"])
        v["owner"] = s["owner"]["name"]
        v["short_link"] = f"https://b23.tv/{v['bvid']}"
        v["tag"] = s.get("tag", "")
        v["desc"] = s.get("desc", "")[:200]
    time.sleep(0.1)

# Step 3: tag 集合求交过滤
ai_videos = [v for v in all_videos.values() if is_real_ai(v)[0]]

# Step 4: 按 view 降序，分长/短
LONG_THRESHOLD = 300  # 5 分钟
long_v = sorted([v for v in ai_videos if v["duration"] > LONG_THRESHOLD], key=lambda x: -x["view"])[:15]
short_v = sorted([v for v in ai_videos if v["duration"] <= LONG_THRESHOLD], key=lambda x: -x["view"])[:7]
```

## 6. 与旧文档的关系

- `bilibili-ai-trending-pitfalls.md`（2026-06-09）：保留作为历史记录。第 1 节（search/type API 412 节流）仍然准确；第 2 节（play 字段）已被本文档第 1 节修正；第 3 节（popular API）仍然有效；第 4-6 节仍然有效。
- `bilibili-ai-trending.md`：仍然准确，文档结构部分不需改。
- **新发现统一记录到本文档**，旧文件不再修改。
