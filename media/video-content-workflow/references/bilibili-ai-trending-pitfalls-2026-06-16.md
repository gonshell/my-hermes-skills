# bilibili-ai-trending — 2026-06-16 实测增量

> 本文是对 `bilibili-ai-trending-pitfalls-2026-06-13.md` 的补充。
> **旧文件保留为历史记录**，不要删；本节是当前推荐做法。

## 1. search/type API 并非完全废弃（2026-06-16 实测修正）

**旧结论**（2026-05-30）："search/type API 对所有关键词均返回 HTTP 412"。

**2026-06-16 实测**：search/type API 实际上对**大部分关键词返回正常 JSON**（code=0），但存在**间歇性失败**（返回空响应体，不是 412）。

**实测结果**（单次运行，keyword=xxx, page=1, pagesize=20）：
- ✅ 成功：`人工智能`, `大模型`, `ChatGPT`, `DeepSeek`, `Claude`, `神经网络`, `Midjourney`, `智能体`, `AI`, `GPT`, `深度学习`, `Kimi`, `ChatBot`, `Siri`
- ❌ 失败（空响应）：`机器学习`, `AIGC`, `LLM`, `AI绘画` — 但换一批请求间隔后可能成功

**根因**：不是 API 废弃，而是**反爬速率限制**。短时间大量请求会触发空响应。

**结论**：search/type API **可用但不可靠**。应作为补充数据源（配合延迟），主力仍用 search/all/v2 + popular + ranking 组合。

### search/type vs search/all/v2 字段差异

| 字段 | search/type | search/all/v2 |
|------|-------------|---------------|
| `play` | 整数或字符串 `'-'` | 在 `data[].play` 中 |
| `like` | 整数或字符串 | 需确认 |
| `duration` | `"MM:SS"` 或 `"HH:MM:SS"` 字符串 | 同 |
| `bvid` | 直接在 result 中 | 在嵌套 `data[]` 中 |
| `author` | 字符串 | 同 |
| `<em>` 标签 | 有 | 有 |

**解析 duration 的统一函数**：
```python
def parse_duration(dur_str):
    """处理 search/type 和 search/all/v2 的 MM:SS / HH:MM:SS 格式"""
    parts = str(dur_str).split(':')
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, IndexError):
        pass
    return 0
```

**注意**：ranking API 的 `duration` 字段是**整数秒**，不需要 parse。

## 2. terminal() 输出截断是主要失败原因（不是 API 返回空）

execute_code 的 `terminal()` helper 有 **50KB stdout cap**。Bilibili 搜索 API 单关键词 20 条结果的 JSON 约 15-25KB，**多关键词连续请求时输出会被截断**，导致 `json.loads()` 失败。

**正确做法 — 必须先写文件再读文件**：
```bash
curl -s 'https://api.bilibili.com/...' -o /tmp/bili_result.json
```
```python
with open('/tmp/bili_result.json', 'r') as f:
    data = json.loads(f.read())
```

**不要**用 `terminal()` 的 stdout 直接解析大 JSON。这是本次 session 最大的踩坑点 — 连续 6 个关键词全部失败，根本原因不是 API 问题，而是 stdout 截断。

## 3. popular API 确认为可靠补充数据源

`/x/web-interface/popular?ps=50&pn=N` 返回**标准化热门视频**（非搜索结果），字段结构与 ranking API 相同（`data.list[].title/bvid/owner.name/stat.view/stat.like/duration`）。

**实测**：pn=1~5 各返回 50 条，共 250 条。与 ranking API 的 100 条合并去重后约 285 条唯一视频。

**使用场景**：
- 当 search API 被限流时，popular + ranking 提供稳定的基础数据池
- 对标题做关键词过滤后仍能找到 10+ 条 AI 相关视频
- **缺点**：popular 是全站热门，AI 内容占比低（~5%），不如 search API 精准

## 4. HTML 实体解码必须在 XML 转义之前

Bilibili 搜索结果标题中包含 HTML 实体（如 `&quot;`），如果直接做 XML 转义（`&` → `&amp;`），会产生 `&amp;quot;`（双重编码）。

**正确顺序**：
```python
import html

def escape_xml(text):
    text = html.unescape(text)   # 先解码 HTML 实体
    text = text.replace('&', '&amp;')   # 再转义 XML
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text
```

## 5. search/type API 的 play/like 字段类型不一致

`play` 和 `like` 可能是整数或字符串（如 `'-'` 表示无数据）。直接做 `int(v['play'])` 会崩溃。

**安全转换**：
```python
play = v.get('play', 0)
if isinstance(play, str):
    play = int(play) if play.isdigit() else 0
like = v.get('like', 0)
if isinstance(like, str):
    like = int(like) if like.isdigit() else 0
```

## 6. is_short 阈值统一建议

历史文件中存在不一致的阈值：
- `bilibili-ai-trending.md`：240 秒（4 分钟）
- `bilibili-ai-trending-pitfalls-2026-06-13.md`：300 秒（5 分钟）
- SKILL.md pitfall 9：180 秒
- 本次 session 使用：60 秒（过低，漏掉了部分短视频）

**建议统一为 90 秒**：B 站小视频（竖屏短视频）通常 < 90 秒，标准视频 > 90 秒。与 `bilibili-trending` 子技能中的 `duration ≤ 90` 保持一致。

> ⚠️ 但最终应以 cron job prompt 中的定义为准（prompt 说"小视频"就用 prompt 的阈值）。

## 7. 本次 session 数据获取流程（供参考）

1. ranking API → 100 条
2. popular API p1-p5 → 250 条
3. search/type API（9 个关键词，带 1s 延迟）→ ~130 条
4. 合并去重 → 285 条唯一视频
5. 标题关键词过滤 → 156 条 AI 相关
6. 排序取 TOP 15 长视频 + TOP 7 小视频

**耗时**：约 30 秒（主要花在 search API 的延迟等待上）。
