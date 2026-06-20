# bilibili-ai-trending 参考（2026年6月实测）

## 数据源方案（已确认）

### ✅ search/all/v2 API — **主力方案（2026-06 实测有效）**

```bash
GET https://api.bilibili.com/x/web-interface/search/all/v2?keyword={keyword}&page=1
```

返回 JSON 中 `data.result[].data[]`，每项 `result_type in ['video', 'archive']` 的条目包含：
- `bvid`, `title`, `author`, `duration`, `play`（播放）, `like`（点赞）

**解析 duration**（格式如 `"12:34"` 或 `"4:0"`）：
```python
def parse_duration(dur_str):
    parts = str(dur_str).split(':')
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except:
        pass
    return 0
```

### ⚠️ search/type API — **间歇性可用，存在速率限制（2026-06-16 修正）**

> **2026-05-30 旧结论**（已修正）：声称"对所有关键词均返回 HTTP 412"。
> **2026-06-16 实测**：大部分关键词返回正常 JSON（code=0），但存在间歇性失败（返回空响应体）。
> 根因是反爬速率限制，不是 API 废弃。可用作补充数据源，需加 0.5-1s 延迟。

```bash
GET https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={keyword}&order=click&page=1&pagesize=20
```

返回 JSON 中 `data.result[]`，字段与 search/all/v2 类似但结构更扁平：
- `bvid`, `title`, `author`, `duration`（MM:SS 字符串）, `play`（整数或 `'-'`）, `like`（整数或字符串）
- `play`/`like` 可能是字符串 `'-'`，需安全转换

> **关键 Pitfall**：terminal() 的 50KB stdout cap 会导致大 JSON 被截断。**必须用 `-o /tmp/file.json` 写文件再读**，不要直接解析 terminal stdout。详见 `<references/bilibili-ai-trending-pitfalls-2026-06-16.md>`

### 排行榜 API — **主力数据源**

```bash
GET https://api.bilibili.com/x/web-interface/ranking/v2?type=all
```
- 返回 `data.list`，100条，按综合得分排序
- **按 AI 关键词过滤**后取 TOP 15 长视频 + TOP 7 小视频
- `owner.name` / `owner.uname` 可能同时为空，需批量调用 `/x/web-interface/view?bvid=xxx` 补全

### popular API — **可靠补充数据源（2026-06-17 更新）**

```bash
GET https://api.bilibili.com/x/web-interface/popular?ps=50&pn=1
```
- 返回 `data.list[]`，字段结构与 ranking API 相同（`title/bvid/owner.name/stat.view/stat.like/duration`）
- **pn=1~10 各 50 条，共 500 条**（2026-06-17 确认 pn=6~10 正常返回，不受限流）
- 与 ranking + search 合并去重后可得 500+ 条唯一视频
- **缺点**：全站热门，AI 内容占比极低（2026-06-19 实测：206 条中仅 1 条，~0.5%），**不能作为 AI 内容唯一数据源，必须搭配 search API**
- **优点**：稳定不限流，作为 search API 被限流时的 fallback
- **JSON 控制字符问题**：popular API 返回的 JSON 含控制字符，`json.loads(s)` 会失败。用 `json.loads(s, strict=False)` 或写文件再读（**不要用 execute_code 中的 `json_parse()`，它不是全局函数，会报 NameError**）

## AI 关键词列表（过滤用，2026-06-10 实测更新）

```python
ai_title_keywords = [
    'AI', '人工智能', '大模型', 'ChatGPT', 'ChatGpt', 'chatgpt',
    'DeepSeek', 'deepseek', 'Claude', 'claude', '机器学习', '神经网络',
    'LLM', 'llm', 'Qwen', 'qwen', 'Kimi', 'kimi', 'Gemini', 'gemini',
    '文心', '通义', '智谱', 'AIGC', 'aigc', '智能体', '深度学习',
    'Sora', 'sora', 'OpenAI', 'openai', 'Copilot', 'copilot',
    'GPT-4', 'GPT4', 'GPT 4', 'GPT5', 'GPT3',
    'Stable Diffusion', 'Midjourney', 'o1推理', 'LangChain', 'langchain',
    'PyTorch', 'pytorch', '吴恩达', 'Suno', 'suno',
    'Transformer', '扩散', 'RAG', 'rag', 'LLaMA', 'llama',
    'ComfyUI', 'LoRA', '多模态', 'MoE', 'RLHF', 'DPO', 'GRPO',
    'MCP', 'token', 'Token', 'Grok', 'grok', 'Agent', 'agent',
    'deep learning'
]
```

> **大小写敏感性实测（2026-06-10）**：
> - `ChatGpt`（小写 p）必须包含 —— 用户标题常用这种写法
> - `ChatGPT` / `chatgpt` / `ChatGpt` 三个变体都要覆盖
> - `DeepSeek`（驼峰）匹配，全小写 `deepseek` 也是合法标题
> - `Claude` / `claude`、`GPT-4` / `GPT4` / `GPT 4` 都要带
> - 单 `GPT` 字符串会误中 K-pop 歌曲（见下面 Pitfall），需配合黑名单

## ⚠️ Pitfall：必须用黑名单处理 K-pop "GPT" 假阳性（2026-06-10 实测）

`STAYC 'GPT' MV` 是 K-pop 女团 STAYC 的歌曲，标题含 "GPT" 但**与 AI 无关**。类似情况：
- `STAYC_official` UP 主的所有视频
- 其他 K-pop 团体以 "GPT" 等 AI 缩写为歌名的内容

**解法**：在关键词过滤后加黑名单二次过滤：
```python
def is_ai_title(title, up=""):
    t = title
    if 'STAYC' in t:                                    # K-pop GPT 假阳性
        return False
    if '健身' in t and 'AI' not in t and 'GPT' not in t:  # 健身教程假阳性
        return False
    if ('玄戒' in t or '小米自研' in t) and 'AI' not in t: # 芯片评测假阳性
        return False
    # 2026-06-12 新增：AI 产品名作为"角色名"假阳性（叉寄系列用"豆包"做角色）
    drama = ["想教我", "大小姐", "少爷", "相亲", "打牌", "谈恋爱", "分手"]
    ai_products = ["豆包", "Kimi", "通义", "文心一言", "ChatGPT", "DeepSeek", "Claude"]
    if any(d in t for d in drama) and any(p in t for p in ai_products):
        if not any(ctx in t for ctx in ["教程", "Prompt", "提示词", "API", "注册", "使用", "怎么用"]):
            return False
    for kw in ai_title_keywords:
        if kw in t:
            return True
    return False
```

**反例**（不要这样写）：用 `'GP T'`（带空格）作为子串检查来"过滤 ChatGPT"——这会**误杀**所有标题中无空格的 ChatGPT 教程（如"ChatGpt充值完整教程"）。2026-06-10 第一次跑就用这个 bug 丢了一个真实 AI 教程。

## 综合评分算法（排行榜 API 用）

```
score = play × 0.01 + like × 0.5 + favourite × 0.8 + danmu × 0.3
```

| 字段 | 排行榜 API 路径 |
|------|--------------|
| 播放量 | `stat.view` |
| 点赞 | `stat.like` |
| 收藏 | `stat.favourite` |
| 弹幕 | `stat.danmu` |
| 时长（秒） | `duration` |
| 发布日期 | `pubdate`（Unix 时间戳） |
| UP主 | `owner.name` 或 `owner.uname` |
| bvid | `bvid` |

## 小视频处理

Bilibili **没有独立的小视频 API**，`type=small_video` 参数返回空数组。

**正确方法**：从搜索结果中**按视频时长过滤**：
- 长视频：`duration >= 240` 秒（4分钟以上）
- 小视频：`duration < 240` 秒

```python
long_videos = [v for v in all_videos if v['duration'] >= 240]
short_videos = [v for v in all_videos if v['duration'] < 240]
```

> **阈值说明（2026-06 实测）**：搜索结果 `duration` 字段以秒为整数（如 `120` 表示2分钟），ranking API `duration` 同理。小视频指竖屏短视频（通常 < 4分钟），长视频指标准横屏内容。

## 热门榜单获取方法（2026-06 实测）

### 方法1：Bilibili 搜索 API（✅ 推荐，2026-06 实测有效）

**完整流程**（Python）：
```python
import json, subprocess, urllib.parse

def search_bilibili(keyword, page=1):
    kw = urllib.parse.quote(keyword)
    cmd = f'''curl -s "https://api.bilibili.com/x/web-interface/search/all/v2?keyword={kw}&page={page}" \
      -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"'''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return json.loads(result.stdout)

# 完整关键词列表见上面"AI 关键词列表"一节
ai_keywords = ai_title_keywords

all_results = []
seen_bvid = set()

for kw in ai_keywords:
    data = search_bilibili(kw)
    if data.get('code') == 0:
        for section in data.get('data', {}).get('result', []):
            if section.get('result_type') in ['video', 'archive']:
                for item in section.get('data', []):
                    bvid = item.get('bvid', '')
                    if bvid and bvid not in seen_bvid:
                        seen_bvid.add(bvid)
                        title = item.get('title', '').replace('<em class="keyword">', '').replace('</em>', '')
                        # 应用 is_ai_title 黑名单二次过滤
                        if not is_ai_title(title):
                            continue
                        all_results.append({
                            'title': title,
                            'bvid': bvid,
                            'link': f"https://www.bilibili.com/video/{bvid}",
                            'duration': parse_duration(item.get('duration', '0')),
                            'view': item.get('play', 0) or 0,
                            'like': item.get('like', 0) or 0,
                            'author': item.get('author', ''),
                        })
```

- 去重用 `seen_bvid` 集合
- **按 `play`（播放量）降序排序**后取 TOP 15 长视频 + TOP 7 小视频
- `execute_code` 比 `terminal` 更适合运行多行 Python 脚本（无 shell 转义问题）
- 标题中的 `<em class="keyword">` 和 `</em>` HTML 标签需要替换
- **必须应用 `is_ai_title` 黑名单二次过滤**，避免 K-pop "GPT"、健身教程、芯片评测等假阳性
- **英文关键词必须用 `\b` word-boundary 正则**，避免 "AI" 匹配 "maintain/captain/again" 等假阳性（详见 `<references/bilibili-ai-trending-pitfalls-2026-06-19.md>`）
- **HTML 实体解码**：标题中可能含 `&quot;` 等 HTML 实体，需 `html.unescape()` 解码后再做 XML 转义，否则产生 `&amp;quot;` 双重编码
- **play/like 类型不一致**：search/type API 的 `play`/`like` 可能是整数或字符串 `'-'`，需安全转换
- **中文关键词含空格的查询返回空**：用 `urllib.parse.quote()` 编码后拼接 URL，或优先用单关键词多次请求（2026-06-19 实测：15 个单关键词全部返回 20 条，含空格组合查询全部返回空）

### 方法2：排行榜 API（备选）

```bash
curl -s 'https://api.bilibili.com/x/web-interface/ranking/v2?type=all' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' \
  -H 'Referer: https://www.bilibili.com/'
```

注意：
- `type=all` 是唯一有效参数，`order=hot` 不是 ranking v2 的有效参数
- 返回 100 条，按内置综合算法排序

### 方法3：Web 搜索（备用/补充）

当 API 不可用或需快速概览时，用 `mcp_minimax_web_search` 搜索关键词：
```
bilibili热门视频 AI人工智能 大模型 2025 site:bilibili.com
```

搜索结果 snippet 中可提取：标题、播放量（万为单位）、UP主、发布日期。

> **注意事项**：
> - 搜索结果中的播放量为估算值（"xx万"），精确数据需调 API
> - 部分视频链接为外部镜像（如 `snm0516.aisee.tv`），需手动替换为 `bilibili.com/video/BVxxx`
> - BV号在搜索结果中可能缺失，需从视频详情页获取

## 文档结构（写入飞书格式）

```xml
<BilibiliAITrending>
<title>Bilibili AI热门视频</title>
<h1>Bilibili AI热门视频 · {当日日期}</h1>
<h2>热门长视频 TOP 15</h2>
<p>按播放量排序</p>
<ol>
  <li seq="auto">
    <a href="https://www.bilibili.com/video/BVxxx">标题</a> ｜
    UP主：xxx ｜播放：xxx ｜点赞：xxx ｜时长：xxx
  </li>
</ol>
<h2>热门小视频 TOP 7</h2>
<p>按播放量排序</p>
<ol>
  <li seq="auto">
    <a href="https://www.bilibili.com/video/BVxxx">标题</a> ｜
    UP主：xxx ｜播放：xxx ｜点赞：xxx ｜时长：xxx
  </li>
</ol>
</BilibiliAITrending>
```

> **根节点包装**：2026-06-10 cron prompt 规定使用 `<BilibiliAITrending>...</BilibiliAITrending>` 自定义根节点。lark-cli 会上报 `degrade_code=4007`（"Unsupported tag <BilibiliAITrending> was escaped"），**这是非致命**——`ok: true`、文档写入成功、目录正常生成。内部 `<h1>/<h2>/<ol>/<li>` 等标签照常解析。

> ⚠️ 文档标题固定为 `<title>Bilibili AI热门视频</title>`，**不要加档期后缀**（如"晚间档"），由 cron job prompt 根据日期生成 h1。

## cronjob 设计要点

### doc_id 独立
每个 cronjob 对应独立飞书文档，不要共享：
- AI热门 job → `Virbd3YyBoYK9XxqaZOccEGRnio`
- 全站热门 job → `TcjbdsX0ToprvCxXPbQcbLqknTq`

### cronjob 路径
```python
output_dir = "/Users/xiesg/.hermes/cron/output/"
```
不要用 `os.path.expanduser("~/.hermes/cron/output/")`。

### 输出文件名
`merged_bilibili-ai.xml`（注意是 `merged_` 前缀，不是 `bilibili-ai_`）

### 触发命令
```bash
# 触发单个 cronjob（job_id 从上面表格查）
lark-cli cron run --job-id <job_id>
```
