# YouTube AI Trending — Feishu 推送工作流

本文件记录将 AI 热门视频数据写入飞书文档并发送通知的标准流程。

---

## 触发场景

定时 cron job 调用 `youtube-ai-trending` skill 获取数据后，需要同步执行：
1. 追加内容到飞书文档
2. 发送飞书群通知

---

## 步骤 1：写入飞书文档

### 目标文档
- 文档 token：`TBEddfdvQogBTxx9HArceKmlnYd`
- 文档标题：《每日AI热门视频推送》

### 写入命令
```bash
# 1. 将 XML 内容写入当前目录下的文件（lark-cli 要求相对路径）
cp /tmp/ai_trending_content.xml ./ai_trending_content.xml

# 2. 使用 append 指令追加
lark-cli docs +update --api-version v2 \
  --doc "TBEddfdvQogBTxx9HArceKmlnYd" \
  --command append \
  --content @./ai_trending_content.xml

# 3. 清理临时文件
rm -f ./ai_trending_content.xml /tmp/ai_trending_content.xml
```

### XML 内容模板

日期标题用 `<h1>`，各区块用 `<h2>`，视频条目用 `<p>` + `<br/>` 换行，URL 直接裸写在文本中（不要用 Markdown 链接格式，飞书表格中无法点击）：

```xml
<h1>YYYY-MM-DD 06:00</h1>

<h2>📊 一、最热门长视频 TOP 10</h2>

<p>1. 视频标题<br/>
   播放量：XXX · 发布时间 · 频道名<br/>
   https://youtube.com/watch?v=VIDEO_ID</p>

<p>2. ...（同上格式）</p>
...
```

**⚠️ 注意事项：**
- `--content @./filename` 中的路径**必须是相对路径**，不能用 `/tmp/xxx` 绝对路径，否则报错 `--file must be a relative path within the current directory`
- 链接用纯文本格式，不要 Markdown 链接语法（`[text](url)` 在飞书表格中渲染为纯文本，无法点击）
- `&` 在 XML 内容中需要转义为 `&amp;`

---

## 步骤 2：发送飞书群通知

### 获取群 ID
```bash
lark-cli im chats list --page-all
```
从返回中找到目标群 `chat_id`（格式：`oc_xxx`）。

### 发送文本消息
```bash
lark-cli im +messages-send \
  --chat-id "oc_xxx" \
  --msg-type text \
  --content '{"text":"📺 每日AI热门视频推送（早）\n✅ 内容已写入《每日AI热门视频推送》\n📅 YYYY-MM-DD 06:00\n🔗 https://zt854jxlft.feishu.cn/docx/TBEddfdvQogBTxx9HArceKmlnYd"}'
```

---

## 完整脚本（供参考）

```bash
# 写入文档
cp /tmp/content.xml ./ai_trending_content.xml
lark-cli docs +update --api-version v2 \
  --doc "TBEddfdvQogBTxx9HArceKmlnYd" \
  --command append \
  --content @./ai_trending_content.xml
rm -f ./ai_trending_content.xml

# 发送通知（群ID固定）
lark-cli im +messages-send \
  --chat-id "oc_110e535468b6ffbf7a978eb95b1cd51f" \
  --msg-type text \
  --content '{"text":"📺 每日AI热门视频推送（早）\n✅ 内容已写入《每日AI热门视频推送》\n📅 2026-05-09 06:00\n🔗 https://zt854jxlft.feishu.cn/docx/TBEddfdvQogBTxx9HArceKmlnYd"}'
```

---

## 相关文件
- 飞书文档：`https://zt854jxlft.feishu.cn/docx/TBEddfdvQogBTxx9HArceKmlnYd`
- 通知群：「牧羊的机器人-群01」（`oc_110e535468b6ffbf7a978eb95b1cd51f`）
