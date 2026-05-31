# Obsidian Vault 路径与同步配置参考

## Vault 路径约定

### 标准路径

macOS 默认：`~/Documents/Obsidian Vault`（即 `/Users/xiesg/Documents/Obsidian Vault`）

Linux/Ubuntu 默认：`~/Documents/Obsidian Vault`

Windows 默认：`%USERPROFILE%\Documents\Obsidian Vault`

### 环境变量

推荐在 `~/.hermes/.env` 中设置：
```bash
OBSIDIAN_VAULT_PATH=/Users/xiesg/Documents/Obsidian\ Vault
```

注意：路径含空格时，file tools 需要用**不带引号的绝对路径**：
```python
# ✅ 正确
path = "/Users/xiesg/Documents/Obsidian Vault/note.md"

# ❌ 错误（引号会进入路径字符串）
path = '"/Users/xiesg/Documents/Obsidian Vault/note.md"'
```

### iCloud 路径（macOS）

如果使用 iCloud 同步，Obsidian 官方推荐的 Vault 位置：
```bash
~/Library/Mobile Documents/iCloud~md~obsidian/
```

**⚠️ 注意事项**：
- 路径中包含 `~md~obsidian` 目录（中间有波浪号），不是普通文件夹
- `obsidian.md` 的 iCloud sync 插件会自动管理此路径
- 如果 Vault 放在 iCloud 路径下，Obsidian Git 插件仍然可以正常工作

---

## Obsidian Git 集成

### 安装与启用

1. 在 Obsidian 中安装 **Obsidian Git** 插件（社区插件）
2. 启用插件后，首次需要配置 GitHub Personal Access Token

### 初始化 Git 仓库（一键脚本）

```bash
#!/bin/bash
# obsidian-git-setup.sh
# 用法：chmod +x obsidian-git-setup.sh && ./obsidian-git-setup.sh

set -e

echo "=== Obsidian Git 自动配置脚本 ==="

# 1. 检查 Git
if ! command -v git &> /dev/null; then
    echo "❌ Git 未安装，正在安装..."
    brew install git  # macOS
    # sudo apt update && sudo apt install git -y  # Ubuntu
fi

# 2. 输入
read -p "GitHub 仓库 URL（格式：https://github.com/用户名/仓库名.git）：" REPO_URL
read -p "GitHub Personal Access Token：" TOKEN
read -p "GitHub 用户名：" GITHUB_USER

# 3. 配置 Git
git config --global user.name "$GITHUB_USER"

# 4. 初始化仓库（如果尚未初始化）
if [ ! -d .git ]; then
    git init
fi

# 5. 添加远程仓库
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"

# 6. 创建 .gitignore（Obsidian 专用）
cat > .gitignore << 'EOF'
.DS_Store
Thumbs.db
.obsidian/workspace
.obsidian/workspace.json
*.tmp
*.bak
EOF

# 7. 首次提交
git add .
git commit -m "Initial commit: Obsidian vault backup"
git branch -M main

echo "✅ 配置完成"
echo "请在 Obsidian → Settings → Obsidian Git 中配置 Token 和仓库 URL"
```

### Obsidian 专用 .gitignore 模板

```gitignore
# .gitignore for Obsidian Vault

# 操作系统文件
.DS_Store
Thumbs.db

# Obsidian 工作状态（每个设备不同）
.obsidian/workspace
.obsidian/workspace.json
.obsidian/apps
.obsidian/community-plugins.json
.obsidian/appearance.json

# 临时文件
*.tmp
*.bak

# 大附件（可选，按需忽略）
# assets/*.png
# assets/*.jpg
# assets/*.pdf
```

**⚠️ 不要忽略这些**（需要版本控制的插件配置）：
- `.obsidian/plugins/` 目录——其他设备需要知道安装了哪些插件
- `.obsidian/core-plugins.json`——核心插件启用状态

### Obsidian Git 插件配置建议

| 设置项 | 推荐值 | 说明 |
|--------|--------|------|
| Auto commit interval | 30 分钟 | 自动 commit 频率 |
| Auto pull after pull | ✅ | 拉取最新更改 |
| Auto push after commit | ✅ | 推送本地更改 |
| Pull updates on startup | ✅ | 启动时拉取 |
| Custom message template | `{{date}} {{message}}` | commit 信息格式 |

---

## Vault 性能优化

### 大型 Vault（>5000 笔记）优化

| 问题 | 解决方案 |
|------|----------|
| 图谱视图卡顿 | 关闭不常用的标签过滤，只显示核心链接 |
| 搜索变慢 | 用 `file_glob: "*.md"` 限制搜索范围 |
| 启动慢 | 禁用不需要的社区插件 |
| 同步慢 | 大附件（>5MB）移到 Vault 外，用相对路径引用 |

### Dataview 性能优化

```dataview
-- ✅ 推荐：精确路径过滤
TABLE file.ctime FROM "01-Permanent"

-- ❌ 避免：全局搜索
TABLE file.ctime FROM ""
```

---

## Obsidian 官方定价（2026-01）

| 产品 | 价格 | 说明 |
|------|------|------|
| Obsidian 核心 | 免费 | 永久免费，核心功能全部可用 |
| Obsidian Sync | $4/月（年付） | 端到端加密，4GB 存储 |
| Obsidian Publish | $8/月 | 发布公开笔记站 |
| Catalyst License | $25/50/200 | 资助开发者，获得早期测试版 |
| Commercial License | $50/人/年 | 公司商业使用 |

---

## 相关链接

- 官方帮助：obsidian.md/help
- 社区插件目录：community.obsidian.md/plugins
- Obsidian Git 插件源码：github.com/vinzent03/obsidian-git
- Quartz（Obsidian 转静态网站）：quartz.jzhao.xyz