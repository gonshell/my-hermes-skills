# YouTube AI 热门视频 — 飞书推送工作流

## 完整步骤

### 步骤 0：数据获取（见 SKILL.md 主文）
- 优先 YouTube browser 提取
- YouTube 超时 → 切换 Bing视频搜索 + Bilibili AI早报
- ⚠️ Bilibili AI早报每期 BV号 不同，必须先搜索再点击，不要 hardcode BV号

### 步骤 1：写入飞书文档

**文档 token**：`TBEddfdvQogBTxx9HArceKmlnYd`（固定值，直接使用）

**操作命令**：
```bash
# 1. 先将 XML 内容写入本地文件（绝对不能用 /tmp/，要用相对路径）
cat > ./lark_content.xml << 'EOF'
<h1>YYYY-MM-DD 20:00</h1>
<h2>📊 一、最热门长视频 TOP 10</h2>
...（XML 格式内容）
EOF

# 2. 追加到飞书文档
lark-cli docs +update --api-version v2 \
  --doc "TBEddfdvQogBTxx9HArceKmlnYd" \
  --command append \
  --content @./lark_content.xml
```

**成功响应**：
```json
{"ok": true, "data": {"result": "success", ...}}
```

**关键Pitfall**：
- `--content` 参数在 `append` 模式下**必须是相对路径**（`@./filename`），不能用 `/tmp/xxx`
- XML 内容中如有 `<`、`>`、`&` 等字符，**不需要额外转义**，直接写入文件即可

### 步骤 2：发送飞书群通知

**查找群ID**：
```bash
lark-cli im chats list
# 返回 chat_id 字段，如 oc_110e535468b6ffbf7a978eb95b1cd51f
```

**发送消息**：
```bash
lark-cli im +messages-send \
  --chat-id "oc_xxx" \
  --text "📺 每日AI热门视频推送（晚）
✅ 内容已写入《每日AI热门视频推送》
📅 YYYY-MM-DD 20:00
🔗 https://zt854jxlft.feishu.cn/docx/TBEddfdvQogBTxx9HArceKmlnYd" \
  --msg-type text
```

⚠️ **必须用 `--text` 而非 `--content`**：前者接收纯文本，后者要求 JSON 格式 `{"text":"..."}`。

### 步骤 3：清理临时文件

```bash
rm -f ./lark_content.xml
```

## 关键Pitfall汇总

| 问题 | 原因 | 解法 |
|------|------|------|
| `--content "@/tmp/xxx"` 报错 | lark-cli 要求相对路径 | 用 `@./filename` |
| `--content "text"` 报错 | append 模式不用 JSON | 用 `--content @./file` |
| `--content '{"text":"..."}'` 报错 | 格式问题 | 用 `--text` 传纯文本 |
| Bilibili 合集页无法渲染 | 页面懒加载/动态渲染 | 改用搜索+点击进入视频页 |
| Bilibili 直接URL访问返回"出错啦!" | bilibili 对直接URL访问有登录态检查 | 先搜索再点击，利用 referrer 头通过检查 |
