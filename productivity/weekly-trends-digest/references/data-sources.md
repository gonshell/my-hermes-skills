# Data Sources Cheat Sheet

Which sources are reliable, which are flaky, and the right way to extract data from each. Last verified 2026-06.

## Quick reference

| Source | URL | Reliability | How to extract | What it gives you |
|--------|-----|-------------|----------------|-------------------|
| 魔搭 weekly 速递 | `developer.aliyun.com/space/modelscope` | High (when findable) | `mcp_minimax_web_search` with `魔搭 每周速递` | Per-week new models, datasets, MCP counts |
| 魔搭首页 | `modelscope.cn` | Low (SPA, bot-blocked) | Search snippet from `modelscope.cn` query | Latest model names + dates |
| HF papers | `huggingface.co/papers` | Medium (curl hangs) | `mcp_minimax_web_search` | Top3 trending papers + titles |
| HF trending models weekly | GitHub `duanyytop/agents-radar/issues` | High (curated weekly) | `mcp_minimax_web_search` for the issue | Clean weekly summary |
| 阿里云首页 | `aliyun.com` | High | `mcp_minimax_web_search` with `site:aliyun.com` | Current Qwen/DeepSeek promo + SOTA flags |
| 魔搭 MCP 广场 | `modelscope.cn/mcp` | Low (SPA) | Search snippet | Total count + new categories |

## Source-by-source detail

### 魔搭 weekly 速递 (`developer.aliyun.com/space/modelscope`)

- **What works**: searching `魔搭 ModelScope 每周速递` returns 5-10 of the most recent 速递 articles with title, URL, and snippet. Each snippet contains the model/dataset/innovation count + a few example names.
- **What doesn't work**: direct curl returns HTML but the article list is loaded via JS. The `developer.aliyun.com` page itself does render server-side, but the per-article link list isn't in the static HTML.
- **Frequency**: weekly (published Mondays). Sometimes skipped during Chinese holidays.
- **Cadence note**: if a 速递 article from the past 7 days doesn't show up in search, the digest should note "本周速递未发布" rather than fabricate.
- **Snippet field extraction**: `本期社区进展:` line gives `📟 N 个模型: ...`, `📁 N 个数据集: ...`, `🎨 N 个创新应用: ...`. The first 3-5 names are usually the most relevant.

### 魔搭首页 (`modelscope.cn`)

- **What works**: search results include a snippet of the homepage with a `Tasks Kimi-K2.7-Code 2026.06.15` style list — recent model + date. This is enough to know "X released on Y".
- **What doesn't work**: direct curl returns 3KB HTML (SPA shell). Browser navigation is bot-blocked. Don't bother trying to scrape the JS-rendered model list.
- **Use case**: spot-check latest release dates for individual models (not bulk extraction).

### HF papers (`huggingface.co/papers`)

- **What works**: search returns snippets with paper titles, author counts, submission dates.
- **What doesn't work**: `curl https://huggingface.co/papers` times out at 60s in our environment. Don't try.
- **Alternative**: GitHub issue `duanyytop/agents-radar` posts curated weekly digests that summarize HF trending — much cleaner for the digest workflow.
- **Keyword scan**: from the snippet titles, count occurrences of: multimodal / VLM, long-context, agent framework, FP4 quantization, video world models. Update the keyword counts in the 趋势 section.

### HF trending models (curated weekly)

- **Best signal**: search for `Hugging Face Trending Models 2026-04-11 duanyytop` returns the latest issue. Each issue has a "Today's Highlights" paragraph + a categorized list (LLMs / Fine-tunes / Quantizations).
- **What to extract**: family name + author + Likes count + reason for trending. This is higher-quality than what HF papers returns.

### 阿里云首页 (`aliyun.com`)

- **What works**: very reliable for the **headline state of Chinese AI**: which Qwen / DeepSeek / Hunyuan / HappyHorse version is being pushed, what promotions are running.
- **Extract**: the page banner + the "热门 AI 应用" carousel section. Search snippet captures this.
- **Use case**: validate that the "head vendor pulse" in the digest matches what 阿里 itself is pushing. Cross-check.

### 魔搭 MCP 广场 (`modelscope.cn/mcp`)

- **What works**: search for `MCP · ModelScope` returns the snippet "ModelScope MCP Plaza ... Expand the Frontiers of Model-Intelligence with MCP ... Nearly 200 DingTalk official" — gives total count + big-batch drops.
- **What doesn't work**: direct curl, same SPA issue.
- **Use case**: total MCP count + notable batch drops. Don't try to extract the per-MCP list — there are 5000+ of them and the search snippet doesn't expose them.

## What's deliberately NOT a source

- **paperswithcode.com** — overlaps with HF, but its search snippets are noisier and not Chinese-friendly
- **Twitter/X** — would be useful but our xurl tool isn't integrated into this workflow
- **Reddit r/LocalLLaMA** — high signal for community sentiment but adds a lot of noise; not worth the cleanup
- **微信公众号 articles** — JS-rendered, not directly extractable via curl; not worth the tooling investment

## Failure modes to expect

1. **速递 article not indexed yet** — search returns last week's only. Add a "本周速递未发布" line, don't guess.
2. **HF curl hangs** — always go through search. If search also fails for HF, drop the 论文 section and note "本周论文数据源不可用".
3. **魔搭 MCP count seems stale** — the SPA page doesn't update in the search snippet; cross-check with the latest 速递 article (which usually says "MCP 数量 N+").
4. **A model name from search doesn't resolve** — that's a signal the search is hallucinating. Verify by searching the model name alone; if no second source confirms, drop it.

## Verification rule

**Every** model/dataset/MCP/paper name in the digest must trace to:
- A `mcp_minimax_web_search` snippet (preferred), OR
- A 速递 article URL (developer.aliyun.com), OR
- The 阿里云 homepage snippet (for head vendor pulse only)

If a name appears in only one source and that source is unclear, mark it `⚠️ 待验证` in the digest. Never invent a name to fill a row.