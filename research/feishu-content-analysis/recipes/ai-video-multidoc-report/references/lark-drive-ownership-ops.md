# 飞书云文档所有权管理操作

> 来源：2026-06-14 session 中处理用户"删除文档 + 转移所有权"请求时发现的工作流。
> 原始 skill `lark-drive` 是 protected（hub-installed），以下操作是其 API 的常用子集，
> 记录在自建 skill 的 references 下供快速查阅。

## 转移文档所有权

**场景**：bot 创建的 doc 需要转给用户（或反过来），同时保留原所有者的访问权限。

**命令**：
```bash
lark-cli drive permission.members transfer_owner \
  --params '{"token": "<doc_token>", "type": "docx"}' \
  --data '{"member_id": "<user_openid>", "member_type": "openid"}'
```

**关键参数**：
- `--params`：URL 参数，包含 `token`（doc token）和 `type`（doc/sheet/bitable/docx/wiki/file）
- `--data`：request body，包含 `member_id` 和 `member_type`
- `member_type` 可选：`openid`（开放平台 ID）/ `userid`（用户自定义 ID）/ `email`（飞书邮箱）/ `appid`（应用 ID）

**可选 query 参数**（在 --params JSON 里加）：
- `need_notification: true/false` — 是否通知新所有者（默认 true）
- `old_owner_perm: "view"/"edit"/"full_access"` — 原所有者保留的权限（默认 full_access）
- `remove_old_owner: true/false` — 是否移除原所有者权限（默认 false）
- `stay_put: true/false` — 文档是否留在原位置（默认 false，移到新所有者空间）

**用户 openid 获取方式**：
- 从飞书通讯录 API：`lark-cli contact` 系列命令
- 从历史操作：bot 与用户交互时飞书事件里带的 `open_id`
- 记忆中的已知值：`ou_a0b6be7e404317f09b2ec6df33bde74b`（牧羊的机器人，2026-06-14 确认）

**典型流程**：
1. bot 创建 doc → doc 归 bot 所有
2. `transfer_owner` 给用户 → 用户成为所有者，bot 保留 full_access
3. 用户可以在自己的飞书空间管理该 doc

## 删除文档

**场景**：清理不需要的 doc。

**命令**：
```bash
lark-cli drive +delete --file-token <doc_token> --type docx --yes
```

**关键参数**：
- `--file-token`：doc token（**不是** `--file`，那是错的 flag 名）
- `--type`：doc 类型（docx/doc/sheet/bitable/file/folder/mindnote/slides/shortcut）
- `--yes`：确认高危操作（不加会报错）

**常见错误**：
- `lark-cli drive +delete --file xxx` → `unknown flag: --file`（正确是 `--file-token`）
- 文档已删除 → API 返回 `1061007 file has been delete`（不是错误，是已经删了）
- 无权限删除 → API 返回 `1061001` 或类似权限错误

## 查询文档权限

```bash
lark-cli drive permission.members auth \
  --params '{"token": "<doc_token>", "type": "docx"}'
```

返回当前 bot 对该 doc 的权限级别。
