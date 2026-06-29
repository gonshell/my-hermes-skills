---
name: weekly-trends-digest
description: Build and ship a recurring weekly AI trends digest. End-to-end orchestration — curate data from public sources (browser_navigate to 4 SPA URLs + querySelectorAll is the recommended path; search MCP as fallback), apply per-dimension ranking rules, render as a dark-themed HTML page (blank fillable + filled example), screenshot to PNG, push to Feishu. Use when user asks for weekly AI digest, 周报, 每周趋势速览, AI trends this week, 魔搭每周, especially when they want it small enough to read in 10 minutes and want it auto-shipped. Pair with hermes-cron-job for scheduling and html-to-image-render for the render step. **Prefer this skill over `modelscope-weekly-trends`** (which is redundant).
---

# Weekly AI Trends Digest

A reusable pattern for building a **10-minute-readable weekly AI trends summary**, anchored on the 魔搭 (ModelScope) ecosystem plus 1-2 global sources. Outputs a single-page HTML, an image, and a Feishu delivery.

## When to use this skill

Trigger when the user wants:

- A weekly AI digest (not deep research, not breaking news — a digest)
- Compact output — readable in 10 minutes, not a 20-page report
- Shippable — push to Feishu / email / chat, not just "show me a page"
- Recurring (this template is built for cron scheduling; see `hermes-cron-job`)

Do NOT use for:
- One-shot deep dives into a single topic → `tech-research-doc`
- Reading and analyzing an existing Feishu doc → `feishu-content-analysis`
- Cross-domain multi-source comparison → `ai-video-multidoc-report`
- A static screenshot of an existing site → `browser_navigate` + `browser_vision`

## The 4 + 1 method (the core pattern)

Every digest answers **3 questions + 1 carry-forward**:

| # | Question | Time | Format |
|---|----------|------|--------|
| 1 | **变化** What changed this week (specific names) | 2 min | 3-5 names + one-line position |
| 2 | **趋势** What direction is heating up (≥3 occurrences) | 3 min | 1-2 directions + evidence count |
| 3 | **反常** What broke the pattern (anomaly + hook) | 2 min | 1 item + watch-next-week note |
| +1 | **钩子** Did last week's hooks resolve | 3 min | 升温 / 持平 / 熄火 per hook |

**Why this shape**:
- 变化 = the news (anyone can find this with search)
- 趋势 = the pattern (requires 4-8 weeks of data to validate)
- 反常 = the insight (the most valuable, hardest to automate)
- 钩子 = the validation loop (this is what makes the digest *compound* in value across weeks)

The 钩子 step is the part most digests skip — and it's the part that actually makes a 4-week digest more valuable than a 1-week one. Force it.

## 4 dimensions × per-dimension ranking rules

The digest is organized along 4 dimensions, **in this fixed order** (signal strength descending):

```
模型 → 数据 → 工具 → 论文
```

Per-dimension ranking rules (see `references/dimensions-ranking.md` for full derivation):

| Dimension | Top criteria | Tiebreaker | Example weight |
|-----------|-------------|------------|----------------|
| 模型 | Trend focus (agent / fp4 / reasoning) | Vendor tier (L1 head > L2 mid > tail) | 100× trend + 10× vendor |
| 数据 | Trend strength (↑↑ > ↑ > →) | Task type importance | 100× strength + 10× task |
| 工具 | Scale (single 200-shot > 5 normal) | Category + exclusive flag | 100× scale + exclusivity |
| 论文 | HF rank (lower number = better) | Focus (new_arch > scaling > app) | 100× rank + 10× focus |

See `scripts/trends_ranker.py` — drop-in Python with `rank_models`, `rank_datasets`, `rank_tools`, `rank_papers`, and a unified `rank(items, dimension)` entry point.

## Data sources (what works, what's flaky)

| Source | URL | Flake notes | Recommended use |
|--------|-----|-------------|----------------|
| 魔搭 weekly 速递 | `developer.aliyun.com/space/modelscope` | Search-only access — go through `mcp_minimax_web_search`, not curl (the site is bot-protected) | Model names + counts |
| 魔搭英文版 papers | `modelscope.ai/papers?type=hot` | **High — browser works** (Weekly Trends tab) | browser_navigate + browser_console | Full titles + dates + likes |
| 魔搭中文版 SPA | `modelscope.cn/{models,datasets,mcp}?sort=latest` | Medium (SPA, but browser renders fine) | browser_navigate + browser_console | Per-task categorical lists + total counts |
| 魔搭首页 | `modelscope.cn` | SPA, only 3KB HTML — JS-rendered | Don't scrape; use the homepage *snippet* from search results |
| HF papers | `huggingface.co/papers` | Curl timeouts on direct fetch; use `mcp_minimax_web_search` instead | Top3 trending + keyword scan |
| HF trending models | GitHub issue `duanyytop/agents-radar/issues` | Curated weekly, much cleaner than HF direct | Weekly summary text |
| 阿里云首页 | `aliyun.com` | Reliable, has current promotions + SOTA flags | Quick pulse check on Qwen/DeepSeek/HappyHorse |
| 魔搭 MCP 广场 | `modelscope.cn/mcp` | **Browser works** — see SPA section | Total count + 14 categories with per-cat counts |
| arXiv fallback | `export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&max_results=20` | High (curl reliable) | `python3` parse XML | Last 20 cs.AI papers (when browser fully unavailable) |

**Verification rule**: every model/dataset/MCP name in the digest must trace back to a search-result snippet or a known weekly 速递 article. Do **not** invent names. If a dimension has no new data this week, say "本周留空" — don't fabricate.

## ⚠️ Pitfall — Design without execution

**The most common failure mode**: writing a SKILL.md / plan / template that looks correct, then "shipping" a markdown summary instead of the actual rendered artifact + image + docx push.

The user will ask "你按当初的设计运行了么" — they expect the **designed artifacts** (HTML rendered → PNG → image inserted into docx), not a text-only fallback.

**Self-check before reporting "done"**:

1. Did you actually run the HTML renderer (Chrome headless + Pillow crop)? Or did you skip because data felt incomplete?
2. Did the PNG get uploaded to the docx via `docs +media-insert`, or did you only push a markdown block?
3. Does the Feishu document contain (a) the rendered image, (b) a text caption summarizing key data, (c) the next-week hooks?

If any answer is "no" or "I substituted a markdown fallback" — that's a design violation. **Do not** ship until each step of the workflow ran end-to-end.

**Why this happens**: when data extraction is partial (e.g. SPA returned a category index but no detail page), the instinct is to ship a markdown wall describing what's known. This bypasses 70% of the skill's value (the rendered grid is what makes the digest scannable in 10 minutes). Use partial data + "[数据不足]" callouts **inside** the rendered template, not as an excuse to skip rendering.

## Layout alternatives

Two layouts ship with this skill. Pick based on data density vs simplicity tradeoff.

| Layout | Cells | Best for | File |
|--------|-------|----------|------|
| **3 + 1 cards** | 4 sections (1=变化 / 2=趋势 / 3=反常 / +1=钩子), each with prose + table | Default; readable in 10 min | `templates/weekly-3plus1-blank.html`, `templates/weekly-3plus1-filled.html` |
| **4×4 grid** | 16 cells (4 板块 × 4 关注点:新增/趋势/反常/钩子) | When user wants higher info density and accepts ~5 min extra scan time | `templates/weekly-grid-16.html` |

The 4×4 layout is denser because each cell carries **4 fields** (name + vendor/size + evidence + inference), but harder to scan quickly. Use it when the user explicitly asks for "more info" or "16 格" style output.

## Step-by-step workflow

### Step 1 — Curate (5-10 min)

**优先路径(2026-06 新):用 `browser_navigate` 访问 4 个 SPA URL,再用 `browser_console` 跑 querySelectorAll 提取。**

- 优点:拿到完整数据(标题/日期/likes/分类),不是 search 片段
- 详见本文末尾 "Browser 工具抓 SPA" 章节

**备选路径(数据源不稳时):用 search MCP**

```python
queries = [
    "魔搭 ModelScope 每周速递 {year}",
    "modelscope MCP 数量 2026 最新统计",
    "Hugging Face daily papers {month} {year}",
    "阿里云 Qwen DeepSeek 最新 模型 2026",
]
```

Collect **only**: model names, dataset names, MCP counts, paper titles. Save to a working file.

### Step 2 — Rank (1 min)

Use `scripts/trends_ranker.py`. Build 4 item lists, call `rank(items, dimension)`, take top 5-7 per dimension.

### Step 3 — Render HTML (2 min)

Two templates available:

- **`templates/weekly-3plus1-blank.html`** — fillable form (textarea + auto date + copy-to-clipboard button)
- **`templates/weekly-3plus1-filled.html`** — completed example showing the visual layout

Both use:
- Dark theme `#0f1115` (WebUI matches it)
- 4 numbered cards (1=变化 s1, 2=趋势 s2, 3=反常 s3, +1=钩子 s4)
- Per-card verdict line + supporting table
- Bottom 归档建议 footer

To customize the filled version:
1. Copy `templates/weekly-3plus1-filled.html` to `weekly-YYYY-Www.html`
2. Replace each answer section with curated + ranked content
3. Update the +1 section with last week's hooks + verdicts

### Step 4 — Screenshot to PNG

Use the `html-to-image-render` skill. Critical flags for digests:

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HTML="/abs/path/weekly-YYYY-Www.html"
OUT="/abs/path/weekly-YYYY-Www.png"

"$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=900,2200 --force-device-scale-factor=2 \
  --screenshot="$OUT" "file://$HTML"

# Pillow crop to content (see html-to-image-render for full script)
python3 -c "from PIL import Image; ..."
```

**Width 900** is the right size for digests — wider than 1100 makes the 4 cards too wide; narrower than 800 crowds the tables.

### Step 5 — Push to Feishu (user message)

Use `lark-cli im +messages-send --image` with **§8 and §9 caveats from `lark-pitfalls`**:
- Must `cd` to image directory first (absolute paths rejected)
- If first upload times out, retry once

```bash
cd /path/to/image_dir
lark-cli im +messages-send --user-id ou_<open_id> \
  --image ./weekly-YYYY-Www.png
```

Returns `message_id` + `chat_id` — log both for archive traceability.

### Step 5b — Insert image INTO the recurring docx (alternative to IM push)

For recurring digests where the user wants a **rolling Feishu docx** (one document accumulating all weeks, instead of separate IM messages), use `lark-cli docs +media-insert` instead of Step 5.

```bash
cd /path/to/image_dir
lark-cli docs +media-insert \
  --doc <DOC_ID> \
  --file ./weekly-YYYY-Www.png \
  --type image \
  --caption "魔搭社区 2026-W26 · 16 格速览 · 2026-06-29"
```

This is a **4-step orchestration** under the hood:
1. Get document root block
2. Create empty image block at end of root
3. Upload local file as multipart to `/drive/v1/medias/upload_all`
4. Bind uploaded media to the new block

**Returns** `block_id` + `file_token`. The image lands inside the docx, viewable when opening the doc.

**CWD-relative path caveat** (same as §5/§7/§8 in `lark-pitfalls`): must `cd` to image directory first.

**Document ownership caveat**: if the bot created the doc, ownership defaults to the bot app — transfer to the user via `lark-cli drive permission.members transfer_owner --params '{"token":"<DOC_ID>","type":"docx",...}' --data '{"member_type":"openid","member_id":"<user_ou>"}' BEFORE first image insert, otherwise the user can't edit it later.

**Image-only is not enough**: the digest skill expects image + text caption (key data tables + next-week hooks) inside the docx. After `+media-insert`, run a normal `docs +update --mode append` with a markdown block containing the key data summary and hooks. Combine: image (Step 5b) → text caption → done.

### Step 6 — Archive

Save the **HTML** (not PNG) to a long-term location for cross-week 钩子 validation:

```
~/workspace/trends/weekly-2026-W26.html
~/workspace/trends/weekly-2026-W27.html
...
```

After 4-8 weeks, open 4-5 in a row —真趋势 vs 噪音 is obvious. This is the **only** artifact you need to keep; PNGs and Feishu messages can be ephemeral.

## Files in this skill

- `templates/weekly-3plus1-blank.html` — fillable weekly template (textareas, copy-to-clipboard)
- `templates/weekly-3plus1-filled.html` — completed example showing the target layout
- `templates/weekly-grid-16.html` — denser 4×4 layout (4 板块 × 4 关注点 = 16 cells); use when user wants more info density
- `scripts/trends_ranker.py` — drop-in Python ranking library (4 dimensions + unified entry)
- `scripts/render_and_push.sh` — one-shot render + Feishu push (uses §8/§9 lark-pitfalls)
- `references/dimensions-ranking.md` — full derivation of per-dimension weight rules
- `references/data-sources.md` — data source cheat sheet including which sources are reliable vs flaky

## Pair with

- `html-to-image-render` — for Step 4 (render HTML → PNG)
- `hermes-cron-job` — for scheduling (recommended: weekly Monday 09:00 with success-silent + failure-alert)
- `lark-pitfalls` §8/§9 — for Step 5 (Feishu push caveats)
- `tech-research-doc` — when the user later wants to deep-dive a specific item surfaced in the digest

## Cron schedule template (recommended)

```
schedule: "0 9 * * 1"   # Monday 09:00
prompt: |
  Build this week's AI trends digest using the weekly-trends-digest skill.
  1. Run the 4 search queries in references/data-sources.md
  2. Rank via scripts/trends_ranker.py
  3. Render HTML from templates/weekly-3plus1-blank.html structure
  4. Screenshot to PNG
  5. Push to Feishu user ou_<open_id>
  6. Archive HTML to ~/workspace/trends/weekly-YYYY-Www.html
  Use last week's archived HTML to fill the +1 钩子 section.
  On success end with: → 完成: [SILENT]
```

## What this skill is NOT

- **Not a deep research pipeline** — if the user wants one topic explored deeply, route to `tech-research-doc`
- **Not a daily digest** — the 4+1 shape assumes a week's worth of signal; for daily, drop the +1 and condense the 3 questions
- **Not multi-source arbitration** — if the user wants to compare what 魔搭 vs HF vs PapersWithCode say about the same model, that's a different skill
- **Not a chat conversation summary** — if the user wants what was decided in last week's meetings, route to `lark-workflow-meeting-summary`

## Browser 工具抓 SPA(2026-06 新发现)

**核心观察**:curl 拿不到 modelscope SPA(只 3KB 空壳),searxng 公网全挂,但 **`browser_navigate` + `browser_console` 能用**,且**比 search MCP 拿片段好得多**(片段只显示前几个,无日期/likes)。

### 4 个实测可访问的 URL

| 板块 | 中文版 | 英文版 |
|---|---|---|
| 模型 | `modelscope.cn/models?sort=latest` | `modelscope.ai/models` |
| 数据 | `modelscope.cn/datasets?sort=latest` | `modelscope.ai/datasets` |
| 工具 MCP | `modelscope.cn/mcp` | `modelscope.ai/mcp` |
| 论文 | `modelscope.cn/papers` | **`modelscope.ai/papers?type=hot`** ← Weekly Trends |

**优先中文版**(数据更全)。英文版 `papers?type=hot` 的 Weekly Trends tab 是论文主源。

### 提取模板

```js
// 在 browser_console 里跑这些 JS 拿结构化数据:

// 模型/数据集/MCP
Array.from(document.querySelectorAll('a[href*="/models/"]')).slice(0, 20).map(a => ({
  name: a.textContent.trim().split('\n')[0],
  href: a.href
}))

// 论文(英文版,带 arxiv_id)
Array.from(document.querySelectorAll('a[href*="/papers/"]')).slice(0, 15).map(a => ({
  title: a.textContent.trim().slice(0, 100),
  arxiv_id: a.href.match(/\/papers\/(\S+)/)?.[1] || ''
}))
```

### 实测数据点(2026-06-29)

- **MCP 总数 9,711 个**(2025-12 数据为 5,500,**半年 +76%**)
- **14 个分类**:开发者工具 3,297(34%) / 搜索工具 1,382(14%) / 日程管理 684 / 浏览器自动化 580 / 知识管理 575 / 交流协作 531 / 学术研究 491 / 金融 407 / 文件系统 380 / 娱乐多媒体 334 / 位置服务 207 / 文化与艺术 114 / 其他 648
- **本周 Weekly Trends 头条**:Qwen-AgentWorld(2026.06.23 publish,30 赞) — 通义实验室世界模型
- **关键合作**:ModelScope MCP x 英特尔 AI Assistant Builder

### 失败兜底

Browser 工具完全不可用时:
- **论文**:arXiv API(curl `export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&max_results=20`,Python 解析 XML)
- **其他 3 板块**:**无可靠备源**,标"data_unavailable",走 SKILL.md "数据不足"分支

### 不要用

- ❌ curl `modelscope.cn/*` — 拿到 3KB 空壳
- ❌ 公网 searxng(5+ 实例实测全部不可用:searx.be / searx.tiekoetter.com / priv.au / search.disroot.org / searxng.site)
- ❌ 浏览器 snapshot 拿完整页 — token 太多,改用 `browser_console` 跑 querySelectorAll 提取

## 与 modelscope-weekly-trends skill 的关系

**`modelscope-weekly-trends` skill 应废弃**,它的全部功能(`scripts/fetch_week.py`、`templates/weekly-grid.html`、`references/data-sources.md` 等)已被本 skill 覆盖且**更通用**。新建 digest 任务时调用本 skill;若已加载 `modelscope-weekly-trends`,优先使用本 skill。