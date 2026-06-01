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

详见 `<references/youtube-ai-trending.md>`

### YouTube 内容热度监控 → `youtube-ai-trending-monitor`

两个维度监控 YouTube AI 内容热度：
- **维度1（当前热度）**：按总播放量排序
- **维度2（当日增量）**：按播放量/发布小时数排序，发现上升速度

详见 `<references/youtube-ai-trending-monitor.md>`

### Bilibili AI 热门 → `bilibili-ai-trending`

详见 `<references/bilibili-ai-trending.md>`

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

详见 `<references/bilibili-trending.md>`

### 飞书文档映射 → `<references/feishu-doc-map.md>`

> ⚠️ **格式一致性要求**：所有写入飞书文档的 cron job prompt 必须显式规定文档标题模板（如 `{任务名} · {日期} · {档期}`）和内容结构（h1/h2 层级 + `<ol>` 列表）。未规定的 prompt 会导致 agent 自由发挥，产生不一致格式（如 lark-table vs Markdown 列表、固定标题 vs 动态标题）。

---

## 网络不可用降级策略

YouTube 在国内网络环境下可能完全不可达（curl 返回 0 字节、browser 超时）。Cron job 遇到此情况时的降级流程：

### 第一优先：用替代数据源获取真实数据

当 YouTube 不可达时，**优先使用替代数据源填充报告**，而非直接放弃：

1. **Bing 视频搜索**（推荐，覆盖全球内容）：
   - URL：`https://www.bing.com/videos/search?q=AI+LLM+GPT+Claude+Gemini+trending+June+2026`
   - 用 `browser_navigate` + `browser_snapshot` 提取搜索结果
   - 搜索词组合：`"Google I/O 2026 AI"` / `"Claude Opus review"` / `"GPT news AI trending"` 等
   - 数据包括：标题、来源网站、时长、上传日期（精确播放量通常缺失）
   - 适合填充长视频和当日新发类别

2. **Bilibili 搜索页**（推荐，覆盖中文 AI 内容）：
   - URL：`https://search.bilibili.com/all?keyword=AI早报&search_type=video&order=pubdate`
   - AI早报系列（橘鸦Juya 等频道）覆盖每日 AI 要闻，播放量高
   - 可补充中文视角的 AI 热门内容

3. **合并数据**：从两个来源合并去重，按播放量排序填充 TOP 10/5 列表

### 第二优先：复用已有数据

1. **快速检测**：先 `curl -s --max-time 10 -o /dev/null -w "%{http_code}" "https://www.youtube.com"` 确认可达性（HTTP 000 = 不通）
2. **查找当日已有数据**：扫描 `output_dir` 中当日早间档文件（`youtube-ai-am_YYYY-MM-DD.xml`），如存在则复用其内容生成晚间档

### 最后手段：标记失败

3. **无已有数据且替代源也无结果**：写入一条「数据获取失败」说明到 XML 并上传飞书，不静默跳过

### 关键规则
- **不要重试浏览器访问 YouTube**：网络不通时浏览器也会超时（60s × N），直接跳过
- **降级时标注数据来源**：在 XML 中标注「数据来源：Bing视频搜索 + Bilibili（YouTube网络不可达）」以保持透明
- **替代源数据质量**：Bing 视频搜索结果不含精确播放量时用 `—` 占位，不要编造数字

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

### lark-cli docs +update（v2 API）
```bash
cd /Users/xiesg && lark-cli docs +update --api-version v2 \
  --doc "<doc_id>" --command overwrite \
  --content @./.hermes/cron/output/file.xml --doc-format xml
```
**必须用 `--command overwrite`，不是 `--mode append`（v1 参数）**

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
| 获取今日热门AI视频 | `youtube-ai-trending` |
| 获取B站今日热门视频 | `bilibili-ai-trending` 或 `bilibili-trending` |
| 从视频提取字幕/摘要 | `youtube-content` |
| 监控YouTube内容热度 | `youtube-ai-trending-monitor` |
| 写入飞书文档（视频内容） | 本 skill + 对应平台子 skill |

> 详细文档结构规范（含方案A/B对比、XML模板、碰撞处理）见 `<references/feishu-doc-structure.md>`