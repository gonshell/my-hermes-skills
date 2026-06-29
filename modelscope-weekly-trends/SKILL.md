---
name: modelscope-weekly-trends
version: 1.2.1
description: |
  魔搭社区 · 周度趋势速览。每周一/三/六 09:00 自动生成,以纯 Markdown 追加到飞书文档。
  4 板块(模型/数据/工具/论文)× 4 关注点(新增/趋势/反常/钩子)。
  不渲染图片,直接写 Markdown 到飞书(飞书原生渲染表格/标题/列表)。
  当用户说"本周魔搭速览"、"生成 W26 趋势"、"modelscope weekly"时调用。
metadata:
  requires:
    bins: ["lark-cli", "python3"]
  cliHelp: "无需 cliHelp,直接由 cron 或手动触发"
---

# modelscope-weekly-trends (v1.2)

## 触发条件

**手动**: "本周魔搭速览" / "生成 W26 趋势" / "modelscope weekly" / "魔搭周报"

**自动**(cron): 每周一/三/六 09:00

## 核心定位

**周维度**。每天魔搭有几百个动作,周维度只关心:
- 哪些方向在升温(趋势)
- 哪些事打破常态(反常)
- 上周关注的有没有结果(钩子)

不做的:每日推送 / 深度技术分析 / 单模型详细测评 / 图片渲染

## 输出方式

**纯 Markdown**,不渲染图片。直接追加到飞书文档末尾。

## 工作流(6 步)

### 步骤 1:检查状态
- 读 `state/config.json` 里的 `feishu_doc_id`
- 若不存在 → 走"初始化流程"(见末尾)
- 若存在 → 继续

### 步骤 2:判断本次类型
- 周一 → `full`(全量快照)
- 周三/周六 → `incremental`(只显示新增)
- 手动触发 → 默认 full

### 步骤 3:拉取数据(LLM 主体用 browser 工具)
- **不要用 curl 抓 modelscope SPA**(curl 拿不到内容)
- 调用 `scripts/fetch_week.py --urls-only` 拿 4 板块 URL 清单
- LLM 主体用 `browser_navigate` 访问每个 URL,再用 `browser_console` 提取结构化数据
- 论文有 arXiv API 备源(脚本自动跑做兜底)

**4 板块主源**:
| 板块 | URL |
|---|---|
| 模型 | `modelscope.cn/models?sort=latest` |
| 数据 | `modelscope.cn/datasets?sort=latest` |
| 工具 | `modelscope.cn/mcp` |
| 论文 | `modelscope.cn/papers` |

详见 `references/data-sources.md`。

### 步骤 4:LLM 归类
- 输入:4 板块原始数据 + `references/judgment-criteria.md`
- 输出:16 格 Markdown 表格 + 关键数据列表 + 反常分析 + 钩子 + 下周重点
- 模板见 `templates/weekly-section.md`

### 步骤 5:追加到飞书文档
- full 模式:从模板生成完整 Markdown → `scripts/append_feishu.py append-text`
- incremental 模式:只追加新增部分
- 写完后 **必须 re-fetch 验证**内容进了文档(防 v1 API 静默失败)

详见 `references/feishu-doc-protocol.md`。

### 步骤 6:更新本地状态
- `scripts/state.py record --week Wxx --type full/incremental`

## 失败处理

详见 `references/safety.md`。

## 初始化流程

1. 创建飞书文档(标题:"魔搭社区 · 周度趋势速览")
2. 转移所有权给用户
3. `state.py set-doc <doc_id>`

## 文件清单

```
SKILL.md
references/
  data-sources.md              # 4 板块 URL + 备源策略
  browser-extract-templates.md # 实测通过的 browser_console JS 提取片段
  judgment-criteria.md         # 16 格判断标准(趋势/反常/钩子)
  feishu-doc-protocol.md       # 飞书追加协议(append-only + 写后验证)
  safety.md                    # 失败处理
templates/
  weekly-section.md            # 全量快照 Markdown 模板(分板块结构)
scripts/
  fetch_week.py                # URL 清单 + arXiv 备源
  append_feishu.py             # 飞书追加(append-text only + 写后验证)
  state.py                     # 状态管理
state/
  config.json                  # feishu_doc_id + 运行记录
```
```

## 已知 Pitfall(2026-06-29 实测)

### P0:飞书写后必须 re-fetch 验证
`docs +update --mode append` **可能返回 `"ok": true` 但实际未写入文档**。2026-06-29 实测:第一次 append 返回成功,但 re-fetch 文档长度未增加;第二次同样命令才真正写入。
**对策**:每次 append/overwrite 后,必须 re-fetch 并比较长度。`append_feishu.py` 已内建此逻辑(`verify=True`)。如果长度未增加,自动重试一次。

### P1:SPA 必须用 browser 工具
modelscope.cn/* 全部是 SPA(React 渲染),curl 只能拿到 3KB 空壳。
**对策**:LLM 主体用 `browser_navigate` 访问 → `browser_console` 提取结构化数据。
**console 提取模板已验证可用**(2026-06-29 实测 4 板块均成功)。详见 `references/browser-extract-templates.md`。

### P2:lark-cli 路径陷阱
所有 lark-cli 的 `--file` / `--markdown @file` **必须是 CWD 相对路径**。绝对路径直接被拒(`must be a relative path`)。
**对策**:临时文件写到 `/tmp/`,用 `cwd=os.path.dirname(tmp)` 执行命令。`append_feishu.py` 已内建此逻辑。

### P3:searxng 公网全部不可用
2026-06-29 实测 5 个公网 searxng 实例(searx.be / searx.tiekoetter.com / priv.au / search.disroot.org / searxng.site)全部不可用(超时/429/空)。
**对策**:不依赖 searxng。论文走 arXiv API(稳定),其他 3 板块靠 browser 工具。

### P4:飞书文档 ownership 转移
首次创建文档后,必须调用 `lark-doc-transfer-ownership` skill 把 ownership 转给用户(`ou_a0b6be7e404317f09b2ec6df33bde74b`)。否则文档只有 bot 能操作。

### P5:skill 目录被误删风险
2026-06-29 实测:整个 `~/.hermes/skills/modelscope-weekly-trends/` 被某次 `rm` 操作误删。
**对策**:(1) state/templates/references/scripts 各放 `.gitkeep` (2)定期备份 (3)不在此目录下执行任何 `rm` 命令。

### P6:飞书 docs +fetch 返回的 markdown 中表格已转换
`docs +fetch` 返回的 markdown 里,飞书原生表格不以 `|` 格式返回(已转为飞书内部格式)。`md.count('|')` 为 0 是正常的,不代表表格丢失。

## 用户偏好(嵌入 skill)

- **纯 Markdown 输出,不渲染 PNG** — 用户明确要求去掉 HTML 模板 + Chrome 渲染 + 图片上传。飞书原生 markdown 表格比 PNG 更好(可搜索/可编辑/手机友好)。
- **先设计再执行** — 用户多次强调"先出方案确认后再做"。新增模板或改动前,必须先展示设计供确认。
- **分板块 > 16 格** — 用户确认:每个板块独立展开(模型/数据/工具/论文各一段)比 4×4 大表格好。信息深度优先于视觉密度。
- **写后必读验证** — 用户发现飞书 API 静默失败后,要求每次写入都验证。已内建到 `append_feishu.py`。

## 设计决策:为什么纯 Markdown 而非 16 格图片

v1.0 设计了 16 格 HTML 模板 + Chrome 渲染 PNG + 飞书传图。实测后放弃,改为纯 Markdown。原因:

| 对比项 | 16 格 HTML/PNG | 纯 Markdown |
|---|---|---|
| 每条信息 | 2-3 个字(表格宽度不够) | 完整描述(厂商/尺寸/特色) |
| 手机端 | 表格截断,无法横向滚动 | 完美适配 |
| 生成耗时 | Chrome headless 5-10s | 0s |
| 失败点 | Chrome + PIL + 飞书图床 | 只有飞书 append |
| 信息深度 | 只有方向 | 方向 + 细节 + 推断 |
| 可搜索 | 图片不可搜 | 飞书全文搜索可用 |

**16 格的思维框架(4 板块 × 4 关注点)保留**,但表达方式从"一个大表格"变成"每个板块独立展开"。
