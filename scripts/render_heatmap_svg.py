"""Render data/contributions.json as an animated 53x7 heatmap SVG."""
import json
from datetime import date

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
CELL, GAP, X0, Y0 = 12, 3, 40, 44
W, H = 860, 196
data = json.load(open("data/contributions.json"))
days = data["days"]
top = max(d["count"] for d in days) or 1

first = date.fromisoformat(days[0]["date"])
offset = (first.weekday() + 1) % 7            # Sunday = row 0
cells, month_labels, last_month = [], [], None
for i, d in enumerate(days):
    col, row = (i + offset) // 7, (i + offset) % 7
    lvl = d["level"]
    if lvl >= 4 and d["count"] >= 0.75 * top:
        lvl = 5                                # neon top end
    dt = date.fromisoformat(d["date"])
    if row == 0 and dt.month != last_month:
        month_labels.append((col, dt.strftime("%b")))
        last_month = dt.month
    delay = (col + row) * 0.022
    x, y = X0 + col * (CELL + GAP), Y0 + row * (CELL + GAP)
    cells.append(f'<rect class="c" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{PALETTE[lvl]}" style="animation-delay:{delay:.2f}s"><title>{d["count"]} on {d["date"]}</title></rect>')

o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
     '<style>text{font:11px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:#8b949e}'
     '.c{opacity:0;animation:pop .45s ease-out forwards}'
     '@keyframes pop{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:none}}</style>',
     f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="#0d1117" stroke="#30363d"/>']
for col, name in month_labels:
    o.append(f'<text x="{X0 + col*(CELL+GAP)}" y="34">{name}</text>')
for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
    o.append(f'<text x="8" y="{Y0 + row*(CELL+GAP) + 10}">{name}</text>')
o += cells
ly = H - 22
o.append(f'<text x="{X0}" y="{ly+9}">{data["total"]:,} contributions in the last year  |  streak {data["current_streak"]}d  |  longest {data["longest_streak"]}d</text>')
lx = W - 40 - 6 * (CELL + 4) - 70
o.append(f'<text x="{lx}" y="{ly+9}">Less</text>')
for i, c in enumerate(PALETTE):
    o.append(f'<rect x="{lx+34+i*(CELL+4)}" y="{ly}" width="{CELL}" height="{CELL}" rx="3" fill="{c}"/>')
o.append(f'<text x="{lx+34+6*(CELL+4)+4}" y="{ly+9}">More</text>')
o.append('</svg>')
open("contrib-heatmap.svg", "w").write("\n".join(o))
print("wrote contrib-heatmap.svg")
