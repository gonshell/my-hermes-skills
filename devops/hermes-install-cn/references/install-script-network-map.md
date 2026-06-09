# install.sh 网络请求完整映射表

> 基于 `NousResearch/hermes-agent` main branch, commit ~b99c6c4 (2026-06-08) 的 install.sh 源码审查。

## 请求时序与阻断分析

### Phase 1: 脚本下载

```
URL: https://hermes-agent.nousresearch.com/install.sh
     (旧 URL: https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh)
方法: curl -fsSL
阻断: raw.githubusercontent.com 在国内被墙
对策: 使用 hermes-agent.nousresearch.com 域名
```

### Phase 2: 依赖检测与安装

```
函数: check_prerequisites() / ensure_tools()
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2a. ripgrep 检测
    - command -v rg → 通常系统已有或 apt install ripgrep
    - Termux: pkg install ripgrep
    - Ubuntu: apt 安装（国内 OK）

2b. ffmpeg 检测
    - command -v ffmpeg → apt install ffmpeg
    - 国内 OK
```

### Phase 3: uv 安装

```
函数: ensure_uv() (脚本内嵌)
━━━━━━━━━━━━━━━━━━━━
URL: https://astral.sh/uv/install.sh (curl | sh)
或:  pip install uv (从 PyPI)
阻断: astral.sh 国内慢但通常可达
对策: pip install uv -i https://mirrors.aliyun.com/pypi/simple/
```

### Phase 4: Node.js 安装

```
函数: check_node() → install_node()
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
URL: https://nodejs.org/dist/latest-v22.x/
文件: node-v22.x.x-{linux|darwin}-{x64|arm64}.tar.xz (或 .tar.gz)
安装到: $HERMES_HOME/node/
PATH 注册: $HERMES_HOME/node/bin/ 加入 PATH
软链: ~/.local/bin/node → $HERMES_HOME/node/bin/node

阻断: ❌ nodejs.org 在国内极慢/超时（这是最常见的安装卡住点）
对策:
  1. 预装 Node.js 22: brew install node@22 (macOS) / apt install nodejs (Ubuntu)
  2. 使用 npmmirror 镜像手动下载: https://npmmirror.com/mirrors/node/
  3. 安装到 $HERMES_HOME/node/ 让脚本检测到并跳过

关键代码 (line ~722-860):
  - 先检测系统 node 命令
  - 再检测 $HERMES_HOME/node/bin/node
  - 都没有才触发 install_node()
  - 版本校验: node_satisfies_build() 要求 ^20.19 || >=22.12
```

### Phase 5: 克隆源码

```
函数: clone_repo()
━━━━━━━━━━━━━━━━━━
URL (SSH): git@github.com:NousResearch/hermes-agent.git
URL (HTTPS): https://github.com/NousResearch/hermes-agent.git
分支: $BRANCH (默认 "main")
深度: --depth 1

阻断: ❌ github.com 在国内被墙/极慢
对策:
  1. 设置 git 代理: git config --global http.proxy ...
  2. 使用 ghproxy: git clone https://ghfast.top/https://github.com/...
  3. 下载 ZIP: github.com/.../archive/main.zip
  4. 有代理机器下载后 U盘拷贝

关键代码 (line ~1092-1180):
  - 先尝试 SSH (5s 超时, BatchMode=yes)
  - SSH 失败后清理残留目录
  - 再尝试 HTTPS clone
  - 两者都失败则 exit 1
```

### Phase 6: Python venv 创建

```
函数: setup_venv()
━━━━━━━━━━━━━━━━━
版本: PYTHON_VERSION="3.11" (硬编码)
命令: $UV_CMD venv venv --python "3.11"
位置: $INSTALL_DIR/venv/

阻断: uv 会从 python-build-standalone 下载 Python 3.11
      (通常托管在 GitHub releases，国内可能慢)
对策:
  - 系统预装 python3.11 (apt install python3.11 python3.11-venv)
  - 脚本在 Termux 上用系统 Python 的 stdlib venv (不走 uv)
  - 非 Termux 的安装总是用 uv 创建 3.11 venv
```

### Phase 7: Python 依赖安装

```
函数: install_deps()
━━━━━━━━━━━━━━━━━━━
Tier 0 (首选): uv sync --extra all --locked (需要 uv.lock)
Tier 1 (降级): uv pip install -e ".[all]"
Tier 2 (再降): uv pip install -e ".[all]" 减去 _BROKEN_EXTRAS
Tier 3 (兜底): uv pip install -e "." (仅核心)

阻断: ❌ pypi.org 在国内被墙/慢
对策: export UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

Ubuntu 特殊处理 (line ~1350-1375):
  - 自动检测 build-essential, python3-dev, libffi-dev
  - 弹出 sudo 提示安装 → 非交互模式下可能卡住
  - 预装可跳过: sudo apt install build-essential python3-dev libffi-dev
```

### Phase 8: Node.js 依赖（browser tools）

```
位置: $INSTALL_DIR/apps/browser-tools/ 或类似
命令: npm install
阻断: ⚠️ registry.npmjs.org 国内慢
对策: npm config set registry https://registry.npmmirror.com
```

### Phase 9: Playwright/Chromium（可选）

```
触发: --skip-browser 未设置时
URL: playwright 自动从 CDN 下载 Chromium
阻断: ❌ playwright CDN 在国内被墙
对策:
  1. PLAYWRIGHT_DOWNLOAD_HOST=https://playwright-mirror.npmmirror.com playwright install chromium
  2. 安装时加 --skip-browser 跳过（飞书场景非必需）
```

## Windows install.ps1 差异

| 项目 | install.sh (Unix) | install.ps1 (Windows) |
|------|-------------------|----------------------|
| 安装路径 | `~/.hermes/hermes-agent/` | `$env:LOCALAPPDATA\hermes\hermes-agent\` |
| 数据路径 | `~/.hermes/` | `$env:LOCALAPPDATA\hermes\` |
| Python 版本 | 3.11 (硬编码) | 3.11 (硬编码) |
| Node.js 版本 | 22 (硬编码) | 22 (硬编码) |
| venv 工具 | uv | uv |
| 包安装 | `uv sync --extra all --locked` | 同 install.sh |
| 进度条 | N/A | PowerShell IWR 进度条（脚本已禁用 $ProgressPreference） |
| 编码 | UTF-8 | 脚本强制 [Console]::OutputEncoding = UTF8 |

## 国内网络完整安装命令序列（最小化卡点）

```bash
# === 预装所有可预装的依赖 ===

# 1. Python 3.11 + 构建工具
sudo apt install -y python3.11 python3.11-venv python3.11-dev \
  build-essential libffi-dev git curl ripgrep

# 2. Node.js 22（避免脚本从 nodejs.org 下载）
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# 3. uv（从国内 PyPI 镜像安装）
pip install uv -i https://mirrors.aliyun.com/pypi/simple/ --break-system-packages

# 4. 克隆源码（浅克隆减少数据量）
git clone --depth=1 https://github.com/NousResearch/hermes-agent.git ~/.hermes/hermes-agent
# 如果 github.com 不通，下载 ZIP 或用 ghproxy

# 5. 安装 Python 依赖（国内 PyPI 镜像）
cd ~/.hermes/hermes-agent
export UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
uv venv venv --python 3.11
source venv/bin/activate
uv pip install -e ".[all]"

# 6. 配置
hermes setup
hermes gateway setup  # 选择 Feishu → 扫 QR 码

# 7. 启动
hermes gateway start
```
