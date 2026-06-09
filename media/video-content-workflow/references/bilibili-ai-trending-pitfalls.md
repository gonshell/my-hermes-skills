# bilibili-ai-trending — 2026-06-09 实测补充

> 本文是对 `bilibili-ai-trending.md` 的补充，记录**本次 cron job 实测中确认的反直觉/易踩坑点**。读 `bilibili-ai-trending.md` 之前先读本节，能少走 2-3 次返工。

## 1. search/type API 并非完全废弃，412 是 anti-bot 节流

> **原文说**：search/type API 完全废弃，所有关键词都 412。
> **实测（2026-06-09）**：可用，但有节奏。

```bash
# 端点（不是完全废弃）
GET https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw}&order=totalview&page={pn}&pagesize=20

# 必带头
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ...
Referer: https://search.bilibili.com/
```

**行为**：
- `order=click`：按点击量，返回数据少（多数 keyword 只能拿到 1-3 条）
- `order=totalview`：按总播放量，返回完整 20 条 ✅ 推荐
- 第一次请求（page=1）有 ~30% 概率返回 412 Precondition Failed
- **重试 page=2 或 sleep 0.5s 后重试 page=1 通常能成功**——412 是 anti-bot 节流，不是封禁
- 不同 keyword 之间 412 状态独立（一个失败不影响其他）

**正确策略**：循环里捕获 412，sleep 0.5s 后重试同一 page（最多 2 次），不要直接跳过整个 keyword。

## 2. search/all/v2 的 play/like 字段不可信，必须跟调 /view

> **原文说**：search/all/v2 返回的 `play` 字段可直接用作播放量。
> **实测（2026-06-09）**：`play` 字段**始终为 0**，不能直接用。

- `play` / `like` / `favourite` 等所有数字字段在 search/all/v2 端点都返回 0
- `duration` 字段是 `"12:34"` 格式的字符串，可正常 parse
- `bvid` / `title` / `author` 正常

**正确流程**：
1. search/all/v2（或 search/type）拿到 bvid 列表
2. **必须**对每个 bvid 调一次 `/x/web-interface/view?bvid=BVxxx` 拿真实数据
3. view 端点返回 `data.stat.view`（精确播放量）、`data.stat.like`、`data.duration`（秒，整数）、`data.owner.name`

```python
# 批量取 view 统计（实测 100 次约 30-40 秒）
import urllib.request, json, time
def fetch_stat(bvid):
    try:
        req = urllib.request.Request(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
            headers={'User-Agent': 'Mozilla/5.0 ...', 'Referer': 'https://www.bilibili.com/'}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            if d.get('code') == 0:
                s = d['data']
                return {
                    'view': s['stat'].get('view', 0),
                    'like': s['stat'].get('like', 0),
                    'duration': s.get('duration', 0),
                    'name': s['owner']['name'],
                    'title': s['title'],  # search 返回的标题可能带 <em>，view 返回的是干净的
                }
    except Exception:
        time.sleep(0.3)
    return None
```

## 3. /x/web-interface/popular 是个被忽略的宝藏端点

原文只提了 `ranking/v2` 和 `search/*`，但 `popular` 是捕获"当下正在爆"的 AI 视频最有效的源：

```bash
# 全站综合热门（5 页 × 50 = 250 条，按热度排序）
GET https://api.bilibili.com/x/web-interface/popular?ps=50&pn=1
```

**优势**：
- 包含实时热度爆款（24h 内上升的视频），search 端点索引滞后
- 字段完整（`view`/`like`/`duration`/`owner.name` 都已填充），**不需要再跟调 /view**
- 配合 AI 关键词过滤后也能拿到一定数量的相关结果

**用法**：先拉 5 页 popular 做 AI 关键词过滤拿到基线热门，再叠加 search/type 多关键词结果（已跟调 view 补全）做合并去重。

## 4. "Ai教程" 是 Adobe Illustrator 假阳性

搜索 "AI" 时大量返回带 `Ai教程`/`illustrator` 的视频（Adobe Illustrator 教程），不是 AI 内容。

**过滤规则**（在 keyword match 之后、最终输出之前做）：
```python
def is_illustrator_pollution(title):
    t = title
    if 'illustrator' in t.lower():
        return True
    # "Ai" + "Adobe" 同时出现也按 Adobe 算
    if 'Ai' in t and 'Adobe' in t:
        return True
    return False
```

这是 keyword `"AI"` 独有的问题，其他 keyword（"大模型"/"DeepSeek"/"Claude" 等）不受影响。

## 5. "小视频" 阈值是个语义模糊点

> **原文说**：小视频阈值 = 240 秒（4 分钟）。
> **本 cron job prompt 说**：小视频 TOP 7（未明确阈值）。
> **实测取舍**：本任务用 5 分钟（300 秒）做分割。
> - 5 分钟是国内"短视频"常见的边界（B站竖屏视频的常见时长）
> - 4 分钟更接近"小视频"的 B站生态定义
> - cron job prompt 没说清时，**用 5 分钟更安全**：避免 4 分 30 秒的教学视频误归"小视频"类

**建议**：在 cron job prompt 里直接写"时长 > 5 分钟为长视频，时长 ≤ 5 分钟为小视频"，消除歧义。

## 6. AI 关键词 strict 列表（推荐）

本次实测 8xx 条 AI 视频覆盖到的关键词，按有效率排序：

```python
ai_keywords_strict = [
    # 高有效率（结果几乎全是 AI）
    'DeepSeek', 'ChatGPT', 'Claude', 'AIGC', 'Sora', 'ComfyUI',
    'OpenAI', 'Anthropic', '智能体', 'AGI',
    # 中等有效率（混合 AI + 周边）
    'AI', '人工智能', '大模型', 'GPT', 'LLM',
    '机器学习', '深度学习', '神经网络', 'transformer', 'Transformer',
    '扩散模型', '大语言模型', '文心一言', '通义千问', '豆包', 'Kimi',
    'Gemini', 'LLaMA', 'Llama', 'Stable Diffusion', 'Midjourney',
    'RAG', 'MCP', 'Prompt', '提示词', '具身智能', '人形机器人',
    # 兜底
    'AI工具', 'AI生成', 'AI绘画', 'AI视频', 'AI动画', 'AI模型',
    'AI编程', 'AI对话', 'AI助手', 'AI智能', 'deepseek', 'claude',
]
```

注意大小写敏感：`DeepSeek` 命中、`deepseek` 也命中，但 `Deepseek`（首字母大写其余小写）不命中。建议两个都列入列表。
