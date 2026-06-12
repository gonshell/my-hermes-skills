# bilibili-ai-trending — 2026-06-12 实测增量

> 本文是对 `bilibili-ai-trending-pitfalls-2026-06-11.md` 的补充，覆盖 2026-06-12 cron job 实测中确认的新发现/修正。
> **旧文件保留为历史记录**，不要删；本节是当前推荐做法。

## 1. 关键词覆盖度提升：28 关键词 → 1100+ 候选

实测 28 关键词 × 2 page（page_size=20）= 56 次请求，**1044 个唯一 bvid**。比 2026-06-11 的 363 候选多 ~2.9x，但长/短视频入选条数无显著增长（长 42 / 短 8）。

**结论**：关键词数量已饱和。再加更多边缘关键词（"神经网络"/"Diffusion"）只增加重复命中率。建议 **保留当前 28 关键词**。

最终推荐关键词列表（实测确认有效）：
```python
KEYWORDS = [
    "DeepSeek", "ChatGPT", "Claude", "大模型", "AIGC", "Sora",
    "OpenAI", "Anthropic", "智能体", "AGI", "AI", "人工智能",
    "机器学习", "深度学习", "神经网络", "Kimi", "豆包", "通义千问",
    "文心一言", "Gemini", "Llama", "Grok", "Midjourney", "Stable Diffusion",
    "MCP", "RAG", "具身智能", "ComfyUI", "Diffusion"
]
```

## 2. AI 产品名作为"角色名/绰号"的新假阳性

2026-06-12 实测发现一个 **新维度假阳性**：`UP主叉寄` 的视频「豆包大小姐想教我打牌（500一小时）」。

- 标题含「豆包」 → 触发 `title-strong:豆包` 匹配
- 实际内容是 **喜剧短剧**，"豆包"是片中角色名（一个爱打牌的虚构人物），与字节豆包 AI 产品无关
- 视频 286 万播放，进入 TOP 7 长视频候选，**会污染最终结果**

**新加黑名单规则**（在原 K-pop 黑名单基础上）：
```python
def blacklist(title, up, tags):
    # 原有 K-pop 检查
    kpop = ["STAYC", "SEVENTEEN", "TWICE", "BLACKPINK", "BTS", "aespa",
            "IVE", "NewJeans", "LE SSERAFAM", "ILLIT", "BABYMONSTER",
            "TWS", "Stray Kids", "TXT", "ENHYPEN", "ZEROBASEONE", "RIIZE"]
    for g in kpop:
        if g in title: return True
    # 新增：AI 产品名 + 戏剧/搞笑 + 缺少 AI 上下文
    if "叉寄" in up and "豆包" in title:
        return True  # 叉寄系列用 AI 产品名做角色名
    # 更通用的规则：标题含 AI 产品名 + 戏剧关键词 + 无 AI 教学特征
    drama_keywords = ["想教我", "大小姐", "少爷", "相亲", "打牌", "谈恋爱", "分手"]
    ai_products = ["豆包", "Kimi", "通义", "文心一言", "ChatGPT", "DeepSeek", "Claude"]
    if any(d in title for d in drama_keywords) and any(p in title for p in ai_products):
        if not any(ctx in title for ctx in ["教程", "Prompt", "提示词", "API", "注册", "使用", "怎么用"]):
            return True
    # 原有 illustrator 黑名单
    if "illustrator" in title.lower() and "AI" not in title: return True
    if "Adobe Illustrator" in title: return True
    return False
```

**关键洞察**：当 AI 产品名已经成为 **大众文化中的"梗"/"角色名"** 时，单纯靠标题/标签关键词匹配必然会有假阳性。**最终输出前应人工抽查 TOP 5 长 + TOP 3 短**，对可疑标题做内容检查（UP主、视频描述、tag 是否带教学特征）。

## 3. search/all/v2 短/长视频分布严重不均

28 关键词 × 40 候选 = 1044 条，enrichment 后 AI 视频 83 条：
- **长视频（>5min）**: 63 条 ✅ 充足选 TOP 15
- **短视频（≤5min）**: 21 条 ✅ 勉强选 TOP 7

**问题**：如果关键词列表只覆盖"专业/教程"向（"大模型"/"AI 教程"），短视频会极少。**保持"豆包"/"Kimi"/"Claude"等 AI 产品名关键词**很关键 —— 这些词的搜索结果里"测评/对比/速通"类短视频占多数。

## 4. "Gemini" 关键词的 K-pop 污染顽固性

2026-06-11 加入了 K-pop 黑名单（STAYC/SEVENTEEN 等），但 2026-06-12 仍遇到：
- 「SEVENTEEN - Gemini (双子座) (文俊辉 JUN Solo)」—— 黑名单匹配，✅ 已过滤
- 「[非商单]Gemini《第一部：盛世天下·媚娘篇》」—— UP主 `Gemini食堂股东一号`，不是 K-pop，但 Gemini 在这里是 **剧名** 而非 AI 模型名（虽然这 UP 确实是 AI 内容创作者）
- 「强到离谱？Gemini 3深度实测」—— ✅ 真实 AI
- 「杀疯了，Gemini 3帮我发论文」—— ✅ 真实 AI

**结论**：单独的 Gemini 词已无法用纯 K-pop 黑名单解决，但 Gemini AI 视频占比很高，**保留 Gemini 关键词 + 接受少量剧名/动漫假阳性** 比"放弃 Gemini 关键词"更划算（去掉会丢 3-5 个高播放量 AI 实测视频）。

## 5. 长视频时长过滤 = 5 分钟 (300s) 的合理性确认

2026-06-12 实测按 300s 切割：
- 40428s 教程（11小时）—— 长 ✅
- 114039s 教程（31小时）—— 长 ✅
- 95311s 教程（26小时）—— 长 ✅
- 874s 教程（14分钟）—— 长 ✅ 合理
- 546s Midjourney 入门（9分钟）—— 长 ✅ 合理
- 244s 提示词网站（4分钟）—— 短 ✅
- 162s Sora 短剧（2分钟）—— 短 ✅
- 82s ChatGPT 教程（1分钟）—— 短 ✅

300s 阈值在 B 站长短视频生态中**效果良好**，没有出现明显的"4 分钟教学视频被错误归为短视频"或"10 分钟长视频被错误归为短视频"的情况。

## 6. 完整工作流（2026-06-12 验证版）

2026-06-12 cron job 验证完整工作流（端到端 ~2 分钟）：

```python
import json, gzip, urllib.parse, urllib.request, time, re, random
from xml.sax.saxutils import escape

# 28 关键词 × 2 page = 56 次 search 请求
KEYWORDS = [
    "DeepSeek", "ChatGPT", "Claude", "大模型", "AIGC", "Sora",
    "OpenAI", "Anthropic", "智能体", "AGI", "AI", "人工智能",
    "机器学习", "深度学习", "神经网络", "Kimi", "豆包", "通义千问",
    "文心一言", "Gemini", "Llama", "Grok", "Midjourney", "Stable Diffusion",
    "MCP", "RAG", "具身智能", "ComfyUI", "Diffusion"
]

# Step 1: search/all/v2 多关键词 (~50s)
# Step 2: 100 条 /view enrichment with 0.12s delay (~30s)
# Step 3: tag + title-strong + blacklist 过滤
# Step 4: duration 切分 + sort by view

# 实测总耗时 2 分钟左右
```

## 7. 与前次文档的关系

- `bilibili-ai-trending-pitfalls-2026-06-11.md`：仍然准确。`is_real_ai` / gzip / `play` 字段修正 / `owner.name` 覆盖等结论全部继续有效。
- `bilibili-ai-trending-pitfalls.md`（2026-06-09）：第 1-5 节仍准确。
- `bilibili-ai-trending.md`：核心方法不变。
- **新发现统一记录到本文档**，旧文件不再修改。

## 8. 输出 XML 模板确认

```xml
<docx><title>Bilibili AI热门视频</title><body>
<BilibiliAITrending>
<h1>Bilibili AI热门视频 · {YYYY年MM月DD日}</h1>

<h2>热门长视频 TOP 15</h2>
<p>按播放量排序</p>
<ol>
<li seq="auto"><a href="链接">标题</a> ｜UP主：xxx ｜播放：xxx ｜点赞：xxx ｜时长：xxx</li>
...
</ol>

<h2>热门小视频 TOP 7</h2>
<p>按播放量排序</p>
<ol>
<li seq="auto"><a href="链接">标题</a> ｜UP主：xxx ｜播放：xxx ｜点赞：xxx ｜时长：xxx</li>
...
</ol>

</BilibiliAITrending>
</body></docx>
```

- 根节点 `<BilibiliAITrending>` 和外层 `<docx>/<body>` 会被 lark-cli 报 `degrade_code=4007` warning，**非致命**（实测 ok: true，文档写入成功，目录正常生成）。
- `<title>` 必须写"**Bilibili AI热门视频**"固定字符串（不能加档期后缀）。
- `<h1>` 包含日期。
- 写完后用 `lark-cli docs +fetch --scope outline` 验证目录，再 `--scope full` 抽查内容。
