# 4 板块数据源规范

## 总体原则(v1.1 修订)

**核心变化**:不用 curl 抓 modelscope SPA(失败率高,SPA 渲染后才能拿到内容)。

**新方案**:
- **主源**:modelscope 4 个 SPA 页面,由 LLM 主体用 `browser_navigate` + `browser_console` 工具访问 + 提取
- **备源**:论文用 arXiv API;其他 3 板块无可靠备源(标"data_unavailable")

## 等级定义

| 等级 | 标识 | 失败处理 |
|---|---|---|
| 🟢 主源 | modelscope SPA(browser 访问) | 浏览器失败 → 标"data_unavailable" |
| 🟡 备源 | arXiv API(curl,仅论文) | 失败 → 标"data_unavailable" |

## 4 板块 URL

| 板块 | 中文版 | 英文版 | 提取字段 |
|---|---|---|---|
| 模型 | `https://modelscope.cn/models?sort=latest` | `https://modelscope.ai/models` | name, vendor, size, tag |
| 数据 | `https://modelscope.cn/datasets?sort=latest` | `https://modelscope.ai/datasets` | name, task, size |
| 工具 MCP | `https://modelscope.cn/mcp` | `https://modelscope.ai/mcp` | name, provider, category, scale, exclusive |
| 论文 | `https://modelscope.cn/papers` | `https://modelscope.ai/papers?type=hot` | title, arxiv_id, summary |

**优先用中文版**(数据更全,优先国内),英文版备用。

## Browser 提取模板

**已单独维护**,详见 `references/browser-extract-templates.md`(2026-06-29 实测通过的 4 板块 JS 片段 + arXiv 解析)。

包含:模型页 / 数据集页 / MCP 页 / 论文页 的 `browser_console` JS 提取代码,以及 arXiv API 备源的解析 regex。

## 备源:arXiv(仅论文)

```
http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&max_results=20
```

`scripts/fetch_week.py` 自动跑这个作为兜底。

## 为什么改

v1.0 用 curl + searxng 抓数据。**实测发现**:
- modelscope SPA curl 只能拿到 3KB 空壳
- 公网 searxng 全部不可用(searx.be / searx.tiekoetter.com / priv.au / 等 5 个都挂)
- arXiv API 稳定但只能补论文

v1.1 改为 LLM 主体用 browser 工具,直接拿渲染后的真实数据。**2026-06-29 实测 4 板块均拿到 15-20 条真实数据**。

## 浏览器不可用时的兜底

如果 browser 工具完全不可用(网络问题、bot 检测),则:
- 论文:用 arXiv API(scripts/fetch_week.py 自动)
- 其他 3 板块:**没有备源**,标"data_unavailable",走 SKILL.md 中"数据不足"分支

这是已知限制,后续 v1.2 可以加更多备源(如:Hugging Face Trending API、阿里云开发者社区每周速递文章解析)。
