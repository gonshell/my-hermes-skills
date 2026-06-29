#!/usr/bin/env python3
"""Build the YouTube AI 早间档/晚间档 XML for 飞书 DocxXML upload.

Used when YouTube is unreachable (HTTP 000) and we fall back to Bing + Bilibili
data. Writes both a date-stamped copy and a `merged_youtube-ai.xml` for lark-cli
upload.

Input schema (matches `scripts/bing_to_bili.py` output — every item has `bv`):
  - long_top10: list[dict]  keys = {title, owner, view, duration, pubdate, bv, source}
  - short_top5: same shape
  - recent_top10: same shape, ordered newest-first

All items today come through B站 /view API (Bing HTML → BVID → /view), so every
dict has a `bv` field and we link directly to https://www.bilibili.com/video/{bv}/.
No more `bilibili_bvid_map` lookup needed.

Output:
- /Users/xiesg/.hermes/cron/output/merged_youtube-ai.xml               (for lark-cli upload)
- /Users/xiesg/.hermes/cron/output/youtube-ai-{am|pm}_{YYYY-MM-DD}.xml  (backup)

Then upload with:
    cd /Users/xiesg && lark-cli docs +update --api-version v2 \\
      --doc "$DOC_TOKEN" --command overwrite \\
      --content @./.hermes/cron/output/merged_youtube-ai.xml --doc-format xml

Warnings to expect (all harmless, content still renders):
  - degrade_code=4007: <docx> and <body> wrapping tags are unsupported, escaped.
  - degrade_code=1017: duplicate <title> detected — keep only one (first wins).
`ok: true` means write succeeded regardless.
"""
import json
import os
import urllib.parse
from datetime import datetime, timezone, timedelta

OUT_DIR = "/Users/xiesg/.hermes/cron/output/"
CST = timezone(timedelta(hours=8))

# 飞书文档 token — 见 SKILL.md "飞书文档写入" 节
DOC_TOKEN_AM="EbHDdKARYo4vEExQiNGc3qiGnSe"  # 早间档
DOC_TOKEN_PM="HhyMdusqdoVcW9xLyd2c2Yc2nnf"  # 晚间档


def escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def fmt_dur(secs) -> str:
    """seconds -> M:SS or H:MM:SS"""
    secs = int(secs)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def fmt_view(v) -> str:
    """12345 -> 1.2万, 1234567 -> 123.5万, 12345678 -> 1234.6万"""
    v = int(v)
    if v >= 10000:
        wan = v / 10000
        if wan >= 10000:
            return f"{wan/10000:.1f}亿"
        return f"{wan:.1f}万"
    return str(v)


def fmt_uploaded(pub_ts) -> str:
    return datetime.fromtimestamp(int(pub_ts), CST).strftime("%m-%d %H:%M")


def build_li(v: dict) -> str:
    """Render one <li> from a bing_to_bili.py output dict.

    Every item today has a `bv` field (B站 /view API response); use the canonical
    B站 URL directly. No more manual title→BVID map.
    """
    bv = v.get("bv")
    if not bv:
        # Defensive fallback — should never happen with current bing_to_bili.py output
        encoded = urllib.parse.quote(v.get("title", "")[:20])
        href = f"https://search.bilibili.com/all?keyword={encoded}"
    else:
        href = f"https://www.bilibili.com/video/{bv}/"
    return (f'<li seq="auto"><a href="{href}">{escape(v["title"])}</a> '
            f'｜频道：{escape(v.get("owner", ""))} '
            f'｜播放：{fmt_view(v.get("view", 0))} '
            f'｜时长：{fmt_dur(v.get("duration", 0))} '
            f'｜上传：{fmt_uploaded(v.get("pubdate", 0))}</li>')


def build_xml(date: str, slot: str,
              long_top10: list[dict],
              short_top5: list[dict],
              recent_top10: list[dict],
              data_source: str = "Bing 视频搜索 + Bilibili /view API "
                                 "(YouTube 网络不可达 HTTP 000，走降级方案)") -> str:
    slot_cn = {"am": "早间档", "pm": "晚间档"}[slot]
    lines: list[str] = []
    # ⚠️ DocxXML wrapper — see SKILL.md "飞书文档写入" pitfall.
    # <docx> and <body> trigger degrade_code=4007 (harmless); inner tags render fine.
    lines.append(f'<docx><title>YouTube AI热门视频 · {slot_cn}</title><body>')
    lines.append(f'<h1>YouTube AI热门视频 · {date} · {slot_cn}</h1>')
    lines.append('')

    lines.append('<h2>最热门长视频 TOP 10</h2>')
    lines.append('<p>本周上传，播放量+互动率综合评分排序</p>')
    lines.append('<ol>')
    for v in long_top10:
        lines.append(build_li(v))
    lines.append('</ol>')
    lines.append('')

    lines.append('<h2>最热门短视频 TOP 5</h2>')
    lines.append('<ol>')
    for v in short_top5:
        lines.append(build_li(v))
    lines.append('</ol>')
    lines.append('')

    lines.append('<h2>当日新发热门视频 TOP 10</h2>')
    lines.append('<p>最近上传，按最新排序</p>')
    lines.append('<ol>')
    for v in recent_top10:
        lines.append(build_li(v))
    lines.append('</ol>')
    lines.append('')

    ts = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")
    lines.append(f'<text color="gray">⚠️ 数据获取时间：{ts} '
                 f'| 数据来源：{data_source}</text>')
    lines.append('</body></docx>')
    return "\n".join(lines)


def write(date: str, slot: str, **kwargs) -> tuple[str, str]:
    os.makedirs(OUT_DIR, exist_ok=True)
    content = build_xml(date, slot, **kwargs)
    merged = os.path.join(OUT_DIR, "merged_youtube-ai.xml")
    dated = os.path.join(OUT_DIR, f"youtube-ai-{slot}_{date}.xml")
    with open(merged, "w", encoding="utf-8") as f:
        f.write(content)
    with open(dated, "w", encoding="utf-8") as f:
        f.write(content)
    return merged, dated


if __name__ == "__main__":
    # Example wiring — load real bing_to_bili.json output.
    DATA_FILE = os.path.join(OUT_DIR, "bing_to_bili.json")
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            data = json.load(f)
        # Default to today's date in CST
        today = datetime.now(CST).strftime("%Y-%m-%d")
        slot = sys.argv[1] if len(sys.argv) > 1 else "am"
        merged, dated = write(today, slot,
                              long_top10=data.get("longs", []),
                              short_top5=data.get("shorts", []),
                              recent_top10=data.get("news", []))
        print(f"wrote: {merged}\nwrote: {dated}")
    else:
        # Dry-run example (no real data)
        merged, dated = write("2026-06-29", "am",
                              long_top10=[], short_top5=[], recent_top10=[])
        print(f"wrote (empty): {merged}\nwrote: {dated}")