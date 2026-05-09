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

## 相关文件位置参考

- 实际 hermes-agent 配置: `/Users/xiesg/.hermes/`
- 实际 skills 目录: `/Users/xiesg/.hermes/skills/`（包含 113 个 skills）
- GitHub 同步仓库: `/Users/xiesg/github/my-hermes-skills/`
- 同步脚本: `/Users/xiesg/github/my-hermes-skills/scripts/sync-skills.sh`
