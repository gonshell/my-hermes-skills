# Incremental Doc Editing After Publish

> 配套主 SKILL.md 的「发布后美化」阶段使用。**当文档已通过 `+create` 发出去、且需要追加图片/Callout/分栏/重排章节时**，用本文档的工作流，而不是删了重建。

## 何时用本参考

- 文档已经发布到飞书，document_id 已拿到
- 用户追加需求：在某段后插图、加 Callout 高亮、把某条 ol 替换成分组卡片、修改某段内容
- 内容太长（> 4000 字符）时分批发布后还要追加
- 不想删了重建（会丢浏览量、丢评论、丢收藏）

**不适用**：文档还没发，或者结构要从头设计 → 用主 SKILL.md 的 create 路径。

## 核心命令速查

```bash
# 拿到所有 H2/H3 的 block_id（用于精准定位）
lark-cli docs +fetch --api-version v2 --doc <doc_id> \
  --scope outline --format pretty
# 输出形如：<h2 id="doxcngDd3vRvVvqgO9jWDwFzRD4">一、...</h2>

# 在指定 block 之后插入内容（XML 格式，支持 callout/img/table 等所有块）
lark-cli docs +update --api-version v2 --doc <doc_id> \
  --command block_insert_after \
  --block-id <anchor_block_id> \
  --content '<callout ...>...</callout>' \
  --doc-format xml

# 替换整个 block 的内容（content 必须是 XML 单 block，不是字符串替换）
lark-cli docs +update --api-version v2 --doc <doc_id> \
  --command block_replace \
  --block-id <target_block_id> \
  --content '<new content>' \
  --doc-format xml

# 删除单个 block（递归删除整棵子树，对 li/p/callout 都生效）
lark-cli docs +update --api-version v2 --doc <doc_id> \
  --command block_delete \
  --block-id <block_id_to_remove>

# 字符串级别替换（用于 ol→callout 的整块替换，但 pattern 必须能精确匹配）
lark-cli docs +update --api-version v2 --doc <doc_id> \
  --command str_replace \
  --pattern '<ol>...原内容...</ol>' \
  --content '<callout>...新内容...</callout>' \
  --doc-format xml
```

## 标准工作流：发布后美化

### Step 1: 列出所有可定位的 block_id

```bash
lark-cli docs +fetch --api-version v2 --doc <doc_id> \
  --scope outline --format pretty
```

输出是 `<h2 id="..."><h3 id="...">` 的 HTML-ish 串。**H2/H3/H4 都有 id**，可以直接做锚点。普通 `<p>` / `<li>` 的 id 需要用 `--scope section --start-block-id <h2_id>` 才能看到。

### Step 2: 拿到具体段落的 block_id（如果要插在段落中间）

```bash
lark-cli docs +fetch --api-version v2 --doc <doc_id> \
  --scope section --start-block-id <h2_id> --end-block-id <next_h2_id> \
  --format pretty
```

section 模式返回的 XML 里每个 `<p> <li> <blockquote>` 都带 `id="..."`。**这是唯一稳定的 id 源**（full 模式的 pretty 不带 id）。

### Step 3: 选择修改方式

| 需求 | 推荐命令 |
|---|---|
| 在某段后插入 Callout / 图片 / 表格 | `block_insert_after` |
| 替换单个段落/列表项的内容 | `block_replace` |
| 删除单个段落/列表项 | `block_delete` |
| 把整段 ol 替换成分组 callout | 多次 `block_delete` 删除所有 li + 1 次 `block_insert_after` 插入新 callout |
| 修改章节标题文字 | `block_replace`（前提是 anchor 拿到 h2 块本身） |

**经验法则**：能用 `block_insert_after` / `block_delete` 解决的，就别用 `str_replace`。`str_replace` 的 pattern 必须精确匹配原文，遇到 `<p>500 亿<del>600 亿美元` 这种字符会被 XML parser 当成非法而失败（实测多次出现 `degrade_code=3001, XML tokenization error`）。

### Step 4: 验证

```bash
# 验证 H2 列表（最快的 sanity check）
lark-cli docs +fetch --api-version v2 --doc <doc_id> \
  --scope outline --format pretty | grep "<h2"

# 验证完整内容（看 callout 数 / img 数 / table 数）
lark-cli docs +fetch --api-version v2 --doc <doc_id> \
  --scope full --format pretty > /tmp/doc.xml
grep -c '<callout' /tmp/doc.xml
grep -c '<img' /tmp/doc.xml
```

## 在文档中插入图片（Mermaid / 架构图）

飞书文档**不支持 Mermaid 原生渲染**（实测 `<whiteboard type="mermaid">` 会返回 warning 2107、显示空白）。**必须先把 Mermaid 转成 PNG/SVG**，再插入。

### 路径 A：mermaid.ink 在线 API（推荐，最快）

```python
import urllib.request, base64, json, zlib

def render_mermaid_png(code: str, outpath: str):
    """用 mermaid.ink JSON 端点渲染（pako 路径已被 Cloudflare 屏蔽）。"""
    payload = json.dumps({"code": code, "mermaid": {"theme": "default"}}).encode()
    b64 = base64.urlsafe_b64encode(payload).decode()
    url = f"https://mermaid.ink/img/{b64}?bgColor=white"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read()
    with open(outpath, "wb") as f:
        f.write(content)
    return len(content)
```

**URL 模式对比**（全部失败模式都列在下面，避免重蹈覆辙）：

| 路径 | 状态 |
|---|---|
| `https://mermaid.ink/img/{base64-json}`（JSON 包装） | ✅ 200，返回 PNG |
| `https://mermaid.ink/svg/{base64-json}` | ✅ 同上，返回 SVG |
| `https://mermaid.ink/img/pako:{base64-zlib}` | ❌ 403 error code 1010（Cloudflare 屏蔽） |
| `https://mermaid.ink/img/base64:{plain-base64}` | ❌ 404 |
| `https://mermaid.ink/img/{base64-json}?type=png&bgColor=white` | ✅ bgColor 参数可用 |

### 路径 B：本地 mermaid-cli（不推荐，依赖陷阱多）

```bash
# 标准安装 —— puppeteer 会自动下载 Chrome for Testing
npm install -g @mermaid-js/mermaid-cli
# 实测问题：macOS 本机的 puppeteer 下载 Chrome for Testing 经常失败
# 错误：DefaultProvider: The browser folder exists but the executable is missing
# 解法：完全跳过 puppeteer，用上面路径 A 的在线 API
```

**如果你坚持本地渲染**：用 `puppeteer-core` 显式指定系统 Chrome：

```bash
PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true npm install @mermaid-js/mermaid-cli puppeteer-core
mmdc -i input.mmd -o output.png -p /tmp/puppeteer-config.json
# puppeteer-config.json：
# { "executablePath": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" }
```

但 lark-cli 的 `docs +media-insert` 已经包揽了"上传+插入"两步，**没有本地 mmdc 也有完整路径**——用 mermaid.ink 在线渲染后直接 upload。

### 插入图片到飞书文档

```bash
# ⚠️ 关键陷阱：--file 必须是 CWD 相对路径
cd /Users/xiesg/workspace/mermaid
lark-cli docs +media-insert \
  --doc <doc_id> \
  --file ./my-diagram.png \
  --caption "图 1：xxx" \
  --align center \
  --selection-with-ellipsis "用文本锚点定位插入位置"
```

`--selection-with-ellipsis` 接受"目标 block 的开头一段文本"作为锚点，飞书自动定位到该 block 之后插入。**实测可用模式**：
- `"NVIDIA 在台北同步发布了"`（15+ 字符，唯一匹配）
- `"RTX Spark 是 NVIDIA 把"`（20 字符）

**失败模式**：少于 10 字符、文本在文档中出现多次（需要用 `start...end` 范围定位）、单/双引号不闭合。

## Callout 模板速查

```xml
<!-- 元信息条（顶部） -->
<callout emoji="📌" background-color="light-blue" border-color="blue">
  <p><b>标题</b></p>
  <p>正文...</p>
</callout>

<!-- 关键定义 -->
<callout emoji="💡" background-color="light-yellow" border-color="yellow">
  <p><b>关键定义</b>：xxx</p>
</callout>

<!-- 核心判断（倾向+替代假设结构） -->
<callout emoji="🟢" background-color="light-green" border-color="green">
  <p><b>倾向</b>：xxx</p>
  <p><b>替代假设</b>：xxx</p>
</callout>

<!-- 分组卡片（参考资料分组） -->
<callout emoji="🏛️" background-color="light-blue" border-color="blue">
  <p><b>分组标题</b></p>
  <ol>
    <li><a href="https://...">条目1</a></li>
    <li><a href="https://...">条目2</a></li>
  </ol>
</callout>
```

**飞书支持的命名色**：`gray/red/orange/yellow/green/blue/purple` 及对应 `light-` 前缀。**不要用 `#RRGGBB` 或自定义名**——会被吞掉。

## 整章替换工作流（参考资料卡片化）

把已有的扁平列表 `<ol>...</ol>` 替换成分组 Callout 卡片：

```python
import subprocess

DOC = "document_id"
H2_ANCHOR = "h2_block_id"   # 章节标题的 block_id
LI_IDS = ["li_1_id", "li_2_id", ...]  # 通过 section fetch 拿到

# 1) 逐个删除 li（每次 delete 之间 sleep 0.3s 防限流）
for bid in LI_IDS:
    subprocess.run(["lark-cli", "docs", "+update", "--api-version", "v2",
                    "--doc", DOC, "--command", "block_delete",
                    "--block-id", bid])

# 2) 在 H2 标题后插入分组 callout
subprocess.run(["lark-cli", "docs", "+update", "--api-version", "v2",
                "--doc", DOC, "--command", "block_insert_after",
                "--block-id", H2_ANCHOR,
                "--content", GROUPED_CALLOUT_XML,
                "--doc-format", "xml"])
```

**不要用 `str_replace` 一次替换整个 `<ol>`**——XML parser 会因原文里包含 `<del>` 等内嵌标签而报 `degrade_code=3001`（实测 14 条 li 的 ol 必失败）。

## 踩坑清单（增量编辑专属）

1. **`--file` 必须是 CWD 相对路径**：`docs +media-insert --file ./x.png` 不能用绝对路径 `/Users/.../x.png`，会报 `unsafe file path`。**必须先 `cd` 到图片所在目录**。这一点主 SKILL.md 陷阱 10 已经写过——`+media-insert` 同样适用。

2. **`--scope full --format pretty` 不带 block_id**：要拿 li/p/callout 等内层 block 的 id，**必须**用 `--scope section --start-block-id <h2_id>`。`outline` 模式只给标题 id。

3. **`str_replace` 容易因内嵌标签失败**：原文档里有 `<del>` / `<a>` / `<b>` 等嵌套时，pattern 必须完全精确匹配（包括所有内嵌标签），否则飞书 XML parser 会报 `degrade_code=3001, XML tokenization error`。**用 block_delete + block_insert_after 更稳**。

4. **`block_delete` 会删子树**：删除 ol 的一个 li 时，**该 li 整体被移除**（含其内部所有 p/span/a）。删除 H2 不会自动删除其下属所有 H3/p。

5. **media-insert 与 update 的 revision_id 行为不同**：`+media-insert` 内部自己管理 revision（4 步编排：upload→locate→insert→bind），不需要 `--revision-id`。`+update` 用 `--revision-id -1`（默认最新）。

6. **批量插入要加 sleep**：连续 5+ 次 `block_insert_after` 容易触发飞书限流。在 Python 里 `time.sleep(0.3)` 一下，实测 14 个 callout + 14 次 delete 共 28 次操作无失败。

7. **Mermaid 字符要 `<br/>` 不要 `\n`**：Mermaid 节点文本里的换行必须用 `<br/>`（HTML 标签），不能直接 `\n`。否则 mermaid.ink 渲染时会忽略换行导致文本连成一行。

8. **subgraph 内嵌重排**：Mermaid 的 `flowchart TB`（top-bottom）和 `flowchart LR`（left-right）会自动决定 subgraph 嵌套方向。如果布局反了（想要竖排结果成横排），换 `direction` 关键字或调整外层 `flowchart` 的方向。

9. **Mermaid 类定义 `classDef` 必须出现在所有节点之后**：把 `classDef` 写在 subgraph 节点前面会报 "UnknownDiagramError"。先定义节点、再应用 class。

10. **孤立箭头与方框高度不一（Mermaid 自动布局陷阱，2026-06-20 实测）**：v1 子图用 TB（top-bottom）+ 内嵌 subgraph 时，Mermaid 会自动重排 layout，可能出现：
    - 子图内的块"独立成一行"产生孤立箭头（如 `A --- B` 中间出现垂直孤立箭头）
    - 同一行 block 高度不统一（Foxconn 块比 GPU 块矮，导致底部不齐）
    - **解法**：简化 subgraph 嵌套（去掉内嵌子图，让所有同级节点平铺），或显式指定 `direction`（TB/LR）让 Mermaid 自己选择。
    - **验证步骤**：生成 PNG 后用 vision_analyze 检查"是否有孤立箭头 + 高度是否一致"，发现再调 v2。

11. **`+media-insert` `--selection-with-ellipsis` 日志要看插入 index（2026-06-20 实测）**：插入日志会打印 `inserting after at index N`——如果 N 与你预期不一致（比如想插在某段后但插在了章节末尾），说明 ellipsis 锚点匹配到了多个 block。**重锚点或加 `start...end` 范围限定**（如 `"NVIDIA 在..."...同章末`）。

## 端到端最小工作流（发布后美化）

1. `docs +fetch --scope outline` 拿到 H2/H3 id 列表 → 2. `docs +fetch --scope section --start-block-id <h2_id>` 拿到具体段落 id → 3. 用 `block_insert_after` 批量加 Callout/图片 → 4. 用 `block_delete` 批量删 li → 5. `docs +fetch --scope full` 验证最终结构。

## IM 消息推送注意事项（2026-06-20 实测）

发飞书消息给用户通知文档交付时：

1. **`+messages-send --content` 必须是 JSON，不是内联文本**：
   - ❌ `--content "📄 GTC Taipei..."` → 报 `--content is not valid JSON`
   - ✅ `--content '{"text":"📄 GTC Taipei..."}'` → 成功
   - **多行消息**：用 `\n` 转义，单引号包外层避免 shell 解析

2. **DM chat_id 来源**：从 `send_message action=list` 拿 `feishu:oc_xxx (dm)` 格式，去掉 `feishu:` 前缀就是 chat_id。

3. **不要假设 bot 能解析 user open_id**：strict mode 下 `contact +search-user` 报错 "strict mode is bot"，`im chats.get` 在 bot 身份下返回受限。如果需要 user open_id（用于权限转移），直接问用户。