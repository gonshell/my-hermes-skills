#!/usr/bin/env python3
"""
Render a local HTML file to a single PNG image using headless Chrome + Pillow crop.

Usage:
  python3 render_html_to_image.py <input.html> <output.png> [--width 1100] [--scale 2]

Defaults:
  --width 1100   logical page width
  --scale 2      device scale factor (retina)
  --bg auto      background color for crop detection (auto-sample from corner if 'auto')

Auto-detects macOS Chrome. Linux fallback: chromium / google-chrome / chrome in PATH.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image


def find_chrome() -> str:
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
        "/Applications/Chromium.app/Contents/MacOS/Chromium",           # macOS Chromium
        shutil.which("google-chrome"),
        shutil.which("chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("msedge"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    raise SystemExit("No Chrome/Chromium found. Install Google Chrome or set PATH.")


def render(html_path: Path, out_path: Path, width: int, scale: int, height: int = 4000) -> None:
    chrome = find_chrome()
    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        f"--force-device-scale-factor={scale}",
        f"--screenshot={out_path}",
        f"file://{html_path}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    # macOS-headless noise: task_policy / CVDisplayLink errors are fine.
    if not out_path.exists() or out_path.stat().st_size == 0:
        print("Chrome stderr/stdout:", proc.stderr[-500:], proc.stdout[-500:], file=sys.stderr)
        raise SystemExit(f"Chrome produced no output at {out_path}")


def crop_to_content(img: Image.Image, bg: tuple) -> Image.Image:
    w, h = img.size
    # Sample the top-left corner for "auto" background, otherwise use provided bg.
    if bg is None:
        bg = img.getpixel((10, 10))
        if isinstance(bg, int):  # grayscale
            bg = (bg, bg, bg)
        else:
            bg = tuple(bg[:3])
    last = 0
    for y in range(h - 1, -1, -5):
        row = img.crop((100, y, w - 100, y + 1))
        non_bg = sum(
            1 for p in row.getdata()
            if abs(p[0]-bg[0])+abs(p[1]-bg[1])+abs(p[2]-bg[2]) > 15
        )
        if non_bg > 5:
            last = y
            break
    return img.crop((0, 0, w, min(last + 30, h)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--width", type=int, default=1100)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--bg", default="auto", help="background color for crop, 'auto' to sample")
    args = ap.parse_args()

    html = args.html.resolve()
    out = args.out.resolve()
    if not html.exists():
        raise SystemExit(f"HTML not found: {html}")

    bg = None
    if args.bg != "auto":
        parts = [int(x) for x in args.bg.split(",")]
        bg = tuple(parts) + (0,) * (3 - len(parts))
        bg = bg[:3]

    # 1. Render (overestimate height; crop will trim)
    render(html, out, args.width, args.scale, height=5000)
    # 2. Crop
    img = Image.open(out)
    final = crop_to_content(img, bg)
    final.save(out, optimize=True)
    print(f"OK {out} ({final.size[0]}x{final.size[1]}, {out.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()