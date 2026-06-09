---
name: hermes-install-cn
description: >
  Hermes Agent 安装指南的中国网络环境适配。覆盖 install.sh/install.ps1 脚本内部行为、
  国内网络阻断点、离线/镜像替代方案、飞书接入配置。当用户需要在国内（无VPN）安装
  Hermes Agent、编写安装手册、或排查安装失败时加载。
triggers:
  - 安装 Hermes
  - Hermes 安装手册
  - 国内网络安装
  - hermes install
  - install.sh
  - 飞书接入 Hermes
  - Hermes 部署
---

# Hermes Agent 国内网络安装知识库

## 安装脚本内部行为分析

> 基于对 `install.sh`（main branch, 2026-06）和 `install.ps1` 的源码审查。

### install.sh 关键网络请求链

安装脚本按以下顺序发起网络请求，**每一步在国内都可能卡住**：

| 阶段 | URL / 域名 | 脚本函数 | 国内可达性 |
|------|-----------|---------|-----------|
| 1. 下载脚本本身 | `hermes-agent.nousresearch.com/install.sh` | — | ⚠️ 可能慢 |
| 2. 克隆源码 | `github.com/NousResearch/hermes-agent.git` | `clone_repo()` | ❌ 被墙/极慢 |
| 3. 安装 uv | `astral.sh` / PyPI | 脚本内检测 | ⚠️ astral.sh 慢 |
| 4. 创建 venv (uv 下载 Python 3.11) | `python-build-standalone` (via uv) | `setup_venv()` | ⚠️ 可能慢 |
| 5. pip install (uv sync) | `pypi.org` | `install_deps()` | ⚠️ 被墙/慢 |
| 6. 下载 Node.js 22 | `nodejs.org/dist/latest-v22.x/` | `install_node()` | ❌ 极慢 |
| 7. npm install (browser tools) | `registry.npmjs.org` | 脚本后续 | ⚠️ 慢 |
| 8. Playwright/Chromium | `playwright.azureedge.net` | 可选步骤 | ❌ 被墙 |
| 9. ripgrep/ffmpeg | 系统 pkg manager | `ensure_tools()` | ✅ 通常 OK |

### install.ps1 (Windows 原生) 关键差异

- 默认安装路径：`$env:LOCALAPPDATA\hermes`（非 `~/.hermes`）
- **克隆源码有 ZIP fallback**：先 git clone，失败时回退到下载 `https://github.com/NousResearch/hermes-agent/archive/refs/heads/main.zip`（install.ps1:1264-1315）— 这比 install.sh 更适合国内网络
- 也从 `github.com` 克隆源码（首选），同样受国内网络影响
- 从 `nodejs.org` 下载 Node.js
- PowerShell 的 `Invoke-WebRequest` 进度条会严重拖慢下载（脚本已禁用 `$ProgressPreference`）
- 强制设置 `[Console]::OutputEncoding = UTF8`（修复 Playwright box-drawing 字符 mojibake）

### 脚本硬编码的关键版本

```
PYTHON_VERSION="3.11"    # install.sh 硬编码，与系统 Python 无关
NODE_VERSION="22"        # 安装脚本自动下载的 Node.js 版本
```

**含义**：即使用户系统装了 Python 3.12，安装脚本仍会用 uv 下载 3.11 创建 venv。
Node.js 会从 nodejs.org 自动下载到 `$HERMES_HOME/node/`。

### Node.js 版本校验

脚本有 `node_satisfies_build()` 函数，要求 Node.js 版本满足 `^20.19 || >=22.12`。
太旧的 Node 会在 vite build 时失败（缺少 `node:util.styleText`）。

## 国内网络安装失败模式与解决方案

### 模式 1：`git clone` 超时

```bash
# 解决：使用国内镜像或手动下载 ZIP
# 方案 A：ghproxy 镜像
git clone --depth=1 https://ghfast.top/https://github.com/NousResearch/hermes-agent.git

# 方案 B：下载 ZIP（浏览器可能比 git 更能穿透）
# https://github.com/NousResearch/hermes-agent/archive/refs/heads/main.zip
```

### 模式 2：`nodejs.org` 下载极慢

```bash
# 解决：预先安装 Node.js，让脚本跳过自动下载
# 安装后脚本检测到 node 命令可用，会跳过 download

# Ubuntu
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS
brew install node@22

# 或使用 npmmirror 提供的 Node.js 二进制
# https://npmmirror.com/mirrors/node/
```

### 模式 3：`uv sync` / `pip install` 失败

```bash
# 解决：使用国内 PyPI 镜像
export UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
uv pip install -e ".[all]"

# 或 pip
pip install -e ".[all]" -i https://mirrors.aliyun.com/pypi/simple/
```

### 模式 4：uv 本身安装失败

```bash
# astral.sh 在国内慢，优先用 pip 安装 uv
pip install uv -i https://mirrors.aliyun.com/pypi/simple/ --break-system-packages
```

## 飞书接入关键路径

### 快速路径：scan-to-create（推荐）

```bash
hermes gateway setup
# 选择 Feishu / Lark → 扫描 QR 码 → 自动创建应用并配置权限
```

一条命令完成飞书应用创建+权限配置+凭证保存。**QR 码扫描方式比手动操作飞书开放平台快得多**。

### 手动路径：飞书开放平台操作

如 QR 码不可用，需在 open.feishu.cn 手动：

**必需权限（5 项，缺一不可）**：
- `im:message` — 接收和读取消息
- `im:message:send_as_bot` — 以机器人身份发送消息
- `im:resource` — 访问用户发送的图片、文件、音频
- `im:chat` — 访问群组元数据
- `im:chat:readonly` — 读取群列表和成员

**推荐权限（3 项，完整功能）**：
- `im:message.reactions:readonly` — 接收表情回应事件
- `admin:app.info:readonly` — 自动检测机器人身份（@提及门控）
- `contact:user.id:readonly` — 解析用户 ID（白名单匹配）

操作步骤：
1. 创建企业自建应用
2. 获取 App ID / App Secret
3. 添加「机器人」能力
4. 批量导入上述 8 项权限（"权限管理" → "批量导入/导出权限"）
5. 配置事件订阅 → 选择「长连接」→ 添加 `im.message.receive_v1`
6. **发布应用 + 配置可用范围**（未发布则员工搜不到机器人 — 常见遗漏）

### 飞书 WebSocket 连接

- 使用 `wss://open.feishu.cn`，无需公网 IP
- 连接模式：`FEISHU_CONNECTION_MODE=websocket`
- 企业内网需确认 `wss://` 协议未被拦截

## 安装手册审查 Checklist

当审查或编写 Hermes 安装手册时，逐项确认：

- [ ] 安装 URL 使用 `hermes-agent.nousresearch.com/install.sh`（非 raw.githubusercontent.com）
- [ ] 说明安装脚本会自动下载 Node.js 22（国内需预装或加速）
- [ ] 说明 Python 版本硬编码为 3.11（uv 自动下载，与系统版本无关）
- [ ] Node.js 版本要求为 `^20.19 || >=22.12`（非 `>=18`）
- [ ] Windows 原生安装路径为 `$env:LOCALAPPDATA\hermes`（非 `~/.hermes`）
- [ ] Windows 支持 PowerShell 原生安装（非仅 WSL2）— 注明 install.ps1 有 ZIP fallback（github.com 失败时下载 archive）
- [ ] 飞书接入推荐 scan-to-create（QR 码扫描）
- [ ] 飞书权限导入 JSON 包含 5 必需 + 3 推荐（共 8 项，不要导入废弃的 `contact:user.base:readonly` 等）
- [ ] 每个 GitHub/nodejs.org/pypi.org 请求都有国内替代方案
- [ ] 离线安装路径为完整的可操作步骤（非笼统描述）
- [ ] 包含 `hermes gateway setup` 的交互流程描述
- [ ] 飞书应用发布后才能被用户搜到（常见遗漏）
- [ ] `.env` 文件权限设置为 `chmod 600`
- [ ] 关键命令和 URL 在文档中标注来源行号或 URL（可验证）
- [ ] 推荐使用 `hermes doctor --fix` 进行安装后诊断
- [ ] **macOS launchd 章节必须用 `hermes gateway install` 自动生成 plist，不要手写 plist 模板**（手写极易出错：Label 不是 `com.hermes-agent.gateway` 而是 `ai.hermes.gateway`，Program 是 venv python + `-m hermes_cli.main` 而非 `which hermes`）
- [ ] **飞书鉴权不通过 `hermes pairing`，用 `FEISHU_ALLOWED_USERS` 环境变量**（`hermes pairing` 只支持 telegram/discord/slack/whatsapp，不支持 feishu）
- [ ] **写平台特定配置（plist / systemd unit / schtasks）前必须从源码读真实生成版本**（如 `hermes_cli/gateway.py:generate_launchd_plist()`），不要凭印象写

## 验证性事实（写手册前必查）

> 不要凭印象写命令或路径。下列每条都已通过源码/官方文档验证：

| 事实 | 验证来源 | 备注 |
|------|---------|------|
| `PYTHON_VERSION="3.11"` 硬编码 | install.sh:59 | 与系统 Python 无关 |
| `NODE_VERSION="22"` 自动下载 | install.sh:60, 790-826 | 国内常卡此处 |
| Node.js 最低要求 `^20.19 \|\| >=22.12` | install.sh:711 `node_satisfies_build()` | 太旧 Node 会在 vite build 失败 |
| 默认路径 Linux/macOS | `~/.hermes/` | 由 `install.sh` 推断 HERMES_HOME |
| 默认路径 Windows 原生 | `$env:LOCALAPPDATA\hermes\` | install.ps1:26-27 HermesHome 默认值 |
| install.ps1 ZIP fallback | install.ps1:1264-1315 | git clone 失败时回退到 GitHub archive |
| `hermes doctor --fix` 命令 | $ hermes doctor --help | 支持自动修复 + ack 安全公告 |
| 飞书 5 必需权限 | hermes-agent.nousresearch.com/docs/.../feishu | im:message / im:resource 等 |
| 飞书 3 推荐权限 | 同上 | im:message.reactions:readonly 等 |
| 飞书 WebSocket URL | `wss://open.feishu.cn` | 长连接模式，无需公网 IP |
| 飞书 `wss://` 企业内网 | 需 IT 部门放行 | 常见卡点 |

## 相关文件

- `references/install-script-network-map.md` — install.sh 网络请求完整映射表
- `references/feishu-permissions-official.md` — **新增** 飞书权限官方列表（5 必需 + 3 推荐，含废弃权限对照、批量导入 JSON 模板、生产环境变量速查）。**已纠正：飞书鉴权不走 `hermes pairing` 子命令（只支持 telegram/discord/slack/whatsapp），用 `FEISHU_ALLOWED_USERS` 环境变量实现白名单**。
- `references/verification-methodology.md` — **新增** 验证性事实核查方法：哪些事实必须验证、5 步验证流程、踩过的坑（`hermes config edit` 不存在、飞书权限已合并、Windows 路径硬编码、write_file 前必须先 read）、验证性手册的标记格式（带行号标注让用户自行验证）。**含 macOS launchd plist 必须从源码读、不能凭印象写**的教训（含 4 个字段的错例对照），以及**子命令支持范围是硬事实、必须查 --help** 的教训。
