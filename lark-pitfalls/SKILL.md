---
name: lark-pitfalls
version: 1.0.0
description: Feishu/Lark CLI workarounds for common failure modes — multi-file Markdown import, document metadata queries, Hermes-specific init issues, and ownership transfer. Use when a standard lark-doc/lark-drive call fails or returns unexpected results.
category: lark
triggers:
  - 飞书 doc 合并
  - 飞书文档 owner
  - lark-cli 报错 not configured
  - bot identity does not support
  - 转移飞书文档所有权
  - 多 .md 合并飞书
---

# Lark / Feishu CLI Workarounds

Common Feishu CLI failure modes and their workarounds. Standard `lark-doc` / `lark-drive` skills cover the happy path; this skill covers the patterns that don't fit cleanly elsewhere.

For the official happy-path skills, use:
- `lark-doc` — create/edit documents (with all 8 update commands)
- `lark-drive` — file/folder management
- `lark-shared` — auth and scope management
- `lark-permission` / `lark-base` / `lark-sheets` etc. — domain-specific ops

This skill is the **layered cookbook** for when those don't work.

---

## §1. Multi-File Markdown Import (lark-doc-md-import)

When the user gives you multiple local `.md` files and wants them combined into a single Feishu doc, you must preprocess the files BEFORE `docs +create`. The default Markdown mode parses the file naively and breaks on common patterns.

### Preprocessing Required

| Problem | Why | Fix |
|---------|-----|-----|
| **YAML frontmatter** | `---` blocks get rendered as garbled text in Feishu Markdown | Strip all `---`-wrapped frontmatter: find position of 2nd `\n---\n`, delete everything from start through it |
| **Obsidian Callout** `> [!NOTE]` | Not supported by Feishu; renders as plain text | Regex convert to standard quote: `re.sub(r'^> \[!([^\]]+)\]\s*([^\n]*)\n', fix_callout, content, flags=re.MULTILINE)`; `[!NOTE]` → `[补充说明]`, `[!WARNING]` → `[⚠️ 警告]`, etc. |
| **Multi-file title conflict** | Feishu uses first H1 as title; no `<title>` support in Markdown mode | Join files with `\n\n---\n\n` separator; first H1 becomes title — don't repeat title in content |
| **ASCII box-drawing becomes garbled** | Non-code-block `┌─┐│└┘` chars get parsed as tables | Confirm all ASCII diagrams are inside code blocks; check for lines with 3+ box-drawing chars outside code fences |
| **Document shows "Untitled"** | Markdown import ignores `<title>` tag; uses first H1 | After import, fix with XML `str_replace`: `lark-cli docs +update --command str_replace --doc-format xml --pattern "Untitled" --content "真实标题"` |

### Standard Preprocess Script

```python
import re, os

def preprocess_md_for_lark(input_paths, output_path):
    callout_map = {
        'NOTE': '补充说明', 'WARNING': '⚠️ 警告', 'TIP': '💡 提示',
        'DANGER': '❗ 危险', 'INFO': 'ℹ️ 信息', 'SUCCESS': '✅ 成功',
    }
    def fix_callout(m):
        kind = m.group(1).upper()
        rest = m.group(2)
        label = callout_map.get(kind, kind)
        return f'> [{label}]{rest}'

    parts = []
    for path in input_paths:
        with open(path, 'r') as f:
            content = f.read()
        # Strip YAML frontmatter
        if content.startswith('---'):
            end = content.find('\n---\n', 4)
            if end != -1:
                content = content[end+5:]
        # Fix Obsidian callouts
        content = re.sub(
            r'^> \[!([^\]]+)\]\s*([^\n]*)\n',
            fix_callout, content, flags=re.MULTILINE
        )
        parts.append(content.strip())

    merged = '\n\n---\n\n'.join(parts)
    with open(output_path, 'w') as f:
        f.write(merged)
    return output_path

# Usage
preprocess_md_for_lark(['ch01.md', 'ch02.md', 'ch03.md'], '/tmp/merged.md')
```

### Pitfalls

- **YAML frontmatter must be stripped at file level** — `docs +create --content @file.md` won't preprocess it
- **Separator must be `\n\n---\n\n`** (three dashes between blank lines), not `---\n` (gets parsed as a horizontal rule)
- **Callout conversion is line-level** — regex needs `flags=re.MULTILINE`
- **"Untitled" fix must use XML str_replace** — Markdown str_replace fails because the doc is stored as XML internally
- **`lark-doc` SKILL.md has a stale reference** to a non-existent `style/lark-doc-create-workflow.md` — ignore it; workflow files live under `references/`

---

## §2. Document Metadata Queries (lark-doc-metadata)

For queries about WHO and WHEN (not the content itself).

### Command

```bash
lark-cli drive metas batch_query \
  --data '{"request_docs":[{"doc_token":"<token>","doc_type":"docx"}]}' \
  --format json
```

### Required Fields

- `doc_token` — the document token (from `/docx/<token>` URL path)
- `doc_type` — `docx`, `sheet`, `bitable`, etc.

### Return Fields

| Field | Meaning |
|-------|---------|
| `owner_id` | Document owner open_id |
| `latest_modify_user` | Last modifier's open_id |
| `create_time` | Unix timestamp (seconds) |
| `latest_modify_time` | Unix timestamp (seconds) |
| `title` | Document title |
| `doc_token` | Document token |

### Auth Requirements

- **Bot identity works** for reading metadata
- Resolving `open_id` to user info (name, email) requires `--as user` + contact permissions
- Cron job targets are typically owned by the user who ran `auth login`

### Use Cases

1. Investigate "who is operating this document" — compare `owner_id` / `latest_modify_user` with expected cron job account
2. Verify cron job target — match token against expected
3. Verify update status — check `latest_modify_time` is in expected range

### Note

- Only metadata, not content. For content, use `lark-cli docs +fetch`
- `docs +fetch` (v1 API) response does NOT include owner / create_time
- `revision_id` in cron job reports is from system record, not queryable from the doc itself

---

## §3. Hermes-Specific CLI Init (lark-cli-hermes-setup)

Hermes Agent binds lark-cli to the `hermes` workspace, which defaults to `identity: bot-only`. This breaks user-identity operations.

### Symptoms

- `docs +search`, `docs +fetch --as user` fail
- `lark-cli auth login --as user` errors
- No interactive auth flow available in bot-only

### Correct Init Steps

#### Step 1: Bind workspace

```bash
lark-cli config bind --source hermes
```

Output contains `"identity":"bot-only"` — this is normal, doesn't break bot operations.

#### Step 2: Confirm needed identity

| Operation | Identity needed | Notes |
|-----------|----------------|-------|
| `docs +create` | bot | OK |
| `docs +update --command append` | bot | OK |
| `docs +fetch` | bot or user | bot can read public docs |
| `docs +search` | **user** | Must be user |
| `docs +update --as user` (precise edit) | user | Requires user auth |
| `drive +search` | **user** | Must be user |

#### Step 3: If user identity needed

**Method A (recommended):** Add scope to the bot in Feishu developer console
- For document operations: `docx:document:readonly` or `docx:document:rw`
- Go to https://open.feishu.cn/app → find app `cli_a95529a37f78dbb4`
- Add the scope — bot can then use the API directly (no user login needed)

**Method B:** Remove bot-only restriction

```bash
lark-cli config strict-mode --help
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `not configured` | Workspace not bound | `lark-cli config bind --source hermes` |
| `bot identity does not support` | Op needs user identity | Add bot scope or remove bot-only |
| `auth login --as user 报错` | bot-only blocks interactive | Add bot scope in developer console |
| `workspace not bound` | Workspace not bound | `lark-cli config bind --source hermes` |

---

## §4. Document Ownership Transfer (lark-transfer-owner)

Transfer doc ownership while keeping the old owner's access.

### Trigger

User says "把文档所有权转给我" / "把权限转给我" with a Feishu doc link.

### Command Format

**Token MUST be inside `--params` JSON, NOT a positional argument:**

```bash
lark-cli drive permission.members transfer_owner \
  --params '{"token":"<file_token>","type":"docx","remove_old_owner":false,"old_owner_perm":"full_access","need_notification":false}' \
  --data '{"member_type":"openid","member_id":"<target_openid>"}'
```

### Parameter Parsing

| Param | Source | Notes |
|-------|--------|-------|
| `file_token` | Doc URL | Extract from `docx/` / `sheets/` / `wiki/` / `bitable/` path |
| `type` | Doc URL path | docx → docx, sheets → sheet, wiki → wiki, bitable → bitable |
| `target_openid` | **Finding it — see below** | User openid, e.g. `ou_a0b6be7e404317f09b2ec6df33bde74b` |
| `remove_old_owner` | Default false | Whether to strip old owner's permission |
| `old_owner_perm` | Default `full_access` | Fallback permission if old owner is removed |
| `need_notification` | Default false | Whether to notify new owner |

### Finding the User's Feishu open_id

The transfer command needs the target user's `ou_` open_id. In Hermes's bot-only mode (`strictMode: bot`), you **cannot** use `lark-cli contact +search-user` (returns `strict_mode` error). Use these fallbacks in order:

1. **Session DB (fastest)** — the feishu session records store the user's open_id in the `source` column:
   ```bash
   sqlite3 $HERMES_HOME/state.db \
     "SELECT source FROM sessions WHERE source LIKE '%feishu%' LIMIT 5;"
   ```
   Output format: `<session_id>|feishu|<open_id>|...` — extract the 3rd pipe-delimited field.

2. **fact_store** — search for previously saved open_id: `fact_store(action='search', query='open_id feishu')`

3. **Ask the user** — fallback if neither (1) nor (2) yields a result. Ask for their `ou_` open_id or feishu email.

**Do NOT try** these approaches (all fail in bot-only mode):
- `lark-cli contact +search-user --query "name"` → `strict_mode` error
- `lark-cli contact +get-user` (no user_id) → `bot identity cannot get current user info`
- Searching `auth.json` / `gateway_state.json` / `channel_directory.json` → these don't store user open_ids

### ⚠️ CRITICAL: memory 中的 open_id 可能冲突 — 必须对账

memory 中可能存了**多个** open_id（不同来源记录了不同 id，比如 USER.md 主条目 vs 某 task 备注）。如果直接拿 memory 的某个 open_id 去 transfer_owner：

- 调用返回 `code: 0`（成功）
- 但飞书元数据 `owner_id` 可能是**另一个** open_id（飞书内部规范化或归一化到与请求 open_id 关联的另一个账号）
- 文档实际归属的人**不是用户本人**——不可逆操作

**强制流程**（用户要求"转所有权"时）：

1. 列出 memory 中所有 `ou_` 开头的 open_id，让用户明确确认是哪一个
2. 调 transfer_owner
3. **必须用 `metas.batch_query`（§2）拉取 `owner_id` 验证**：
   ```bash
   lark-cli drive metas batch_query \
     --data '{"request_docs":[{"doc_token":"<file_token>","doc_type":"docx"}]}'
   ```
   返回 JSON 的 `metas[0].owner_id` 必须等于用户确认的 open_id
4. **如果 `owner_id` ≠ 用户确认的 open_id**：立即告知用户冲突，请用户确认实际归属。不要自行再调 transfer_owner（飞书可能会再次归一化到同一账号，无法靠重试解决）
5. 把验证后的 open_id 更新到 memory（覆盖冲突条目）

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `missing required path parameter: token` | Token as positional | Must be inside `--params` JSON |
| `unknown flag: --file-token` | Using non-existent flag | No `--file-token` flag in the right command |
| `Permission denied` | bot is not doc owner | Current owner must first transfer to bot |
| `code: 0` 但 `owner_id` 不对 | 飞书内部规范化或 memory 冲突 | 用 `metas.batch_query` 验证后请用户确认 |

### Verification

#### 必做：验证实际 owner（用 `metas.batch_query`）

```bash
lark-cli drive metas batch_query \
  --data '{"request_docs":[{"doc_token":"<file_token>","doc_type":"docx"}]}'
```

返回 JSON 的 `metas[0].owner_id` 才是真实 owner。**不要用 `transfer_owner` 的 `code: 0` 当成功标志**——那是过程成功，不是结果正确。

#### 可选：验证 bot 还能不能访问

```bash
lark-cli drive permission.members auth \
  --params '{"token":"<file_token>","type":"docx","action":"view","member_type":"openid","member_id":"<bot_openid>"}'
```

(Note: it's `auth`, not `list` — `list` doesn't exist for this subcommand. Also: `--params` 里传 `member_type` + `member_id`，**没有 `--data` 标志**——这是 v1 子命令和原生 API 的差异之一。)

---

## §5. `--content @<filepath>` 必须是 CWD 相对路径

适用于 `docs +create` / `docs +update` 的 `--content @<path>` 语法。

### 失败信息

```
--content: invalid file path "/tmp/xxx.xml": --file must be a relative path
within the current directory, got "/tmp/xxx.xml" (hint: cd to the target
directory first, or use a relative path like ./filename)
```

### 根因

lark-cli 把 `@<filepath>` 当作**当前进程工作目录**的相对路径解析，**不支持绝对路径**。临时写到 `/tmp` 或任意其他位置都会失败。

### 正确做法

```bash
# 1. cp 到 CWD（通常是工作区）
cp /tmp/big_doc.xml ./big_doc.xml

# 2. 用 @./ 引用
lark-cli docs +update --doc "$DOC_TOKEN" --command append --content @./big_doc.xml
```

### 适用场景

- 写较大内容（>10KB XML/Markdown）时，先写到文件再 `@` 引用
- 配合 `execute_code` 生成 XML 后落到 CWD，再传给 `docs +update`
- 不要试图 `cd /tmp` 然后用相对路径（其他命令的工作目录依赖会受影响）

---

## §6. `drive permission.members auth` 的正确传参

`auth` 子命令用 `--params` 一个 flag 传**全部 query 参数**（含 `member_type`、`member_id`），**没有 `--data` 标志**。`permission.members` 下的其他子命令（`create`、`transfer_owner`）才需要 `--data`。

```bash
# ✅ 正确
lark-cli drive permission.members auth \
  --params '{"token":"<doc_token>","type":"docx","action":"view","member_type":"openid","member_id":"<openid>"}'

# ❌ 错误：会报 "unknown flag: --data"
lark-cli drive permission.members auth \
  --params '{"token":"...","type":"docx","action":"view"}' \
  --data '{"member_type":"openid","member_id":"..."}'
```

`auth` 用于验证某用户对某文档是否有指定动作的权限（返回 `auth_result: true|false`），常用来：
- transfer 后验证新 owner 实际权限
- 排查 "Permission denied" 错误

## §7. `docs +media-insert --file` 必须用相对路径

与 §5 同根：`--file` 解析为**当前进程工作目录的相对路径**，不支持绝对路径。

### 失败信息

```
unsafe file path: --file must be a relative path within the current directory,
got "/tmp/cchistory_images/cchistory.png"
```

### 正确做法

```bash
# ✅ 先 cd 到图片目录，再用相对路径
cd /tmp/cchistory_images
lark-cli docs +media-insert --doc doxcnXXX --file "./cchistory.png"

# 或用子 shell 避免污染工作目录
(cd /tmp/cchistory_images && lark-cli docs +media-insert --doc doxcnXXX --file "./cchistory.png")
```

### 与 `--content @<filepath>` 的区别

| 场景 | 标志 | 路径要求 |
|------|------|---------|
| 在文档中插入图片/文件 | `--file` | 必须是 CWD 相对路径 |
| 引用本地 XML/Markdown 文件内容 | `--content @<filepath>` | 必须是 CWD 相对路径 |

两者根因相同（lark-cli 对 `@<filepath>` 和 `--file` 都用 CWD 相对路径解析），但错误信息不同，遇到任一都要想到是路径问题。

## §8. `im +messages-send --image` 必须是 CWD 相对路径

与 §5 (`--content @`) 和 §7 (`docs +media-insert --file`) 同根:`--image` 解析为**当前进程工作目录的相对路径**,不支持绝对路径。

### 失败信息

```
--image: --file must be a relative path within the current directory,
got "/Users/.../foo.png" (hint: cd to the target directory first,
or use a relative path like ./filename)
```

### 正确做法

```bash
# ✅ 先 cd 到图片目录,再用相对路径
cd /path/to/image_dir
lark-cli im +messages-send --user-id ou_xxx --image ./foo.png

# ✅ 或用子 shell
(cd /path/to/image_dir && lark-cli im +messages-send --user-id ou_xxx --image ./foo.png)
```

### 适用场景

- 用 bot/user 身份给用户私发或群发图片(报告截图、模型图、HTML 渲染结果)
- 配合 `html-to-image-render` 流程:渲染 → 推到飞书

### 与其他相对路径 flag 的统一表

| 命令 | 标志 | 路径要求 |
|------|------|---------|
| `docs +create` / `+update` | `--content @` | CWD 相对 |
| `docs +media-insert` | `--file` | CWD 相对 |
| `im +messages-send` | `--image` | CWD 相对 |
| `im +messages-send` | `--file` | CWD 相对 |
| `im +messages-send` | `--video` | CWD 相对 |

根因相同,任何 `--file` / `--image` / `--content @` 报错"must be a relative path"时,都是同一个修复:cd 后用 `./`。

## §9. `im +messages-send` 图片上传偶发超时 → 重试 1 次通常就过

### 现象

`--image` 路径完全正确,但首次调用:

```
uploading image: foo.png
Error: image upload failed: Post "https://open.feishu.cn/open-apis/im/v1/images":
read tcp 192.168.x.x:xxxxx->220.181.164.102:443: read: operation timed out
```

### 根因

飞书图床 (`/open-apis/im/v1/images`) 的上传 endpoint 偶发 30s+ 不返回,通常是公网出口到阿里机房的 TCP 链路抖动,不是 lark-cli 的 bug 也不是配额问题。

### 正确做法

**重试 1 次,不要换 base64/不要换命令**。原因:
- 上传成功后会得到 `image_key`,后续 send 调用走另一条短路径,不会再卡
- 第二次走同一命令即可
- 如果重试 2 次仍失败,才是真问题(账号配额、bot 权限、图床服务故障),这时再去查

```bash
# 第一次失败 → 直接重试
lark-cli im +messages-send --user-id ou_xxx --image ./foo.png
# 第二次通常成功,返回 message_id + chat_id
```

### 不要做

- ❌ 不要把图片 base64 编码内联(飞书 IM 没有 image-base64 这种 msg_type,只会报错)
- ❌ 不要把图缩到很小再传(超时跟大小无关,1KB 图也会卡)
- ❌ 不要换身份(`--as user`)——图床 endpoint 是 bot 服务,user/bot 走的不是同一条

### 适用场景

- `im +messages-send --image` 偶发超时
- 配套 `html-to-image-render` 输出的大图(单文件 500KB-2MB 都在偶发区间内)

## §10. `docs +update --mode append` 静默失败(返回 ok 但内容未写入)

### 现象

```bash
lark-cli docs +update --doc DqQ6xxx --mode append --markdown "@./content.md"
```

返回:
```json
{"ok": true, "data": {"message": "文档更新成功（append模式）", "mode": "append", "success": true}}
```

但 `docs +fetch` 后发现**内容长度没有增加**,新增内容不存在于文档中。

### 根因

v1 API 的 append 操作在特定条件下**静默吞掉内容**:
- 文档刚被 overwrite 后立即 append(锁未释放)
- 并发 append(同一文档多个 append 队列竞争)
- v1 API deprecated 但仍在用(v2 行为可能不同)

**无法从返回值判断是否真的写入** — `ok: true` 只表示 HTTP 请求成功,不代表内容持久化。

### 正确做法:写后必读验证

每次 append/overwrite 后,**必须 re-fetch 验证**:

```bash
# 1. 记录写入前长度
BEFORE=$(lark-cli docs +fetch --doc "$DOC_ID" 2>/dev/null | python3 -c "import json,sys; print(len(json.loads(sys.stdin.read())['data']['markdown']))")

# 2. 执行 append
lark-cli docs +update --doc "$DOC_ID" --mode append --markdown "@./content.md"

# 3. re-fetch 验证长度增加
AFTER=$(lark-cli docs +fetch --doc "$DOC_ID" 2>/dev/null | python3 -c "import json,sys; print(len(json.loads(sys.stdin.read())['data']['markdown']))")

# 4. 如果长度没增加,重试
if [ "$AFTER" -le "$BEFORE" ]; then
    echo "⚠️ 长度未增加(${BEFORE}→${AFTER}),重试..."
    lark-cli docs +update --doc "$DOC_ID" --mode append --markdown "@./content.md"
fi
```

### 自动化封装(推荐)

在任何脚本里调用飞书写入时,封装为带验证的函数:

```python
def append_feishu_with_verify(doc_id: str, md_path: str) -> bool:
    len_before = fetch_doc_length(doc_id)
    result = run_lark_cli(["docs", "+update", "--doc", doc_id, "--mode", "append", "--markdown", f"@{md_path}"])
    if not result.get("ok"):
        return False
    len_after = fetch_doc_length(doc_id)
    if len_after <= len_before:
        # 重试一次
        run_lark_cli(["docs", "+update", "--doc", doc_id, "--mode", "append", "--markdown", f"@{md_path}"])
        len_after2 = fetch_doc_length(doc_id)
        return len_after2 > len_before
    return True
```

### 不要做

- ❌ 不要用 `success: true` 当作"内容已持久化"的标志
- ❌ 不要假设"返回 ok"就跳过 re-fetch
- ❌ 不要连续快速 append 多次(间隔 ≥ 2 秒)

### 适用场景

- 任何 `docs +update --mode append` / `--mode overwrite` 调用
- cron job 自动追加周报/日报到飞书文档
- 批量追加多个章节到同一文档

## Related

- `lark-doc` — primary document API
- `lark-drive` — file/folder management
- `lark-shared` — auth and scope management
- `lark-permission` — permission operations
- `lark-im` — IM message sending (use `--image` with §8/§9 caveats)
- `html-to-image-render` — render HTML to PNG before pushing via §8/§9
