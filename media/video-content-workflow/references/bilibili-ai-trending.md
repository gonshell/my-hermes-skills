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

### ⚠️ search/type API — **完全废弃，返回 HTTP 412**

> **结论（2026-05-30 实测）**：`https://api.bilibili.com/x/web-interface/search/type` 对**所有关键词**均返回 HTTP 412。
> **不要依赖此 API**。

### 排行榜 API — **备选补充**

```bash
GET https://api.bilibili.com/x/web-interface/ranking/v2?type=all
```
- 返回 `data.list`，100条，按综合得分排序
- **按 AI 关键词过滤**后取 TOP 15 长视频 + TOP 7 小视频
- `owner.name` / `owner.uname` 可能同时为空，需批量调用 `/x/web-interface/view?bvid=xxx` 补全

### AI 关键词列表（过滤用，2026-06 更新）

```
AI, 人工智能, 大模型, ChatGPT, DeepSeek, Claude, GPT, 机器学习,
神经网络, LLM, Qwen, Kimi, Gemini, 文心, 通义, 智谱, AIGC,
Agent, 智能体, Chatbot, BOT, 语言模型, 深度学习,
Sora, OpenAI, Copilot, GPT-4, Stable Diffusion, Midjourney,
o1, 推理模型, LangChain, PyTorch, 吴恩达, 上海交大
```

> 注意：`DeepSeek` 要用正确大小写，`Deepseek`（全小写）不匹配。GPT-4 要带连字符。

### 综合评分算法（排行榜 API 用）

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

ai_keywords = ['AI', '人工智能', '大模型', 'ChatGPT', 'DeepSeek', 'Claude', 'GPT',
               '机器学习', '神经网络', 'AIGC', 'GPT-4', 'OpenAI', 'Sora', 'LLM',
               '文心', '通义千问', '智谱', 'Copilot', '多模态', '深度学习', '吴恩达']

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
```

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
