# My Hermes Skills

个人 Hermes Agent Skills 备份仓库，通过 cron 每日自动同步。

## 同步机制

- **源目录**: `~/.hermes/skills/`
- **同步脚本**: `devops/hermes-skills-git-sync/scripts/sync.sh`
- **执行方式**: cron 每日 23:00 自动运行
- **同步策略**: `rsync -aL --delete`（跟随软链接，复制真实内容）

## 手动同步

```bash
# 执行同步
bash ~/.hermes/skills/devops/hermes-skills-git-sync/scripts/sync.sh
```

## 目录结构

```
my-hermes-skills/
├── .archive/                    # 已归档的 skills
├── apple/                       # Apple/macOS 相关
├── autonomous-ai-agents/        # AI Agent 编排
├── creative/                    # 创意内容生成
├── data-science/                # 数据科学
├── devops/                      # DevOps 工具
├── lark-*/                      # 飞书系列 skills（23 个）
├── mlops/                       # MLOps 工具
├── productivity/                # 生产力工具
├── research/                    # 研究工具
├── software-development/        # 软件开发
├── tech-blog/                   # 技术博客
└── ...
```

## Skills 统计

- 164 个 skills 已启用
- 23 个飞书相关 skills
- 9 个 hub 安装的 skills

## License

MIT License
