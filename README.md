# My Hermes Skills

个人 Hermes Agent Skills 管理仓库。

## 目录结构

```
my-hermes-skills/
├── scripts/
│   └── sync-skills.sh     # 同步脚本
├── SKILLS.md              # Skills 元数据清单
├── social-media/
│   └── weibo/             # 微博技能
│       └── SKILL.md
├── media/
│   └── bilibili-ai-trending/
│       └── SKILL.md
└── ...（其他自定义 skills）
```

## 同步说明

### 自动同步（推荐）

```bash
# 同步所有 skills
./scripts/sync-skills.sh

# 只同步指定 skills
./scripts/sync-skills.sh weibo bilibili-ai-trending

# 干跑模式（只显示，不复制）
DRY_RUN=1 ./scripts/sync-skills.sh
```

### 手动同步

```bash
# 从 ~/.hermes/skills 复制到本仓库
rsync -av --exclude='.DS_Store' ~/.hermes/skills/weibo/ ./social-media/weibo/
```

## 推荐的 .gitignore

```
.DS_Store
*.log
*.tmp
__pycache__/
```

## 添加新 Skill

1. 在对应分类目录下创建 skill 目录
2. 放入 `SKILL.md`
3. 运行 `./scripts/sync-skills.sh` 同步
4. 提交到 Git

## License

MIT License
