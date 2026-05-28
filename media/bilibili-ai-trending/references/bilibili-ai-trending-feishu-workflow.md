# Bilibili AI 热门视频 — 飞书推送工作流

## 文档信息
**文档 token**：`MjT6dT3abopHBpxkwPCcauGWn6e`
**文档标题**：每日Bilibili AI热门视频推送

## 完整步骤

### 步骤 0：数据获取（见 SKILL.md 主文）
- Bilibili browser 提取
- 按综合评分排序（播放量对数 + 新鲜度）
- 输出格式见 SKILL.md

### 步骤 1：写入飞书文档

**文档 token**：`MjT6dT3abopHBpxkwPCcauGWn6e`（固定值，直接使用）

**操作流程（保留7天逻辑）**：

```
1. 读取文档现有内容
   lark-cli docs +fetch --api-version v2 --doc "MjT6dT3abopHBpxkwPCcauGWn6e"

2. 解析内容，过滤掉 >7 天的旧段落
   - 用 Python 解析文档文本，识别日期标记（如 YYYY-MM-DD 或 MM-DD 格式）
   - 过滤掉早于 7 天前的条目

3. 拼接：保留内容 + 今日新内容

4. 整体 overwrite 写入
   lark-cli docs +update --api-version v2 \
     --doc "MjT6dT3abopHBpxkwPCcauGWn6e" \
     --command overwrite \
     --content @./lark_content.xml
```

**注意**：
- `--api-version v2` 是**所有** lark-cli docs 命令的必填参数
- `--content` 必须用相对路径 `@./filename`（`@/tmp/xxx` 绝对路径会报错）
- overwrite 模式下用 `--command overwrite`（不是 `--mode`）
- XML 中 `<>&` 字符无需额外转义

### 步骤 2：发送通知（仅出错时）

告警格式（cron 自动送达本窗口）：
```
🚨 定时任务执行出错

📌 任务：每日Bilibili AI热门视频推送
⏰ 时间：<当前时间，格式如 2026-05-28 21:00:00>
❌ 阶段：<获取数据/读取文档/写入文档/未知>
📝 错误：<具体错误描述>
```

通知目标：本聊天窗口（`oc_de41dc899cd2e0f9afad7dddb8fa1e89`），由 cron 自动送达，无需手动发送。

### 步骤 3：清理临时文件

```bash
rm -f ./lark_content.xml
```

## 通知策略

| 状态 | 行为 |
|------|------|
| 成功 | 静默，不发任何消息 |
| 出错 | 输出告警格式，cron 自动送达本窗口 |

## 关键Pitfall汇总

| 问题 | 原因 | 解法 |
|------|------|------|
| `unknown command "doc" for "lark-cli"` | 命令格式错误，`+fetch` 是 docs 子命令 | 用 `lark-cli docs +fetch` 不是 `lark-cli doc +fetch` |
| `unknown flag: --doc-token` | flag 名称错误 | 用 `--doc` 不是 `--doc-token` |
| `unknown flag: --doc` | API 版本缺失 | 必须加 `--api-version v2` |
| `--content "@/tmp/xxx"` 报错 | lark-cli 要求相对路径 | 用 `@./filename` |
| `--command overwrite` 误写成 `--mode` | v2 API 用 --command | 必须用 `--command` |
| Bilibili 搜索页 `browser_click` 不导航 | Bilibili 动态渲染 | 从初始快照提取所有数据 |