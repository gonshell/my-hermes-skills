# Hermes Agent `$HOME` 环境陷阱

## 关键发现

当 Hermes Agent 通过 cron 或其他方式运行时，`$HOME` 变量被设定为 `/Users/xiesg/.hermes/home`，而不是预期的 `/Users/xiesg`。

这导致：
- `~/.hermes/skills` 实际指向 `/Users/xiesg/.hermes/home/.hermes/skills`（不存在）
- 真实的 skills 目录在 `/Users/xiesg/.hermes/skills`

## 验证方法

```bash
echo ~        # 打印 $HOME 的值
ls ~/.hermes  # 列出 hermes 配置目录内容
```

## 已知路径映射

| 用途 | 正确路径 | 错误路径（$HOME/.hermes/home/.hermes/...） |
|------|----------|-------------------------------------------|
| Skills 目录 | `/Users/xiesg/.hermes/skills` | `/Users/xiesg/.hermes/home/.hermes/skills` |
| GitHub 仓库 | `/Users/xiesg/github/my-hermes-skills` | 不受影响（绝对路径） |

## 正确的运行环境

在 cron 任务或需要引用 `~/.hermes/` 路径的脚本前，设置：

```bash
HOME=/Users/xiesg ./scripts/sync-skills.sh
```

## 同步 skills 至 GitHub 的 cron 任务问题

**cron job**: `每日同步 skills 到 GitHub`（`a272cd0e7ca4`），schedule `0 22 * * *`

### 已发现的问题

**问题 1: `$HOME` 陷阱导致 copy 不完整（根本原因）**
- cron 环境中 `$HOME = /Users/xiesg/.hermes/home`
- 同步脚本中 `cp -r ~/.hermes/skills/*` 复制了 `/Users/xiesg/.hermes/home/.hermes/skills/`（空目录）
- 实际 skills 在 `/Users/xiesg/.hermes/skills/`，但 cron 环境中找不到
- 结果：GitHub 仓库只有 30 个 skills，本地有 55 个，缺失 25+ 个（所有 `lark-*` 全丢）

**问题 2: `git push` 在 cron 环境中静默失败**
- 仓库使用 SSH URL（`git@github.com:gonshell/my-hermes-skills.git`）
- cron 环境无 SSH agent，`git push` 返回非零退出码但 Hermes 标记为 `ok`
- 本地分支持续领先 origin/main，但从未真正 push 上去

### 修复方向

1. 同步脚本必须在 `cp` 前设置 `HOME=/Users/xiesg`，确保指向真实 skills 目录
2. push 改用 HTTPS + GitHub Token，或在 push 前 `eval "$(ssh-agent)"` 并添加 key
3. cron job 的 `deliver: local` 使错误不外发，需改为 `deliver: origin` 以暴露失败

### 验证命令

```bash
# 检查源目录 skills 数量
ls /Users/xiesg/.hermes/skills/ | wc -l

# 检查 GitHub 仓库同步情况
ls /Users/xiesg/github/my-hermes-skills/ | wc -l

# diff 两边
diff <(ls /Users/xiesg/.hermes/skills/ | sort) <(ls /Users/xiesg/github/my-hermes-skills/ | sort)
```

## 相关文件位置参考

- 实际 hermes-agent 配置: `/Users/xiesg/.hermes/`
- 实际 skills 目录: `/Users/xiesg/.hermes/skills/`（包含 55 个 skills）
- GitHub 同步仓库: `/Users/xiesg/github/my-hermes-skills/
- 同步脚本: `/Users/xiesg/github/my-hermes-skills/scripts/sync-skills.sh`
