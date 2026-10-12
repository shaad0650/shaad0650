"""Hand-authored neofetch-style info card. EDIT THE CONFIG BLOCK, then run:
    python scripts/make_info_card.py          # animated
    STATIC=1 python scripts/make_info_card.py # frozen frame for previews"""
import os
from html import escape

# ---------------- CONFIG ----------------
USER, HOST = "shad", "github"
ROWS = [  # (key, [lines])  keep each line <= ~42 chars
    ("Now",        ["Backend Intern @ Harman International", "Building AI agents for test-bench work"]),
    ("Edu",        ["IIIT DM Jabalpur, class of 2027"]),
    ("Stack",      ["Node.js, TypeScript, Next.js", "PostgreSQL/PostGIS, Redis", "Socket.io, React Native/Expo"]),
    ("Highlights", ["Built a Python/SVG GitHub profile", "Animated ASCII art + auto-updated heatmap"]),
]
KEY_COLORS = ["#58a6ff", "#d2a8ff", "#7ee787", "#ffa657"]
# ----------------------------------------
STATIC = os.environ.get("STATIC") == "1"
W, LH, X0, X1 = 490, 22, 24, 130
y = 84
body, delay = [], 0.2
body.append(f'<text x="{X0}" y="62" class="l" style="--d:{delay:.2f}s"><tspan fill="#7ee787" font-weight="bold">{escape(USER)}@{escape(HOST)}</tspan></text>')
body.append(f'<text x="{X0}" y="78" class="l" style="--d:{delay+.1:.2f}s" fill="#484f58">{"-"*(len(USER)+len(HOST)+1)}</text>')
y = 102
for i, (k, lines) in enumerate(ROWS):
    for j, ln in enumerate(lines):
        delay += 0.18
        key = f'<tspan fill="{KEY_COLORS[i % len(KEY_COLORS)]}" font-weight="bold">{escape(k)}</tspan>' if j == 0 else ""
        body.append(f'<text x="{X0}" y="{y}" class="l" style="--d:{delay:.2f}s">{key}'
                    f'<tspan x="{X1}" fill="#c9d1d9">{escape(ln)}</tspan></text>')
        y += LH
    y += 8
H = y + 10
anim = "" if STATIC else ".l{opacity:0;animation:in .5s ease-out forwards;animation-delay:var(--d)}@keyframes in{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}"
static_css = ".l{opacity:1}" if STATIC else ""
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<style>text{{font:13px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}{anim}{static_css}</style>
<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="#0d1117" stroke="#30363d"/>
<rect x="0.5" y="0.5" width="{W-1}" height="30" rx="10" fill="#161b22"/><rect x="0.5" y="20" width="{W-1}" height="11" fill="#161b22"/>
<circle cx="20" cy="16" r="5" fill="#ff5f56"/><circle cx="38" cy="16" r="5" fill="#ffbd2e"/><circle cx="56" cy="16" r="5" fill="#27c93f"/>
<text x="{W/2}" y="20" text-anchor="middle" fill="#8b949e" style="font-size:12px">neofetch</text>
{chr(10).join(body)}
</svg>'''
open("info-card.svg", "w").write(svg)
print("wrote info-card.svg")
