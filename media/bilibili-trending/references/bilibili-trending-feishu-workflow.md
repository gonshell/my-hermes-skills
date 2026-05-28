# Bilibili 全站热门视频 — 飞书推送工作流

## 文档信息
**文档 token**：`DrVkdlj3OokcHQxYD5hcdcAin9g`
**文档标题**：每日Bilibili全站热门视频推送

## 完整步骤

### 步骤 0：数据获取（见 SKILL.md 主文）
- 使用 `popular` API 获取 B站热门视频
- 过滤 3天内发布视频
- 按综合评分排序
- 输出格式见 SKILL.md

### 步骤 1：写入飞书文档

**文档 token**：`DrVkdlj3OokcHQxYD5hcdcAin9g`（固定值，直接使用）

**操作流程（保留7天逻辑）**：

```bash
# 1. 读取文档现有内容
lark-cli docs +fetch --api-version v2 --doc "DrVkdlj3OokcHQxYD5hcdcAin9g"

# 2. 解析内容过滤（见下方 Python 脚本），输出 lark_content.md

# 3. 整体 overwrite 写入（推荐用 Markdown 格式，内容写入文件后 pipe 进 stdin）
cat ./lark_content.md | lark-cli docs +update \
  --api-version v2 \
  --doc "DrVkdlj3OokcHQxYD5hcdcAin9g" \
  --command overwrite \
  --markdown -
```

**⚠️ 关键注意事项**：
- `--content @./filename` 或 `--markdown -` 要求**相对路径**，不能用 `/tmp/xxx` 绝对路径（否则报错：`--file must be a relative path within the current directory`）
- overwrite 模式的参数是 `--command overwrite`（不是 `--mode`）
- 大段内容推荐直接 pipe 文件到 stdin（`--markdown -`），避免相对路径踩坑
- v2 API 返回 `[deprecated]` 警告不影响写入成功（`"success": true` 即可）
- 内容用 Markdown 格式即可（链接在飞书文档中会直接渲染为可点击），无需使用 XML

### 步骤 2：发送通知（仅出错时）

告警格式（cron 自动送达本窗口）：
```
🚨 定时任务执行出错

📌 任务：每日Bilibili全站热门视频推送
⏰ 时间：<当前时间，格式如 2026-05-28 22:00:00>
❌ 阶段：<获取数据/读取文档/写入文档/未知>
📝 错误：<具体错误描述>
```

通知目标：本聊天窗口（`oc_de41dc899cd2e0f9afad7dddb8fa1e89`），由 cron 自动送达，无需手动发送。

### 步骤 3：清理临时文件

```bash
rm -f ./lark_content.md
```

## 通知策略

| 状态 | 行为 |
|------|------|
| 成功 | 静默，不发任何消息 |
| 出错 | 输出告警格式，cron 自动送达本窗口 |

## 关键Pitfall汇总

| 问题 | 原因 | 解法 |
|------|------|------|
| `--content "@/tmp/xxx"` 报错 | lark-cli 要求相对路径 | 用 `cat file.md \| lark-cli ... --markdown -` pipe 方式 |
| `--command overwrite` 误写成 `--mode` | v2 API 用 --command | 必须用 --command |
| popular API 返回 -352 | 限流 | 等待1秒后重试，最多3次 |
| 小视频仅返回4条 | popular 接口小视频本身就少 | 正常现象，可接受 |