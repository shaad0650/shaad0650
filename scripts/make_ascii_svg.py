"""Convert source-prepped.png into a self-typing monochrome ASCII SVG.
Usage: python scripts/make_ascii_svg.py [--dark]
  default : dark pixels -> dense glyphs (ink-on-paper look)
  --dark  : bright pixels -> dense glyphs (looks right on dark GitHub themes)"""
import os
import sys
from PIL import Image

COLS = 120
FONT = 10                      # px
CW = FONT * 0.6                # monospace char width
LH = FONT * 1.2                # line height
X_SCALE = 0.92
RAMP = " .`:-=+*cs#%@"         # sparse -> dense
INK = "#c9d1d9"
ROW_DELAY, WIPE = 0.07, 0.55   # stagger between rows, wipe duration (s)
dark = "--dark" in sys.argv

img = Image.open("source-prepped.png").convert("L")
w, h = img.size
rows = max(1, round(h / w * COLS * (CW / LH)))
img = img.resize((COLS, rows), Image.LANCZOS)
mask = None
if os.path.exists("source-mask.png"):
    mask = Image.open("source-mask.png").convert("L").resize((COLS, rows), Image.LANCZOS)

lines = []
for y in range(rows):
    s = ""
    for x in range(COLS):
        if mask is not None and mask.getpixel((x, y)) < 100:
            s += " "
            continue
        v = img.getpixel((x, y))
        d = (v / 255.0) if dark else ((255 - v) / 255.0)
        if not dark and v >= 250:
            d = 0
        s += RAMP[min(len(RAMP) - 1, int(d * len(RAMP)))]
    lines.append(s.rstrip())

W, H = COLS * CW, rows * LH
PAD = 12
X_OFFSET = PAD + W * (1 - X_SCALE) / 2
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W*X_SCALE+2*PAD:.0f} {H+2*PAD:.0f}" width="{W*X_SCALE+2*PAD:.0f}" height="{H+2*PAD:.0f}">',
     '<defs>']
for i in range(rows):
    t = i * ROW_DELAY
    o.append(f'<clipPath id="c{i}"><rect x="0" y="{i*LH:.1f}" width="0" height="{LH:.1f}">'
             f'<animate attributeName="width" from="0" to="{W:.0f}" begin="{t:.2f}s" dur="{WIPE}s" fill="freeze"/></rect></clipPath>')
o.append('</defs>')
o.append(f'<g transform="translate({X_OFFSET:.1f},{PAD}) scale({X_SCALE},1)" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="{FONT}" fill="{INK}" xml:space="preserve">')
for i, ln in enumerate(lines):
    if not ln.strip():
        continue
    t = i * ROW_DELAY
    y = i * LH + FONT
    esc = ln.replace("&", "&amp;").replace("<", "&lt;")
    o.append(f'<text x="0" y="{y:.1f}" textLength="{len(ln)*CW:.1f}" lengthAdjust="spacing" clip-path="url(#c{i})">{esc}</text>')
    o.append(f'<rect x="0" y="{i*LH+1:.1f}" width="{CW:.1f}" height="{LH-2:.1f}" fill="{INK}" opacity="0">'
             f'<animate attributeName="x" from="0" to="{W:.0f}" begin="{t:.2f}s" dur="{WIPE}s" fill="freeze"/>'
             f'<set attributeName="opacity" to="0.9" begin="{t:.2f}s"/>'
             f'<set attributeName="opacity" to="0" begin="{t+WIPE:.2f}s"/></rect>')
o.append('</g></svg>')
open("avi-ascii.svg", "w").write("\n".join(o))
print(f"wrote avi-ascii.svg ({COLS}x{rows} chars)")
