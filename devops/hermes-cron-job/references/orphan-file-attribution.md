# 孤儿文件归因与多源码目录状态比对工作流

> 来源：本会话（2026-06-30）牧羊的机器人连续两次追问 "X 文件谁在用？"以及一次"再看看该源码目录的状态"——提炼出独立可复用的工作流。

## 触发场景

- `git status --porcelain` 列了若干 untracked / orphan，**用户问"X 文件谁在用 / 是干啥的 / 能删吗"**
- 用户说"该源码目录的状态"（注意"该"——可能是单数也可能是复数，要先列出所有候选再让用户识别哪个是他心里想的，或者两者都对比）
- 升级后复核、`hermes update` 后复查、新装 skill 后引入文件清单
- 准备 `rm` / `mv` 之前必须做的归属调查

## 核心规则

**1. 用户的"该"是模糊指代，先列候选再确认。**
看到 `~/.hermes/hermes-agent` 这种路径时**主动 grep 同名目录树**（`find /Users/xiesg -maxdepth 4 -name 'hermes-agent' -type d`），如果有副本（本次发现了 `/Users/xiesg/dev/hermes-agent`），**两个都要 state，按大小/venv/SHA/活跃度对比**——不要默认只跑一个。

**2. "X 文件谁在用"的标准动作链（grep 证据链，不是"应该是 X"）。**

```
a. ls -la X 看大小/mtime（0 字节是历史占位强信号）
b. sqlite3 X '.tables' 看是否有结构（空 sqlite 几乎一定是历史遗留）
c. lsof X 看进程是否持有
d. search_files pattern='X' target=files 全局定位同名文件
e. search_files pattern='X' target=content 抓所有源码引用
f. 区分两类引用：
   - 字符串字面量（"_DEFAULT_EXPORT_EXCLUDE_ROOT"、"test fixture 创建空文件"）→ 不算"在用"
   - 真实读写（open(X) / sqlite3.connect(X) / load(X) / importlib.import_module(X) / pipeline stdout → X）→ 算"在用"
g. cron / scheduled 维度（jobs.json 里的 script / prompt）也要查，常被遗漏
```

**判别孤儿**：
```
0 字节 + 无进程持有 + 无源码 open 调用 + 0 引用入口  → 孤儿（可删，无可丢）
非 0 字节 + 无源码引用             → 高度疑似孤儿（需 grep 全文找调用方）
非 0 字节 + 有源码调用             → 真在用（保留）
```

**3. "源码仓库状态"对多个候选目录，要列对比表，不写散文描述。**

例如本次的 ~/.hermes/hermes-agent vs /Users/xiesg/dev/hermes-agent：

| 维度 | .hermes/hermes-agent | dev/hermes-agent |
|---|---|---|
| HEAD | 824f2279d (v0.17.0) | a68ac0c49 (v0.16.0) |
| upstream 同步 | 0/0 | 0/0 |
| tracked 干净度 | clean | clean |
| untracked 数 | 0（现场查，不是历史值） | 0 |
| 安装 venv | 有（editable） | 无 |
| 全局 hermes 符号链接源 | 是 | 否 |
| 7 天内本地文件改动 | 有 ui-tui/ 增量（属正常 git pull） | 无 |
| 分支数 | 1361 | 1261 |

**4. 报告前自检**：是否每一个数字都来源于刚才执行的命令？**绝不**复用上一回合的 `git status` 输出（状态会变！）。本次对话中我两次跑 `git status --porcelain` 输出从"8 个 untracked"变成"0 个 untracked"，就是因为磁盘上文件被清掉了——**绝对不能用"应该还在"做断言**。

**5. 报告完成后，明确询问"是否需要处理"——列出具体动作 + 风险，但不要擅自执行。**

## 常见陷阱

- **"0 引用" ≠ "0 重要性"**：一个孤儿 `.sh` 脚本可能是用户在某次挫折中写的排查工具，删了之后用户再也想不起来当初为啥写。**正确动作**：先汇报"无任何源码调用方、可删"，再问"印象中有手动清理过吗"——而不是直接 `rm`。
- **字符串字面量陷阱**：`_DEFAULT_EXPORT_EXCLUDE_ROOT` 跳过列表里的文件名 / 测试 fixture 字节填充 / docker stage hook 的白名单 / `print` 调试输出——这些都是"代码中出现了字符串 X"≠ "代码 open 了文件 X"。区分清楚能省很多无效结论。
- **`lsof` 0 持有可能骗你**：进程退出后 lsof 立刻空，但 SQLite WAL/checkpoint 残留可能让 `wc -c` 看着非 0。**配套用法**：`sqlite3 X '.tables'` 看 schema 是否存在；schema 空 = 数据库级孤儿。
- **同名文件名跨目录混淆**：`~/.hermes/state.db`（562MB，活跃）和 `~/.hermes/hermes-agent/hermes_state.db`（0 字节，历史占位）大小差 9 个数量级。**绝对不要用"应当……"做归类**。
- **`/tmp` 是兜底副本来源**：磁盘上清掉的文件可能在 `/tmp/` 留有 21:12 之类的备份版（本次发现 `merged_bilibili-ai.xml` 在 `/tmp/` 留了一份）。不要假设彻底丢了，先全局 find 一遍同名文件。
- **大小不等于价值**：`bilibili_fetch.sh` 只有 307 B，但 `hermes_state.db` 0 字节。两个都是孤儿但语义不同：`sh` 是用户曾经写过的 shell 经验，`db` 是项目早期数据库名演化占位。

## 关联用户偏好（写在这里给下次会话参考）

- 用户问 "X 谁在用" = 期望拿到**证据链**（grep 命令、文件名匹配、引用统计），不是单段散文判断
- 用户问 "该目录状态" 时如果存在多副本，**对比展示**而不是默认选一个
- 用户说"先这样"或"先放着"= 暂停动作，但**仍要给出后续动作清单**等他点头
- 用户偏好"逐个设计、逐个确认、逐个修改"（来自 session-state-verification）——孤儿文件清理也按这个走

## 标准调查 checklist（一页可复制）

```bash
# 1. 列出目录状态
ls -la /path/to/dir
cd /path/to/dir && git log -1 --oneline && git rev-parse @{u} && git status --porcelain | head -10

# 2. 多副本对比（如果有）
for d in /Users/xiesg/.hermes/hermes-agent /Users/xiesg/dev/hermes-agent; do
  cd "$d" 2>/dev/null && {
    echo "$d: HEAD=$(git log -1 --format=%h) up=$(git rev-parse @{u} 2>&1) untracked=$(git status --porcelain | wc -l | tr -d ' ')"
  }
done

# 3. 归属调查
lsof /path/to/file 2>&1 | head -5
sqlite3 /path/to/file.db '.tables' 2>&1
search_files pattern='filename' target=content path=/Users/xiesg/.hermes
search_files pattern='filename' target=files

# 4. 同名副本兜底
find /Users/xiesg /tmp -name 'filename*' -not -path '*/node_modules/*' 2>/dev/null | head -10

# 5. .gitignore / info/exclude 是否放过
grep -nE 'pattern' /path/to/.gitignore /path/to/.git/info/exclude 2>/dev/null

# 6. 报告模板
#   - 文件基本信息（大小/mtime/lsof/schema）
#   - 真实调用证据（grep + 类型区分）
#   - 结论（孤儿/在用/未知）
#   - 风险评估（最坏情况是什么）
#   - 给用户的可选项（rm / mv / 留）
```
