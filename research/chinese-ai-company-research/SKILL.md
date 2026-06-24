---
name: chinese-ai-company-research
description: "Research Chinese AI/large-model companies' organizational structure, team composition, job titles, and recruiting signals. Triggered when the user asks about a Chinese AI company (字节/阿里/腾讯/百度/DeepSeek/智谱/月之暗面/Kimi/MiniMax/阶跃/百川/商汤/旷视/面壁/MiniMax等) and wants to know their teams, hiring, product org, or how they structure a specific capability (e.g. Agent, Context Engineering, RLHF). Deliverable is usually a structured map of teams plus actual job titles plus JD content where available, not generic AI industry analysis. Use multi-path iteration — official recruitment portals are JS-rendered and bot-protected, so this skill teaches the working path: official portal entry-points, GitHub raw community guides (e.g. FlorianBruniaux/claude-code-ultimate-guide), 小宇宙/知乎/掘金 long-form interviews with product leads, LinkedIn English, Moka/ShowMoka portals via curl. Never conclude 找不到 after one search path."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [china, ai-company, research, recruiting, org-chart, jobs]
---

# Chinese AI Company Research

## When to use

The user asks about a Chinese AI company and wants:
- Job titles / JD content (especially for emerging English terms like "Harness Engineer", "Context Engineer", "Loop Engineer", "Agent Engineer", "Prompt Engineer", "RLHF Engineer")
- Team structure (which team owns which product, who leads it, headcount signals)
- Product org or engineering org map
- How a capability is staffed (e.g. "字节怎么做 Harness 类工作")

NOT for: model technology research (use `ai-agent-research`), market valuation, financial analysis.

## Core principle: multi-path iteration, never one-shot declare

Chinese AI companies do NOT publish well-indexed JD content. Public search engines return:
- Boss直聘/拉勾/猎聘/脉脉 — JS rendered, bot-protected (Cloudflare + slider)
- 企业官方招聘官网 (jobs.bytedance.com, app.mokahr.com/*, zhipuai.cn/careers) — login walls or single-page SPA
- 百度百科/微信公众号 — mostly press releases, no JD

So the working path is **5 paths in parallel, not 1 path then give up**:

1. **SearXNG public web search** with multiple keyword variants (Chinese + English, product name + role name, company name + role name)
2. **Hit the company's own careers or join-us URL directly** — many have a navigation link even if the page is JS-rendered; the HTML still has the redirect URL or Moka link
3. **Search GitHub raw** for community-maintained role/salary/landscape guides (e.g. `FlorianBruniaux/claude-code-ultimate-guide/guide/roles/ai-roles.md` has the most authoritative "what status is X role at" assessment)
4. **Long-form interviews on 小宇宙/知乎/掘金/InfoQ** — product leads (字节 TRAE 石扬, Manus Peak, 智谱 GLM 团队) often describe org structure and role definitions verbally even when no JD exists
5. **LinkedIn (English)** — DeepSeek, Moonshot, Zhipu, MiniMax post internships and senior roles here; the JD content is fully visible without auth for most posts

After running all 5, you may still have no exact JD. That is OK — report the **negative finding** with the path-trail so the user knows what was tried, then map the actual Chinese Title the work is done under (see "Title translation" below).

## Title translation: the most important table

The English terms "Harness Engineer / Context Engineer / Loop Engineer / Agent Engineer" are **methodology names, NOT HR system titles** at Chinese companies (as of 2026-06). They appear in:
- Martin Fowler's Harness Engineering article
- Karpathy's "Context Engineering" tweet thread
- Peter Steinberger's Loop Engineering tweet (2026-06, brand new)
- Anthropic's "Effective context engineering for AI agents" (2025-09)

Actual Chinese HR titles for equivalent work (verified via JD scraping 2026-06-23):
- 字节 TRAE 团队: "AI Agent 工程师", "AI IDE 工程师", "Agent 框架工程师"
- 阿里通义/阿里云: "AI 数据湖与 Agent 开发工程师", "大模型数据工程-Agentic&多模态开发工程师", "通义灵码工程师"
- DeepSeek: "AGI 大模型实习生", "AI 基础设施工程师"
- 智谱 GLM: "Agent 系统工程师", "AutoGLM 工程师", "GLM-OS 工程师"
- 月之暗面 Kimi: "Agent 系统工程师", "Kimi 产品工程师", "K2 模型工程师"

When the user asks for an English Title, return BOTH the English concept AND the actual Chinese title plus the work content. Do not pretend the English title exists.

## Anti-bot landscape (2026-06 snapshot)

| Site | Status | Working approach |
|---|---|---|
| Boss直聘 (zhipin.com) | 滑块验证, 必登录 | 无 cookie 抓不到 JD; 只能通过其 CDN/镜像被 SearXNG 索引的少量快照 |
| 拉勾 (lagou.com) | Cloudflare | 搜索引擎不索引 JD 详情页 |
| 猎聘 (liepin.com) | 需登录 | 公开 JD 偶尔被 Google 收录 |
| 脉脉 (maimai.cn) | 需登录 | 仅产品页面可读 |
| 字节 jobs.bytedance.com | JS SPA, 需登录 | 仅首页可读; 列表无 cookie 抓不到 |
| 阿里 / 阿里云 careers | JS SPA, 需登录 | 同上 |
| 智谱 zhipuai.cn | 无独立 careers 页, 导航链接在 zhipuai.cn → 加入我们 → mokahr 或自建 ATS | mokahr 链接 curl 重定向循环 |
| 月之暗面 moonshot.ai | 纯产品页, 无 careers | 走 LinkedIn |
| DeepSeek deepseek.com | 链接到 mokahr.com/social-recruitment/high-flyer/140576 | mokahr 重定向循环, 改用 LinkedIn |
| 小宇宙 podcast | 完全可读 | 长访谈, 信息密度高, 含产品负责人原话 |
| 知乎 | 全文索引好 | 大厂员工匿名分享, 时效性中 |
| 掘金/CSDN | 全文索引好 | 工程师跳槽分享, 偶尔有真实 JD 截图 |
| LinkedIn 国际站 | 大部分可读 | 中文 JD 直接发英文, 适合国际团队岗 |

## Output format

The user usually wants one of these shapes — confirm with `clarify` if ambiguous, default to the role-mapping shape:

1. **Role map (默认)**: table of English concept → Chinese Title → which companies → JD summary link
2. **Company deep-dive**: org chart + product-team leads + recent hires + JD samples
3. **Job-title inventory**: all known titles at a company + salary band (when公开)

Always include: **path-trail footer** listing which sources were checked, so the user sees what was actually tried (not "全网搜不到"). Memory rule: "禁止过早宣告搜不到".

## Known exceptions to "Harness/Context/Loop/Agent is methodology not Title" (2026-06-22)

- **DeepSeek Harness 部门**（负责人崔添翼，2026-06-22 X 公开直聘，挂出 3 个完整 JD）：Harness 研究员 / Harness 研发工程师 / Harness 产品经理。来源：量子位/华尔街见闻转载原帖截图（https://wallstreetcn.com/articles/3775172 ）。JD 完整文本见 `references/deepseek-harness-jd-transcript.md`。
- 字节/阿里/腾讯/智谱/月之暗面**均未跟进**用 Harness Title，截至 2026-06 仍是孤例。
- 更新判别规则：当用户问"Harness Engineer 有 JD 吗"时，不要一刀切说"没有"——答"绝大多数公司没有，但 DeepSeek 2026-06 公开招 3 个 Harness 岗，国内唯一"。

## MCP search 故障时的 fallback 顺序

`mcp_websearch_searxng_searxng_web_search` 在 2026-06-24 实测会偶发 "MCP server unreachable after 3 consecutive failures"，auto-retry 约 50s。**不要傻等**：

1. 立即切到 `mcp_minimax_web_search`（实测稳定，返回结构一致：title/link/snippet/date）
2. 如果 minimax 也不通 → 改用 `terminal` 调 curl 抓 Google / Bing / 搜狗
3. SearXNG 恢复后**可以双源交叉验证**，但不要因为它挂了阻塞

## Pitfalls

- **Harness / Context / Loop / Agent Engineer 是术语，不是 Title**——但有 1 个反例：DeepSeek。详见上方"Known exceptions"。
- **不要在第一次 SearXNG 失败就停下**。每次失败换一个路径（企业名变体 → 招聘平台变体 → 社区平台 → 英文 LinkedIn → 高校就业网宣讲会公告 → 媒体截图转载），至少跑 4-5 轮再下结论。**高校就业网（如 jobs.blcu.edu.cn 、jobs.xidian.edu.cn）是 BOSS/拉勾/猎聘被反爬后的金矿**——宣讲会公告会完整贴出 JD 全文。
- **不要把"找不到 JD"包装成"反爬所以做不了"**——反爬只是路径之一，还有至少 5 条可达路径。
- **不要凭"概念文章"伪装成"JD 真实存在"**。Concept article does not equal job listing. If only the former exists, say so explicitly。
- **薪资数字是估算时必须标"未公开"**。不要从"25-50K"这种单一截图外推整个公司的 band。
- **新概念（小于 6 个月）国内可能完全没有 JD**。Loop Engineering 是 2026-06 提出的，截至 2026-06-23 全球都没有以 Loop Engineer 为 Title 的公开招聘。
- **面经的真相信号比 JD 更强**——公司挂了 100 个 JD 不如 5 篇候选人真实面经有用。优先找 牛客/CSDN/知乎/博客园 上"公司名 + 岗位 + 面经"组合。具体来源清单见 `references/face-verify-sources.md`。

## Verification

Before claiming a JD exists, verify with the actual page (not just the search result snippet):
- `mcp_websearch_searxng_web_url_read` on the JD page
- Or `curl` to fetch the raw HTML and grep for "Harness" / "Context" / "Agent" / "Loop"
- If the JD is behind login, report "页面存在但需登录，内容无法验证" — do not paraphrase the snippet into "this is what the JD says"

## References

- `references/role-landscape-2026-06.md` — verified status of each English title as of 2026-06 (Harness = emerging/not-yet-institutionalized, Agent Engineer = high-growth, Context = methodology, Loop = new concept)
- `references/chinese-titles-mapping.md` — verified Chinese titles for each company (filled in from JD scraping; will go stale, treat as snapshot)
- `references/sources-by-company.md` — for each of the 12+ companies, which sources are actually accessible from this sandbox (no login, no proxy)
- `references/deepseek-harness-jd-transcript.md` — 2026-06-22 DeepSeek Harness 三岗位 JD 完整文本转录（已知 exception to "Harness = no JD"）
- `references/face-verify-sources.md` — 17+ 个面经来源 URL（牛客/CSDN/知乎/博客园），按"公司×岗位类"分组，附面经的覆盖深度说明
