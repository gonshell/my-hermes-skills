---
name: lark-doc-metadata
version: 1.0.0
description: 飞书云文档元数据查询：文档归属（owner）、最后修改人、创建/修改时间、标题等非内容信息。用于排查"谁在操作这个文档"、核对 cron job 写入目标、验证文档更新状态。
tags: [lark, feishu, doc, metadata]
---

# 飞书云文档元数据查询

## 命令

```bash
# 查询文档元数据（bot 身份即可，无需 --as user）
lark-cli drive metas batch_query \
  --data '{"request_docs":[{"doc_token":"<token>","doc_type":"docx"}]}' \
  --format json
```

**必填字段：**
- `doc_token`：文档 token（URL 中 `/docx/<token>` 部分）
- `doc_type`：`docx`（文档）、`sheet`（表格）、`bitable`（多维表格）等

## 返回字段说明

| 字段 | 含义 |
|------|------|
| `owner_id` | 文档所有者 open_id |
| `latest_modify_user` | 最后修改人 open_id |
| `create_time` | 创建时间（Unix 时间戳，秒） |
| `latest_modify_time` | 最后修改时间（Unix 时间戳，秒） |
| `title` | 文档标题 |
| `doc_token` | 文档 token |

**时间戳转换（Python）：**
```python
from datetime import datetime
ts = 1780146268
print(datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M'))
```

## 身份要求

- 使用 **bot 身份**即可读取（lark-cli 默认 bot）
- 若要进一步查询 open_id 对应的用户信息（姓名、邮箱）→ 需要 `--as user` 且应用有通讯录权限；否则返回 `41050 no user authority`
- 定时任务写入的文档，owner 通常是执行 `auth login` 的用户账号

## 典型场景

1. **排查"是谁在操作这个文档"** — 查询 owner_id 和 latest_modify_user，比对 cron job 执行账号
2. **核对 cron job 写入目标** — 拿到的 token 与 feishu-doc-map.md 中的预期 token 比对
3. **验证文档更新状态** — 检查 latest_modify_time 是否在预期时间范围内

## 注意事项

- 只能查**元数据**，不是内容。查内容用 `lark-cli docs +fetch`
- `docs +fetch`（v1 API）返回的 content 中**不包含** owner、create_time 等元数据
- cron job deliver 报告中出现的 `revision_id` 来自系统记录，不是从文档本身查询得到