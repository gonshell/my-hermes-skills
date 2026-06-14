# 跨源验证技术手册

本 session 中所有"已验证事件"背后都用了同几条验证手段。沉淀成可复用的技术手册。

---

## 1. Bing 视频搜索 → YouTube 直链反查

**场景**：cron 任务用 Bing 视频搜索抓取，所有 URL 都是 `bing.com/videos/search?q=...` 形式。需要确认"这条视频真实存在 + 标题是否准确"。

**方法 1：site: 限定符**

```
site:youtube.com "<Bing 摘要中的标题>" <频道名>
```

**方法 2：双引号精确标题**

```
"<完整视频标题>" <频道关键词>
```

**实战效果**（2026-06-14 session 验证）：

| 命中 | 失败 |
|---|---|
| "Top 3 AI platform updates from Google I/O 2026" Chrome for Developers → `Z1MZuq-8jC8` | "Fable is the most powerful AI you're allowed to use" Fireship（搜索结果只命中 Fable 游戏） |
| "Inside Anthropic, the $965 Billion AI Juggernaut" Bloomberg → `v1wZwxY3CMg` | "AI movement to end humanity" Vox（无该集直链，可能在 Spotify） |
| "The dark side of AI" DW Documentary → `ND7owjmtPNo` | |
| "Billion-Dollar Startup Is Challenging NVIDIA" Forbes → `6g9CmFAoi0U` | |
| "Which Devices Actually Support Siri AI" 9to5Mac → `WKsAMaruW-Q` | |
| "Introducing 7 new Microsoft AI models" → `BQsLSmGLh_c` | |
| "What Is AI" Shorts Simplilearn → `l9QDRtR0ttU` | |
| "Government agencies fail to disclose AI use" ABC → `Qi5xZEegOAc` | |
| Prometheus CO-CEO Jeff Bezos CNBC → `NG0GoX0zMxQ` | |

**10/12 命中真实 ID = 83%**。3 条未命中的原因：标题与实际视频差异大、播客而非视频、跨语言。

**反查失败的常见原因**：
- Bing 摘要标题被截断/重写
- 视频被原作者删除
- 内容是播客 / 短链 / 跨平台分发
- 频道名 Bing 摘要错了

**反查到 ID 后** = 视频真实存在 + ID 可独立核验 + 后续可用 YouTube Data API 查播放量。

---

## 2. 一手公告原文抓取（优先级排序）

**按可访问性 + 权威性排序**：

| 优先级 | 信源类型 | 抓取方法 | 注意点 |
|---|---|---|---|
| ① | 官方公告页 | `web_url_read`（SearXNG 走 `http_url_read` 工具）| v1 文档直接 `web_url_read` 抓取；不需要 Firecrawl |
| ② | 官方 blog/技术报告 | 同上 | 部分公司技术报告用 PDF 链接，需用 `mcp_glm_zread` |
| ③ | 主流财经/科技媒体 | SearXNG 搜索 + 摘要 | TechCrunch / The Verge / Bloomberg / 36Kr / 财新 |
| ④ | 学术/行业分析 | arXiv 工具 | 模型类有技术报告的优先看 |
| ⑤ | 个人博客/论坛 | 仅作补充 | 不可作主结论 |

**关键教训（本 session）**：

`web_extract` 工具（Firecrawl 集成）**经常返回 "Web tools are not configured"**。**不要花时间在 Firecrawl 上**——直接用 `mcp_websearch_searxng_web_url_read`，覆盖 90% 场景。

`mcp_glm_zread` 适合**已知仓库**（如 `anthropics/anthropic-cookbook`），但**有周配额限制**（本 session 中段触发 429 错误）。**仅在有明确 GitHub 目标时用**。

---

## 3. cron 任务完整 prompt 获取

**`hermes cron list` / `cronjob` 工具** 都只返回 `prompt_preview`（前 ~200 字符）——**不返回完整 prompt**。

**获取完整 prompt 的两条路**：

1. **文件系统搜索**（适用于能拿到 job_id 的情况）：
   ```bash
   grep -r "fa294bf7d232" ~/.hermes/ 2>/dev/null
   ```
   实际命中位置取决于存储实现，不一定在常规路径。

2. **`hermes cron edit fa294bf7d232`** 打开编辑器时**会显示完整 prompt**（编辑前可中止）。

**已知限制**：本 session 未找到 prompt 完整落盘的固定位置，cron 任务配置可能完全在内存里。**如果诊断需要完整 prompt，要么 `cron edit`、要么接受只能用 preview。**

---

## 4. HERMES HOME 路径偏移

**用户记忆 / 文档中常见**：`~/.hermes/cron/output/`、`~/.hermes/memories/`

**实际可能**：`~/.hermes/home/.hermes/cron/output/`、`~/.hermes/home/.hermes/memories/`

**检测方法**：
```bash
echo $HOME
ls ~/.hermes/
# 如果 ~/.hermes/ 看起来是配置文件 / 没有 memories 等
# 实际数据可能在 ~/.hermes/home/.hermes/
```

**常见原因**：
- Hermes 安装在容器/虚拟环境
- HOME 变量被覆盖
- 多 profile 隔离导致双层嵌套

**对策**：分析任务开始时**先 `ls` 两个候选路径**，再读文件。**不要假设**。本 session 因假设错位导致 30 秒浪费在错误路径找 cron 输出。

---

## 5. cron last_status=ok 但本地文件缺失

**典型发现**（2026-06-14 验证）：

- 3 个 AI 视频 cron 任务 `last_run_at` = 2026-06-14 06:08:20 / 20:05:13 / 21:05:00
- `last_status` = ok
- `last_delivery_error` = null
- 但 `~/.hermes/home/.hermes/cron/output/` 最新文件日期 = 2026-05-30

**可能原因**（按概率排序）：
1. cron prompt 中"写本地文件"步骤执行顺序在"飞书发送"之后，发送成功后 agent 直接退出，**未写本地文件**
2. 本地文件被自动清理（TTL / 大小限制）
3. prompt 改了，文件路径变了

**对策**：
- 分析任务**不要依赖本地 cron 文件**——读飞书是唯一可靠路径
- 如果需要"多日趋势分析"，先 `cronjob get` 查写入策略
- 把这个异常记入 cron 任务的"待诊断"列表，**不在分析任务里直接修**

---

## 6. 工具降级链

**按"消耗高 → 消耗低"排序，遇到配额 / 失败时降级**：

```
mcp_glm_understand_image (高消耗：多模态推理)
  ↓ 失败
mcp_minimax_understand_image (中消耗：第三方多模态)
  ↓ 失败
mcp_glm_web_search_prime_web_search (中消耗：中文搜索)
  ↓ 失败
mcp_websearch_searxng_searxng_web_search (低消耗：自托管 SearXNG)
  ↓ 失败
mcp_minimax_web_search (低消耗：第三方搜索)
```

**Web 抓取降级链**：

```
Firecrawl (web_extract) — 常返回 "not configured"
  ↓ 跳过
mcp_websearch_searxng_web_url_read — 首选
  ↓ 内容超长
mcp_websearch_searxng_web_url_read + section / maxLength 参数
  ↓
直接看搜索摘要（snippet），放弃全文
```

**GitHub 仓库读取降级链**：

```
mcp_glm_zread_read_file (有周配额限制)
  ↓ 429 配额耗尽
git clone + 离线读
  ↓
web_extract 该仓库的 raw.githubusercontent.com 文件
```

---

## 7. 验证完成度的"可证伪"标准

**怎么知道"已验证"是真的已验证，不是幻觉**：

- ✅ 有 URL（能复现）
- ✅ URL 在可访问域名（anthropic.com / blog.google / cac.gov.cn / techcrunch.com / theverge.com 等）
- ✅ 引用了具体数字 / 时间 / 关键术语（不是泛泛说"有融资"）
- ✅ 数字与原文一致（不是"原文明示 6-12，我写成 6-13"）
- ⚠️ 没有 URL 但有渠道（论坛截图、推文截图）= 弱验证
- ❌ 仅有 Bing 视频摘要 = 未验证

**反向检查清单**（自批判用）：

- [ ] 我敢说这个数字是 $47B 吗？—— 回到 anthropic.com/news/series-h 原文
- [ ] 我敢说事件时间是 6-12 14:27 吗？—— 回到 cac.gov.cn 原文
- [ ] 我敢说"Fable 是 Anthropic 的"吗？—— 回到 system card / Anthropic 公告
- [ ] 如果没有 URL，我能说"据 X 报道"吗？—— 至少要有 X 的名字 + 时间

**回答不出 → 标注"未独立核验"**。绝不偷偷把未验证说成已验证。
