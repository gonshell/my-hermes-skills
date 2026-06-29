#!/usr/bin/env python3
"""
fetch_week.py - 4 板块数据源(URL 清单)

返回 4 个 URL + browser_console 提取模板,由 LLM 主体用 browser 工具访问。
论文有 arXiv API 备源(脚本自动跑做兜底)。
"""

import json
import subprocess
import sys
from datetime import datetime
from typing import Dict, Any, List


URLS = {
    "models": {
        "url": "https://modelscope.cn/models?sort=latest",
        "hint": "提取 name / vendor / size / tag",
        "js": (
            "Array.from(document.querySelectorAll('a[href*=\"/models/\"]'))"
            ".filter(a=>a.href.match(/\\/models\\/[^\\/]+\\/[^\\/]+$/))"
            ".slice(0,20).map(a=>({name:a.textContent.trim().slice(0,80),href:a.href}))"
        ),
    },
    "datasets": {
        "url": "https://modelscope.cn/datasets?sort=latest",
        "hint": "提取 name / task / size",
        "js": (
            "Array.from(document.querySelectorAll('a[href*=\"/datasets/\"]'))"
            ".filter(a=>a.href.match(/\\/datasets\\/[^\\/]+\\/[^\\/]+$/))"
            ".slice(0,20).map(a=>({name:a.textContent.trim().slice(0,80),href:a.href}))"
        ),
    },
    "tools": {
        "url": "https://modelscope.cn/mcp",
        "hint": "提取 name / provider / category / scale",
        "js": (
            "Array.from(document.querySelectorAll('main a'))"
            ".filter(a=>a.querySelector('img')||a.textContent.includes('@')||a.href.includes('mcp'))"
            ".slice(0,25).map(a=>({name:a.textContent.trim().replace(/\\s+/g,' ').slice(0,90),href:a.href}))"
            ".filter(x=>x.name.length>10)"
        ),
    },
    "papers": {
        "url": "https://modelscope.cn/papers",
        "hint": "提取 title / arxiv_id / summary",
        "js": (
            "Array.from(document.querySelectorAll('main a[href*=\"/papers/\"]'))"
            ".slice(0,15).map(a=>({"
            "title:a.textContent.trim().replace(/\\s+/g,' ').slice(0,100),"
            "arxiv:a.href.match(/\\/papers\\/(\\S+)/)?.[1]||'',"
            "href:a.href}))"
        ),
    },
}

ARXIV_API = "http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&max_results=20"


def run_cmd(cmd: str, timeout: int = 20) -> Dict[str, Any]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "timeout"}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}


def parse_arxiv(xml: str) -> List[Dict]:
    import re
    titles = re.findall(r"<title>([^<]+)</title>", xml)
    links = re.findall(r"<id>([^<]+)</id>", xml)
    items = []
    for i, t in enumerate(titles[1:], start=0):
        if i < len(links):
            items.append({"name": t.strip(), "url": links[i].strip()})
        if len(items) >= 20:
            break
    return items


def fetch_papers_fallback() -> Dict:
    r = run_cmd(f"curl -sL --max-time 15 '{ARXIV_API}' 2>/dev/null | head -c 100000")
    items = parse_arxiv(r["stdout"]) if r["ok"] else []
    return {"status": "ok" if items else "failed", "items": items, "count": len(items)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--urls-only", action="store_true", help="只输出 URL + JS 提取模板")
    parser.add_argument("--out", help="输出文件")
    args = parser.parse_args()

    if args.urls_only:
        out = json.dumps({"urls": URLS, "arxiv_fallback": ARXIV_API, "fetched_at": datetime.now().isoformat()}, ensure_ascii=False, indent=2)
    else:
        papers = fetch_papers_fallback()
        out = json.dumps({
            "models": {"status": "pending_browser", "url": URLS["models"]["url"]},
            "datasets": {"status": "pending_browser", "url": URLS["datasets"]["url"]},
            "tools": {"status": "pending_browser", "url": URLS["tools"]["url"]},
            "papers": papers,
            "urls": {"urls": URLS, "arxiv_fallback": ARXIV_API},
            "fetched_at": datetime.now().isoformat(),
        }, ensure_ascii=False, indent=2)

    if args.out:
        with open(args.out, "w") as f:
            f.write(out)
        print(f"已写入 {args.out}")
    else:
        print(out)
