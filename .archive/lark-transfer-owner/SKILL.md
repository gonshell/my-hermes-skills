---
name: lark-transfer-owner
description: 转移飞书云文档所有权，旧 owner 保留权限
---

# lark-transfer-owner

转移飞书云文档所有权，旧 owner 保留权限。

## 触发条件

用户说"把文档所有权转给我"、"把权限转给我"等，附带了飞书文档链接。

## 命令格式

**token 必须放在 `--params` JSON 里，不能作为 positional 参数：**

```
lark-cli drive permission.members transfer_owner \
  --params '{"token":"<file_token>","type":"docx","remove_old_owner":false,"old_owner_perm":"full_access","need_notification":false}' \
  --data '{"member_type":"openid","member_id":"<target_openid>"}'
```

## 参数解析规则

从用户输入提取，不需用户额外提供：

| 参数 | 来源 | 说明 |
|------|------|------|
| file_token | 文档链接 URL | 从 `docx/` 或 `sheets/` 等路径后提取 |
| type | 文档链接路径 | docx → docx, sheets → sheet, wiki → wiki, bitable → bitable |
| target_openid | 记忆或上下文 | 用户 openid: `ou_a0b6be7e404317f09b2ec6df33bde74b` |
| remove_old_owner | 默认 false | 是否移除旧 owner 权限 |
| old_owner_perm | 默认 full_access | 移除旧 owner 时的兜底权限 |
| need_notification | 默认 false | 是否通知新 owner |

## 常见错误排查

| 错误信息 | 原因 | 解决 |
|----------|------|------|
| `missing required path parameter: token` | token 作为 positional 参数传了 | 必须放在 `--params` JSON 里 |
| `unknown flag: --file-token` | 用了不存在的 flag | 正确格式不用 --file-token |
| `Permission denied` | bot 不是文档 owner | 需要当前 owner 先转移给 bot |

## 验证

转移后用 `auth` 子命令确认 bot 仍有权限（`list` 子命令不存在，别写错）：

```
lark-cli drive permission.members auth --params '{"token":"<file_token>","type":"docx","action":"view"}'
```