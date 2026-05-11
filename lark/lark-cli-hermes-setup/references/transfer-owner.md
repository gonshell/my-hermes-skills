# drive permission.members transfer_owner — 踩坑记录

## 核心问题

`lark-cli drive permission.members transfer_owner` 的 `--type` 参数**不是直连 flag**，必须包装在 `--params` JSON 里。

## 正确调用方式

```bash
lark-cli drive permission.members transfer_owner \
  --params '{"type":"docx","token":"文档token"}' \
  --data '{"member_id":"用户openid","member_type":"openid"}'
```

**注意：** token 要同时出现在 `--params` 的 JSON 里。CLI 内部会把 params + path token 合成完整 URL。

## 常见错误

| 错误 | 原因 |
|------|------|
| `unknown flag: --type` | `--type` 是 query 参数，不能做直连 flag |
| `missing required path parameter: token` | token 没放对位置（需在 `--params` 而非直接做 positional） |
| 操作无报错但权限未转移 | 用了 bot 身份而非 user 身份 |

## 身份要求

- **必须用 `--as user`** 或确认 lark-cli 已配置 user token
- bot 身份执行 transfer_owner 会静默失败（返回成功但实际未转移）

## type 值参考

| 文档类型 | type 值 |
|---------|---------|
| 新版云文档 (docx) | `docx` |
| 旧版文档 | `doc` |
| 知识库节点 | `wiki` |
| 电子表格 | `sheet` |
| 多维表格 | `bitable` |

## Schema 查看

```bash
lark-cli schema drive.permission.members.transfer_owner
```
