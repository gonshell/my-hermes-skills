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
- 文档 token：`TBEddfdvQogBTxx9HArceKmlnYd`（无空格）
- 文档标题：《每日AI热门视频推送》

### 写入命令
```bash
# 1. 使用 write_file 直接写入当前目录（lark-cli 要求相对路径）
#    内容为完整 XML 字符串（已在 skill 输出格式中定义）
# 2. 使用 append 指令追加
lark-cli docs +update --api-version v2 \
  --doc "TBEddfdvQogBTxx9HArceKmlnYd" \
  --command append \
  --content @./ai_trending_content.xml

# 3. 清理临时文件
rm -f ./ai_trending_content.xml
```

**⚠️ `write_file` 路径规则**：写入时必须用相对路径 `./ai_trending_content.xml`，不能用 `/tmp/ai_trending_content.xml`，否则 lark-cli 报错 `--file must be a relative path within the current directory`。用 `write_file` 直接写到当前目录即可，无需经过 `/tmp/` 中转。

### XML 内容模板

日期标题用 `<h1>`，各区块用 `<h2>`，视频条目用 `<ol><li>` 列表结构（不要用多个 `<p><br/>` 堆砌），URL 裸写在文本中：

```xml
<h1>YYYY-MM-DD 06:00</h1>

<h2>📊 一、最热门长视频 TOP 10</h2>

<ol><li seq="auto"><p><b>视频标题</b></p><p>播放量：XXX | 发布时间 | 频道名</p><p><a href="https://youtube.com/watch?v=VIDEO_ID">https://youtube.com/watch?v=VIDEO_ID</a></p></li>...</ol>

<h2>📊 二、最热门短视频 TOP 5</h2>

<ol><li seq="auto"><p><b>视频标题</b></p><p>播放量：XXX | 发布时间</p><p><a href="https://youtube.com/shorts/VIDEO_ID">https://youtube.com/shorts/VIDEO_ID</a></p></li>...</ol>

<h2>📊 三、当天新发热门视频</h2>

<h3>长视频 TOP 5</h3>
<ol>...</ol>

<h3>短视频 TOP 3</h3>
<ol>...</ol>

<p>📝 摘要说明：当前热门主题分析...</p>
```

**⚠️ 注意事项：**
- `--content @./filename` 中的路径**必须是相对路径**，不能用 `/tmp/xxx` 绝对路径，否则报错 `--file must be a relative path within the current directory`
- 链接用纯文本或 `<a href>` 格式，不要 Markdown 链接语法（`[text](url)` 在飞书表格中渲染为纯文本，无法点击）
- `&` 在 XML 内容中需要转义为 `&amp;`
- `<ol>` 配合 `seq="auto"` 自动编号，条目多时比手写序号更健壮

---

## 步骤 2：发送飞书群通知

### 获取群 ID
优先使用环境变量，无需额外读取文件或调用 API。

```bash
# 方法1（推荐）：从环境变量直接获取
# cron job 运行时 FEISHU_HOME_CHANNEL 自动设置为当前会话 chat_id
echo $FEISHU_HOME_CHANNEL
# 输出: oc_de41dc899cd2e0f9afad7dddb8fa1e89

# 方法2：读取 cron jobs.json 获取 origin chat_id
cat ~/.hermes/cron/jobs.json | python3 -c "
import json,sys
jobs = json.load(sys.stdin)['jobs']
for j in jobs:
    if 'AI' in j.get('name','') and '早' in j.get('name',''):
        print(j['origin']['chat_id'])
"

# 方法3（备选）：列出所有群
lark-cli im chats list --page-all
```

### 发送文本消息
```bash
# 推荐：使用 --text 短格式（自动包装为 {"text":"..."}，无需手写 JSON）
# chat_id 从 FEISHU_HOME_CHANNEL 环境变量获取，cron job 自动注入
lark-cli im +messages-send \
  --chat-id "${FEISHU_HOME_CHANNEL}" \
  --text $'📺 每日AI热门视频推送（早/晚）\n✅ 内容已写入《每日AI热门视频推送》\n📅 YYYY-MM-DD HH:00\n🔗 https://zt854jxlft.feishu.cn/docx/TBEddfdvQogBTxx9HArceKmlnYd'
```

---

## 完整脚本（供参考）

```bash
DOC_TOKEN="TBEddfdvQogBTxx9HArceKmlnYd"
CHAT_ID="${FEISHU_HOME_CHANNEL:-oc_de41dc899cd2e0f9afad7dddb8fa1e89}"
DATE_STR=$(date '+%Y-%m-%d')

# 写入文档
lark-cli docs +update --api-version v2 \
  --doc "$DOC_TOKEN" \
  --command append \
  --content @./ai_trending_content.xml

# 发送通知（使用 --text 短格式，无需手写 JSON，早/晚根据 cron job 调整）
lark-cli im +messages-send \
  --chat-id "$CHAT_ID" \
  --text $'📺 每日AI热门视频推送（早/晚）\n✅ 内容已写入《每日AI热门视频推送》\n📅 '"$DATE_STR"' HH:00\n🔗 https://zt854jxlft.feishu.cn/docx/'"$DOC_TOKEN"
```

---

## 相关文件
- 飞书文档：`https://zt854jxlft.feishu.cn/docx/TBEddfdvQogBTxx9HArceKmlnYd`
- 通知群：`$FEISHU_HOME_CHANNEL`（cron job 自动注入，当前为 `oc_de41dc899cd2e0f9afad7dddb8fa1e89`）
