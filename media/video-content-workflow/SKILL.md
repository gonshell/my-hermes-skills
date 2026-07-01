---
name: video-content-workflow
description: "YouTube/Bilibili视频内容工作流：从热门榜单获取、内容提取（字幕/摘要）、到飞书文档发布的完整管道。覆盖：热门榜单抓取 → 内容提取 → 格式转换 → 飞书发布。当用户要求获取热门视频、从视频提取内容、或需要将视频内容写入飞书文档时使用。"
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [video, youtube, bilibili, trending, content-extraction, transcript, feishu]
    absorbed: [youtube-ai-trending, bilibili-ai-trending, bilibili-trending, youtube-ai-trending-monitor, youtube-content]
---

# 视频内容工作流

完整管道：热门榜单获取 → 内容提取（字幕/摘要） → 飞书文档发布。

## 热门榜单获取（Choose by platform）

### YouTube AI 热门 → `youtube-ai-trending`

获取 YouTube 上 AI 领域热门视频和当日新发视频。数据分类：
- **最热门长视频 TOP 10**：搜索词 `AI news OR LLM OR GPT OR ChatGPT OR Claude`，过滤器长视频（`sp=CAE%253D`）
- **最热门短视频 TOP 5**：搜索词 `AI news OR LLM OR GPT OR ChatGPT OR Claude`，点击 Shorts 标签
- **当日新发热门视频 TOP 10**：点击 `最近上传` 标签 → JS 提取长视频 → 过滤时间戳含"分钟"或"小时"的条目

关键 Pitfall：
- `browser_snapshot` 会被截断（~310行），不适用于提取10+条数据。**必须用 `browser_console` 执行 JavaScript 提取**。
- YouTube 本周新发 AI 视频数量很少，"最近上传"标签通常只返回 4-6 条，**不要强行凑数**，以实际获取量为准。
- ⚠️ **YouTube "AI" 关键词歧义**（2026-06-16 实测）：搜索 "AI news" 会返回大量 **Air India (AI)** 航空新闻（如 "Air India Plane Crash"、"AI-171 Crash"），与人工智能无关。**必须使用 "artificial intelligence" 或 "ChatGPT Claude GPT LLM Gemini" 等无歧义关键词**，避免 "AI news"、"AI update" 等短查询。
- **并行搜索策略**（2026-06-16 实测高效）：使用 `delegate_task` 派出 3 个并行子 agent，分别搜索不同关键词组合（如 "AI ChatGPT Claude GPT LLM"、"artificial intelligence machine learning 2026"、"AI tools agent news"），各自用 `sp=CAMSBAgEEAE%3D` 过滤本周上传，合并去重后按播放量排序。比单 agent 串行搜索快 3-5 倍。
- **YouTube 不可达时（HTTP 000）走 `references/youtube-unreachable-fallback.md`**：Bing 视频搜索 + B站 `/view` API 是首选方案。早间档 06:00 CST **不要**用 B站 search API `order=pubdate` 补"当日新发"——会被 0-view 灌水（ETC 设备/世界杯预测/"ai真好玩"）淹没。**晚间档 20:00 CST 可以用 B站 search API**（AI 早报生态已发完），但要走 4 维质量过滤（view ≥ 5、title len ≥ 4、owner len ≥ 2、AI 关键词必须匹配）剔除 0-view 灌水。详见该文件"06:00 CST 早间档垃圾坑" + "20:00 CST 晚间档数据流"小节。

  **2026-06-24 晚间档实测新增**（必读）：
  - **KPL/王者荣耀电竞赛选手"Gemini"** 假阳性：标题含「书源/子阳/虞姬/DRG/TES/SYG/EWC」+ Gemini → 必须 EXCLUDE_KW 剔除（`EXCLUDE_KW` 已扩展）
  - **硬件评测假阳性**：「黑爵T520AI鼠标」「XX AI 耳机」等型号带 AI 的硬件评测视频 → 新增 `HARDWARE_KW` 黑名单
  - **不翻墙广告灌水**：「国内真正的无限制使用ChatGPT-5.5教程」「100%免费」等充值引流 → 新增 `SPAM_KW` 黑名单
  - **round 2 扩量必跑**：晚间档 cron 必须加 `--round-2` 参数，把候选池从 90 BVID 扩到 ~300（5 Bing query + 24 B站 query），news TOP 10 才凑得齐
  - `scripts/bing_to_bili.py` 已同步升级（含 `--round-2` CLI arg、`HARDWARE_KW`/`SPAM_KW` 黑名单、`looks_like_ai_strict` 备用入口）

详见 `<references/youtube-ai-trending.md>` + `<references/youtube-ai-trending-filters.md>`（sp 参数速查 + JS 提取代码 + 降级策略）+ `<references/youtube-unreachable-fallback.md>`（YouTube 网络不通时的 Bing + B站降级方案，含 2026-06-20 晚间档实测的 search API 412 节流模式 + 4 维质量过滤配方 + **2026-06-22 晚间档实测新增：8 query 慢速重试模式 + 晚间档专属黑名单（游戏角色/战队/AI 广告灌水）+ news 凑 8 条接受不凑 10 + `merged_youtube-ai.xml` 文件名约定**）

### YouTube 内容热度监控 → `youtube-ai-trending-monitor`

两个维度监控 YouTube AI 内容热度：
- **维度1（当前热度）**：按总播放量排序
- **维度2（当日增量）**：按播放量/发布小时数排序，发现上升速度

详见 `<references/youtube-ai-trending-monitor.md>`

### Bilibili AI 热门 → `bilibili-ai-trending`

详见 `<references/bilibili-ai-trending.md>`

> **2026-06-09 实测补充**：search/type API 可用（412 是 anti-bot 节流，retry 即可）/ search/all/v2 的 play 字段始终为 0 / `/x/web-interface/popular` 是被忽略的热门源 / "Ai教程"是 Adobe Illustrator 假阳性。详见 `<references/bilibili-ai-trending-pitfalls.md>`

> **2026-06-16 实测修正**：search/type API 并非废弃（大部分关键词返回正常 JSON），但存在间歇性速率限制。**最大坑是 terminal() 输出截断**（50KB cap），必须写文件再读。popular API 确认为可靠补充。HTML 实体需 `html.unescape()` 解码后再 XML 转义。详见 `<references/bilibili-ai-trending-pitfalls-2026-06-16.md>`

> **2026-06-13 实测增量**：100/100 `/view` 返回 tag 为空字符串 → tag 求交过滤失效，必须用标题强关键词兜底 / 补 `Mamba` / `deepseek`(lowercase s) / `Deep Learning` 关键词 / "AI" 单词用 word-boundary 正则避免 Illustrator 误中。详见 `<references/bilibili-ai-trending-pitfalls-2026-06-13.md>`

> **2026-06-19 实测增量**：execute_code 中 `json_parse` 非全局可用（NameError）、popular+ranking AI 命中率仅 ~1%（必须搭配 search API）、中文关键词含空格的查询返回空（用单关键词）、word-boundary 正则过滤模板。详见 `<references/bilibili-ai-trending-pitfalls-2026-06-19.md>`

> **2026-06-20 实测增量**：execute_code 是全新解释器（import 不持久，漏一个 re 就全报 NameError）/ Adobe Illustrator 假阳性必须显式黑名单（word-boundary 不够）/ search/all/v2 数据已准确可直接信任（省去 ~80% /view 调用）/ "AI 弱关键词 + desc 二次过滤" 是反模式（desc 多为空，会误杀 GPT-image/Cursor/Trae 等真实 AI 视频）/ tname/tags/desc 现在 API 返回全空。详见 `<references/bilibili-ai-trending-pitfalls-2026-06-20.md>`

> **2026-06-12 实测增量**：确认 28 关键词覆盖度（~1044 候选）/ 新增"AI 产品名做角色名"假阳性黑名单（叉寄豆包大小姐等）/ 确认 5 分钟长短视频阈值合理 / 输出 XML 模板定型。详见 `<references/bilibili-ai-trending-pitfalls-2026-06-12.md>`

> **2026-06-11 实测增量**：修正 play 字段结论（实际可用，但 like 错位为收藏数）/ 新增 gzip 解压 / 新增 tag 集合求交过滤（质量提升）/ 推荐使用 `/view?bvid=` 的 owner.name 覆盖 author。详见 `<references/bilibili-ai-trending-pitfalls-2026-06-11.md>`

> **2026-06-10 实测补充**：
> - `STAYC 'GPT' MV` 是 K-pop 假阳性（UP主 STAYC_official），单 `GPT` 关键词会误中。**必须配合 STAYC 黑名单二次过滤**。
> - `ChatGpt`（小写 p）是用户常用大小写变体，关键词列表必须同时含 `ChatGPT` / `ChatGpt` / `chatgpt` 三个变体。
> - **不要**用 `'GP T'`（带空格）作为子串检查来"过滤 ChatGPT"——这会**误杀**所有无空格的 ChatGPT 标题（如"ChatGpt充值完整教程"），丢真实 AI 内容。
> - 关键词列表补全：`kimi/Grok/grok/Token/MoE/llama/ComfyUI/LoRA/Suno/MCP/LangChain/深度学习/扩散` 等缺失词条会导致 30+ 真实 AI 视频被滤掉。

### Bilibili 全站热门 → `bilibili-trending`

获取 Bilibili 全站热门视频，与 AI 热门不同的全站综合排名。

**输出文件路径：必须写入 `/Users/xiesg/workspace/work-outputs/`，严禁写入 subagent 的 CWD。**

```python
output_dir = "/Users/xiesg/workspace/work-outputs/"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "bilibili-trending.xml")
```

#### 长视频 TOP 15
`https://api.bilibili.com/x/web-interface/ranking/v2?type=all&order=hot`

#### 小视频 TOP 7
从 `type=all&order=hot` 排序中**按视频时长过滤**，取 `duration ≤ 90` 秒的前7条。Bilibili 没有独立小视频 API，`type=small`/`type=smallvideo` 均返回 -400（请求错误）或空数组，按播放量排序（不是综合评分）。

#### API 字段
`bvid, title, owner.name, owner.uname, stat.view, stat.like, duration, pubdate`

> ⚠️ `owner.name` 和 `owner.uname` 可能同时为空，需调用 `/x/web-interface/view?bvid=xxx` 补全。

详见 `<references/bilibili-trending.md>`（文档结构 + XML 格式）+ `<references/bilibili-trending-reproduction.md>`（curl 复现命令，含 2026-06-10 修正：terminal curl 重新可用、综合评分冲突澄清、cron job XML 根节点兼容性说明）

### 飞书文档映射 → `<references/feishu-doc-map.md>`

> ⚠️ **格式一致性要求**：所有写入飞书文档的 cron job prompt 必须显式规定文档标题模板（如 `{任务名} · {日期} · {档期}`）和内容结构（h1/h2 层级 + `<ol>` 列表）。未规定的 prompt 会导致 agent 自由发挥，产生不一致格式（如 lark-table vs Markdown 列表、固定标题 vs 动态标题）。

---

## 关键 Pitfall

### 1. lark-cli `+update` 写 XML 时 `<docx>` 和 `<body>` 标签会被转义（degrade_code=4007）

每次上传都会在响应中看到：
```
"warnings": [
  "degrade_code=4007,msg=Unsupported tag <docx> was escaped...",
  "degrade_code=4007,msg=Unsupported tag <body> was escaped..."
]
```

**这是非致命的** — `ok: true`、文档写入成功、目录正常生成。`degrade_code=4007` 表示 lark 把这两个根包装标签当成了不支持的 inline 标签并 escape，但里面的 `<h1>/<h2>/<ol>/<li>` 等内容会正常解析。

**结论**：继续使用 `<docx><title>...</title><body>...</body></docx>` 包装（参考下面的 XML 模板），不要为了消除 warning 而改用裸 XML（裸 XML 反而会导致飞书把整个内容当文本）。

### 1b. lark-cli `degrade_code=1017` "Duplicate document title was filtered"（2026-06-29 早间档实测新增）

**症状**：lark-cli overwrite 返回 `ok: true` 但 warnings 里多一条：
```
degrade_code=1017, msg=Duplicate document title was filtered: 1 duplicate <title>
tag was filtered; the first <title> was kept. Keep only one document title; when
using --title, do not also generate another <title> in content
```

**含义**：lark-cli 检测到 XML 里有多个 `<title>` 标签，自动保留第一个并丢弃其余。**文档标题仍正确显示**（第一个生效），写入成功。

**触发条件**：当前模板写 `<docx><title>...</title><body>...` 是规范的。如果 XML 末尾不慎多写了一个独立 `<title>...</title>`（在 `</body>` 之外）、或某条 `<a>`/`<h2>` 内部文本恰好匹配了 title 提取规则，都可能触发。

**处理**：不要在 `</body></docx>` 之外再加 `<title>`。如果仍触发 1017，**`ok: true` 即可判定成功**——这是无害的去重行为，不是写入失败。

### 2. Bilibili 搜索页 DOM 把所有视频标题都遮盖为"稍后再看"

`https://search.bilibili.com/all?keyword=AI&...` 页面里，所有视频卡片的 `<h3>` 标题文本都是 `稍后再看{播放量}{时长}` 格式，真实标题被前端动态注入但抓取时被覆盖。

**解法**：用 `browser_console` 抓取所有 `a[href*="/video/BV"]` 链接得到 BVID 列表，然后**通过 API 批量解析真实标题**：
```bash
for b in BV...; do
  curl -s "https://api.bilibili.com/x/web-interface/view?bvid=$b" -A "Mozilla/5.0" | python3 -c "
import sys, json
d = json.load(sys.stdin).get('data', {})
print(f\"{$b}\t{d.get('title','')}\t{d.get('owner',{}).get('name','')}\t{d.get('stat',{}).get('view',0)}\t{d.get('duration',0)}\t{d.get('pubdate',0)}\")
"
done
```

API 返回字段：`title / owner.name / stat.view / duration / pubdate`，完全够用。

### 3. Bing 视频搜索 RSS feed 不可用

`https://www.bing.com/videos/feed?count=30&q=...&format=rss` 会 301 重定向到 `https://cn.bing.com/videos/feed?...`，而 cn.bing.com 端点直接返回 HTML 搜索页（无视 format=rss）。

**正确做法**：用 `browser_navigate` 打开 `https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+trending&FORM=HDRSC6`，通过 `browser_console` 执行 JS 提取结构化数据，或 `browser_snapshot` 阅读可见结果。

### 4. Bing 视频搜索同语义关键词结果几乎不变化（2026-06-12 早间档实测）

3 个不同 AI 关键词的 Bing 视频搜索前 10 条结果几乎完全相同 — 反驳了之前"换关键词拿更多结果"的说法。早间档 06:00 CST 应**只用 1 次泛 AI 关键词查询**凑长/短视频，**不要**做第二组 Bing 关键词浪费时间，跨平台用 Bilibili 补"当日新发"。详见 `<references/youtube-unreachable-fallback.md>` 中"Bing 关键词实际差异比预期小"一节。

### 5. ⚠️ Bing 在 headless 浏览器下只渲染 1 条（2026-06-14 早间档实测）

`browser_navigate` Bing 视频搜索 → `browser_console` 抓 `a[aria-label*="来源"]` **只返回 1 条**（页面 531px 高，几乎全是导航）。原因：Bing 视频用虚拟列表 + IntersectionObserver 懒加载，headless Playwright 不触发。

**正确做法 — curl-first**：用 curl 拿 SSR HTML（506KB，28+ 条），再 grep aria-label + BVID。**速度 2-3s vs 浏览器 60s+**。完整流程见 `<references/youtube-unreachable-fallback.md>` "Bing 在 headless 浏览器下渲染不完整" 一节。

可重跑脚本：`scripts/bing_to_bili.py`（一站式 curl Bing + B站 search API + B站 /view API 批量解析，输出 longs/shorts/news 三组 JSON；**2026-06-20 升级**：BVID 直取 + 4 维质量过滤 + `--today-only` 选项；**2026-06-24 升级**：加 `--round-2` 参数扩量到 5 Bing query + 24 B站 query，扩 EXCLUDE_KW/HARDWARE_KW/SPAM_KW 三层黑名单过滤假阳性）。

  ⚠️ **`--out` 参数必须是文件路径，不是目录**（2026-06-25 实测）：传目录会导致 `IsADirectoryError`。正确用法：
  ```bash
  python3 scripts/bing_to_bili.py --out /Users/xiesg/.hermes/cron/output/bing_to_bili.json --round-2
  ```
  而非 `--out /Users/xiesg/.hermes/cron/output/`（缺文件名）。

### 6. ⚠️ Bing 中文网络出口下结果是 bilibili 包装（2026-06-14 早间档实测）

`curl https://www.bing.com/videos/search?q=AI+LLM+GPT+...` 拿到的前 28+ 条结果**几乎全部是 bilibili 源视频**（Bing 聚合了 bilibili 视频）。每条 aria-label 格式为 `...来源: bilibili · 时长: ... · 已浏览: ... · 上传时间: ... · 上传人: ...`，周围 HTML 有 `/video/BV...` 链接。

**正确做法**：从 Bing HTML 提取 BVID → 调 `https://api.bilibili.com/x/web-interface/view?bvid=xxx` 拿**真实权威**标题/播放量/时长/上传时间（B站官方数据），**XML 链接直接用 B站 URL `https://www.bilibili.com/video/{bv}/`**，不要用 Bing search URL。`scripts/bing_to_bili.py` 已实现完整链路。

### 7b. ⚠️ execute_code 中 `from youtube_ai_xml_build import write` 失败（2026-07-01 早间档实测）

`templates/youtube-ai-xml-build.py` 文件名带连字符（`youtube-ai-xml-build.py`），**不是合法的 Python 模块名**。execute_code 的 sys.path 默认不包含 templates 目录，且连字符文件名无法用 `import` 直接加载。

**症状**：
```python
from youtube_ai_xml_build import write
# ModuleNotFoundError: No module named 'youtube_ai_xml_build'
```

**解法 A — 用 `importlib.util.spec_from_file_location`（推荐，数据已经在内存或带日期戳文件时）**：
```python
import importlib.util, json
spec = importlib.util.spec_from_file_location(
    "youtube_ai_xml_build",
    "/Users/xiesg/.hermes/skills/media/video-content-workflow/templates/youtube-ai-xml-build.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
write = mod.write

with open('/Users/xiesg/.hermes/cron/output/bing_to_bili_2026-07-01.json') as f:
    data = json.load(f)
merged, dated = write('2026-07-01', 'am',
                      long_top10=data['longs'],
                      short_top5=data['shorts'],
                      recent_top10=data['news'])
```

**解法 B — 直接调 CLI 入口（更简单，但只能读 `bing_to_bili.json` 默认路径）**：
```bash
cd /Users/xiesg/.hermes/skills/media/video-content-workflow && \
  python3 templates/youtube-ai-xml-build.py am
# 默认读 /Users/xiesg/.hermes/cron/output/bing_to_bili.json
# 输出 merged_youtube-ai.xml + youtube-ai-am_{today}.xml
```

注意：CLI 入口只能读 `bing_to_bili.json`（固定路径），**如果数据已写到带日期戳的文件（如 `bing_to_bili_2026-07-01.json`），必须用解法 A** 或者先 `cp` 覆盖默认路径。

**额外坑 — `shutil.copy` SameFileError**：`write()` 返回值 `(merged, dated)`，`merged` 路径默认是 `/Users/xiesg/.hermes/cron/output/merged_youtube-ai.xml`。在它上面再 `shutil.copy(merged, target_merged)`，如果 `target_merged` 等于 merged 路径本身，会抛 `SameFileError`。`write()` 第一次调用就同时写两个文件（merged + dated），不需要再 copy。

### 7. ⚠️ Bing aria-label 格式随出口语言变化（2026-06-16 晚间档实测）

中文出口下 aria-label 含"来源"（`来源: bilibili · 时长: ... · 已浏览 ...`），`aria-label*="来源"` 可匹配。但英文出口下格式变为 `"title from domain · uploaded on ... · Click to play."`，**不含"来源"，匹配 0 条**。

**正确做法 — BVID 直取**：不依赖 aria-label 语言，直接 `grep -oE '/video/BV[A-Za-z0-9]{10}'` 从 Bing HTML 提取 BVID，再调 B站 `/view` API 拿权威数据。2026-06-16 实测 34 个 BVID 全部成功。详见 `<references/youtube-unreachable-fallback.md>` "BVID 直取为首选" 一节。

## 网络不可用降级策略

YouTube 在国内网络环境下可能完全不可达（curl 返回 0 字节、browser 超时）。Cron job 遇到此情况时的降级流程：

### 第一优先：用替代数据源获取真实数据

当 YouTube 不可达时，**优先使用替代数据源填充报告**，而非直接放弃：

1. **Bing 视频搜索**（推荐，覆盖全球内容）：
   - URL：`https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+Gemini+trending+June+2026`
   - **提取技巧（2026-06-16 更新）**：**首选 BVID 直取**（`grep -oE '/video/BV[A-Za-z0-9]{10}'`），不依赖 aria-label 语言。aria-label 格式随出口语言变化（中文含"来源"，英文不含），`aria-label*="来源"` 在英文出口下匹配 0 条。
   - **更优技巧（2026-06-14）**：**curl 拿 SSR HTML**（headless 浏览器只渲染 1 条），grep BVID，调 B站 `/view` API 拿真实数据。详见 Pitfall 5/6/7。
   - 搜索词组合：`"Google I/O 2026 AI"` / `"Claude Opus review"` / `"GPT news AI trending"` 等
   - **链接转换**：Bing aria-label 卡片 99% 是 bilibili 源 → **XML 用 B站 URL** `https://www.bilibili.com/video/{bv}/`，不用 Bing search URL
   - 数据包括：标题、来源网站、时长、上传日期、精确播放量（B站 API 提供权威数据，不是 Bing 估算）
   - 适合填充长视频和当日新发类别
   - **XML 模板**：`templates/youtube-ai-xml-build.py`（处理 bing/bilibili 双源 + 排序 + 飞书 DocxXML 包装）
   - **可重跑脚本**：`scripts/bing_to_bili.py`（curl Bing + curl B站 + B站 /view API → JSON，~2 分钟）→ 输入到 `templates/youtube-ai-xml-build.py`（自动读取 `bing_to_bili.json` 输出并构建 XML）
- ⚠️ **2026-06-29 早间档实测修正**：`templates/youtube-ai-xml-build.py` 之前要求的 input schema 是 `{title, channel, views, duration, uploaded, src}`（老设计），但 `scripts/bing_to_bili.py` 实际输出 `{title, owner, view, duration, pubdate, bv, source}`。**两个 schema 不兼容**——直接喂老模板会因字段名不匹配（`channel` vs `owner`、`views` vs `view`、`uploaded` vs `pubdate`）导致 `<li>` 渲染异常。老模板的 `bilibili_bvid_map`（标题→BVID 映射）也已废弃——`bing_to_bili.py` 每条都带 `bv` 字段，URL 直接 `https://www.bilibili.com/video/{bv}/` 拼出。**重写后的模板已对齐新 schema 并自带 `fmt_view/fmt_dur/fmt_uploaded` 辅助函数**，可直接 `python3 templates/youtube-ai-xml-build.py` 跑（不传参则用今天日期 + am slot）

2. **Bilibili 搜索页**（推荐，覆盖中文 AI 内容）：
   - URL：`https://search.bilibili.com/all?keyword=AI早报&search_type=video&order=pubdate`
   - AI早报系列（橘鸦Juya 等频道）覆盖每日 AI 要闻，播放量高
   - **提取技巧（2026-06-11）**：带 `&search_type=video` 时 `browser_console` 走 `a[href*="/video/BV"]` 可同时拿到真实 BVID + 真实标题（h3.textContent），比 snapshot 解析更准
   - 可补充中文视角的 AI 热门内容

3. **合并数据**：从两个来源合并去重，按播放量排序填充 TOP 10/5 列表

### 第二优先：复用已有数据

1. **快速检测**：先 `curl -s --max-time 10 -o /dev/null -w "%{http_code}" "https://www.youtube.com"` 确认可达性（HTTP 000 = 不通）
2. **查找当日已有数据**：扫描 `output_dir` 中当日早间档文件（`youtube-ai-am_YYYY-MM-DD.xml`），如存在则复用其内容生成晚间档

### 最后手段：标记失败

3. **无已有数据且替代源也无结果**：写入一条「数据获取失败」说明到 XML 并上传飞书，不静默跳过

### 关键规则
- **不要重试浏览器访问 YouTube**：网络不通时浏览器也会超时（60s × N），直接跳过
- **同样不要重试浏览器访问 Bing**：Bing 视频搜索在 headless 下只渲染 1 条，**用 curl 拿 HTML**（Pitfall 5）
- **降级时标注数据来源**：在 XML 中标注「数据来源：Bing视频搜索 + Bilibili（YouTube网络不可达）」以保持透明
- **替代源数据质量**：走 B站 `/view` API 时数据是**B站官方权威**的（精确播放量、真实标题、真实 UP 主），不需要 `—` 占位
- **06:00 CST 早报空窗**：B 站 AI 早报生态 07:00-10:00 CST 才发，早间档 cron 在 06:00 CST 触发时**当天 B 站早报还不存在**。处理详见 `<references/youtube-unreachable-fallback.md>` 的"06:00 CST 早报空窗"小节
- **is_short 判定陷阱**：解析后的 `"47:40".split(":")` 是 2 段，跟 `"1:26"` 一样，不能用 `len(parts) == 2` 判 short。必须转秒后用 `dur_to_seconds <= 180` 判（详见同 reference 的 parse_dur 注释）

详见 `<references/youtube-unreachable-fallback.md>`

---

## 内容提取

### YouTube 字幕提取 → `youtube-content`

```bash
/Users/xiesg/.hermes/hermes-agent/venv/bin/python3
uv pip install youtube-transcript-api
python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --text-only
```

---

## 飞书文档发布

### lark-cli --content 路径规则
- `--content @/absolute/path` 和 `--content @~/path` 均报错
- **必须从 HERMES_HOME（`/Users/xiesg/`）用相对路径**：`@./.hermes/cron/output/file.xml`
## 飞书文档写入（XML 格式规范）

> ⚠️ **2026-06-07 关键修复 + 2026-06-13 强化 + 2026-06-14 早间档再次确认**：lark-cli `--doc-format xml` 期望 DocxXML 格式（`<docx><title>...</title><body>...</body></docx>`），**不是** XML 根节点格式。错误格式（`<YouTubeTrending>...</YouTubeTrending>`、`<rss>...</rss>`、裸 `<title>...</title>` 顶层标签 或 `<?xml?>` 声明）会导致飞书将标签作为纯文本转义，目录功能失效。

### ⚠️ Cron job prompt 中的常见错误格式（必须忽略用户提示里的错误格式）

**多个 cron job prompt 历史观察**（2026-06-13 / 2026-06-14 / 2026-06-16 三次确认）：任务描述中经常出现这样的"格式规范"：

```
- 文档标题：`<title>YouTube AI热门视频 · 晚间档</title>`，固定不变
- 一级标题：`<h1>YouTube AI热门视频 · {当日日期} · 晚间档</h1>`
- 文档格式规范（必须严格遵守）
- 完整根节点 `<YouTubeTrending>` 和各分类节点
```

并提到"完整根节点 `<YouTubeTrending>` 和各分类节点"——这是**不推荐**的。`<?xml>` 声明和 `<YouTubeTrending>` 等非 DocxXML 根标签会被 lark-cli escape（degrade_code=4007），但**内部的 DocxXML 标签（`<title>`、`<h1>`、`<h2>`、`<ol>`、`<li>`、`<a>`）仍然正常解析渲染**。

> **2026-06-16 实测确认**：使用 `<?xml version="1.0"?>` + `<YouTubeTrending>` 根节点写入飞书文档 `EbHDdKARYo4vEExQiNGc3qiGnSe`，lark-cli 返回 `ok: true` + `result: "success"` + `revision_id: 37`，两个 degrade_code=4007 warning 仅针对 `<?xml>` 和 `<YouTubeTrending>`，内部 h1/h2/ol/li/a 标签全部正常渲染。之前的"所有标签全部失效"结论过于绝对。

**正确做法**（优先级从高到低）：
1. **优先使用本 skill 的 DocxXML 模板**（`<docx><title>...</title><body>...</body></docx>` 包装），避免 degrade_code=4007 warning
2. 标题 `<title>` 必须是 `<docx>` 下的第一个子元素，不能独立放在根节点外面
3. 如果 cron job prompt 要求 `<YouTubeTrending>` 根节点，**可以照做但会收到 warning** — 不会导致内容失效，只是不优雅
4. **lark-cli 返回的 `degrade_code=4007` warning**（"Unsupported tag `<xxx>` was escaped"）是**正常的、非致命的**——不支持的根标签会被 escape，但内部 DocxXML 标签正常解析。`ok: true` 即代表成功

### 格式合规清单（写 XML 前对照）

- [ ] 根节点是 `<docx>`（不是 `<YouTubeTrending>`、`<rss>`、`<document>` 等）
- [ ] `<title>` 在 `<docx>` 第一个子元素位置
- [ ] 所有正文在 `<body>` 里
- [ ] 不写 `<?xml version="1.0"?>` 声明
- [ ] 不写独立的顶层 `<title>`（在 `<body>` 外的）
- [ ] 链接用 `<a href="...">标题</a>`，不用 Markdown `[文字](url)`
- [ ] 列表用 `<ol><li seq="auto">`，不用 `-` / `*` / `<ul>`

### 正确 XML 模板（晚间档）

```xml
<docx><title>YouTube AI热门视频 · 晚间档</title><body>
<h1>YouTube AI热门视频 · {YYYY-MM-DD} · 晚间档</h1>

<h2>最热门长视频 TOP 10</h2>
<p>本周上传，播放量+互动率综合评分排序</p>
<ol>
<li seq="auto"><a href="URL">标题</a> ｜频道：xxx ｜播放：xxx ｜时长：xxx ｜上传：xxx</li>
...
</ol>

<h2>最热门短视频 TOP 5</h2>
<ol>
<li seq="auto"><a href="URL">标题</a> ｜频道：xxx ｜播放：xxx ｜时长：xxx ｜上传：xxx</li>
...
</ol>

<h2>当日新发热门视频 TOP 10</h2>
<p>最近上传，按最新排序</p>
<ol>
<li seq="auto"><a href="URL">标题</a> ｜频道：xxx ｜播放：xxx ｜时长：xxx ｜上传：xxx</li>
...
</ol>

</body></docx>
```

### 错误格式 ❌

```xml
<!-- ❌ 根节点 + XML 声明会导致标签被飞书转义为纯文本 -->
<?xml version="1.0" encoding="UTF-8"?>
<YouTubeTrending>
<title>YouTube AI热门视频 · 晚间档</title>
<h1>YouTube AI热门视频 · {date} · 晚间档</h1>
...
</YouTubeTrending>
```

### 飞书文档写入命令

```bash
cd /Users/xiesg && lark-cli docs +update --api-version v2 \
  --doc "<doc_id>" --command overwrite \
  --content @./.hermes/cron/output/youtube-ai-pm_YYYY-MM-DD.xml --doc-format xml
```

早间档文档 token：`EbHDdKARYo4vEExQiNGc3qiGnSe`
晚间档文档 token：`HhyMdusqdoVcW9xLyd2c2Yc2nnf`
### cronjob 路径偏移
`os.path.expanduser("~/.hermes/cron/output/")` 在 cronjob 中展开为错误路径。**必须硬编码绝对路径**：
```python
output_dir = "/Users/xiesg/.hermes/cron/output/"
```

### cronjob 文件名约定
- 早间档：`youtube-ai-am_YYYY-MM-DD.xml`（am 前缀）
- 晚间档：`youtube-ai-pm_YYYY-MM-DD.xml`（pm 前缀）
- 下划线连接日期，不用空格

早间档飞书文档 token：`EbHDdKARYo4vEExQiNGc3qiGnSe`

### 合并多 XML 文件流程
1. 扫描 `~/.hermes/cron/output/youtube-ai_*.xml`，过滤 7 天内文件
2. 按日期倒序排序，逐文件读取，跳过 `<!-- -->` 和 `<title>` 行，拼接正文
3. 写入 `merged_youtube-ai.xml`，用 lark-cli 写入飞书后删除 merged 文件

### 飞书文档标题修改
```bash
lark-cli drive files patch \
  --params '{"file_token":"<doc_token>","type":"docx"}' \
  --data '{"new_title":"新标题"}'
```

---

## 触发条件

| 用户请求 | 技能 |
|---|---|
| 获取今日热门AI视频 | **本 skill**（`video-content-workflow`） |
| 获取B站今日热门视频 | **本 skill**（含 `bilibili-ai-trending` / `bilibili-trending` 子流程） |
| 从视频提取字幕/摘要 | `youtube-content` |
| 监控YouTube内容热度 | **本 skill**（含 `youtube-ai-trending-monitor` 子流程） |
| 写入飞书文档（视频内容） | 本 skill + `lark-doc` |

> 详细文档结构规范（含方案A/B对比、XML模板、碰撞处理）见 `<references/feishu-doc-structure.md>`