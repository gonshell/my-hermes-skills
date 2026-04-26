# Weibo CLI — 设计文档

> 状态：设计阶段，CLI 尚未实现

## 项目概览

- **目标**：类似 `xurl` / `xitter` 的微博命令行工具
- **语言**：Go（推荐）或 Python
- **仓库**：（待创建）

---

## 命令结构

```
weibo post "内容"                    # 发微博
weibo post -i <media_id> "内容"       # 带图片发帖
weibo post reply <id> "内容"          # 回复

weibo read <微博ID>                   # 读单条微博
weibo timeline                        # 自己时间线
weibo user <uid_or_name>             # 用户信息

weibo search "关键词"                 # 搜索（热度排序）
weibo hot                            # 实时热搜（需登录态）

weibo comment <微博ID>                # 评论列表
weibo comment add <微博ID> "内容"       # 添加评论

weibo like <微博ID>                  # 点赞
weibo unlike <微博ID>                # 取消点赞

weibo repost <微博ID> "内容"          # 转发
```

---

## API 覆盖

| 功能 | Weibo API 端点 | 方法 |
|------|---------------|------|
| 发微博 | `/2/statuses/update.json` | POST |
| 带图发帖 | `/2/statuses/upload.json` | POST (multipart) |
| 读取微博 | `/2/statuses/show.json` | GET |
| 时间线 | `/2/statuses/home_timeline.json` | GET |
| 用户信息 | `/2/users/show.json` | GET |
| 搜索 | `/2/search/statuses.json` | GET |
| 热榜 | ⚠️ 需要登录态 | — |
| 评论列表 | `/2/comments/show.json` | GET |
| 发评论 | `/2/comments/create.json` | POST |
| 点赞 | `/2/favorites/create.json` | POST |
| 取消赞 | `/2/favorites/destroy.json` | POST |
| 转发 | `/2/statuses/repost.json` | POST |

---

## 认证

### OAuth2 流程

```
1. 用户在微博开放平台创建应用，获取 App Key + App Secret
2. 构造授权 URL，引导用户在浏览器授权
3. 授权后获取 code，换取 access_token
4. access_token 持久化到 ~/.config/weibo-cli/config.yaml
```

### 环境变量

```
WEIBO_APP_KEY       — App Key
WEIBO_APP_SECRET    — App Secret
WEIBO_ACCESS_TOKEN  — Access Token
```

---

## 热榜实现方案

### 方案对比

| 方案 | 稳定性 | 实现难度 | 说明 |
|------|--------|----------|------|
| A. Cookie 方式 | 低 | 中 | 从浏览器提取 SUB cookie，携带访问热榜接口，有时效性 |
| B. 第三方聚合 API | 中 | 低 | 调用非官方聚合接口，不稳定 |
| C. 自建代理服务 | 高 | 高 | 在国内服务器部署，持有登录态，最可靠 |

### 推荐路径

1. **先实现**：发帖、读取、评论、点赞、搜索（官方 API 完全支持）
2. **后期扩展**：热榜（根据用户需求选择方案）

---

## Go 项目结构（推荐）

```
weibo-cli/
├── cmd/
│   ├── root.go
│   ├── post.go
│   ├── read.go
│   ├── search.go
│   ├── hot.go
│   ├── comment.go
│   ├── like.go
│   ├── user.go
│   └── timeline.go
├── internal/
│   ├── api/
│   │   ├── client.go
│   │   ├── posts.go
│   │   ├── users.go
│   │   ├── search.go
│   │   └── hot.go
│   ├── auth/
│   │   └── oauth2.go
│   └── config/
│       └── config.go
├── main.go
├── go.mod
└── README.md
```

---

## 安装

```bash
go install github.com/user/weibo-cli@latest

# 或 Clone 后编译
git clone https://github.com/user/weibo-cli.git
cd weibo-cli && go build -o weibo .

# 授权
weibo auth --appkey=YOUR_APP_KEY --appsecret=YOUR_APP_SECRET
```

---

## 参考

- 微博开放平台: https://open.weibo.com/develop
- 微博 API 文档: https://open.weibo.com/wiki/%E5%BE%AE%E5%8D%9AAPI
