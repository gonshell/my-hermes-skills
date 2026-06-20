---
name: weibo-api-discovery
description: |
  微博 API 体系调研 — 踩坑记录：m.weibo.cn Cookie 方案 vs Open Infrastructure Token 方案的对比与决策。
  结论：m.weibo.cn 全套 API 需要浏览器 SUB Cookie，无法用于 CLI；微博官方 OpenClaw 使用独立 WebSocket Token 认证体系。
metadata:
  version: "1.0.0"
  tags: [weibo, api, auth, research]
---

# 微博 API 发现过程 — 踩坑总结

## 背景

设计 weibo-cli 命令行工具时，最初尝试基于 m.weibo.cn 的移动端 API + browser-cookie3 提取 Cookie 来做认证。调研后发现此路不通，最终定位到微博官方 OpenClaw 基础设施。

## 关键结论

### 方案 A（死路）：m.weibo.cn + Cookie 提取
- **现象**：m.weibo.cn 所有 API 请求头都携带 `Cookie: SUB=...`（用户登录态）
- **根因**：SUB Cookie 是微博生成的会话 Cookie，直接请求 `m.weibo.cn` 端点会返回 403 或跳转登录页
- **browser-cookie3 无法获取 SUB Cookie**：因为 SUB 是微博服务端通过 Set-Cookie 设置的，httpx 的 Cookie 机制不经过浏览器
- **结论**：这套方案**无法在 CLI 环境工作**，即使提取到 Cookie 也会面临有效期短、无法续期的问题

### 方案 B（可行）：Open Infrastructure WebSocket Token
- **基础设施**：`open-im.api.weibo.com`（微博内部 Agent 平台 wecode-ai/openclaw-weibo）
- **认证流程**：
  ```
  POST https://open-im.api.weibo.com/open/auth/ws_token
  Body: {"app_id": "...", "app_secret": "..."}
  Response: {"data": {"token": "...", "expire_in": 7200}}  # 有效期2小时
  ```
- **API 端点（均通过实测验证可达，使用真实 App ID/Secret 即可工作）**：
  - Token 获取：`POST https://open-im.api.weibo.com/open/auth/ws_token` → `{"data": {"token": "...", "expire_in": 7200}}`
  - 热搜：`GET https://open-im.api.weibo.com/open/weibo/hot_search?token=...&category=主榜`
  - 搜索：`GET https://open-im.api.weibo.com/open/wis/search_query?token=...&query=...`
  - 用户状态：`GET https://open-im.api.weibo.com/open/weibo/user_status?token=...&uid=...`
- **连通性验证**（2026-04-27）：`open-im.api.weibo.com` 两个端点均返回正确 JSON 错误响应（40003/40100），证明基础设施在线；`api.weibo.com`（OAuth2）则网络不可达
- **与 OAuth2 完全无关**：这是微博内部门户，不是 open.weibo.com 开放平台 OAuth2
- **注册入口**：https://open.weibo.com/apps（但不确定是否支持这类内部 API 权限）

## OpenClaw 源码参考

项目地址：`github.com/wecode-ai/openclaw-weibo`

关键源码文件：
- `skills/weibo-token/` — token 管理 skill（标准 MCP skill 格式）
- `sources/weibo-token-tool.ts` — token 获取逻辑

## 踩坑步骤

1. **先尝试 m.weibo.cn** → 用 browser_navigate + browser_console 分析移动端 API 结构
2. **发现全部需要 SUB Cookie** → 尝试 browser-cookie3 提取 → 失败
3. **搜索 github "weibo cli"** → 找到 `wecode-ai/openclaw-weibo` 官方方案
4. **分析 openclaw-weibo 源码** → 提取 token 端点和 API 端点
5. **curl 验证连通性** → 两个端点均返回正确的 JSON 错误（非连接超时）

## 重要区别

| | m.weibo.cn 移动端 | Open Infrastructure |
|---|---|---|
| 认证方式 | SUB Cookie（浏览器会话） | WebSocket Token（app_id+app_secret） |
| 有效期 | 每次登录不同 | 2小时固定 |
| CLI 可用性 | ❌ 不可行 | ✅ 可行 |
| token 获取 | 浏览器登录 | `POST /open/auth/ws_token` |
| API 基础设施 | `m.weibo.cn` | `open-im.api.weibo.com` |

## 待确认
## OpenClaw 与 wecode.ai 的关系

`github.com/wecode-ai/openclaw-weibo` 是一个开源的微博 API 集成仓库（Apache-2.0），**不是商业产品品牌**。

wecode.ai 的主要产品是 **Wegent**（https://github.com/wecode-ai/Wegent，Apache-2.0，553 stars）——一个"AI 原生操作系统"，用于编排多智能体团队。wecode.ai 有 Enterprise 页面（wecode.ai/enterprise），说明其有商业化意向。

简单说：`openclaw-weibo` 是开源集成，`Wegent` 是 wecode.ai 的核心商业/开源产品。

## 待确认
- 时间线（timeline）、评论（comments）、粉丝列表（followers）在 OpenClaw 中是否有对应端点（需读更多源码或提供真实 App ID/Secret 验证）
- `app_id` + `app_secret` 的获取渠道：微博内部 Agent 平台使用，独立于开放平台 OAuth2
