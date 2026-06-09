# YouTube AI 热门视频 — 飞书推送工作流

## 文档信息
**文档 token**：`TBEddfdvQogBTxx9HArceKmlnYd`
**文档标题**：每日AI热门视频推送

## 完整步骤

### 步骤 0：数据获取（见 SKILL.md 主文）
- 优先 YouTube browser 提取

**⚠️ 重要**：YouTube 不可访问时直接报错，**不使用任何备选数据源**。输出告警格式后直接结束任务，不写入任何数据。

### 步骤 1：写入飞书文档（保留7天逻辑）

**文档 token**：`TBEddfdvQogBTxx9HArceKmlnYd`（固定值，直接使用）

**操作流程**：

```
1. 读取文档现有内容
   lark-cli docs +fetch --api-version v2 --doc "TBEddfdvQogBTxx9HArceKmlnYd"
   ⚠️ 注意：是 docs（复数），不是 doc；用 --doc（不是 --doc-token）

2. 解析内容，过滤掉 >7 天的旧段落
   - 用 Python 解析文档文本，识别日期标记（如 YYYY-MM-DD 或 MM-DD 格式）
   - 过滤掉早于 7 天前的条目

3. 拼接：保留内容 + 今日新内容

4. 整体 overwrite 写入
   lark-cli docs +update --api-version v2 \
     --doc "TBEddfdvQogBTxx9HArceKmlnYd" \
     --command overwrite \
     --content @./output.xml \
     --doc-format xml
   ⚠️ 注意：是 --command overwrite（不是 --mode）；是 --doc（不是 --doc-token）
```

**注意**：
- `--content` 必须用相对路径 `@./filename`
- overwrite 模式下用 `--command overwrite`（不是 `--mode`）
- XML 中 `<>&` 字符无需额外转义
- 成功时不发任何通知（静默）

### 步骤 2：发送通知（仅出错时）

告警格式（cron 自动送达本窗口）：
```
🚨 定时任务执行出错

📌 任务：每日AI热门视频推送(早/晚)
⏰ 时间：<当前时间，格式如 2026-05-28 20:00:00>
❌ 阶段：<获取数据/读取文档/写入文档/未知>
📝 错误：<具体错误描述>
```

通知目标：本聊天窗口（`oc_de41dc899cd2e0f9afad7dddb8fa1e89`），由 cron 自动送达，无需手动发送。

### 步骤 3：清理临时文件

```bash
rm -f ./output.xml
```

## 通知策略

| 状态 | 行为 |
|------|------|
| 成功 | 静默，不发任何消息 |
| 出错 | 输出告警格式，cron 自动送达本窗口 |

## 关键Pitfall汇总

| 问题 | 原因 | 解法 |
|------|------|------|
| `--content "@/tmp/xxx"` 报错 | lark-cli 要求相对路径 | 用 `@./filename` |
| `--command overwrite` 误写成 `--mode` | v2 API 用 --command | 必须用 --command |
| `lark-cli doc +get-content` 报错 unknown command | 正确命令是 `docs +fetch`（复数） | 注意 `doc` vs `docs` 区分 |
| `lark-cli doc +overwrite` 报错 unknown command | 正确命令是 `docs +update`（复数） | 读取用 +fetch，写入用 +update |
| `lark-cli docs +update --mode overwrite` 报错 unknown flag | v2 API 用 --command | 必须用 `--command overwrite` |
| YouTube 不可访问时自动切换 Bilibili | Skill 中有备选方案章节 | 已删除备选方案，YouTube 不可用直接报错 |