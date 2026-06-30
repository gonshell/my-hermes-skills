# Hermes Agent 本地仓库状态诊断（cron 升级前后必看）

`/Users/xiesg/.hermes/hermes-agent` 是 Hermes Agent 的**本地源码仓库** + **editable mode 安装目录**，不是普通的 pip 安装位置。任何"升级是否真的生效"的问题都必须先把这个目录摸清楚。

## 状态快照（2026-06-30 验证）

- 路径：`/Users/xiesg/.hermes/hermes-agent`
- 版本：`v0.17.0 (2026.6.19)`，与 `pyproject.toml` 的 `version = "0.17.0"` 一致
- 分支：`main`，HEAD = `824f2279d`，与 `origin/main` 完全同步
- Git 状态：tracked 全部干净，仅有 8 个 untracked 临时文件（见"常见噪音"）

## 安装链：符号链接 → venv → editable install

```
~/.local/bin/hermes          ← 用户 PATH 里的全局 hermes 命令
  → /Users/xiesg/.hermes/hermes-agent/venv/bin/hermes    ← venv 里的 hermes wrapper
       内容：
         #!/Users/xiesg/.hermes/hermes-agent/venv/bin/python3
         import sys
         from hermes_cli.main import main
         if __name__ == "__main__":
             sys.exit(main())
  → ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/__editable__.hermes_agent-0.17.0.pth
       内容（一行）：
         import __editable___hermes_agent_0_17_0_finder;
         __editable___hermes_agent_0_17_0_finder.install()
  → 实际指向 /Users/xiesg/.hermes/hermes-agent/ 下所有 .py 文件
```

**关键点**：editable install（pip install -e / `__editable__` .pth 文件）意味着改源码**立即生效**，不需要 `pip install` 重装。这也是为什么本仓库可以同时充当"开发克隆"和"运行时目录"——`hermes` 命令其实是 import 当前源码。

## 验证命令链（按这个顺序跑最稳）

```bash
# 1. Git 状态
cd /Users/xiesg/.hermes/hermes-agent
git status                                                    # 看是否有冲突、stash、修改
git log -1 --oneline                                          # 当前 HEAD 提交
git rev-parse @{u}                                            # 远端 HEAD
git status -sb                                                # 一行输出 ahead/behind 关系

# 2. 全局 hermes 版本（必须和 git HEAD 对得上）
hermes --version
# 期望输出：
#   Hermes Agent v0.17.0 (2026.6.19) · upstream 824f2279
# "upstream" 后跟的 SHA 必须等于 git log -1 输出的 SHA
# 不一致 = gateway 进程没重启（仍在跑旧字节码），升级未闭环

# 3. Editable install 是否还在
ls ~/.hermes/hermes-agent/venv/lib/python*/site-packages/ | grep -i editable
# 期望输出：__editable__.hermes_agent-0.17.0.pth
# 文件缺失 = venv 被重装过、editable link 断了，要重新 `pip install -e .`

# 4. 包装链验证（用户改 PATH 或 venv path 后排错用）
which hermes
ls -la ~/.local/bin/hermes
ls -la /Users/xiesg/.hermes/hermes-agent/venv/bin/hermes

# 5. pyproject vs 已装版本对齐
grep -E '^version|^name' ~/.hermes/hermes-agent/pyproject.toml
cat ~/.hermes/hermes-agent/hermes_agent.egg-info/PKG-INFO | head -10
# PKG-INFO 的 Version 必须等于 pyproject 的 version
```

## 常见噪音：untracked 文件（参考值，2026-06-30 实测）

仓库下 `git status --porcelain` 偶然会挂着别的 cron/agent 跑出来的临时产物。**该列表是当时观察，不是持久状态**——后续会话实测这些文件可被外部清理（手动 rm / 沙箱化 / 重命名）从磁盘上消失。**判断当前是否仍有 untracked 必须现场跑 `git status --porcelain`**，不要照搬下列列表。

2026-06-30 当时观察到的 8 个：

```
bilibili_fetch.sh                           (executable, 307 B；孤儿脚本，0 引用)
bilibili_trending_2026-05-31_221035.xml     (B站原始数据)
hermes_state.db                             (空, 0 B；源头源码里只有 profiles.py / profile_distribution.py / docker/stage2-hook.sh / test_backup.py 当字面量引用，无任何 open 调用)
merged_bilibili-ai.xml                      (6.3 KB)
merged_bilibili.xml                         (4.6 KB)
report_md.txt                               (28.8 KB)
world_model_report.xml                      (34.9 KB)
世界模型技术研判报告_具身智能专题.md         (39.2 KB, 中文文件名)
```

**为什么会留在这里**：这些是其它 cron 任务（bilibili 抓取、世界模型研判）生成时把 cwd 落在了 `~/.hermes/hermes-agent/` 而不是 `/tmp/` 或 `~/.hermes/cron/output/`。`.gitignore` 没拦到（不是 .pyc、不是 test、不是 build artifact 类型）。

**归属调查标准动作**（"X 文件谁在用？"的标准流程，2026-06-30 实测）：见 `references/orphan-file-attribution.md`。

**清理动作**（不删的话，每次 git status 都会刷出来）：
- 可以直接 `rm` 掉（确认文件没人在用，0 字节文件直接删无可丢）
- 或移到 `~/.hermes/scripts/`、 `~/.hermes/cron/output/`
- 或在 `.gitignore` 加一条兜底（但根仓库的 .gitignore 是 upstream 维护的，不该本地改）

**判别规则**：`git status` 出现一堆 untracked 但 `git log -1` 干净的"看起来很脏"现象 = 临时文件堆积，不算 git 冲突。**但**如果前后两次 `git status` 输出不一致 = 磁盘上文件被清掉了，不能用"应该还在"做假设——下一次又要重新调研。

## 升级闭环 vs 不闭环

`hermes update` 完成后四种结果对应三种状态：

| `hermes --version` 输出 | git HEAD | 状态 |
|---|---|---|
| BEFORE == AFTER | HEAD unchanged | **升级没跑成**（preflight 失败、HTTP/2 cancel、网络断、180s 超时） |
| BEFORE != AFTER（after 跟 git log SHA 对得上） | HEAD == upstream | **升级成功 + gateway 会话还是旧版**（需要重启 gateway） |
| BEFORE != AFTER，after 跟 git log SHA 对不上 | HEAD 还在旧版 | **包装链坏了**（venv pth 文件丢、或 hermes 跑的不是这个仓库） |
| BEFORE != AFTER，after 跟 git log SHA 对得上 | HEAD == upstream == after SHA | **真正的完全升级 + 重启 gateway 后** |

**判别规则**："升级后能不能用新功能"取决于 gateway 重启，不是 `hermes update` 退出码。

## 升级任务对应 cron job

任务 `70610d135141`「每周六Hermes Agent升级」的完整 prompt 见 `~/.hermes/cron/jobs.json`，prompt 设计规范详见本 skill 的"自变更型 cron 任务"小节。

