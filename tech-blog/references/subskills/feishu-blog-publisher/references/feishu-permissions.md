# Feishu 文档权限管理与所有权转移

> 当用户说"把权限转给我"、"让团队可编辑"、"你是 owner 我也要 owner" 等场景，用本文档。配套主 SKILL 的"发布后"阶段。

## 三种身份的关键区分（最常踩坑）

飞书的 `permission.members` 类 API 三种身份行为差异巨大：

| 身份 | token 类型 | 能做什么 | 不能做什么 |
|---|---|---|---|
| **bot（tenant_access_token）** | `tenant_access_token` | 创建文档、上传文件、读自己建的 doc、调用 `transfer_owner`（受限）| 不能搜用户（strict mode）、不能 `auth login` 后用 user 身份 |
| **已登录 user（user_access_token）** | `user_access_token` | 搜用户、调用 `transfer_owner` 给其他人、以个人身份操作 | 需要用户在终端跑 `lark-cli auth login` |
| **未登录 user** | 无 | — | — |

**默认状态**：bot 创建的 docx，bot 是 owner。**任何打开链接的登录用户默认有查看权限**（不需要额外授权）。

## "把权限转给我"的完整工作流

用户说"把文档所有权转给我、你保留权限"时，标准的执行路径：

### 步骤 1：拿到用户的 member_id

transfer_owner 需要 `member_type` + `member_id`：

| member_type | member_id 格式 | 怎么拿到 |
|---|---|---|
| `openid` | `ou_xxx` | 用户在飞书"设置 → 关于飞书 → open_id"复制 |
| `email` | `邮箱地址` | 用户口头告诉你 |
| `userid` | `u_xxx` | 仅企业内通讯录场景可用 |

**bot 身份的限制**：
- `lark-cli contact +search-user` 在 strict mode 下被禁（报错 "strict mode is bot"）
- `lark-cli im chats.get` 在 bot 身份下返回受限，没有用户 open_id
- **直接问用户最稳**——发 IM 消息告诉他获取方式

### 步骤 2：dry-run 先验证参数格式

```bash
lark-cli drive permission.members transfer_owner \
  --params '{"token":"<doc_id>","type":"docx","old_owner_perm":"full_access","remove_old_owner":false,"stay_put":false,"need_notification":false}' \
  --data '{"member_type":"openid","member_id":"ou_INVALID_TEST"}' \
  --dry-run
```

dry-run 输出会展示实际请求 URL + body + params。**关键检查点**：
- `as: bot` —— bot 身份可以调用（schema 的 `accessTokens: ["tenant", "user"]` 接受 tenant）
- path 是 `/open-apis/drive/v1/permissions/{token}/members/transfer_owner`
- body 是 `{"member_id":"...","member_type":"..."}`

### 步骤 3：实跑（去掉 dry-run）

```bash
lark-cli drive permission.members transfer_owner \
  --params '{"token":"<doc_id>","type":"docx","old_owner_perm":"full_access","remove_old_owner":false,"stay_put":false,"need_notification":false}' \
  --data '{"member_type":"openid","member_id":"<用户提供的 ou_xxx>"}'
```

### 关键参数语义表

| 参数 | 取值 | 含义 | 用户原话对应 |
|---|---|---|---|
| `old_owner_perm` | `full_access` / `view` / `edit` | 给原 owner（bot）保留的权限级别 | "你保留权限" → `full_access` |
| `remove_old_owner` | `true` / `false` | 是否移除原 owner | 不动原 owner → `false` |
| `stay_put` | `true` / `false` | 文档是否留在原位置 | 默认 `false`，文档会移到新 owner 的空间 |
| `need_notification` | `true` / `false` | 是否通知新 owner | 默认 `true`，DM 通知；批量转移时设 `false` |

### 错误码速查

| 错误码 | 含义 | 处理 |
|---|---|---|
| `1063001 Invalid parameter` | member_id 格式错或不存在 | 重新获取 member_id |
| `403` | bot 没权限（应用未开通 drive:permission 权限） | 联系管理员开权限，或换 user 身份调用 |
| `230020 permission denied` | 当前 owner（bot）无权转给别人 | 检查 bot 是否真的 owner |

## "邀请协作者"而非"转移 owner"

如果用户的真实需求是"让团队成员能编辑"而非"我要当 owner"：

```bash
lark-cli drive permission.members create \
  --params '{"token":"<doc_id>","type":"docx"}' \
  --data '{"member_type":"email","member_id":"<user@company.com>","perm":"edit","need_notification":false}'
```

`perm` 可选：`view` / `edit` / `full_access`。

**判断标准**：
- "我自己要能编辑" → 用 `transfer_owner` 把所有权转给他
- "让团队/某同事能编辑但保持 owner" → 用 `create` 加 full_access 协作者
- "所有人都能看就行" → 默认就有查看权限，不用调

## 给 DM 用户发"转移完成"通知

转移成功后，通过 IM 通知用户（见 `incremental-doc-editing.md` 末尾的"IM 消息推送注意事项"）：

```bash
lark-cli im +messages-send --as bot \
  --chat-id <用户 DM 的 oc_xxx> \
  --content '{"text":"✅ 文档所有权已转移\n\n文档：https://...\n\n新 owner：你\n原 owner（bot）：保留 full_access 权限\n\n你可以直接在飞书打开 → 右上角\"...\" → 权限设置 查看。"}'
```

## 踩坑清单

1. **bot 身份 ≠ 没权限**：传统认知是"严格模式下 bot 啥都不能做"。实测 `transfer_owner` 和 `permission.members create` 都能在 bot 身份下成功调用（应用配置了 `drive:permission` 权限范围）。

2. **`auth login` 不是万能钥匙**：用户跑 `lark-cli auth login` 后，lark-cli 切换到 user 身份。但这只是"个人能编辑文档"，**不等于"获得文档所有权"**。如果用户原话是"我要当 owner"，必须走 transfer_owner。

3. **DM chat_id ≠ user open_id**：`send_message action=list` 给的 `feishu:oc_xxx` 是 chat_id（对话 ID），不是 user_id。两个 ID 在飞书是不同的概念（一个是会话、一个是用户）。

4. **必须 dry-run 验证再实跑**：transfer_owner 是 destructive 操作（一旦转移，原 owner 的 full_access 会变成 view）。先用 invalid member_id dry-run 看返回的 API path 是否正确。

5. **`transfer_owner` 的 stay_put 慎用**：默认 `false` 会把文档从 bot 空间移到新 owner 空间。如果用户在 bot 空间下挂载了 wiki 节点，转移后 wiki 链接可能失效。`true` 保持位置但限制文档只能在"个人文件夹"下。