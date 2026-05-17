# Python Environments on macOS — Finding the Right One

## The Problem

macOS has multiple Python installations. The venv at
`/Users/xiesg/.hermes/hermes-agent/venv/bin/python3` is the agent's own environment
(with many packages pre-installed) but has **no pip module**. System Python is at
`/usr/local/bin/python3` (3.14, no pip). The hermes venv has pip but it's not
at the expected path.

## Finding Python with pymupdf

```bash
# Agent's venv python — no pip
/Users/xiesg/.hermes/hermes-agent/venv/bin/python3 -c "import pymupdf; print(pymupdf.__version__)"

# System Python — has pip via /usr/local/bin/pip3
/usr/local/bin/python3 -c "import pymupdf; print(pymupdf.__version__)"

# Install pymupdf on system Python if missing
/usr/local/bin/python3 -m pip install pymupdf --break-system-packages -q
```

## Rule

For **one-liner inline Python** in terminal calls: use `/usr/local/bin/python3`
(because it has pip and pymupdf already installed via the skill session).

For **scripts run via `execute_code`** (sandboxed, uses its own venv): no external packages —
use `terminal()` for anything needing pymupdf.

## Why execute_code can't use pymupdf

The `execute_code` sandbox has its own isolated Python environment with only stdlib
and a few built-in hermes_tools imports. It cannot reach `/usr/local/bin/python3`'s
site-packages. Always use `terminal()` for pymupdf work.