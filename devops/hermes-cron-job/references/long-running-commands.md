# Cron Jobs 中的长命令执行模式

当 cron 任务的某个步骤可能超过 60 秒（`hermes update`、`pip install -U`、大文件 `git clone`、`npm install`、批量 curl 下载等），默认的 `terminal(timeout=N)` 前台调用会被沙箱默认的 180 秒或者你设的 540 秒超时强制中断。本参考给出在 cron 任务里跑长命令的标准模式。

## 核心模式：background + notify_on_complete

```python
terminal(
    command="hermes update --yes",
    background=true,
    notify_on_complete=true,
    timeout=560,           # 必须 > 命令实际耗时上限；540 秒（9 分钟）适合 git pull + pip install
)
```

- `background=true` 让进程脱离前台，**不会**被 `terminal` 的超时切断
- `notify_on_complete=true` 是关键 —— 进程退出后系统会**自动**给当前 session 发一条通知，告诉你 exit_code 和完整 stdout/stderr
- 不要把 `notify_on_complete` 和 `watch_patterns` 同时设；后者是为"永远不退出的 server 启动完成"那种一次性中间信号设计的

## `timeout` shell 命令 vs background 模式

**`timeout` 命令在用户环境实测可用**（2026-06-30）：macOS 通过 coreutils 或 brew 安装的 GNU `timeout` 是有的，cron 沙箱里跑 `timeout 540 hermes update --yes` 能正常返回 exit code。**首选 `timeout N cmd`**——简单直接，exit code 透传（124=超时、其他=命令自身退出码）。

如果 `which timeout` 为空（最小化 macOS 环境），回退到上面的 `background + notify_on_complete` 模式。**不要**用 `terminal(timeout=540)` 前台等——沙箱 180s 默认 timeout 仍可能夹住，且 agent 必须阻塞到结束才能继续。

**`timeout 540` 的选择依据**：git pull + pip install 在网络正常时 30-60s，遇到冷启动或大版本升级可能 3-5 分钟。540s（9 分钟）留足余量。`hermes update` 自身在第 8801-8821 行的 non-interactive 分支会跑 `git fetch` + `git pull` + `pip install -e .`，任何一个慢都会拖时间。

## `process wait` 的 60 秒天花板

`process(action='wait', session_id=..., timeout=N)` 请求的 timeout 会被**强制夹到 60 秒**：

```json
{"status": "timeout", "output": "", "timeout_note": "Requested wait of 300s was clamped to configured limit of 60s"}
```

所以"wait 540 秒一次性等完"做不到。**正确做法**：

```python
# 启动
process(action='wait', session_id=..., timeout=60)   # 永远传 60
process(action='poll', session_id=...)                # 检查 status
# 重复直到 status != 'running'
```

或者更简单：**完全不用 `wait`**，依赖 `notify_on_complete` 让系统在你继续做别的事时回调通知你进程结束。

## 完整模板：跑长命令 → 拿到 exit_code 和 stdout

```python
# 1. 启动
result = terminal(
    command="hermes update --yes",
    background=true,
    notify_on_complete=true,
    timeout=560,
)
session_id = result["session_id"]

# 2. 等通知（你可以并行做别的事）
# 系统会在进程退出时自动回调，传入 exit_code + output

# 3. 如果要主动读输出：
process(action='log', session_id=session_id, limit=200)

# 4. 如果要杀进程：
process(action='kill', session_id=session_id)
```

## 在 cron 任务 prompt 里指定这个模式

cron job 的 prompt 里如果让 agent 跑长命令，应该**显式告诉它用 `background=true`** 而不是写 "请用 timeout 540 秒"。例：

> **执行升级**：用 `terminal(background=true, notify_on_complete=true, timeout=560)` 跑 `hermes update --yes`（不要用 shell `timeout` 命令 —— macOS 没有；不要用 `terminal` 前台 + 长 timeout —— 沙箱可能夹住）。完成后从系统通知里取 exit_code 和 stdout。

agent 看到这条才知道该用哪个工具参数。

## 常见陷阱

- **`notify_on_complete=true` 必须配 `background=true`**：单独设 `notify_on_complete` 不生效（前台命令马上返回了，没东西可通知）。
- **`terminal(background=true)` 后立即 `process(action='wait')` 会拿到 "session not found"**：启动和第一次 wait 之间有几秒延迟；先 `process(action='list')` 或 `process(action='poll')` 一次确认 session_id 已注册。
- **进程 stdout 不会实时回流**：background 命令的输出要等进程退出后用 `process(action='log')` 一次性读。如果需要实时看进度（比如 pip install 的下载百分比），用 `watch_patterns` 匹配关键中间信号（如 "Successfully installed"），但要注意每 15 秒限流。
- **退出码不一定是 0/1**：很多工具用 0=成功、非 0=各种失败。`hermes update` 在 git fetch 失败时返回 1，但在 stash 冲突自动回退时可能返回 0 —— 看具体命令的 manpage，别假设。
- **`notify_on_complete` 在极长任务下可能漏触发**：实测 9+ 分钟的 `hermes update` 在 ~10 分钟时回调正常到达，但如果总长超过 30 分钟，沙箱通知机制可能不可靠。超长任务（>30 分钟）建议拆成多个 cron job 或加心跳。