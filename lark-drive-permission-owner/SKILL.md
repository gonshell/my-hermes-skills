---
name: lark-drive-permission-owner
version: 1.0.0
description: "飞书云文档权限与所有权：permission 检查、owner 转移、delete 操作边界。2026-05-17 session 踩坑记录。"
---

# lark-drive-permission-owner

> 2026-05-17 session 踩坑记录：权限检查、owner 转移、delete 操作的边界。

## 核心概念

| 权限操作 | API | 执行主体限制 |
|----------|-----|-------------|
| 查询权限 | `permission.members auth` | 任意有权限者 |
| 授权/添加协作者 | `permission.members create` | owner 或有 `manage_public` 者 |
| 转移 owner | `permission.members transfer_owner` | **仅 owner** |
| 删除文档 | `drive +delete` | **仅 owner** |

## `permission.members auth` 能查什么

- 可查项：`view`、`edit`、`share`、`comment`、`export`、`copy`、`print`、`manage_public`
- **不可查：`delete`** — 没有这个 action
- 返回 `auth_result: true` 只代表"你有该权限"，不代表你能执行需要 owner 身份的操作

## Owner 转移的限制

- Bot 无法将自己设为用户文档的 owner（`permission denied`）
- Owner 转移只能发生在同一租户内的用户之间
- 转移后原 owner 可选择保留权限（`old_owner_perm` 参数）

## Wiki 文档的 token 分辨率

Wiki URL（`/wiki/<node_token>`）**不能**直接作为 file_token 使用：

```bash
# 1. 查询节点，拿到真实 obj_token
lark-cli wiki spaces get_node --params '{"token":"<WIKI_NODE_TOKEN>"}'

# 返回：
#   node.node_token   = wiki 节点 token
#   node.obj_token    = 真实文档 token（如 docx）
#   node.obj_type     = 文档类型（docx/doc/sheet/bitable/...）
#   node.owner        = 文档 owner open_id
```

## Delete 操作要求

```bash
lark-cli drive +delete --file-token "<obj_token>" --type <obj_type> --yes
```

- **必须使用 `obj_token`（真实文档 token），不是 `node_token`**
- 执行者必须是文档 owner，否则 `forbidden`
- Bot 作为非 owner 无法删除用户拥有的文档

## 典型错误

| 错误 | 原因 | 解法 |
|------|------|------|
| `forbidden` on delete | Bot 不是 owner | 用户自己删除，或转回 owner 再删 |
| `permission denied` on transfer_owner | 非 owner 尝试转移 | 仅 owner 可执行 |
| `not exist` on file.comments | 用错了 token（如用了 node_token） | 先 `wiki spaces get_node` 解析为 obj_token |

## 补充场景：Wiki 文档在 Feishu UI 删除失败

当文档位于 Bot 的知识库空间（如"牧羊的机器人-02的云文档"）时，Feishu UI 删除会提示"删除的内容将进入其所在知识库回收站，30 天后自动彻底删除"后失败——这是 UI 层校验，非 API 错误。

**根因**：文档 owner 是用户，但文档在 bot 的 wiki 空间下；UI 检测到 wiki 归属与 owner 不一致，拒绝放行。

**解法**：
1. 用户在飞书 App 直接打开文档 → 右上角「···」→「删除」手动删除
2. 或者：将文档从 bot wiki 空间 move 到用户自己的云空间（需要 `move` 权限），再由用户在目标位置删除

## Bot 作为操作方的最佳实践

1. **确认 owner**：查询 `wiki spaces get_node` 或 `permission.members auth`
2. **如果 owner 是用户**：告知用户需要自己删除，或将 owner 转为 bot 再操作
3. **如果 owner 是 bot**：直接执行 delete

## ⚠️ `transfer_owner` CLI 命令 bug（v1.0.19）

`lark-cli drive permission.members transfer_owner` 命令存在参数解析 bug：token 参数无论以何种方式传入（位置参数、`--token` flag、`--params token` 字段），均被忽略并报错 "missing required path parameter: token"。

**解法**：

**方案 1（推荐）**：在飞书文档界面直接操作 → 右上角「···」→「更多」→「转移所有权」

**方案 2**：用 curl 调用 REST API，需自行获取 tenant_access_token：
```bash
# 获取 tenant token
TENANT_TOKEN=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "app_id=cli_a95529a37f78dbb4&app_secret=$APP_SECRET&grant_type=client_credentials" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tenant_access_token'])")

# 调用 transfer_owner（转移后保留旧 owner 全部权限）
curl -s -X POST "https://open.feishu.cn/open-apis/drive/v1/permissions/{token}/members/transfer_owner?type=docx&remove_old_owner=false&old_owner_perm=full_access" \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"member_id":"<open_id>","member_type":"openid"}'
```

**验证 scope**：`lark-cli auth check --scope "docs:permission.member:transfer"`