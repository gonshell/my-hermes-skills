# 飞书 Markdown 写入模式（ad-hoc 分析报告用）

**与 cron XML 写入的区别**：本 skill 输出的**分析报告**是 markdown；`video-content-workflow` 输出的**视频榜单**是 DocxXML。两条路径分离。

## 适用场景

- ad-hoc 用户问"把 v2 报告写到飞书" / "给我出一份分析报告" / "把这份 markdown 同步到飞书"
- 报告本身是 markdown 格式（带表格、链接、强调、引用）
- 一次性写入，不进 cron 任务循环

**不适用**：
- cron 任务定时写入视频榜单（用 `video-content-workflow` 的 DocxXML 模式）
- 需要富 block（callout / grid / checkbox / 画板）—— 改用 XML 模式

## 命令模板

### 创建新文档

```bash
# 1) 把 md 文件 cp 到 HERMES_HOME（避开绝对路径陷阱）
cp /Users/xiesg/workspace/my-report.md ./report.md

# 2) 创建 + 显式 markdown 格式
lark-cli docs +create --api-version v2 --doc-format markdown --content @report.md
```

返回：
```json
{
  "ok": true,
  "data": {
    "document": {
      "document_id": "MLR7duTUnoln0WxI0ErcLrrun4g",
      "revision_id": 4,
      "url": "https://zt854jxlft.feishu.cn/docx/MLR7duTUnoln0WxI0ErcLrrun4g"
    },
    "permission_grant": {
      "status": "skipped",
      "perm": "full_access"
    }
  }
}
```

### 覆盖已存在文档

```bash
lark-cli docs +update --api-version v2 \
  --doc "<existing_doc_id>" --command overwrite \
  --doc-format markdown --content @report.md
```

返回：
```json
{
  "ok": true,
  "data": {
    "document": { "revision_id": 7, "url": "..." },
    "result": "success"
  }
}
```

⚠️ **revision_id 跳变是正常的**（create 一次返回 4，overwrite 一次返回 7）—— 不是错误。

## 路径陷阱（与 cron XML 模式相同）

- ❌ `--content @/Users/xiesg/workspace/report.md`（绝对路径）
- ❌ `--content @~/workspace/report.md`（~ 展开失败）
- ✅ `--content @./report.md`（HERMES_HOME 是 CWD）
- ✅ `--content @./.hermes/cron/output/file.md`（HERMES_HOME 下的相对路径）

## Bot 创建的身份与权限

- **默认身份是 bot**（除非配置 `--as user`）
- bot 创建的 doc 归属 bot，不是 user
- `permission_grant.status=skipped` 表示 CLI 当前没配置 user open_id，**user 可管理权限未自动授权**
- 解决方案：
  - 让用户在飞书里手动把自己加为可管理权限
  - 或用 `lark-transfer-owner` skill 转 owner 给 user
  - 或先 `lark-cli auth login --scope "..."` 配置 user open_id

## 验证写入完整

```bash
# 看 outline（只列 H1/H2）
lark-cli docs +fetch --api-version v2 --doc "<doc_id>" \
  --doc-format markdown --scope outline

# 看完整 markdown
lark-cli docs +fetch --api-version v2 --doc "<doc_id>" \
  --doc-format markdown --scope full
```

写入成功后 fetch 输出的字符数 ≈ 原文件字符数（可能略少，因为表格语法在飞书侧被规范化）。

## Markdown 特殊字符转义

详见 `references/lark-doc-md.md`（lark-doc skill 提供）。常见要点：

- `$` → `\$`（避免被解析为数学公式）
- `<` → `\<`（避免被解析为 XML 标签）
- `#` 行首 → `\#`（避免被解析为标题）

**ad-hoc 报告通常不需要转义**——大多数内容是自然段落。但表格、URL、代码块内含 `$` 或 `<` 时要小心。

## 与 cron XML 模式的快速对照

| 维度 | cron XML（video-content-workflow） | ad-hoc markdown（本 skill） |
|---|---|---|
| 触发 | cron 定时任务 | 用户单次请求 |
| 输出格式 | DocxXML `<docx><title>...</title><body>...</body></docx>` | Markdown `#` 标题 / 表格 / 链接 |
| 富 block | 支持 callout/grid/checkbox/画板 | 不支持（用 markdown 原生语法） |
| 写入命令 | `+update --command overwrite --doc-format xml` | `+update --command overwrite --doc-format markdown` |
| 警告 | `degrade_code=4007`（`<docx>`/`<body>` 被 escape，非致命） | 无类似警告 |
| 文件路径 | `~/.hermes/cron/output/*.xml` | `~/workspace/*.md` |

**关键差异**：cron XML 的 `<docx>` / `<body>` 根标签会被 escape 警告但功能正常；markdown 模式完全没这个问题，所以**ad-hoc 报告**优先用 markdown。

## 实测案例（2026-06-14 v3 报告）

- 报告源文件：`/Users/xiesg/workspace/feishu_videos_analysis_2026-06-14_v3.md`（7.5 KB）
- 复制到 CWD：`cp ... ./v3_report.md`
- 写入命令：`lark-cli docs +create --api-version v2 --doc-format markdown --content @v3_report.md`
- 返回 doc_id：`MLR7duTUnoln0WxI0ErcLrrun4g`
- revision=4
- URL：`https://zt854jxlft.feishu.cn/docx/MLR7duTUnoln0WxI0ErcLrrun4g`
- 验证 fetch：10.2 KB markdown 完整返回，6 H2 章节 + 5 H3 子节 + 6 判断子节全部渲染
- 后续覆盖：`+update --command overwrite` 把 v3 替换为最终版，revision=7

**结论**：markdown 路径对 ad-hoc 报告完美可用，无路径陷阱，无 escape 警告。
