# 验证性事实核查方法（写安装手册的黄金标准）

> 当编写/审查 Hermes 安装手册时，每条命令、URL、环境变量、文件路径都必须可验证。
> 本文档记录"哪些事实必须验证"、"怎么验证"、以及"踩过的坑"。

## 必须验证的事实清单

| 事实类型 | 验证方式 | 失败后果 |
|---------|---------|---------|
| 安装 URL | `curl -I <url>` 看 HTTP 状态 | 文档中的 URL 用户打不开 |
| install.sh 函数名/行号 | `curl <url> \| grep -n "函数名"` | 文档说"第 X 行"但脚本已变 |
| 硬编码版本 | `grep "PYTHON_VERSION=\|NODE_VERSION=" <脚本>` | 文档说"Python 3.12 推荐"但脚本硬编码 3.11 |
| CLI 命令存在性 | 直接执行 `<command> --help` | 文档里推荐了一个不存在的命令 |
| 权限 scope 名称 | 官方文档 cross-check | 申请了一堆废弃/合并过的 scope |
| 文件路径 | `grep "$env:LOCALAPPDATA" <ps1脚本>` | 写 `~/.hermes/` 但 Windows 实际是 `%LOCALAPPDATA%\hermes\` |

## 验证流程（5 步法）

```bash
# Step 1: 拉取安装脚本到本地(或直接在线 grep)
curl -fsSL https://hermes-agent.nousresearch.com/install.sh -o /tmp/install.sh

# Step 2: grep 关键事实(带行号)
grep -n "PYTHON_VERSION\|NODE_VERSION\|node_satisfies_build\|HERMES_HOME" /tmp/install.sh

# Step 3: 验证 CLI 命令真实存在(必须用真实环境,不是记忆)
hermes doctor --help      # ✓ 真实存在,带 --fix 选项
hermes gateway setup --help  # ✓ 真实存在
hermes model --help       # 是否存在待验证

# Step 4: 验证官方文档(用 browser_navigate 看渲染后的页面)
browser_navigate url=https://hermes-agent.nousresearch.com/docs/...
browser_console expression="(()=>{const a=document.querySelector('article'); return a?a.innerText:null;})()"

# Step 5: 在手册中标注来源(让用户能自行验证)
"PYTHON_VERSION="3.11" # install.sh:59"
"Node.js 要求 ^20.19 || >=22.12 # install.sh:711 node_satisfies_build()"
```

## 踩过的坑(避免重复)

### 坑 1: 不要相信"先有命令" — 实际跑才知道

```bash
# 错误做法(凭印象写):
"运行 hermes config edit 进入交互式配置"  # 但 hermes config edit 不存在!

# 正确做法:
hermes config --help  # 实际查命令
# 确认是 hermes setup / hermes gateway setup
```

### 坑 2: 不要照搬旧文档 — 权限会合并/废弃

飞书权限在不断合并:
- `im:message.p2p_msg:readonly` + `im:message.group_msg` + `im:message.group_at_msg:readonly` → 全部合并到 `im:message`
- 旧手册列 8-10 项权限是过时的,新版本只需 5 必需 + 3 推荐

### 坑 3: 路径要分平台

| 平台 | 安装路径 | .env 路径 | 注意 |
|------|---------|-----------|------|
| Linux/macOS/WSL2 | `~/.hermes/hermes-agent/` | `~/.hermes/.env` | 默认 |
| Windows 原生 | `$env:LOCALAPPDATA\hermes\hermes-agent\` | `$env:LOCALAPPDATA\hermes\.env` | 安装脚本硬编码 |

可通过 `HERMES_HOME` 环境变量统一。

### 坑 4: write_file 前必须先 read 全文

```python
# 错误做法:
write_file(path=big_file, content=new_content)  # 工具会拒绝,警告"未读全文"
# 或者:在 subagent 上下文,文件可能已被其他 subagent 改动

# 正确做法:
read_file(path=big_file, offset=1, limit=2000)  # 至少扫一遍结构
# 再用 patch 逐步修改,而非整文件覆盖
```

### 坑 5: 不要用 raw.githubusercontent.com 作为主要安装 URL

```bash
# ❌ 国内经常被墙
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# ✓ 官方控制域名(走 CDN,稳定性更好)
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

### 坑 6: 平台特定的配置文件不要凭印象写

**反例**：写 macOS launchd plist 时，凭印象写：

```xml
<key>Program</key>
<string>$(which hermes)</string>
```

**实际**（从 `~/.hermes/hermes-agent/hermes_cli/gateway.py:generate_launchd_plist()` 读出）：

```xml
<key>ProgramArguments</key>
<array>
    <string>/Users/你/.hermes/hermes-agent/venv/bin/python</string>
    <string>-m</string>
    <string>hermes_cli.main</string>
    <string>gateway</string>
    <string>run</string>
    <string>--replace</string>
</array>
```

**错的字段**（凭印象容易写错）：
- **Label**：`com.hermes-agent.gateway`（错）→ 实际是 `ai.hermes.gateway`
- **Program**：`$(which hermes) gateway`（错）→ 实际是 venv python 跑 `hermes_cli.main`
- **KeepAlive**：`<true/>`（多数文档这么写）→ 实际就是 `<true/>`（碰对了）
- **日志**：合并到一个文件（错）→ 实际是分两个文件 `gateway.log` + `gateway.error.log`
- **缺字段**：`WorkingDirectory`、`EnvironmentVariables`（PATH/VIRTUAL_ENV/HERMES_HOME）、`LimitLoadToSessionType=[Aqua, Background]`

**教训**：

```
写平台特定的配置文件时，必须从源码读真实生成的版本
  1. macOS launchd → ~/.hermes/hermes-agent/hermes_cli/gateway.py
  2. Linux systemd → 同上
  3. Windows schtasks → 同上
  4. 永远不要凭印象写 Label/Program/路径
```

**正确做法**：

```bash
# 找实际生成 plist 的代码
grep -rn "ai.hermes.gateway\|generate_launchd_plist" ~/.hermes/hermes-agent/hermes_cli/

# 读出真实模板
sed -n '3153,3250p' ~/.hermes/hermes-agent/hermes_cli/gateway.py
```

更省事的做法是 **直接用 `hermes gateway install` 让脚本自动生成**，手册里只写一句"运行 `hermes gateway install`，plist 由脚本自动生成到 `~/Library/LaunchAgents/ai.hermes.gateway.plist`"。

### 坑 7: 子命令支持范围是"硬事实"，不是"通用概念"

反例：以为所有 messaging 平台（飞书 / 微信 / 钉钉）的鉴权都通过 `hermes pairing`。**错**。

**必须查 `hermes <subcommand> --help` 看支持的子参数**：

```bash
$ hermes pairing approve --help
usage: hermes pairing approve [-h] platform code
positional arguments:
  platform    Platform name (telegram, discord, slack, whatsapp)
  code        Pairing code to approve
```

→ 飞书不在支持列表。同理 `hermes gateway`、`hermes tools enable` 等子命令都只支持特定参数。

**写手册时**：把"假设 XX 平台都走统一流程"换成"先查 --help 看支持范围"。

## 验证性手册的标记格式

在文档中使用这种格式标注(用户能直接验证):

```markdown
**事实** | **来源(可验证)**

Python 3.11 硬编码 | install.sh:59
Node.js 22 自动下载 | install.sh:790-826
Node.js 版本要求 | install.sh:711 node_satisfies_build() 返回值
WSL2 install 路径 | install.ps1:26-27 HermesHome 默认值
zip fallback | install.ps1:1264-1315
hermes doctor --fix | $ hermes doctor --help
飞书 5 必需权限 | hermes-agent.nousresearch.com/docs/user-guide/messaging/feishu "Required permissions"
```

> 用户可以 grep 出脚本对应行号,或 curl 验证 URL,或 --help 验证命令。
> 这种"可审计"格式比"凭印象"权威得多。
