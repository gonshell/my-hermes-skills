#!/usr/bin/env python3
"""
state.py - 状态管理

state/config.json 结构:
{
    "feishu_doc_id": "DqQ6daptXoSRzKxUvjRcMCasnng",
    "feishu_doc_url": "https://www.feishu.cn/docx/...",
    "created_at": "2026-06-29T21:15:53",

    "last_run": {
        "week": "2026-W26",
        "type": "full" | "incremental",
        "at": "2026-06-29T21:25:19",
        "data_count": 30,
        "feishu_ok": true
    },

    "week_runs": [
        {"week": "2026-W26", "type": "full", "at": "..."},
        ...
    ]
}
"""

import json
import os
from datetime import datetime
from typing import Optional


STATE_DIR = os.path.expanduser("~/.hermes/skills/modelscope-weekly-trends/state")
STATE_PATH = os.path.join(STATE_DIR, "config.json")


def _ensure_dir():
    """仅创建目录,不调 save"""
    os.makedirs(STATE_DIR, exist_ok=True)


def init():
    """初始化状态(创建空文件)"""
    _ensure_dir()
    if not os.path.exists(STATE_PATH):
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)


def load() -> dict:
    """加载状态"""
    _ensure_dir()
    if not os.path.exists(STATE_PATH):
        return {}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(state: dict):
    """保存状态"""
    _ensure_dir()
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_doc_id() -> Optional[str]:
    return load().get("feishu_doc_id")


def set_doc_id(doc_id: str, doc_url: str = ""):
    state = load()
    state["feishu_doc_id"] = doc_id
    state["feishu_doc_url"] = doc_url
    state["created_at"] = datetime.now().isoformat()
    save(state)


def record_run(week: str, run_type: str, data_count: int = 0, feishu_ok: bool = True, note: str = ""):
    """记录一次运行"""
    state = load()
    now = datetime.now().isoformat()
    state["last_run"] = {
        "week": week,
        "type": run_type,
        "at": now,
        "data_count": data_count,
        "feishu_ok": feishu_ok,
        "note": note,
    }
    if "week_runs" not in state:
        state["week_runs"] = []
    state["week_runs"].append({
        "week": week, "type": run_type, "at": now, "note": note,
    })
    save(state)


def is_ran_this_week(week: str) -> bool:
    """本周是否跑过"""
    state = load()
    return state.get("last_run", {}).get("week") == week


def get_last_run() -> Optional[dict]:
    return load().get("last_run")


# =========================================================================
# CLI
# =========================================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="状态管理")
    sub = parser.add_subparsers(dest="cmd")

    p_show = sub.add_parser("show", help="显示当前状态")
    p_set = sub.add_parser("set-doc", help="设置飞书 doc_id")
    p_set.add_argument("doc_id")
    p_set.add_argument("--url", default="")
    p_record = sub.add_parser("record", help="记录一次运行")
    p_record.add_argument("--week", required=True)
    p_record.add_argument("--type", required=True, choices=["full", "incremental"])
    p_record.add_argument("--data-count", type=int, default=0)
    p_record.add_argument("--note", default="")
    p_reset = sub.add_parser("reset", help="重置状态(慎用)")

    args = parser.parse_args()

    if args.cmd == "show":
        state = load()
        print(json.dumps(state, ensure_ascii=False, indent=2))
    elif args.cmd == "set-doc":
        set_doc_id(args.doc_id, args.url)
        print(f"✅ doc_id 已设置: {args.doc_id}")
    elif args.cmd == "record":
        record_run(args.week, args.type, args.data_count, note=args.note)
        print(f"✅ 已记录: {args.week} {args.type}")
    elif args.cmd == "reset":
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)
        print("✅ 状态已重置")
    else:
        parser.print_help()
