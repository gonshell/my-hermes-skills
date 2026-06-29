#!/usr/bin/env python3
"""
append_feishu.py - 追加 Markdown 到飞书文档

v1.2:只做 append-text,不传图片。
"""

import json
import os
import subprocess
import sys
import tempfile
from typing import Optional


STATE_PATH = os.path.expanduser("~/.hermes/skills/modelscope-weekly-trends/state/config.json")


def load_state() -> dict:
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_doc_id() -> Optional[str]:
    return load_state().get("feishu_doc_id")


def fetch_doc_length(doc_id: str) -> int:
    """re-fetch 文档,返回 markdown 长度(写后验证用)"""
    try:
        result = subprocess.run(
            ["lark-cli", "docs", "+fetch", "--doc", doc_id],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return len(data.get("data", {}).get("markdown", ""))
    except Exception:
        pass
    return -1


def append_markdown(doc_id: str, markdown: str, verify: bool = True) -> bool:
    """
    追加 markdown 到飞书文档末尾。
    lark-cli 要求 --markdown 路径是 CWD 相对,所以用 tempfile。
    verify=True 时写后 re-fetch 验证长度增加。
    """
    len_before = fetch_doc_length(doc_id) if verify else 0

    try:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8",
        )
        tmp.write(markdown)
        tmp.close()

        result = subprocess.run(
            ["lark-cli", "docs", "+update",
             "--doc", doc_id, "--mode", "append",
             "--markdown", f"@{os.path.basename(tmp.name)}"],
            capture_output=True, text=True, timeout=60,
            cwd=os.path.dirname(tmp.name),
        )
        os.unlink(tmp.name)

        if result.returncode != 0:
            print(f"❌ 追加失败: {result.stderr}", file=sys.stderr)
            return False

        data = json.loads(result.stdout)
        if not data.get("ok"):
            print(f"❌ 追加失败: {data.get('error', result.stdout)}", file=sys.stderr)
            return False

        print("✅ 追加命令成功")

        if verify:
            len_after = fetch_doc_length(doc_id)
            if len_after <= len_before:
                print(f"⚠️ re-fetch 长度未增加(before={len_before}, after={len_after}),重试...", file=sys.stderr)
                return append_markdown(doc_id, markdown, verify=False)
            print(f"✅ 验证通过: {len_before} → {len_after}")

        return True

    except Exception as e:
        print(f"❌ 异常: {e}", file=sys.stderr)
        return False


# =========================================================================
# CLI
# =========================================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="追加 Markdown 到飞书文档")
    parser.add_argument("--doc", help="文档 ID,默认从 state 读")
    parser.add_argument("--markdown", required=True, help="markdown 字符串 或 @filepath")
    parser.add_argument("--no-verify", action="store_true", help="跳过写后验证")
    args = parser.parse_args()

    doc_id = args.doc or get_doc_id()
    if not doc_id:
        print("❌ 无 doc_id,请 --doc 指定或 state.py set-doc", file=sys.stderr)
        sys.exit(1)

    md = args.markdown
    if md.startswith("@"):
        with open(md[1:], "r", encoding="utf-8") as f:
            md = f.read()

    ok = append_markdown(doc_id, md, verify=not args.no_verify)
    sys.exit(0 if ok else 1)
