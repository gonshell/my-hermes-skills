---
name: workspace-organization
description: Organize project files into ~/workspace/ with a structured subdirectory taxonomy. Triggered when user says "organize", "move files", "workspace", or asks to set up a working directory structure.
trigger:
  - "organize files into ~/workspace"
  - "按目录层次移动"
  - "set up workspace directory"
  - "workspace structure"
---

# Workspace Organization

## Core Principle
User's `~/workspace/` = `/Users/xiesg/workspace/` — the canonical project working area, separate from vault-style repos like Obsidian Vault.

**Path resolution critical rule**: In terminal sessions, `~/` resolves to the session's home dir. When running as Hermes subprocess, `~` = the shell account's home, which may be `/Users/xiesg/` NOT the agent's runtime dir. **Always use absolute paths** (`/Users/xiesg/workspace/`) for user-facing workspace operations. Do NOT rely on `~` expansion for user-level directories.

## Standard Taxonomy

```
~/workspace/
├── <project-a>/
│   ├── scripts/       ← .py, .sh executable scripts
│   └── *.xml, *.md   ← content/documents
├── <project-b>/
├── opc/               ← OPC-related files (opc_*.xml)
├── feishu-work/        ← Feishu/Lark I/O files (lark_*.xml)
├── ai-school/          ← AI school blog/research files
├── bilibili/
│   ├── scripts/       ← video processing scripts
│   └── *.xml, *.md   ← content files
└── work-outputs/      ← generic outputs (output.*, pm-*, am-*, etc.)
```

## Execution Protocol

1. **Read the target structure from user** — do not invent subdirectories beyond what user specifies
2. **Create dirs with absolute path** — `mkdir -p /Users/xiesg/workspace/{dir1,dir2,...}` 
3. **Move files one logical group at a time** — group by user-provided taxonomy
4. **Verify with `find /Users/xiesg/workspace -type f | sort`**
5. **Report final structure** as a tree

## Directory Creation Template

```bash
mkdir -p /Users/xiesg/workspace/{bilibili/scripts,opc,feishu-work,ai-school,work-outputs}
```

Adjust subdirectory names per user's requested structure. Never use `~` in mkdir — always `/Users/xiesg/workspace/`.

## Pitfalls
## Pitfalls

- **`~` resolves to different homes depending on execution context** — the most critical pitfall:
  - In **Hermes agent session** (main terminal): `~` = `/Users/xiesg/` (user's actual home)
  - In **Hermes subprocess / cron job**: `~` = `/Users/xiesg/.hermes/home/` (Hermes runtime home)
  - **Workaround**: Always use **absolute paths** (`/Users/xiesg/workspace/`) for any user-facing workspace operations, even when `~` seems to work in the current session — it may break silently in a subprocess
  - **Diagnosis**: If `mv ~/workspace/foo bar` lands files in `~/.hermes/home/workspace/foo` instead of `/Users/xiesg/workspace/foo`, the session context changed. Re-run with absolute path and verify with `find /Users/xiesg/workspace/` not `ls ~/workspace/`
- **Creating dirs inside agent runtime instead of user workspace** — check with `ls /Users/xiesg/workspace/` before mv
- **Confusing vault (Obsidian Vault at ~/Documents/Obsidian Vault/) with workspace** — these are separate, distinct purposes
- **Files can silently land in the wrong workspace** — always verify final location with `find <absolute-path> -type f` after mass moves