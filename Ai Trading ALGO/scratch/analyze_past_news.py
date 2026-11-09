import json
from datetime import datetime

with open("../ff_calendar_cache.json", "r", encoding="utf-8") as f:
    events = json.load(f)

print("=" * 90)
print("PAST ECONOMIC CALENDAR & HIGH-VOLATILITY RELEASES (LAST WEEK & MONTH)")
print("=" * 90)

high_medium = [e for e in events if e.get("impact") in ["High", "Medium"]]

for e in high_medium:
    d = e.get("date", "")[:16].replace("T", " ")
    country = e.get("country", "")
    impact = e.get("impact", "")
    title = e.get("title", "")
    forecast = e.get("forecast", "-")
    prev = e.get("previous", "-")
    print(f"{d} | [{country:<3}] {impact:<6} | {title:<40} | F: {forecast:<7} | P: {prev}")

print("=" * 90)
