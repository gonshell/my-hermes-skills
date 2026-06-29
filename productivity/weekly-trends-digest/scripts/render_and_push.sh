#!/usr/bin/env bash
# weekly-trends-digest/scripts/render_and_push.sh
#
# Render an HTML digest to PNG, then push to Feishu via lark-cli.
# Implements the §8/§9 caveats from lark-pitfalls (CWD-relative path + retry-once).
#
# Usage:
#   ./render_and_push.sh <input.html> <output.png> <feishu_open_id>
#
# Example:
#   ./render_and_push.sh weekly-2026-W26.html weekly-2026-W26.png ou_xxxx
#
# Output (after success):
#   - Writes <output.png> to the same dir as <input.html>
#   - Sends the PNG to the given Feishu open_id
#   - Prints message_id + chat_id on stdout (last line)
#
# Exit codes:
#   0 = pushed successfully
#   1 = render failed
#   2 = Feishu push failed after retry
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "usage: $0 <input.html> <output.png> <feishu_open_id>" >&2
  exit 1
fi

INPUT_HTML="$1"
OUTPUT_PNG="$2"
FEISHU_OPEN_ID="$3"

# Resolve to absolute paths (lark-cli requires CWD-relative paths)
INPUT_HTML="$(cd "$(dirname "$INPUT_HTML")" && pwd)/$(basename "$INPUT_HTML")"
INPUT_DIR="$(dirname "$INPUT_HTML")"
OUTPUT_PNG="$(cd "$(dirname "$OUTPUT_PNG")" && pwd)/$(basename "$OUTPUT_PNG")"

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# --- Step 1: render HTML to PNG -----------------------------------------------
echo "[1/2] Rendering HTML to PNG..."
echo "  in:  $INPUT_HTML"
echo "  out: $OUTPUT_PNG"

"$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --window-size=900,2200 --force-device-scale-factor=2 \
  --screenshot="$OUTPUT_PNG" \
  "file://$INPUT_HTML" 2>&1 | tail -2

if [[ ! -f "$OUTPUT_PNG" ]]; then
  echo "ERROR: Chrome did not write $OUTPUT_PNG" >&2
  exit 1
fi

# --- Step 1b: Pillow crop bottom whitespace ----------------------------------
echo "[1b]  Cropping bottom whitespace..."
python3 - <<PYEOF
from PIL import Image
im = Image.open("$OUTPUT_PNG")
bg = (15, 17, 21)
w, h = im.size
last = 0
for y in range(h - 1, -1, -5):
    row = im.crop((100, y, w - 100, y + 1))
    pixels = list(row.getdata())
    non_bg = sum(1 for p in pixels if abs(p[0]-bg[0])+abs(p[1]-bg[1])+abs(p[2]-bg[2]) > 15)
    if non_bg > 5:
        last = y
        break
cropped = im.crop((0, 0, w, min(last + 30, h)))
cropped.save("$OUTPUT_PNG")
print(f"  cropped: {cropped.size}")
PYEOF

# --- Step 2: push to Feishu (with retry-once per §9) -------------------------
echo "[2/2] Pushing to Feishu..."
cd "$INPUT_DIR"

# First attempt
if lark-cli im +messages-send --user-id "$FEISHU_OPEN_ID" \
    --image "./$(basename "$OUTPUT_PNG")" 2>&1 | tee /tmp/lark_push.log; then
  echo "  push OK (first try)"
else
  echo "  first try failed, retrying once per lark-pitfalls §9..."
  sleep 2
  if ! lark-cli im +messages-send --user-id "$FEISHU_OPEN_ID" \
      --image "./$(basename "$OUTPUT_PNG")" 2>&1 | tee /tmp/lark_push.log; then
    echo "ERROR: Feishu push failed twice. Check /tmp/lark_push.log" >&2
    exit 2
  fi
  echo "  push OK (retry)"
fi

echo "done."