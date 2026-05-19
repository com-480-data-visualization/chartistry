#!/usr/bin/env python3
"""Generates analysis/precompute.ipynb — the data pipeline notebook."""
from pathlib import Path
import nbformat as nbf

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.10.0"},
}

def md(src): return nbf.v4.new_markdown_cell(src)
def code(src): return nbf.v4.new_code_cell(src)

cells = []

# ── TITLE ──────────────────────────────────────────────────────
cells.append(md("""\
# Chartistry — Precompute Pipeline

Produces `website/public/data.json` — the single file powering all website interactivity.

**Run from the `chartistry/` root directory.**

| Step | What it computes |
|------|-----------------|
| 1 | Load + preprocess all country CSVs |
| 2 | Text features (caps, emojis, word count) |
| 3 | Hook labels from LLM classification (if available) |
| 4 | Global stats → choropleth + heatmaps |
| 5 | Per (country × category) stats → word freq, emojis, timing, examples |
| 6 | Export + validate |
"""))

# ── CELL 1: SETUP ──────────────────────────────────────────────
cells.append(md("## Step 1 — Setup"))

cells.append(code("""\
%pip install -q pandas numpy emoji tqdm nltk
"""))

cells.append(code("""\
import os, json, re, warnings
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd
import emoji as emoji_lib
from tqdm.auto import tqdm

import nltk
nltk.download("stopwords", quiet=True)
from nltk.corpus import stopwords

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", None)

# ── Paths (notebook runs from analysis/, so go up one level) ──
ROOT     = Path("..").resolve()   # → chartistry/
DATA_DIR = ROOT / "data"
OUT_DIR  = ROOT / "public"
HOOK_LABELS_PATH = ROOT / "code" / "text_analysis" / "data" / "hook_labels_elite.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────
COUNTRY_NAMES = {
    "CA": "Canada",  "DE": "Germany", "FR": "France",
    "GB": "UK",      "IN": "India",   "JP": "Japan",
    "KR": "S. Korea","MX": "Mexico",  "RU": "Russia",
    "US": "USA",
}
COUNTRY_FLAGS = {
    "CA": "🇨🇦", "DE": "🇩🇪", "FR": "🇫🇷", "GB": "🇬🇧", "IN": "🇮🇳",
    "JP": "🇯🇵", "KR": "🇰🇷", "MX": "🇲🇽", "RU": "🇷🇺", "US": "🇺🇸",
}

# ── Stopwords (multi-language) ─────────────────────────────────
ALL_STOPS = set()
for lang in ["english","french","german","spanish","portuguese","russian"]:
    try: ALL_STOPS.update(stopwords.words(lang))
    except: pass

CUSTOM_STOPS = {
    "official","video","ft","feat","new","full","episode","ep","season",
    "series","part","vs","der","die","das","und","fur","ein","ist",
    "auf","auch","mit","von","les","des","une","pour","avec",
}
ALL_STOPS.update(CUSTOM_STOPS)

# ── Sampling constants (MUST match text_analysis.ipynb) ────────
LLM_CLOSED_SAMPLE = 500
RANDOM_SEED       = 42

print("✅ Setup complete")
print(f"   Data dir  : {DATA_DIR.resolve()}")
print(f"   Output    : {OUT_DIR.resolve()}")
print(f"   Stopwords : {len(ALL_STOPS)} words")
print(f"   Hook file : {'✅ found' if HOOK_LABELS_PATH.exists() else '⚠️  not found (hook examples will be empty)'}")
"""))

# ── CELL 2: LOAD ───────────────────────────────────────────────
cells.append(md("## Step 2 — Load & Preprocess"))

cells.append(code("""\
def smart_read_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "cp949", "shift-jis"):
        try:
            return pd.read_csv(path, encoding=enc, on_bad_lines="skip")
        except Exception:
            pass
    return pd.read_csv(path, encoding="latin-1", on_bad_lines="skip")


def load_category_map(data_dir: Path) -> dict:
    cat_map = {}
    for jf in data_dir.glob("*_category_id.json"):
        country = jf.stem[:2].upper()
        try:
            data = json.loads(jf.read_bytes().decode("utf-8", errors="replace"))
            for item in data.get("items", []):
                cat_map[(country, int(item["id"]))] = item["snippet"]["title"]
        except Exception:
            pass
    return cat_map


# Load all country files
dfs = []
for csv_path in sorted(DATA_DIR.glob("*videos.csv")):
    country = csv_path.stem[:2].upper()
    df_c = smart_read_csv(csv_path)
    df_c["country"] = country
    dfs.append(df_c)
    print(f"  [{country}] {len(df_c):,} rows")

df_raw   = pd.concat(dfs, ignore_index=True)
cat_map  = load_category_map(DATA_DIR)
print(f"\\n✅ Raw: {df_raw.shape[0]:,} rows from {df_raw['country'].nunique()} countries")
"""))

cells.append(code("""\
# Decode double-encoded strings (Cyrillic, CJK, etc.)
from ftfy import fix_text
import re

def smart_fix(x):
    if not isinstance(x, str):
        return x
    fixed = fix_text(x)
    if re.search(r'Ã|Ð|√|¬', fixed):
        try:
            fixed = fixed.encode('latin1').decode('utf-8')
            fixed = fix_text(fixed)
        except:
            pass
    return fixed

# ── Normalize & clean ──────────────────────────────────────────
df = df_raw.copy()
df = df.rename(columns={"view_count": "views", "like_count": "likes"})

for col in ["title", "tags", "description", "channel_title"]:
    df[col] = df.get(col, pd.Series("", index=df.index)).fillna("").astype(str)

print("Fixing double-encodings in titles...")
df["title"] = df["title"].apply(smart_fix)

for col in ["views", "likes", "dislikes", "comment_count", "category_id"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Category name
def resolve_category(row):
    return (cat_map.get((row["country"], row["category_id"]))
            or cat_map.get(("US", row["category_id"]), "Unknown"))

df["category_name"] = df.apply(resolve_category, axis=1)

# Dates
df["trending_date"] = pd.to_datetime(
    df["trending_date"].astype(str).str.strip(), format="%y.%d.%m", errors="coerce"
)
df["publish_time"] = pd.to_datetime(df["publish_time"], errors="coerce", utc=True)
df["publish_time"] = df["publish_time"].dt.tz_convert(None)

df["publish_hour"]  = df["publish_time"].dt.hour
df["publish_day"]   = df["publish_time"].dt.day_name()
df["days_to_trending"] = (df["trending_date"] - df["publish_time"]).dt.days

# Dedup: keep peak-trending row per video+country
df = (df.sort_values("views", ascending=False)
        .drop_duplicates(subset=["video_id", "country"])
        .reset_index(drop=True))

# Engagement
df["views"]         = df["views"].fillna(0).clip(lower=1)
df["likes"]         = df["likes"].fillna(0)
df["comment_count"] = df["comment_count"].fillna(0)
df["engagement_ratio"] = (df["likes"] + df["comment_count"]) / df["views"]

print(f"✅ Preprocessed: {df.shape[0]:,} rows")
print(f"   Countries : {sorted(df['country'].unique())}")
print(f"   Categories: {df['category_name'].nunique()} unique (excl. Unknown)")
df.head(2)
"""))

# ── CELL 3: TEXT FEATURES ──────────────────────────────────────
cells.append(md("## Step 3 — Text Features"))

cells.append(code("""\
def caps_ratio(s: str) -> float:
    alpha = [c for c in str(s) if c.isalpha()]
    return sum(1 for c in alpha if c.isupper()) / len(alpha) if alpha else 0.0

df["title_len"]     = df["title"].str.len()
df["word_count"]    = df["title"].str.split().str.len().fillna(0).astype(int)
df["caps_ratio"]    = df["title"].map(caps_ratio)
df["emoji_count"]   = df["title"].map(lambda s: emoji_lib.emoji_count(str(s)))
df["punct_density"] = df["title"].str.count(r"[!?…]") / df["title_len"].clip(lower=1)
df["has_number"]    = df["title"].str.contains(r"\\d+", regex=True).astype(int)

print("✅ Text features added")
df[["title","title_len","caps_ratio","emoji_count","punct_density"]].head(3)
"""))

# ── CELL 4: HOOK LABELS ────────────────────────────────────────
cells.append(md("## Step 4 — Hook Labels (from LLM classification)"))

cells.append(code("""\
hook_lookup = {}
hook_stats  = {}

if HOOK_LABELS_PATH.exists():
    hook_lookup = json.loads(HOOK_LABELS_PATH.read_text())
    
    # We want to know the distribution for the ELITE (Top 100) specifically
    # Re-create the elite_df (Top 100 per Ctry/Cat)
    elite_df = (df.groupby(["country", "category_name"], group_keys=False)
                .apply(lambda g: g.head(100))
                .reset_index(drop=True))
    
    # Map each video in elite_df to its hook
    elite_df["hook"] = elite_df["title"].map(lambda t: hook_lookup.get(t, {}).get("category"))
    
    # Pre-calculate distributions for each combo
    hook_stats = (elite_df.groupby(["country", "category_name"])["hook"]
                  .value_counts(normalize=True)
                  .unstack(fill_value=0)
                  .to_dict(orient="index"))
    
    print(f"✅ Hook analytics ready for {len(hook_stats)} combinations")
    print(f"   Total labelled in elite sample: {elite_df['hook'].notna().sum()}")
else:
    print("⚠️  Hook labels file not found — hook distributions will be empty")
"""))

# ── CELL 5: HELPERS ────────────────────────────────────────────
cells.append(md("## Step 5 — Helper Functions"))

cells.append(code("""\
# Regex covering Latin, Cyrillic, CJK, Hangul, Hiragana/Katakana
_WORD_PATTERN = re.compile(
    r"[a-zA-ZÀ-ÿА-яёЁ"
    r"\\u4e00-\\u9fff"   # CJK unified
    r"\\uac00-\\ud7a3"  # Hangul
    r"\\u3040-\\u30ff"  # Hiragana + Katakana
    r"]{2,}"
)

def get_top_words(titles: list, n: int = 30) -> list:
    words = []
    for title in titles:
        for tok in _WORD_PATTERN.findall(str(title).lower()):
            if tok not in ALL_STOPS and len(tok) >= 2:
                words.append(tok)
    return [{"text": w, "freq": c} for w, c in Counter(words).most_common(n)]


def get_top_emojis(titles: list, n: int = 10) -> list:
    all_emojis = [e["emoji"] for t in titles for e in emoji_lib.emoji_list(str(t))]
    return [{"emoji": e, "count": c} for e, c in Counter(all_emojis).most_common(n)]


def get_timing_heatmap(grp: pd.DataFrame) -> list:
    valid = grp.dropna(subset=["publish_day","publish_hour","views"])
    if valid.empty:
        return []
    hm = (valid.groupby(["publish_day","publish_hour"])["views"]
          .mean().reset_index())
    return [
        {"day": row["publish_day"], "hour": int(row["publish_hour"]),
         "avg_views": round(row["views"])}
        for _, row in hm.iterrows()
    ]


def get_hook_examples(country: str, category: str) -> list:
    if not hook_lookup:
        return []
    # Fetch all classified videos from the elite Top 100 for perfect alignment with distribution
    sub_elite = elite_df[
        (elite_df["country"] == country) & 
        (elite_df["category_name"] == category) & 
        elite_df["hook"].notna()
    ]
    results = []
    for _, row in sub_elite.iterrows():
        results.append({
            "title":    row["title"],
            "hook":     row["hook"],
            "video_id": row["video_id"],
            "views":    int(row["views"])
        })
    return results


def get_top_videos(grp: pd.DataFrame, n: int = 50) -> list:
    top = grp.nlargest(n, "views")
    return [
        {"video_id": row["video_id"], "title": row["title"],
         "channel": row["channel_title"], "views": int(row["views"]),
         "pub": row["publish_time"].strftime("%Y-%m-%dT%H:%M:%SZ") if pd.notna(row.get("publish_time")) else ""}
        for _, row in top.iterrows()
    ]


def best_timing(timing_hm: list):
    if not timing_hm:
        return None, None
    best = max(timing_hm, key=lambda x: x["avg_views"])
    return best["day"], best["hour"]


print("✅ Helper functions ready")
"""))

# ── CELL 6: GLOBAL STATS ───────────────────────────────────────
cells.append(md("## Step 6 — Global Stats"))

cells.append(code("""\
# Per-country summary (for world choropleth)
global_by_country = {}
for country, grp in df.groupby("country"):
    cat_dist = (
        grp["category_name"].value_counts(normalize=True)
        .head(10).mul(100).round(1).to_dict()
    )
    global_by_country[country] = {
        "name":                 COUNTRY_NAMES.get(country, country),
        "flag":                 COUNTRY_FLAGS.get(country, ""),
        "total_videos":         len(grp),
        "avg_views":            round(grp["views"].mean()),
        "median_views":         round(grp["views"].median()),
        "avg_days_to_trending": round(grp["days_to_trending"].dropna().mean(), 1),
        "top_category":         grp["category_name"].value_counts().index[0],
        "category_distribution": cat_dist,
    }

# Avg views heatmap: country × category
views_hm_raw = (df.groupby(["country","category_name"])["views"].mean().reset_index())
views_heatmap = {}
for _, row in views_hm_raw.iterrows():
    views_heatmap.setdefault(row["country"], {})[row["category_name"]] = round(row["views"])

# Count heatmap: country × category (number of trending videos)
count_hm_raw = (df.groupby(["country","category_name"]).size().reset_index(name="count"))
count_heatmap = {}
for _, row in count_hm_raw.iterrows():
    count_heatmap.setdefault(row["country"], {})[row["category_name"]] = int(row["count"])

# Engagement heatmap: like+comment ratio
engage_hm_raw = (df.groupby(["country","category_name"])["engagement_ratio"].mean().reset_index())
engage_heatmap = {}
for _, row in engage_hm_raw.iterrows():
    engage_heatmap.setdefault(row["country"], {})[row["category_name"]] = round(row["engagement_ratio"], 4)

countries  = sorted(df["country"].unique().tolist())
categories = sorted(df[df["category_name"] != "Unknown"]["category_name"].unique().tolist())

# UTC publish-hour share (global map "Publication time" mode)
_ph = df.dropna(subset=["publish_hour"]).copy()
_ph["publish_hour"] = _ph["publish_hour"].astype(int)
_hour_tab = _ph.groupby(["country", "publish_hour"]).size().unstack(fill_value=0)
_hour_tab = _hour_tab.reindex(columns=list(range(24)), fill_value=0)
_hour_tab = _hour_tab.reindex(index=countries, fill_value=0)
_hour_pct = _hour_tab.div(_hour_tab.sum(axis=1), axis=0).replace([float("inf"), float("-inf")], 0).fillna(0) * 100
publish_hour_share = {}
for h in range(24):
    publish_hour_share[str(h)] = {c: round(float(_hour_pct.loc[c, h]), 4) for c in countries}
_flat_ph = [publish_hour_share[str(h)][c] for h in range(24) for c in countries]
publish_hour_zmax = min(100.0, max(max(_flat_ph) * 1.05, 1.0)) if _flat_ph else 10.0

print(f"✅ Global stats computed")
print(f"   {len(countries)} countries × {len(categories)} categories")
print(f"   Country list: {countries}")
"""))

# ── CELL 7: PER-COMBO STATS ────────────────────────────────────
cells.append(md("## Step 7 — Per (Country × Category) Stats"))

cells.append(code("""\
by_country_category = {}
combos = list(df.groupby(["country","category_name"]))

for (country, category), grp in tqdm(combos, desc="Computing combos"):
    titles       = grp["title"].tolist()
    top_words    = get_top_words(titles, n=30)
    top_emojis   = get_top_emojis(titles, n=10)
    timing_hm    = get_timing_heatmap(grp)
    hook_examples= get_hook_examples(country, category)
    top_videos   = get_top_videos(grp, n=50)
    best_day, best_hour = best_timing(timing_hm)

    by_country_category.setdefault(country, {})[category] = {
        # Size
        "video_count":       len(grp),
        # Engagement
        "avg_views":         round(grp["views"].mean()),
        "median_views":      round(grp["views"].median()),
        "engagement_ratio":  round(grp["engagement_ratio"].mean(), 4),
        # Text style
        "caps_ratio_avg":    round(grp["caps_ratio"].mean(), 3),
        "emoji_count_avg":   round(grp["emoji_count"].mean(), 2),
        "title_len_avg":     round(grp["title_len"].mean(), 1),
        "punct_density_avg": round(grp["punct_density"].mean(), 4),
        "has_number_pct":    round(grp["has_number"].mean() * 100, 1),
        # Timing
        "best_day":          best_day,
        "best_hour":         best_hour,
        "avg_days_to_trend": round(grp["days_to_trending"].dropna().mean(), 1)
                             if grp["days_to_trending"].notna().any() else None,
        # Rich content
        "top_words":         top_words,
        "top_emojis":        top_emojis,
        "timing_heatmap":    timing_hm,
        "hook_examples":     hook_examples,
        "hook_distribution": hook_stats.get((country, category), {}),
        "top_videos":        top_videos,
    }

n_combos = sum(len(v) for v in by_country_category.values())
print(f"\\n✅ {n_combos} (country × category) combinations computed")
"""))

# ── CELL 8: EXPORT ─────────────────────────────────────────────
cells.append(md("## Step 8 — Export `data.json`"))

cells.append(code("""\
output = {
    "meta": {
        "generated_at": pd.Timestamp.now().isoformat(),
        "n_countries": len(countries),
        "n_categories": len(categories),
        "n_videos_total": len(df),
    },
    "countries":  countries,
    "categories": categories,
    "country_names": COUNTRY_NAMES,
    "country_flags": COUNTRY_FLAGS,
    "global": {
        "by_country":       global_by_country,
        "views_heatmap":    views_heatmap,
        "count_heatmap":    count_heatmap,
        "engage_heatmap":   engage_heatmap,
        "publish_hour_share": publish_hour_share,
        "publish_hour_zmax":  publish_hour_zmax,
    },
    "by_country_category": by_country_category,
}

out_path = OUT_DIR / "data.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

size_mb = out_path.stat().st_size / 1_000_000
print(f"✅ Exported → {out_path}")
print(f"   File size: {size_mb:.2f} MB")
"""))

# ── CELL 9: VALIDATE ───────────────────────────────────────────
cells.append(md("## Step 9 — Validate Output"))

cells.append(code("""\
with open(OUT_DIR / "data.json") as f:
    loaded = json.load(f)

print("✅ data.json validation")
print(f"   Countries  : {loaded['countries']}")
print(f"   Categories : {len(loaded['categories'])} — {loaded['categories'][:5]}...")
print(f"   Total videos: {loaded['meta']['n_videos_total']:,}")

# Spot-check one (country, category)
cc = loaded["by_country_category"]
spot_c = "US" if "US" in cc else loaded["countries"][0]
spot_cat = next((cat for cat in ["Entertainment","Gaming","Music"]
                 if cat in cc.get(spot_c,{})), None)
if not spot_cat and spot_c in cc:
    spot_cat = list(cc[spot_c].keys())[0]

if spot_cat:
    data = cc[spot_c][spot_cat]
    print(f"\\n📦 Spot-check [{spot_c} × {spot_cat}]:")
    print(f"   Videos        : {data['video_count']:,}")
    print(f"   Avg views     : {data['avg_views']:,}")
    print(f"   Caps ratio    : {data['caps_ratio_avg']}")
    print(f"   Emoji avg     : {data['emoji_count_avg']}")
    print(f"   Best time     : {data['best_day']} {data['best_hour']}:00")
    print(f"   Top words     : {[w['text'] for w in data['top_words'][:8]]}")
    print(f"   Top emojis    : {[e['emoji'] for e in data['top_emojis']]}")
    print(f"   Hook examples : {len(data['hook_examples'])}")
    print(f"   Top videos    : {len(data['top_videos'])}")

print("\\n🎉 Precompute complete! data.json is ready for the website.")
"""))

# ── Write notebook ─────────────────────────────────────────────
nb.cells = cells
out_path = Path(__file__).parent / "precompute.ipynb"
with open(out_path, "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print(f"✅ Notebook written → {out_path}")
