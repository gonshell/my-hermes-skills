# lark-doc-pitfalls 核心参考

> 飞书文档操作的高风险踩坑点。遇到飞书文档操作问题时先查此处。

## 最高频 Pitfall（必须背熟）

### `overwrite` + Markdown 内容必须带 `--doc-format markdown`

否则 API 返回 `partial_success` + warning `"Instruction produced no document changes"`，文档内容**完全不更新**。

```bash
# 错误 ❌
lark-cli docs +update --api-version v2 --doc "<doc_id>" --command overwrite --content @./lark_content.md

# 正确 ✅
lark-cli docs +update --api-version v2 --doc "<doc_id>" --command overwrite --doc-format markdown --content @./lark_content.md
```

### `--content @<filepath>` 必须用相对路径

```bash
# 错误 ❌
--content @/tmp/file.xml

# 正确 ✅
cp /tmp/content.xml ./content.xml
--content @./content.xml
```

### XML 内容禁止包含 `<title>` 标签

`<title>xxx</title>` 会被飞书解析为文档标题，覆盖手动设置的标题。每次 overwrite 后 `+fetch` 返回 `title: "Untitled"`。

```xml
<!-- ❌ 禁止 -->
<title>YouTube AI热门视频</title>
<h1>YouTube AI热门视频</h1>

<!-- ✅ 正确 -->
<!-- 每日AI热门视频推送 | 2026-05-29 21:00:00 -->
<h1>YouTube AI热门视频</h1>
```

## 扩展已有文档的标准流程（2026-06-24 验证）

当用户给一个已有飞书 doc token 并要求"加 N 章"或"补内容"时，按这个流程：

1. **先 `+fetch --scope outline` 确认现状**（不要直接 overwrite）——确认现有章节标题、避免重复、与用户对话过的结构一致
2. **写新章节到独立文件**（不要 heredoc 一次性灌整个 append）：
   ```bash
   # 先写到 /tmp
   write_file /tmp/feishu_chapter9.xml "<h1>第 9 章 ...</h1>..."
   # 再 cp 到 CWD（lark-cli 路径要求）
   cp /tmp/feishu_chapter9.xml ./feishu_chapter9.xml
   lark-cli docs +update --api-version v2 --doc "<doc_id>" --command append --content @feishu_chapter9.xml
   ```
3. **分批 append**（每章一个文件一次 append），不要一次 append 全部——这样如果中途某章失败，已 append 的内容不会丢
4. **写完再 `+fetch --scope outline` 验证**：确认新增章节标题出现在 outline 中
5. **大文件 append 经验值**：本会话测试 19KB + 28KB 的两次 append 都成功（合计 47KB 增量），单次 < 50KB XML 应该是安全的

## XML append 与 overwrite 的选型

| 场景 | 命令 | 原因 |
|---|---|---|
| 在已有文档尾部追加新章节 | `+update --command append --content @file.xml` | 保留现有内容 |
| 修改文档中间某段 | `+update --command str_replace` 或 `block_replace` | 精准修改 |
| 整篇重写 | `+update --command overwrite --doc-format markdown` | 谨慎使用，会清空原内容 |
| 新建文档 | `+update --command append`（对刚 create 的 doc 也有效） | 第一次内容写入 |

## 标题修改

**`+update --new-title` 无法修改 UI 标题**（v1 API 写入成功但 fetch 返回 null；v2 API 根本不支持）。

用户偏好解法：**删除重建**
```bash
lark-cli drive +delete --file-token "<token>" --type docx --yes
lark-cli docs +create --api-version v2 --title "新标题" --content @./file.xml --doc-format xml
```

## 删除文档

```bash
lark-cli api DELETE "/open-apis/drive/v1/files/<token>?type=docx" --params '{"type":"docx"}'
```

## 代码块写入

| 标签格式 | Feishu Block Type | `append` |
|----------|-------------------|----------|
| `<code_block>...</code_block>` | `code_block` | ❌ 内容丢失 |
| `<pre lang="x"><code>...</code></pre>` | `paragraph` | ✅ 正确 |

```python
def md_code_block_to_feishu_xml(code_text: str, lang: str) -> str:
    escaped = code_text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
    if lang:
        return f'<pre lang="{lang}"><code>\n{escaped}\n</code></pre>'
    else:
        return f'<pre><code>\n{escaped}\n</code></pre>'
```

## LaTeX 渲染

飞书使用 KaTeX 子集，**不支持 `\text{}`、`\mbox{}`、`\mathrm{}`**。

```latex
% 错误
$\pi \text{ 弧度} = 180°$

% 正确
$\pi 弧度 = 180°$
```

## 并行 Agent append 陷阱

1. **骨架 + 并行追加 → 内容重复**：骨架中占位标题/段落会保留，与 Agent 追加内容重复。解法：骨架只放 title + callout，不放章节标题。
2. **并行 append → 嵌套层级错误**：append 的内容嵌套在上一章节的子树中。解法：用 `overwrite` 重建 block 树。

## `block_insert_after` 必须先 fetch

```python
# 找到目标 block 的 id
match = re.search(r'<h2[^>]*id="([^"]+)"[^>]*>01 产品概述</h2>', content)
block_id = match.group(1)
```

## 文档所有权转移（transfer_owner）的 3 个实战坑

**坑 A：bot 身份 + strict mode 下禁止切到 user**（2026-06-21 实测）

在 Hermes 默认配置下，`lark-cli auth login` 会被 `strict mode=bot` 拦截（`error: "strict mode is bot, only bot identity is allowed"`），AI agent 只能以 bot 身份操作。**这意味着 bot 创建的飞书文档默认归 bot 所有，不是当前 user。**

**应对**：
- bot 创建文档后，CLI 仍会尝试给"当前 CLI user"授可管理权限——但 **user 未登录时 status=skipped**
- 必须主动调 `drive permission.members transfer_owner` API，把 owner 转给 user
- 不要假设"用 user 身份登录就能解决"——strict mode 是硬约束

**坑 B：`--content @<filepath>` 必须 CWD 相对路径（同样适用于 transfer）**

`drive permission.members transfer_owner` 调用虽然不直接传文件，但**所有 lark-cli 操作的工作目录假设都是当前 shell 的 CWD**。如果调用前后切换了目录，传参可能错乱。**保持 CWD 稳定**。

**坑 C：transfer_owner API 返回 code:0 ≠ 实际 owner 就是传入的 open_id（关键）**

**真实失败路径（2026-06-21 宇通客车文档案例）**：
- 用户选定的 open_id 是 `ou_bb96cfb0a6902e8c678db9896518939f`（USER.md 主条目）
- 调用 `transfer_owner` 时传入此 open_id，API 返回 `code: 0 / msg: Success`
- 但通过 `drive metas batch_query` 验证元数据：实际 `owner_id` 是 `ou_a0b6be7e404317f09b2ec6df33bde74b`（memory 另一条目）
- 两个 open_id 都被记在 memory 不同位置
- 两个 open_id 都有 view 权限（`permission.members.auth` 都返回 auth_result: true）

**判别规则（调 transfer_owner 后的强制验证）**：
1. **必须用 `drive metas batch_query` 验证实际 owner_id**——不要相信 API 返回
2. 如果实际 owner 与传入不同，**保持现状**（重复 transfer 通常不会改变）
3. **memory 冲突**：两个 open_id 都指向 user（猜测是 user 的不同身份/应用），让用户确认
4. 不要再发起 transfer——很可能回到相同状态

**验证命令模板**：
```bash
lark-cli --as bot drive metas batch_query \
  --data '{"request_docs":[{"doc_token":"<doc_id>","doc_type":"docx"}]}'
# 输出: data.metas[0].owner_id 即为真实 owner
```

**预防**：在执行 transfer_owner 前，**先问用户"您本人有几个 open_id / 工作生活是否分开"**——比事后排查更高效。