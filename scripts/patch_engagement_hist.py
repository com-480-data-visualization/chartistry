"""
Patch data.json with per-combo avg_likes, avg_comments, and days_to_trend_hist.
Run from the project root: python3 scripts/patch_engagement_hist.py
"""
import json
import csv
from datetime import datetime
from collections import defaultdict

COUNTRIES = ['CA', 'DE', 'FR', 'GB', 'IN', 'JP', 'KR', 'MX', 'RU', 'US']
HIST_MAX_DAY = 30  # bucket "30+" catches everything beyond


def parse_days(publish_time, trending_date):
    """Return days from publish to trending, or None on parse failure."""
    try:
        pub = datetime.fromisoformat(publish_time.replace('Z', '+00:00'))
        # trending_date format: YY.DD.MM  (e.g. 17.14.11 = 2017-Nov-14)
        yy, dd, mm = trending_date.split('.')
        trend = datetime(2000 + int(yy), int(mm), int(dd))
        diff = (trend - datetime(pub.year, pub.month, pub.day)).days
        return max(0, diff)
    except Exception:
        return None


def build_histogram(days_list, max_day=HIST_MAX_DAY):
    counts = defaultdict(int)
    for d in days_list:
        counts[min(d, max_day)] += 1
    return [{"day": d, "count": counts.get(d, 0)} for d in range(max_day + 1)]


# Load category mappings
cat_maps = {}
for c in COUNTRIES:
    try:
        with open(f"data/{c}_category_id.json") as f:
            raw = json.load(f)
            cat_maps[c] = {str(item["id"]): item["snippet"]["title"]
                           for item in raw["items"]}
    except Exception as e:
        print(f"Warning: could not load category map for {c}: {e}")
        cat_maps[c] = {}

# Accumulate per-combo stats from raw CSVs
stats = defaultdict(lambda: {"likes": [], "comments": [], "days": []})

for c in COUNTRIES:
    path = f"data/{c}videos.csv"
    print(f"Reading {path} ...")
    try:
        with open(path, encoding="latin1") as f:
            for row in csv.DictReader(f):
                cat_id = row.get("category_id", "").strip()
                category = cat_maps[c].get(cat_id)
                if not category:
                    continue
                try:
                    views    = int(row["views"])
                    likes    = int(row["likes"])
                    comments = int(row["comment_count"])
                except (ValueError, KeyError):
                    continue
                if views < 1000:
                    continue
                days = parse_days(
                    row.get("publish_time", ""),
                    row.get("trending_date", ""),
                )
                key = (c, category)
                stats[key]["likes"].append(likes)
                stats[key]["comments"].append(comments)
                if days is not None and days <= 90:
                    stats[key]["days"].append(days)
    except Exception as e:
        print(f"  Error: {e}")

# Load and patch data.json
print("Loading data.json ...")
with open("public/data.json") as f:
    data = json.load(f)

patched = 0
for c in COUNTRIES:
    if c not in data["by_country_category"]:
        continue
    for category, combo in data["by_country_category"][c].items():
        key = (c, category)
        s = stats.get(key)
        if not s:
            continue
        combo["avg_likes"]         = int(sum(s["likes"])    / len(s["likes"]))    if s["likes"]    else 0
        combo["avg_comments"]      = int(sum(s["comments"]) / len(s["comments"])) if s["comments"] else 0
        combo["days_to_trend_hist"] = build_histogram(s["days"]) if s["days"] else []
        patched += 1

print(f"Patched {patched} combos.")
print("Writing data.json ...")
with open("public/data.json", "w") as f:
    json.dump(data, f, separators=(",", ":"))
print("Done.")
