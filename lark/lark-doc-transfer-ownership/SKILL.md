---
name: lark-doc-transfer-ownership
description: 将飞书云文档（docx / wiki 等）的所有权转移给指定用户。支持单文档和批量场景。固定目标 open_id，全程跳过失败项并最终汇总报告。
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli drive permission.members transfer_owner --help"
---

# lark-doc-transfer-ownership

将飞书云文档的所有权转移给指定用户（默认 `ou_a0b6be7e404317f09b2ec6df33bde74b`）。

支持单文档和批量。失败项跳过，最终汇总报告。

## ⚠️ 关键约束

- **不可逆操作**：所有权一旦转出，原所有者变为协作者。
- **高风险写**：`drive.permission.members.transfer_owner` 在 schema 中标记 `danger=true` + `risk=high-risk-write`。执行前必须 `lark-cli schema drive.permission.members.transfer_owner` 校验参数。
- **目标 open_id 硬编码**：`ou_a0b6be7e404317f09b2ec6df33bde74b`。不读 memory，不向用户追问。
- **失败行为**：单文档失败 → 跳过该项 → 继续下一项 → 最终汇总报告。**scope 不足是全局性失败，立即终止**。
- **默认参数**：`need_notification=false`（不打扰新所有者）、`remove_old_owner=false`（原 bot 保留 full_access 便于后续修改）、`stay_put=true`（文档位置不变）。

## 触发条件

- "把飞书文档 X 所有权转给我"
- "把这个文档 transfer 给我"
- "把 {url} 的所有权改成我的"
- 批量："把以下文档所有权都转给我：[url1, url2, url3]"

## 流程

### Step 1 · Schema 校验
```bash
lark-cli schema drive.permission.members.transfer_owner
```
确认 schema 中 `member_type` 支持 `openid`，且所需 scope `docs:permission.member:transfer` 已授权。

### Step 2 · 解析 URL 列表

- `/docx/{token}` → 直接用 token，type=docx
- `/wiki/{token}` → 先解析：
  ```bash
  lark-cli wiki spaces get_node --params '{"token":"<wiki_token>"}'
  ```
  从返回的 `node.obj_token` 取真实 token，`node.obj_type` 取 type（docx / sheet / bitable / file 等）。
- 不支持的 URL 格式 → 跳过该项，最终报告列出。

### Step 3 · 循环 transfer（每个文档一次）

```bash
lark-cli drive permission.members transfer_owner \
  --params '{"token":"<doc_token>","type":"<doc_type>",
             "need_notification":"false",
             "remove_old_owner":"false",
             "stay_put":"true"}' \
  --data '{"member_id":"ou_a0b6be7e404317f09b2ec6df33bde74b",
           "member_type":"openid"}'
```

**判断**：
- `code=0` → 进入 Step 4 验证
- `code≠0` → 记录 `{code, msg}` → 跳过该项 → 继续下一项

### Step 4 · 验证 owner_id（仅对成功的项）

```bash
lark-cli drive metas batch_query \
  --data '{"request_docs":[{"doc_token":"<doc_token>","doc_type":"<doc_type>"}]}' \
  --as user
```

**断言**：返回的 `metas[0].owner_id == "ou_a0b6be7e404317f09b2ec6df33bde74b"`

- 通过 → 标记 ✅ 成功
- 不匹配 → 标记 ⚠️ 异常（transfer 返回成功但 owner 未变更，需人工复查）

### Step 5 · 输出汇总报告

```markdown
## 所有权转移结果

✅ 成功（{N} 项）：
- 《{title}》({token}) → owner_id 验证通过

❌ 失败（{M} 项）：
- 《{title}》({token}) — {code}: {msg}

⚠️ 异常（{K} 项）：
- 《{title}》({token}) — transfer 返回成功但 owner_id 未变更，需人工复查

📊 总结：{N}/{total} 成功，{M} 失败，{K} 异常
```

## Verify 模式

默认 **关闭**。

触发词："先 verify 一下"、"先 dry-run"、"先看一下"。

启用后，Step 3 执行前先打印：

```markdown
## 转移计划（verify 模式，未执行）

将把以下 {N} 个文档所有权转移给 ou_a0b6be7e404317f09b2ec6df33bde74b：

1. 《{title}》({url}) → token={token}, type={type}
2. 《{title2}》({url2}) → token={token2}, type={type2}
...

参数：need_notification=false, remove_old_owner=false, stay_put=true

回复 "go" 确认执行，或 "cancel" 取消。
```

用户说 `go` 才执行 transfer。说 `cancel` 或其它 → 中止。

## 跨 skill 引用

- `lark-drive`：提供 `transfer_owner` / `metas batch_query` / `wiki spaces get_node` 命令
- `lark-shared`：认证和权限处理
- 不依赖 `lark-doc`（transfer 不涉及读写文档内容）

## 已知限制

- 不可逆。原所有者变成协作者（除非 `remove_old_owner=true`，本 skill 不用）。
- 文档必须在目标用户有访问权限的范围内（个人文件夹/共享空间）。跨租户失败。
- wiki 节点类型不在 transfer 支持范围时，会被 schema 拒绝。
