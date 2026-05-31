---
name: agentic-development
description: "Agent驱动的软件开发方法论：探索性实验（spike）→ 计划制定（writing-plans）→ 子代理委托（subagent-driven-development）→ 代码审查（requesting-code-review）→ 系统调试（systematic-debugging）的完整流程。覆盖：一次性实验验证、多步骤计划、子Agent工作流、代码审查、系统调试。当用户要求'试试这个'、'制定计划'、'交给子Agent做'、'审查PR'、'系统调试'时使用。"
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [development, agentic, spike, planning, subagent, code-review, debugging, workflow, delegation]
    related_skills: [hiclaw, codebase-communication, ai-agent-research]
    absorbed: [spike, writing-plans, subagent-driven-development, requesting-code-review, systematic-debugging, python-debugpy, node-inspect-debugger, debugging-hermes-tui-commands]
---

# Agentic 软件开发方法论

Agentic 开发流程：探索验证 → 计划制定 → 子代理委托 → 代码审查 → 系统调试。

## 1. 探索性实验 → `spike`

**使用场景**：用户说"让我试试这个"、"我想看X是否可行"、"在commit之前快速验证Y"、"比较A和B"。

Spike 是**一次性的、可丢弃的**验证实验。验证完成后扔掉，用真实实现替代。

**何时用 Spike**：
- 验证技术可行性（"这个东西能做到吗？"）
- 比较多个方案（"方案A vs 方案B哪个更好？"）
- 快速构建 MVP（"先出个能跑的东西看看"）
- 探索未知领域（"没有文档，试了才知道"）

**何时不用 Spike**：
- 已知正确做法，直接实现即可
- 需要长期保留的代码（用真正的 skill/test 替代）
- 生产环境代码

详见 `references/spike.md`

## 2. 计划制定 → `writing-plans`

**使用场景**：实现多步骤功能、分解复杂需求、向子代理委托任务之前。

好计划让实施者无需猜测。包含：需要改哪些文件、完整代码、测试命令、检查哪些文档、如何验证。假设实施者是熟练开发者但对工具集或问题域几乎不了解。

**何时用**：
- 实施多步骤功能之前
- 分解复杂需求之前
- 通过 `subagent-driven-development` 向子代理委托之前

详见 `references/writing-plans.md`

## 3. 子代理委托 → `subagent-driven-development`

**使用场景**：向子代理委托复杂的多步骤任务，需要父Agent做协调器。

**关键原则**：
- 所有上下文必须嵌入 goal 中，不要让子代理读取文件
- 遇到需要用户决策的点，用 `clarify` 暂停
- 实施 RED-GREEN-REFACTOR TDD 循环
- 完成后验证再返回

详见 `references/subagent-driven-development.md`

## 4. 代码审查 → `requesting-code-review`

**使用场景**：提交PR或代码变更之前进行安全扫描和质量检查。

**前置检查**：
- 敏感信息泄露扫描
- 代码质量检查
- 自动化修复建议

详见 `references/requesting-code-review.md`

## 5. 系统调试 → `systematic-debugging`

**使用场景**：遇到 bug 需要找到根本原因再修复，而不是随机打补丁。

**核心原则**：永远在找根本原因之前不要尝试修复。症状修复是失败。

**四阶段**：
1. **理解问题** — 收集症状、确定边界条件、建立复现步骤
2. **定位根本原因** — 用假设驱动调查，找到 root cause
3. **设计修复** — 修复必须解决根本原因，不是症状
4. **验证** — 确认修复有效，原有功能不受影响

详见 `references/systematic-debugging.md`

---

## 调试工具专项

### Python 调试 → `python-debugpy`

三种工具，按场景选择：

| 工具 | 何时用 |
|------|--------|
| `breakpoint()` + pdb | 本地、交互式、最简单 |
| `python -m pdb` | 不修改源码快速检查 |
| `debugpy` | 远程/无头/附加到运行中进程 |

**优先用 `breakpoint()`**，最便宜且有效。

详见 `references/python-debugpy.md`

### Node.js 调试 → `node-inspect-debugger`

两个工具：
- **`node inspect`** — 内置、零安装、CLI REPL，最适合快速检查
- **`ndb` / CDP via `chrome-remote-interface`** — 脚本化、自动化断点

**优先用 `node inspect`**，始终可用。

详见 `references/node-inspect-debugger.md`

### Hermes TUI 命令调试 → `debugging-hermes-tui-commands`

Hermes TUI 命令跨越三层：Python 命令注册表、tui_gateway JSON-RPC 桥接、Ink/TypeScript 前端。当命令在自动补全中缺失、在 TUI 中不能正常工作、配置持久化但 UI 不更新时，几乎总是一层与另一层不同步。

详见 `references/debugging-hermes-tui-commands.md`

---

## 触发条件

| 用户说 | 使用 Skill |
|--------|-----------|
| "让我试试这个"、"验证一下"、"spike this" | `spike` |
| "制定计划"、"写个实现计划" | `writing-plans` |
| "交给子Agent做"、"并行处理" | `subagent-driven-development` |
| "审查这个PR"、"代码审查" | `requesting-code-review` |
| "遇到bug"、"系统调试"、"找根本原因" | `systematic-debugging` + 对应调试工具 |
| Python调试 | `python-debugpy` |
| Node.js调试 | `node-inspect-debugger` |
| Hermes TUI命令问题 | `debugging-hermes-tui-commands` |