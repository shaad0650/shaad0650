"""Scrape the public contribution calendar (no token needed).
Usage: GH_USER=yourname python scripts/fetch_contributions.py   (or pass username as arg)"""
import json, os, re, sys
from datetime import date, timedelta
import requests
from bs4 import BeautifulSoup

user = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GH_USER")
if not user:
    sys.exit("Set GH_USER or pass the username as an argument")

r = requests.get(f"https://github.com/users/{user}/contributions",
                 headers={"User-Agent": "Mozilla/5.0 profile-heatmap"}, timeout=30)
r.raise_for_status()
soup = BeautifulSoup(r.text, "html.parser")
tips = {t.get("for"): t.get_text(" ", strip=True) for t in soup.find_all("tool-tip")}

days = []
for td in soup.select("td.ContributionCalendar-day"):
    d = td.get("data-date")
    if not d:
        continue
    m = re.match(r"(\d+)", tips.get(td.get("id"), ""))
    days.append({"date": d, "count": int(m.group(1)) if m else 0, "level": int(td.get("data-level", 0))})
days.sort(key=lambda x: x["date"])
if not days:
    sys.exit("No contribution cells parsed - GitHub markup may have changed")

counts = {x["date"]: x["count"] for x in days}
# longest streak
longest = run = 0
prev = None
for x in days:
    dt = date.fromisoformat(x["date"])
    if x["count"] > 0:
        run = run + 1 if prev and (dt - prev).days == 1 else 1
        longest = max(longest, run)
        prev = dt
    else:
        run, prev = 0, None
# current streak (today may still be empty)
cur, d = 0, date.fromisoformat(days[-1]["date"])
if counts.get(d.isoformat(), 0) == 0:
    d -= timedelta(days=1)
while counts.get(d.isoformat(), 0) > 0:
    cur += 1
    d -= timedelta(days=1)
best = max(days, key=lambda x: x["count"])
months = {}
for x in days:
    months[x["date"][:7]] = months.get(x["date"][:7], 0) + x["count"]

os.makedirs("data", exist_ok=True)
json.dump({"user": user, "total": sum(counts.values()), "current_streak": cur, "longest_streak": longest,
           "best_day": best, "monthly": months, "days": days}, open("data/contributions.json", "w"), indent=1)
print(f"{user}: {sum(counts.values())} contributions, streak {cur}, longest {longest}")
