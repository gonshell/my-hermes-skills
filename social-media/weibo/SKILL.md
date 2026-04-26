# NOTE

> **2026-04-26:** Weibo CLI 尚未开发完成。此 Skill 为设计文档，待 CLI 实现后补充完整内容。
> CLI 设计方案见：[../../docs/weibo-cli-design.md](../../docs/weibo-cli-design.md)

---

```yaml
name: weibo
description: 微博发布、读取、热榜及用户互动 — 通过 weibo-cli 或直接 API 调用。发微博、读微博、评论、点赞、转发、搜索、热榜获取。
version: 0.1.0
author: Hermes Agent (custom)
license: MIT
platforms: [linux, macos]
prerequisites:
  commands: [curl, jq]
  env_vars: [WEIBO_APP_KEY, WEIBO_APP_SECRET, WEIBO_ACCESS_TOKEN]
metadata:
  hermes:
    tags: [weibo, social-media, 微博]
    homepage: https://github.com/你的用户名/my-hermes-skills
```

# Weibo — 微博社交操作

支持：
- 发微博 / 带图发微博 / 回复
- 读取微博（含转发数、评论数、点赞数）
- 评论：列表 / 发评论 / 删除评论
- 点赞 / 取消点赞
- 转发
- 搜索（支持热度排序）
- 获取用户信息
- ⚠️ 实时热榜（见下方限制说明）

---

## 重要限制：热榜

Weibo **官方热榜接口需要登录态**，普通 Access Token 无法访问。

当前可选方案：

| 方案 | 稳定性 | 难度 | 说明 |
|------|--------|------|------|
| Cookie 方式 | 低 | 中 | 从浏览器提取 SUB cookie，可访问热榜，但有时效性 |
| 第三方聚合 API | 中 | 低 | 非官方，有可用接口但不稳定 |
| 自建代理服务 | 高 | 高 | 在国内服务器部署，持有登录态，最可靠 |

**推荐**：如需稳定热榜，建议方案 C（自建代理）。如仅需公开微博数据（发帖/读取等），方案 A/B 均可用。

---

## 前置准备

### 1. 创建微博应用

1. 访问 https://open.weibo.com/develop
2. 创建应用，获取 **App Key** 和 **App Secret**
3. 设置授权回调地址：`http://localhost:8080/callback`

### 2. 获取 Access Token

用户需要手动完成 OAuth2 授权（无法通过 Agent 自动完成，因为需要用户在浏览器登录）：

1. 构造授权 URL 并让用户访问：

```
https://api.weibo.com/oauth2/authorize?client_id=YOUR_APP_KEY&redirect_uri=http://localhost:8080/callback&response_type=code
```

2. 用户授权后，浏览器会跳转到 `http://localhost:8080/callback?code=XXXXX`
3. 用授权码换取 Token：

```bash
curl -X POST "https://api.weibo.com/oauth2/access_token" \
  -d "client_id=YOUR_APP_KEY" \
  -d "client_secret=YOUR_APP_SECRET" \
  -d "grant_type=authorization_code" \
  -d "code=XXXXX" \
  -d "redirect_uri=http://localhost:8080/callback"
```

4. 返回的 `access_token` 即为所需 Token

### 3. 配置环境变量

```bash
export WEIBO_APP_KEY="your_app_key"
export WEIBO_APP_SECRET="your_app_secret"
export WEIBO_ACCESS_TOKEN="your_access_token"
```

建议写入 `~/.bashrc` 或 `~/.zshrc`。

---

## API 基础

**Base URL:** `https://api.weibo.com`

所有 API 需要携带 `access_token` 参数：
```
?access_token=YOUR_ACCESS_TOKEN
```

**常用请求方式：**
- GET：查询类操作（读取微博、用户信息、评论列表）
- POST：写入类操作（发微博、发评论、点赞、转发）

**返回格式：** JSON

---

## 命令速查

### 发微博

```bash
# 发文字微博
curl -s -X POST "https://api.weibo.com/2/statuses/update.json" \
  -d "access_token=$WEIBO_ACCESS_TOKEN" \
  --data-urlencode "status=Hello Weibo!"

# 发带图片微博（需先上传图片获取 media_id）
curl -s -X POST "https://api.weibo.com/2/statuses/upload.json" \
  -d "access_token=$WEIBO_ACCESS_TOKEN" \
  --data-urlencode "status=Hello with image!" \
  -F "pic=@/path/to/image.jpg"

# 回复微博
curl -s -X POST "https://api.weibo.com/2/comments/create.json" \
  -d "access_token=$WEIBO_ACCESS_TOKEN" \
  -d "id=微博ID" \
  --data-urlencode "comment=赞！"

# 转发微博
curl -s -X POST "https://api.weibo.com/2/statuses/repost.json" \
  -d "access_token=$WEIBO_ACCESS_TOKEN" \
  -d "id=微博ID" \
  --data-urlencode "status=转发内容"
```

### 读取微博

```bash
# 获取单条微博详情（含转发数/评论数/赞数）
curl -s "https://api.weibo.com/2/statuses/show.json?access_token=$WEIBO_ACCESS_TOKEN&id=微博ID"

# 获取用户发布的微博列表
curl -s "https://api.weibo.com/2/statuses/user_timeline.json?access_token=$WEIBO_ACCESS_TOKEN&uid=用户UID"

# 获取当前登录用户时间线
curl -s "https://api.weibo.com/2/statuses/home_timeline.json?access_token=$WEIBO_ACCESS_TOKEN"
```

### 搜索

```bash
# 搜索微博（按热度排序）
curl -s "https://api.weibo.com/2/search/statuses.json?access_token=$WEIBO_ACCESS_TOKEN&q=关键词&xsort=hot"

# 搜索用户
curl -s "https://api.weibo.com/2/search/users.json?access_token=$WEIBO_ACCESS_TOKEN&q=用户名"
```

### 用户信息

```bash
# 获取用户信息
curl -s "https://api.weibo.com/2/users/show.json?access_token=$WEIBO_ACCESS_TOKEN&uid=用户UID"

# 或通过 screen_name
curl -s "https://api.weibo.com/2/users/show.json?access_token=$WEIBO_ACCESS_TOKEN&screen_name=用户名"
```

### 评论

```bash
# 获取微博的评论列表
curl -s "https://api.weibo.com/2/comments/show.json?access_token=$WEIBO_ACCESS_TOKEN&id=微博ID"

# 发评论
curl -s -X POST "https://api.weibo.com/2/comments/create.json" \
  -d "access_token=$WEIBO_ACCESS_TOKEN" \
  -d "id=微博ID" \
  --data-urlencode "comment=写得很好！"

# 删除评论
curl -s -X POST "https://api.weibo.com/2/comments/destroy.json" \
  -d "access_token=$WEIBO_ACCESS_TOKEN" \
  -d "cid=评论ID"
```

### 点赞

```bash
# 点赞
curl -s -X POST "https://api.weibo.com/2/favorites/create.json" \
  -d "access_token=$WEIBO_ACCESS_TOKEN" \
  -d "id=微博ID"

# 取消点赞
curl -s -X POST "https://api.weibo.com/2/favorites/destroy.json" \
  -d "access_token=$WEIBO_ACCESS_TOKEN" \
  -d "id=微博ID"

# 获取当前用户的点赞列表
curl -s "https://api.weibo.com/2/favorites.json?access_token=$WEIBO_ACCESS_TOKEN"
```

### 热榜（⚠️ 需登录态）

```bash
# 方法 A：携带 Cookie 访问（Cookie 有时效性）
curl -s "https://weibo.com/ajax/statuses/hot_band" \
  -H "Cookie: SUB=your_weibo_cookie_here"

# 方法 B：通过第三方聚合接口（非官方，可能不稳定）
# 具体接口需自行调研可用服务
```

---

## 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| `WEIBO_APP_KEY` | 微博应用 App Key | 是 |
| `WEIBO_APP_SECRET` | 微博应用 App Secret | 是 |
| `WEIBO_ACCESS_TOKEN` | 用户 Access Token | 是 |

---

## 常见错误

| error_code | 说明 | 解决方案 |
|------------|------|----------|
| 10006 | 缺少 appkey 参数 | 请求中携带 `access_token` |
| 20003 | 用户不存在 | 检查 UID 或 screen_name |
| 20019 | 重复内容 | 修改微博内容后重试 |
| 21332 | Token 无效或过期 | 重新获取 Access Token |
| 10023 | 接口调用频率超限 | 降低请求频率，等待后重试 |

---

## 相关资源

- 微博开放平台文档: https://open.weibo.com/develop
- 微博 API 文档: https://open.weibo.com/wiki/%E5%BE%AE%E5%8D%9AAPI
- CLI 设计方案: [../../docs/weibo-cli-design.md](../../docs/weibo-cli-design.md)
