# 飞书 docx 读取：两条路径与常见陷阱

## TL;DR

| 路径 | 何时用 | 失败信号 |
|------|-------|---------|
| `feishu_doc_read` 工具 | **仅在飞书评论/回调上下文** | 普通对话 → `Feishu client not available (not in a Feishu comment context)` |
| `lark-cli docs +fetch --api-version v2` | **通用路径**，所有上下文 | `--api-version v1` 已弃用，v2 单次返回一屏 |

**默认使用 lark-cli v2**。`feishu_doc_read` 留作飞书评论回调链路里使用。

---

## 路径 1：feishu_doc_read 工具

```python
feishu_doc_read(doc_token="HhyMdusqdoVcW9xLyd2c2Yc2nnf")
```

**成功条件**：当前对话是飞书文档评论触发的上下文（bot 收到评论回调后调起 LLM）。

**失败信号**（在普通对话中）：

```
Feishu client not available (not in a Feishu comment context)
```

→ **不要重试**，立即切到 lark-cli 路径。

---

## 路径 2：lark-cli docs +fetch（通用路径）

### 基本命令

```bash
lark-cli docs +fetch --api-version v2 --doc "<token>" --format pretty
```

输出是可读 HTML：
```html
<title>文档标题</title>
<h1>...</h1>
<h2>...</h2>
<li><a href="...">条目</a></li>
```

### 关键陷阱

#### 陷阱 1：v1 API 已弃用

```bash
# ❌ 弃用
lark-cli docs +fetch --api-version v1 --doc <token>

# ✅ 当前推荐
lark-cli docs +fetch --api-version v2 --doc <token>
```

工具会主动提示：`[NOTE] v1 API is deprecated and will be removed in a future release.`

#### 陷阱 2：v2 API 单次返回一屏（约一档内容）

`--limit` 参数控制返回的 block 数，但**默认一屏只够覆盖 1 档 cron 推送的输出**（如一个完整的"晚间档"）。早间档和 B 站档如果也被写入了同一份文档，**默认只会看到最后写入的那一档**。

#### 陷阱 3：JSON 输出结构

```bash
lark-cli docs +fetch --api-version v2 --doc <token> --format json
```

返回结构：

```json
{
  "ok": true,
  "identity": "bot",
  "data": {
    "document": {
      "content": [...],     // block 数组
      "document_id": "...",
      "revision_id": 25
    },
    "log_id": "..."
  }
}
```

**注意**：`data.content` 在大文档里可能 5000+ blocks，json 输出需要后续用 jq / python 处理。

#### 陷阱 4：分页/多档覆盖

需要分页时用 `--offset` / `--limit`：

```bash
# 第一段
lark-cli docs +fetch --api-version v2 --doc <token> --limit 100

# 后续段（如果 v2 支持 offset）
lark-cli docs +fetch --api-version v2 --doc <token> --limit 100 --offset 100
```

但**注意**：分页读 block 是按文档物理顺序，不是按"档"分。如果档间没有显式分隔（h1/h2 标题），分页不会自动按"档"切分。

### 推荐工作流

```bash
# 1. 先看文档元信息
lark-cli docs +fetch --api-version v2 --doc <token> --format json | \
  python3 -c "
import json, sys
d = json.load(sys.stdin)['data']['document']
print('revision:', d['revision_id'])
print('blocks:', len(d['content']))
print('doc_id:', d['document_id'])
"

# 2. pretty 模式看一档内容
lark-cli docs +fetch --api-version v2 --doc <token> --format pretty
```

---

## 其他输出格式

| `--format` | 用途 |
|-----------|------|
| `pretty` (默认 pretty 表格样式？) | **首选**：人读 HTML 列表 |
| `json` | 程序化处理，配合 `--jq` |
| `ndjson` | 流式，每行一个 JSON 对象 |
| `csv` | 表格导出 |
| `table` | 终端表格 |

`--jq` 过滤示例（json 模式）：

```bash
lark-cli docs +fetch --api-version v2 --doc <token> --format json --jq '.data.document.content | length'
```

---

## 与 lark-doc skill 的关系

`lark-doc` skill 描述说"获取文档内容（支持 simple/with-ids/full 三种导出详细度，以及 full/outline/range/keyword/section 五种局部读取模式）"——**这是更高层的能力**，会自动用 `+fetch` 命令并应用过滤器。

**本任务（读 + 跨源分析）的具体场景**：直接用 `lark-cli docs +fetch --format pretty` 即可，不需要走 `lark-doc` skill 的 `simple/full/range` 模式。

---

## 故障排查

| 错误 | 原因 | 解法 |
|------|------|------|
| `Feishu client not available` | 用了 `feishu_doc_read` 但不在评论上下文 | 切到 `lark-cli` |
| `[NOTE] v1 API is deprecated` | 用了 v1 | 改 v2 |
| 文档只看到一档内容 | 多档 cron 覆盖 | 明说"只看到最后写入的一档" |
| 找不到 block 内容 | `--format` 不对 | pretty/table 是人读，json 给程序 |
| bot 没有权限 | 没认证或 scope 不够 | 走 `lark-shared` skill 配置 |
