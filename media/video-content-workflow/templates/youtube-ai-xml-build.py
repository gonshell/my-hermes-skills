#!/usr/bin/env python3
"""Build the YouTube AI 早间档/晚间档 XML for 飞书 DocxXML upload.

Used when YouTube is unreachable (HTTP 000) and we fall back to Bing + Bilibili
data. Writes both a date-stamped copy and a `merged_youtube-ai.xml` for lark-cli
upload.

Inputs:
- long_top10: list[dict] with keys {title, channel, views, duration, uploaded, src}
  src ∈ {"bing", "bilibili"} — bing items use bing search URL; bilibili items
  must have a BVID resolvable via bilibili_bvid_map below.
- short_top5: same shape
- recent_top10: same shape, ordered newest-first

Output:
- /Users/xiesg/.hermes/cron/output/merged_youtube-ai.xml   (for lark-cli upload)
- /Users/xiesg/.hermes/cron/output/youtube-ai-{am|pm}_{YYYY-MM-DD}.xml   (backup)

Then upload with:
    cd /Users/xiesg && lark-cli docs +update --api-version v2 \\
      --doc "$DOC_TOKEN" --command overwrite \\
      --content @./.hermes/cron/output/merged_youtube-ai.xml --doc-format xml

`<docx>/<body>` wrapping tags will trigger a `degrade_code=4007` warning in
the response — this is harmless. ok:true means write succeeded.
"""
import os
import urllib.parse
from datetime import datetime

OUT_DIR = "/Users/xiesg/.hermes/cron/output/"

# 飞书文档 token — 见 SKILL.md “飞书文档写入” 节
DOC_TOKEN_AM = "EbHDdKARYo4vEExQiNGc3qiGnSe"  # 早间档
DOC_TOKEN_PM = "HhyMdusqdoVcW9xLyd2c2Yc2nnf"  # 晚间档

# Map bilibili 完整标题 → BVID (looked up via browser_console a[href*="/video/BV"])
bilibili_bvid_map: dict[str, str] = {
    # "完整标题": "BVxxx",
}


def escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("—", "-"))


def bing_link(title: str) -> str:
    return f"https://www.bing.com/videos/search?q={urllib.parse.quote(title)}"


def build_li(v: dict) -> str:
    title_esc = escape(v["title"])
    if v.get("src") == "bilibili":
        bvid = bilibili_bvid_map.get(v["title"])
        if bvid:
            href = f"https://www.bilibili.com/video/{bvid}/"
        else:
            # Last-resort: bilibili search results page for the title prefix
            href = (f"https://search.bilibili.com/all?keyword="
                    f"{urllib.parse.quote(v['title'][:20])}")
    else:
        href = bing_link(v["title"])
    return (f'<li seq="auto"><a href="{href}">{title_esc}</a> '
            f'｜频道：{escape(v["channel"])} '
            f'｜播放：{v["views"]} '
            f'｜时长：{v["duration"]} '
            f'｜上传：{v["uploaded"]}</li>')


def build_xml(date: str, slot: str,
              long_top10: list[dict],
              short_top5: list[dict],
              recent_top10: list[dict]) -> str:
    slot_cn = {"am": "早间档", "pm": "晚间档"}[slot]
    lines: list[str] = []
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

    ts = datetime.now().strftime("%Y-%m-%d %H:%M CST")
    lines.append(f'<text color="gray">⚠️ 数据获取时间：{ts} '
                 f'| 数据来源：Bing视频搜索 + Bilibili '
                 f'（YouTube网络不可达 HTTP 000）</text>')
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
    # Example wiring — replace with real Bing+bilibili data.
    long_top10: list[dict] = []
    short_top5: list[dict] = []
    recent_top10: list[dict] = []
    merged, dated = write("2026-06-11", "am",
                          long_top10=long_top10,
                          short_top5=short_top5,
                          recent_top10=recent_top10)
    print(f"wrote: {merged}\nwrote: {dated}")