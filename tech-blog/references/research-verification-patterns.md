# Research Verification Patterns — 网络调研数据的可信度陷阱

## 核心教训

delegate_task 返回的网络调研结果**不等于事实**。Web search 摘要、二手媒体报道、甚至多个来源交叉印证的数据都可能包含错误。技术博客的事实安全网必须是阶段5的技术审查。

## 2026-06 NVIDIA GTC Taipei 博客实证

### 错误1：参数量数量级混淆
- **来源**：web search 子代理返回 "320B参数的VLA模型"
- **实际**：Alpamayo 2 是 32B（320亿）参数，不是 320B
- **根因**：中文"320亿"被错误映射为320B（实际应为32B，1B=10亿）
- **教训**：中英文数字单位转换是高频错误点，必须交叉验证

### 错误2：代际参数混用
- **来源**：web search 返回 "72个Grace核心"
- **实际**：Vera CPU 采用 88 个自研 Olympus 核心，72 核是上一代 Grace 的规格
- **根因**：搜索结果混入了前代产品的数据
- **教训**：新产品发布时，搜索结果常混入前代产品规格，必须区分代际

### 错误3：模型变体参数错误
- **来源**：web search 返回 Cosmos 3 Super=32B, Nano=8B
- **实际**：Super=64B, Nano=16B
- **根因**：不同来源报道不一致，子代理选了错误的版本
- **教训**：同一产品的不同变体参数必须逐一验证，不能假设比例关系

### 错误4：性能倍数存疑
- **来源**：web search 返回训练性能"3.5倍Blackwell"
- **实际**：多个权威来源称训练性能是"5倍Blackwell"
- **根因**：不同来源对同一指标的解读不同
- **教训**：性能倍数等关键指标需要找到一手来源（官方新闻稿/产品页）

## 通用验证策略

### 高风险数据类型（必须交叉验证）
1. **参数量/规格数字** — 中英文单位转换、代际混用、变体混淆
2. **性能倍数** — 不同基准、不同精度下的倍数差异大
3. **发布日期/上市时间** — 传闻vs确认、不同地区时间差
4. **价格** — 不同配置、不同渠道的价格差异

### 验证方法优先级
1. **一手来源**：官方产品页、官方新闻稿、官方技术文档
2. **权威二手来源**：AnandTech、WikiChip、SemiAnalysis 等专业硬件媒体
3. **多源交叉**：至少 3 个独立来源一致
4. **避免**：单一中文科技媒体报道（翻译错误风险高）

### delegate_task 调研的正确用法
- ✅ 用于**发现**信息线索和方向
- ✅ 用于**初步**收集技术规格
- ❌ 不要直接将返回数据写入文章
- ❌ 不要假设"多个来源一致=正确"（可能是同一错误源的传播）

## 2026-06-19 NVIDIA GTC Taipei 2026 keynote 博客实证（第二轮）

**输入**：YouTube 视频链接（keynote 完整回放, wSp6AiNIrsY）+ NVIDIA 官方 GTC Taipei 页面（https://www.nvidia.com/en-tw/gtc/taipei）

### 工具链选择（2026-06 验证）

| 工具 | 可用性 | 备注 |
|---|---|---|
| `web_search` | ❌ | 报 "Web tools are not configured"（Firecrawl 未配置） |
| `web_extract` | ❌ | 同上 |
| `terminal curl YouTube` | ❌ | 30s 超时，无有效返回 |
| `mcp_minimax_web_search` | ✅ | 主搜索引擎，返回结果带 relevance_score |
| `mcp_websearch_searxng_searxng_web_search` | ✅ | SearXNG 元搜索，备用入口 |

**关键经验**：Hermes 默认 `web_search`/`web_extract` 走 Firecrawl，未配置时**不可用**。**有厂商发布会类一手素材时，直接走 MCP 的 `mcp_websearch_searxng_searxng_web_search` 或 `mcp_minimax_web_search`**，两个均可用且返回更干净（带 relevance_score + snippet + date 字段）。

**调用模式**：
```
1. mcp_websearch_searxng_searxng_web_search(query="...", num_results=10) → 候选链接列表
2. mcp_websearch_searxng_web_url_read(url, maxLength=10000) → 单页正文 markdown
3. 重复 1-2 直到覆盖关键主题（一般 5-10 次调用足够）
```

### 数字验证结果（与 2026-06 第一次 NVIDIA 博客的对比）

| 数据点 | 第一次错误版本 | 本次交叉验证结果 | 验证依据 |
|---|---|---|---|
| Vera CPU 核心数 | 72（Grace 规格混入） | **88 Olympus 核心** | NVIDIA 官方产品页 + WinBuzzer |
| Vera CPU 线程数 | - | **176（空间多线程）** | NVIDIA 官方产品页 |
| NVLink-C2C 带宽 | - | **1.8 TB/s** | NVIDIA 产品页 + 多源一致 |
| Rubin GPU HBM4 | - | **288 GB / 50 PFLOPS FP4** | NVIDIA 产品页 + LinkedIn |
| Spectrum-X CPO 功耗 | - | **5× 优于传统光模块** | NVIDIA Blog 5/21/2026 |
| RTX Spark 性能 | - | **1 PFLOPS FP4 / 128 GB 统一内存** | NVIDIA Newsroom 5/31/2026 |
| RTX Spark CUDA 核心 | - | **6,144** | NVIDIA Newsroom 官方 |
| Nemotron 3 Ultra 总参 | - | **550B MoE，激活 55B** | NVIDIA Blog + 多源一致 |
| Nemotron 3 Ultra 提速 | - | **5× 推理 / -30% 成本** | NVIDIA Blog |
| GR00T 1.7 训练数据 | - | **20,000 小时第一人称** | NVIDIA Blog |
| GR00T 模型下载 | - | **274,000** | NVIDIA Blog |
| GR00T-X 数据集下载 | - | **10,000,000+** | NVIDIA Blog |

**结论**：第一次（陷阱 16 提到的）"delegate 调研返回的参数量/代际/变体错误"，**通过"先读官方一手页 → 再读二手报道 → 数字不一致时以官方为准"流程全部规避**。本次所有数字均来自 NVIDIA Newsroom / NVIDIA Blog / NVIDIA 产品页三个一手源。

### 工具链优先级（更新版）

对于"厂商发布会 + 官方页面"类输入，按以下顺序获取一手信息：

1. **厂商官方 Newsroom**（`nvidianews.nvidia.com` / `investor.nvidia.com`）→ 新闻稿，参数最准
2. **厂商官方 Blog**（`blogs.nvidia.com`）→ 详细功能描述 + 生态合作伙伴列表
3. **厂商产品页**（`nvidia.com/en-us/data-center/...`）→ 规格参数
4. **次级专业媒体**（SiliconANGLE / AnandTech / The Verge）→ 评论与产业上下文
5. **个人博客 / Substack**（如 `tspasemiconductor.substack.com`）→ 仅作交叉印证

### 文档结构（"厂商发布会综合报道"模板）

针对 keynote + 官方页面这种**"一个事件 + 多个产品线"**的输入形态，推荐结构：

```
1. 总览/导语（一段话点出为什么这次重要）
2. 主题 1：基础设施（AI 工厂、网络、电力）
3. 主题 2：硬件栈（CPU / GPU / 互联）
4. 主题 3：端侧 / PC（如有）
5. 主题 4：软件 / 模型 / 智能体
6. 主题 5：物理 AI / 机器人（如有）
7. 主题 N：安全 / 合规 / 媒体（如有）
8. "现场的非技术信号"（产业级观察，1 节）
9. 判断与启示（每条 倾向 + 替代假设，按用户 v2 洞见模板）
10. 关键数字一览表（直接可复用）
11. 附录：参考资料清单
```

**判断与启示**（第 9 节）按用户已固化的洞见 v2 模板：

```
判断 N：[一句话反常断言]
倾向：[最相信 X 的理由]
替代假设：[如果判断是错的，最可能的另一种解释 + 怎么区分]
```

每个数字、技术参数、引述的原话都必须有可点击的一手链接。

### 厂商发布会博客的"快速通道"

对于 keynote + 官方页面的输入，可以跳过完整 pipeline（阶段1-7.6）：

1. **直接阶段 1**：视频章节时间戳（YouTube 描述里 `0:00 Topic`）+ 官方页面 → 主题列表
2. **阶段 4 一气呵成**：主 session 写完整篇文章
3. **阶段 5 数字审查**：逐条核对关键技术数字（按上表）
4. **跳过阶段 2 / 6 / 7.5**：这类报告不需要叙事线生成、不需要多角色反馈、不需要读者剪裁（用户已明确要"详实、真实、可信"，不是"读者体验"）

**何时用完整 pipeline**：
- 单源访谈/转录类（见 SKILL.md 陷阱 22，逐字核查必要）
- 范式/概念命名类（见 templates/paradigm-naming-blog-outline.md）
- 读者面向消费者/营销类（需要 5 角色反馈保质量）

**何时用快速通道**：
- 厂商发布会综合报道（数字 + 产品 + 产业信号为主）
- 多源一手资料齐全的报告（不需要推断）
