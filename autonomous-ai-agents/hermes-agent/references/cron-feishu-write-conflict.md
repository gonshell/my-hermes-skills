# Cron + 飞书写入冲突防范

## 核心问题

当两个 cron job 同时用 `overwrite` 写入同一个飞书文档时，后触发的那一个会覆盖先写入的内容（revision_id 较新的保留，较旧的丢失）。

**触发场景**：例如 YouTube 早间档（06:00）和 YouTube 晚间档（20:00）都向同一个文档写入，晚间任务触发时会把早间任务的数据覆盖。

## 解法：每个并行写入器独立文档

为每个 cron job 分配独立的飞书文档 doc_id：

| Job | 时间 | 文档 doc_id |
|-----|------|-------------|
| YouTube 早间档 | 06:00 | `<doc_token_AM>` |
| YouTube 晚间档 | 20:00 | `<doc_token_PM>` |
| Bilibili AI 热门 | 21:00 | `<doc_token_AI>` |
| Bilibili 全站热门 | 22:00 | `<doc_token_Trending>` |

## 操作步骤

### 1. 创建独立文档（每个写入器一个）

```bash
# 用 lark-cli docs +create 创建，每个文档带独立初始内容
lark-cli docs +create --api-version v2 --content "<title>文档标题</title><p>初始内容</p>"
# 记录返回的 doc_token
```

### 2. 转移所有权（如果需要）

```bash
lark-cli drive permission.members transfer_owner \
  --params "{\"token\":\"<doc_token>\",\"type\":\"docx\",\"remove_old_owner\":false,\"old_owner_perm\":\"full_access\",\"need_notification\":false}" \
  --data '{"member_type":"openid","member_id":"<user_openid>"}'
```

### 3. 更新 cron job prompt 的 doc_id

```bash
hermes cron edit <job_id>  # 或用 cronjob tool 的 update action
```

### 4. 验证写入不碰撞

触发两个任务后，分别 `lark-cli docs +fetch --api-version v2 --doc <token>` 验证数据各自独立保留。

## 附：成功静默模式（deliver:local）

不需要定时任务向聊天窗口推送成功通知时：

1. cron job 设置 `deliver:local`（输出仅存入 session，不推送）
2. prompt 内部处理逻辑：写入成功后静默，出错时主动用 `send_message` 告警到指定 channel

这样用户只在出问题 时收到通知，正常运行时完全无打扰。

## 判断是否需要独立文档

| 场景 | 是否需要独立文档 |
|------|------------------|
| 多个 writer，`overwrite` 写入同一文档 | ✅ 是 |
| 多个 writer，`append` 追加到同一文档 | ❌ 否（追加不冲突） |
| 单一 writer，定期更新同一文档 | ❌ 否 |
| 不同时间窗口写入同一文档（时间不重叠） | ⚠️ 可选（保守起见仍建议分开） |

**经验法则**：如果两个 cron job 的 `overwrite` 写入发生在同一 UTC 小时境内，给它们分配独立 doc_id。
