# 飞书机器人权限官方列表（来源：hermes-agent.nousresearch.com/docs）

> 基于官方文档 `https://hermes-agent.nousresearch.com/docs/user-guide/messaging/feishu` 验证（2026-06-08）。
> 凡是手册中提到"必需权限"或"推荐权限"，以本文件为准。

## 必需权限（5 项）

| Scope | 用途 | 缺失后果 |
|-------|------|---------|
| `im:message` | 接收和读取消息 | 机器人收不到任何消息 |
| `im:message:send_as_bot` | 以机器人身份发送消息 | 机器人能收但不能回 |
| `im:resource` | 访问图片、文件、音频 | 用户发图/文件/语音时无法处理 |
| `im:chat` | 访问群组元数据 | 群聊相关 API 全部失败 |
| `im:chat:readonly` | 读取群列表和成员 | 群成员解析失败 |

> 旧文档/网上教程常漏掉 `im:resource` — 接收图片/文件/语音时机器人会报错。

## 推荐权限（3 项，启用完整功能）

| Scope | 用途 | 缺失后果 |
|-------|------|---------|
| `im:message.reactions:readonly` | 接收表情回应事件 | 用户 @反应时无事件触发 |
| `admin:app.info:readonly` | 自动检测机器人身份（@提及门控） | 群聊 @机器人时无法准确识别自己 |
| `contact:user.id:readonly` | 解析用户 ID（白名单匹配） | `FEISHU_ALLOWED_USERS` 白名单功能失效 |

## 批量导入 JSON 模板

```json
{
  "scopes": {
    "tenant": [
      "im:message",
      "im:message:send_as_bot",
      "im:resource",
      "im:chat",
      "im:chat:readonly",
      "im:message.reactions:readonly",
      "admin:app.info:readonly",
      "contact:user.id:readonly"
    ]
  }
}
```

> 飞书开发者控制台 → 权限管理 → 批量导入/导出权限 → 粘贴上述 JSON。

## 不再使用的旧权限（已废弃，列出供排查）

| 旧 Scope | 替代 |
|---------|------|
| `contact:user.base:readonly` | 改用 `contact:user.id:readonly`（ID-only，权限更小） |
| `contact:user.employee_id:readonly` | 不在官方必需列表，非必需不要申请 |
| `im:message.p2p_msg:readonly` | 已合并到 `im:message` |
| `im:message.group_msg` | 已合并到 `im:message` |
| `im:message.group_at_msg:readonly` | 已合并到 `im:message` |
| `docx:document:readonly` | 仅在启用飞书文档功能时需要；飞书聊天场景不需要 |

> 旧安装手册常列的"6-10 项权限"是过时的批量模板，申请了多余权限反而可能触发企业管理员审核。

## 权限发布后常见遗漏

1. **应用未发布** → 员工搜不到机器人。检查"版本管理与发布"→ 创建版本 → 提交发布
2. **不在用户可用范围** → 即使应用发布了，该用户也不可见。检查"应用发布"→"可用范围"是否包含该用户/部门
3. **企业策略限制自建应用** → 需联系企业管理员（IT 部门）放行

## 飞书环境变量速查（生产部署）

```bash
# 必需
export FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxxx
export FEISHU_APP_SECRET=your-a...here
export FEISHU_DOMAIN=feishu             # 国内版;国际版用 lark
export FEISHU_CONNECTION_MODE=websocket # 推荐;不需公网 IP

# 生产推荐
export FEISHU_ALLOWED_USERS=ou_xxx,ou_yyy   # 白名单(逗号分隔 open_id)
export FEISHU_HOME_CHANNEL=oc_xxx           # cron 推送目标群

# 群聊策略(open|allowlist|disabled,默认 allowlist)
export FEISHU_GROUP_POLICY=allowlist
export FEISHU_REQUIRE_MENTION=true          # 群聊需 @机器人

# Webhook 模式才需要(不推荐)
export FEISHU_ENCRYPT_KEY=...               # 签名验证
export FEISHU_VERIFICATION_TOKEN=...        # 负载内 token 校验
```

## `hermes gateway setup` 交互流程

```
1. 选择平台: Feishu / Lark
2. 输入 App ID
3. 输入 App Secret
4. 选择 Domain: feishu (国内)
5. 连接方式: 直接回车 (默认 websocket)
6. 鉴权选项:
   - 输入 1: 不限制（企业内所有人可用，最快）
   - 输入 2: 白名单（生产推荐，配合 FEISHU_ALLOWED_USERS）
```

> 如果选择白名单但没设置 `FEISHU_ALLOWED_USERS`，会进入空配对模式，需要把 `FEISHU_ALLOWED_USERS=ou_xxx,ou_yyy` 写入 `~/.hermes/.env` 并 `hermes gateway restart`。

> **重要纠正**：**不要用** `hermes pairing approve feishu <open_id>`。已通过 `hermes pairing approve --help` 验证：`hermes pairing` 仅支持 `telegram / discord / slack / whatsapp` 四个平台，飞书鉴权不走 `pairing` 子命令。飞书的用户授权机制是 `FEISHU_ALLOWED_USERS` 环境变量（白名单模式）或留空（开放模式）。
