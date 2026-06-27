---
name: lark-cli-hermes-setup
description: 在 Hermes 环境（Mac 本地 Agent）中使用 lark-cli 的正确初始化流程，解决 bot-only 模式限制。
triggers:
  - lark-cli 报错 "not configured"
  - lark-cli 报错 "bot identity does not support"
  - 需要用 lark-cli 操作飞书文档
  - 首次在 Hermes 中使用 lark-cli
---

# lark-cli Hermes 环境初始化

## 已知问题

Hermes Agent 环境中 lark-cli 默认绑定到 `hermes` workspace，但 config 显示 `identity: bot-only`，导致：
- `docs +search`、`docs +fetch --as user` 等需要 user 身份的命令全部报错
- `lark-cli auth login --as user` 命令行方式在 bot-only 下报错
- bot-only 模式下 CLI 不会触发交互式授权流程

## 正确初始化步骤

### 第一步：绑定 workspace
```bash
lark-cli config bind --source hermes
```
输出包含 `"identity":"bot-only"` 是正常的，不影响 bot 身份操作。

### 第二步：确认需要的身份
| 操作 | 所需身份 | 备注 |
|------|---------|------|
| `docs +create` | bot | 可用 |
| `docs +update --command append` | bot | 可用 |
| `docs +fetch` | bot 或 user | bot 可读公开文档 |
| `docs +search` | user | **必须 user** |
| `docs +update --as user`（精准编辑）| user | 需要用户授权 |
| `drive +search` | user | **必须 user** |

### 第三步：如果需要 user 身份（搜索文档时）
**命令行 `lark-cli auth login --as user` 在 bot-only 下会报错**，正确方式是：

**方式 A（推荐）：在飞书开发者后台为应用开通对应 scope**
- 文档相关 scope：`docx:document:readonly`（只读）或 `docx:document:rw`（读写）
- 在 [飞书开发者后台](https://open.feishu.cn/app) 找到 cli_a95529a37f78dbb4
- 添加所需权限后，bot 身份即可使用对应 API（无需 user login）

**方式 B：解除 bot-only 限制**
```bash
# 查看是否有解除命令
lark-cli config strict-mode --help
```

## 快速检查清单

```bash
# 1. 检查绑定状态
lark-cli config show

# 2. 如果需要搜索文档，先尝试 bot 是否可用
lark-cli docs +fetch --api-version v2 --doc "已有文档token"

# 3. 如果 bot 不可用，再走 user auth 流程
lark-cli auth login --as user
```

## 参考

- [`references/transfer-owner.md`](references/transfer-owner.md) — `drive permission.members transfer_owner` 的正确调用方式（--params JSON 包装 vs --type flag 踩坑）

## 常见错误对照

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `not configured` | 未绑定 workspace | `lark-cli config bind --source hermes` |
| `bot identity does not support` | 操作需要 user 身份 | 开通 bot scope 或解除 bot-only |
| `auth login --as user 报错` | bot-only 模式下 CLI 不支持交互 | 在开发者后台为 bot 添加 scope |
| `workspace not bound` | workspace 未绑定 | `lark-cli config bind --source hermes` |
