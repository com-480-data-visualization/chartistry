#!/usr/bin/env python3
"""Generates youtube_analysis.ipynb — the full 4-phase analysis pipeline."""
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

# ── TITLE ──────────────────────────────────────────────────────────────────────
cells.append(md("""# 🎬 YouTube Trending Video — Text Analysis Pipeline

A 4-phase exploratory analysis of YouTube trending video **titles** and **tags** across 11 countries.

| Phase | Name | Goal | Key Output |
|-------|------|------|------------|
| **1** | The Basics | Surface features → engagement correlation | Heatmap + violins |
| **2** | Semantic Landscape | Multilingual embeddings + UMAP → content map | Interactive scatter |
| **3** | Hook Taxonomy | Inductive LLM taxonomy → rhetorical style by country | Stacked bar / joyplot |
| **4** | Tag Constellation | Co-occurrence network → niche bridges | Interactive network |
"""))

# ── SECTION 0: SETUP ────────────────────────────────────────────────────────
cells.append(md("## ⚙️ Section 0 — Setup & Configuration"))

cells.append(code("""\
%pip install -q kagglehub pandas numpy matplotlib seaborn plotly emoji \\
    sentence-transformers umap-learn scikit-learn networkx pyvis \\
    openai python-dotenv tqdm scipy python-louvain \\
    chardet deep-translator langdetect
"""))

cells.append(code("""\
import os, json, re, warnings, time
from pathlib import Path
from collections import Counter, defaultdict
from itertools import combinations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import emoji as emoji_lib
from tqdm.auto import tqdm
from dotenv import load_dotenv
import openai
import scipy.stats as stats
import chardet

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", None)
pd.set_option("display.max_colwidth", 70)

load_dotenv()
API_KEY         = os.getenv("CSCS_SERVING_API")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.swissai.svc.cscs.ch/v1")
LLM_MODEL       = os.getenv("LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct")

# ── Pipeline config ───────────────────────────────────────────
DATASET             = "both"    # "old" | "new" | "both"
MAX_ROWS            = 50_000    # cap for embedding phase
LLM_OPEN_SAMPLE     = 150       # titles for open coding (Phase 3a)
LLM_CLOSED_SAMPLE   = 500       # titles for closed coding (Phase 3d)
LLM_SAT_SAMPLE      = 60        # titles for saturation check (Phase 3d)
TAG_TOP_K           = 200       # top-K tags for Phase 4 network
TRANSLATE_FOR_DISPLAY = True    # translate non-English titles for hover tooltip
RANDOM_SEED         = 42
np.random.seed(RANDOM_SEED)

COUNTRY_NAMES = {
    "US": "🇺🇸 USA",    "GB": "🇬🇧 UK",       "DE": "🇩🇪 Germany",
    "CA": "🇨🇦 Canada", "FR": "🇫🇷 France",   "RU": "🇷🇺 Russia",
    "MX": "🇲🇽 Mexico", "KR": "🇰🇷 S. Korea", "JP": "🇯🇵 Japan",
    "IN": "🇮🇳 India",  "BR": "🇧🇷 Brazil",
}

print("✅ Config loaded")
print(f"   Dataset      : {DATASET}")
print(f"   Max rows     : {MAX_ROWS:,}")
print(f"   LLM model    : {LLM_MODEL}")
print(f"   API key      : {'✅ found' if API_KEY else '❌ MISSING — check .env'}")
print(f"   Translation  : {'✅ on' if TRANSLATE_FOR_DISPLAY else 'off'}")
"""))

# ── SECTION 1: DATA ───────────────────────────────────────────────────────────
cells.append(md("## 📥 Section 1 — Data Download & Loading"))

cells.append(code("""\
import kagglehub

dataset_paths = {}
if DATASET in ("old", "both"):
    print("⬇️  Downloading old dataset...")
    dataset_paths["old"] = Path(kagglehub.dataset_download("datasnaek/youtube-new"))
    print(f"   → {dataset_paths['old']}")

if DATASET in ("new", "both"):
    print("⬇️  Downloading new dataset...")
    dataset_paths["new"] = Path(kagglehub.dataset_download("rsrishav/youtube-trending-video-dataset"))
    print(f"   → {dataset_paths['new']}")
print("✅ Downloads complete")
"""))

cells.append(code("""\
def smart_read_csv(filepath: Path) -> pd.DataFrame:
    \"\"\"Try multiple encodings; use chardet as fallback.\"\"\"
    for enc in ("utf-8", "utf-8-sig", "cp949", "shift-jis"):
        try:
            return pd.read_csv(filepath, encoding=enc, on_bad_lines="skip")
        except (UnicodeDecodeError, Exception):
            pass
    # chardet auto-detection fallback
    raw = filepath.read_bytes()
    detected = chardet.detect(raw[:100_000]).get("encoding", "latin-1") or "latin-1"
    try:
        return pd.read_csv(filepath, encoding=detected, on_bad_lines="skip")
    except Exception:
        return pd.read_csv(filepath, encoding="latin-1", on_bad_lines="skip")


def load_country_files(base_path: Path, version_tag: str) -> pd.DataFrame:
    csv_files = list(base_path.glob("**/*videos.csv"))
    if not csv_files:
        csv_files = list(base_path.glob("**/*trending_data.csv"))
    print(f"  [{version_tag}] {len(csv_files)} country files")
    dfs = []
    for f in sorted(csv_files):
        country_code = f.stem[:2].upper()
        df = smart_read_csv(f)
        df["country"]         = country_code
        df["dataset_version"] = version_tag
        dfs.append(df)
        print(f"    [{country_code}] {len(df):,} rows  (encoding auto-detected)")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def load_category_map(base_path: Path) -> dict:
    cat_map = {}
    for jf in base_path.glob("**/*_category_id.json"):
        country = jf.stem[:2].upper()
        try:
            data = json.loads(jf.read_bytes().decode("utf-8", errors="replace"))
            for item in data.get("items", []):
                cat_map[(country, int(item["id"]))] = item["snippet"]["title"]
        except Exception:
            pass
    return cat_map


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={"view_count": "views", "like_count": "likes"})
    for col in ["title", "tags", "description", "channel_title"]:
        df[col] = df.get(col, pd.Series("", index=df.index)).fillna("").astype(str)
    for col in ["views", "likes", "comment_count", "category_id"]:
        df[col] = pd.to_numeric(df.get(col, np.nan), errors="coerce")
    df["tags"] = df["tags"].replace("[none]", "")
    return df
"""))

cells.append(code("""\
frames, cat_map_global = [], {}
for version, base_path in dataset_paths.items():
    print(f"\\n📂 Loading [{version}]")
    frames.append(load_country_files(base_path, version))
    cat_map_global.update(load_category_map(base_path))

df_raw = pd.concat(frames, ignore_index=True)
df_raw = normalize_columns(df_raw)

id_col = "video_id" if "video_id" in df_raw.columns else df_raw.columns[0]
df = (df_raw
      .sort_values("views", ascending=False)
      .drop_duplicates(subset=[id_col, "country", "dataset_version"])
      .reset_index(drop=True))

def resolve_category(row):
    return (cat_map_global.get((row["country"], row["category_id"]))
            or cat_map_global.get(("US", row["category_id"]), "Unknown"))

df["category_name"] = df.apply(resolve_category, axis=1)
df["country_name"]  = df["country"].map(COUNTRY_NAMES).fillna(df["country"])

print(f"\\n✅ Final DataFrame: {df.shape[0]:,} rows × {df.shape[1]} cols")
print(f"   Countries : {sorted(df['country'].unique())}")
print(f"   Versions  : {df['dataset_version'].unique().tolist()}")
df.head(3)
"""))

cells.append(code("""\
summary = (df.groupby(["dataset_version","country_name"])
           .agg(videos=("title","count"),
                avg_views=("views","mean"),
                median_views=("views","median"),
                categories=("category_name","nunique"))
           .round(0))
display(summary)
print("\\n🔍 Missing values (%):")
print((df[["title","tags","views","likes","comment_count"]].isnull().mean()*100).round(2))
"""))

# ── PHASE 1 ───────────────────────────────────────────────────────────────────
cells.append(md("""---
## 📊 Phase 1 — The Basics: Surface-Level Text Features
"""))

cells.append(code("""\
def caps_ratio(s: str) -> float:
    alpha = [c for c in s if c.isalpha()]
    return sum(1 for c in alpha if c.isupper()) / len(alpha) if alpha else 0.0

def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    t = df["title"]
    df = df.copy()
    df["title_len"]      = t.str.len()
    df["word_count"]     = t.str.split().str.len().fillna(0).astype(int)
    df["caps_ratio"]     = t.map(caps_ratio)
    df["emoji_count"]    = t.map(lambda s: emoji_lib.emoji_count(str(s)))
    df["has_emoji"]      = (df["emoji_count"] > 0).astype(int)
    df["exclaim_count"]  = t.str.count("!")
    df["question_count"] = t.str.count(r"\\?")
    df["punct_density"]  = t.str.count(r"[!?…]") / df["title_len"].clip(lower=1)
    df["has_number"]     = t.str.contains(r"\\d+", regex=True).astype(int)
    df["tag_count"]      = df["tags"].apply(
        lambda s: len([x for x in str(s).split("|") if x.strip().strip('"')])
    )
    return df

df        = extract_features(df)
FEATURES  = ["title_len","word_count","caps_ratio","emoji_count",
             "punct_density","exclaim_count","has_number","tag_count"]
TARGETS   = ["views","likes","comment_count"]
print("✅ Features extracted")
df[FEATURES].describe().round(3)
"""))

cells.append(code("""\
# 1a. Correlation heatmap
corr_df = df[FEATURES + TARGETS].copy()
corr_df[TARGETS] = np.log1p(corr_df[TARGETS])
corr_matrix = corr_df.corr().loc[FEATURES, TARGETS]

fig, ax = plt.subplots(figsize=(8, 5))
sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="RdBu_r",
            center=0, vmin=-0.25, vmax=0.25,
            linewidths=0.5, linecolor="#333", annot_kws={"size": 10}, ax=ax)
ax.set_title("Correlation: Surface Title Features vs. Engagement (log-scale)",
             fontsize=13, fontweight="bold", pad=12)
plt.xticks(rotation=0); plt.yticks(rotation=0)
plt.tight_layout()
plt.savefig("phase1_heatmap.png", dpi=150, bbox_inches="tight")
plt.show()
"""))

cells.append(code("""\
# 1b. Violin plots: caps_ratio and emoji_count by country
top_ctry = df["country"].value_counts().head(8).index
df_v = df[df["country"].isin(top_ctry)].copy()

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle("Title Style Distribution by Country", fontsize=14, fontweight="bold")
for ax, (col, label) in zip(axes, [("caps_ratio","Caps Ratio"),("emoji_count","Emoji Count")]):
    plot_df = df_v[df_v[col] <= df_v[col].quantile(0.98)]
    order   = plot_df.groupby("country_name")[col].median().sort_values(ascending=False).index
    sns.violinplot(data=plot_df, y="country_name", x=col, order=order,
                   palette="Set2", inner="quartile", orient="h", cut=0, bw_adjust=0.8, ax=ax)
    ax.set_title(label, fontsize=12, fontweight="bold"); ax.set_ylabel("")
    ax.axvline(plot_df[col].median(), color="red", ls="--", alpha=0.5, lw=1.5, label="Global median")
    ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig("phase1_violins.png", dpi=150, bbox_inches="tight")
plt.show()
"""))

cells.append(code("""\
# 1c. Top emojis bar chart
all_emojis = [e["emoji"] for title in df["title"]
              for e in emoji_lib.emoji_list(str(title))]
top20 = Counter(all_emojis).most_common(20)
if top20:
    labels, counts = zip(*top20)
    fig = go.Figure(go.Bar(
        y=list(labels)[::-1], x=list(counts)[::-1], orientation="h",
        marker=dict(color=list(counts)[::-1], colorscale="Viridis"),
        text=list(counts)[::-1], textposition="outside",
    ))
    fig.update_layout(title="🎨 Top 20 Emojis in Trending Titles (Global)",
                      xaxis_title="Count", height=520, template="plotly_dark",
                      yaxis=dict(tickfont=dict(size=18)))
    fig.show()
    fig.write_html("phase1_top_emojis.html")
    print("Saved → phase1_top_emojis.html")
"""))

# ── PHASE 2 ───────────────────────────────────────────────────────────────────
cells.append(md("""---
## 🗺️ Phase 2 — The Semantic Landscape

**Model:** `paraphrase-multilingual-MiniLM-L12-v2` — covers 50+ languages including Korean, Japanese, Russian, Hindi, Arabic.  
**Display:** Non-ASCII titles are translated to English *for the hover tooltip only* (embeddings use the original text).

> ⚠️ If you previously ran Phase 2 with the English model, delete `data/embeddings_cache.npz` before re-running.
"""))

cells.append(code("""\
# Delete stale cache if switching models
EMBED_CACHE  = Path("data/embeddings_cache.npz")
TRANS_CACHE  = Path("data/title_translations.json")
EMBED_MODEL  = "paraphrase-multilingual-MiniLM-L12-v2"

# Optional: uncomment to force re-encode
# EMBED_CACHE.unlink(missing_ok=True)

print(f"Embedding model : {EMBED_MODEL}")
print(f"Cache exists    : {EMBED_CACHE.exists()}")
"""))

cells.append(code("""\
from langdetect import detect, LangDetectException

def detect_lang(text: str) -> str:
    try:
        return detect(str(text)[:200])
    except LangDetectException:
        return "unknown"

# Sample for Phase 2
sample_df = df.drop_duplicates(subset=["title"]).copy()
if MAX_ROWS and len(sample_df) > MAX_ROWS:
    sample_df = sample_df.sample(MAX_ROWS, random_state=RANDOM_SEED)
    print(f"ℹ️  Sampled {len(sample_df):,} titles for embedding")

# Detect language (fast — local model, no API)
print("🔍 Detecting languages...")
sample_df["lang"] = [detect_lang(t) for t in tqdm(sample_df["title"], desc="lang detect")]
lang_counts = sample_df["lang"].value_counts().head(10)
print("\\nTop detected languages:")
print(lang_counts.to_string())
"""))

cells.append(code("""\
from deep_translator import GoogleTranslator

def translate_titles(df: pd.DataFrame, cache_path: Path) -> pd.Series:
    \"\"\"Translate non-ASCII (non-English) titles for hover display. Cached.\"\"\"
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        print(f"📂 Loaded {len(cached)} cached translations")
    else:
        cached = {}

    needs_translation = df[~df["title"].str.isascii() | (df["lang"] != "en")]["title"].unique()
    missing = [t for t in needs_translation if t not in cached]
    print(f"🌐 Translating {len(missing):,} new titles (may take a while)...")

    translator = GoogleTranslator(source="auto", target="en")
    for i, title in enumerate(tqdm(missing, desc="Translating")):
        try:
            cached[title] = translator.translate(title[:500]) or title
        except Exception:
            cached[title] = title
        if i > 0 and i % 100 == 0:
            time.sleep(1)  # gentle rate limiting

    cache_path.parent.mkdir(exist_ok=True)
    cache_path.write_text(json.dumps(cached, ensure_ascii=False, indent=2))
    return df["title"].map(lambda t: cached.get(t, t))

if TRANSLATE_FOR_DISPLAY:
    sample_df["title_display"] = translate_titles(sample_df, TRANS_CACHE)
    print("✅ Translation done")
else:
    sample_df["title_display"] = sample_df["title"]
    print("ℹ️  Translation skipped (TRANSLATE_FOR_DISPLAY=False)")
"""))

cells.append(code("""\
from sentence_transformers import SentenceTransformer

titles = sample_df["title"].tolist()
embeddings = None

if EMBED_CACHE.exists():
    print("📂 Loading cached embeddings...")
    cache = np.load(EMBED_CACHE, allow_pickle=True)
    if len(cache["titles"]) == len(titles):
        embeddings = cache["embeddings"]
        print(f"✅ Cache hit  {embeddings.shape}")
    else:
        print("⚠️  Cache size mismatch — recomputing (delete cache file to suppress)")

if embeddings is None:
    print(f"🔄 Encoding {len(titles):,} titles with {EMBED_MODEL}...")
    model      = SentenceTransformer(EMBED_MODEL)
    embeddings = model.encode(titles, show_progress_bar=True, batch_size=64,
                              normalize_embeddings=True)
    EMBED_CACHE.parent.mkdir(exist_ok=True)
    np.savez(EMBED_CACHE, embeddings=embeddings, titles=np.array(titles))
    print(f"✅ Shape: {embeddings.shape} — saved to cache")
"""))

cells.append(code("""\
import umap

print("🗺️  Running UMAP (~1–2 min for 50k rows)...")
reducer = umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1,
                    metric="cosine", random_state=RANDOM_SEED, verbose=False)
coords = reducer.fit_transform(embeddings)

sample_df = sample_df.reset_index(drop=True)
sample_df["umap_x"] = coords[:, 0]
sample_df["umap_y"] = coords[:, 1]
print(f"✅ UMAP done: {coords.shape}")
"""))

cells.append(code("""\
# Interactive semantic scatter — color by category, hover shows translated title
plot_df = sample_df.assign(
    views_fmt = sample_df["views"].map(lambda v: f"{v:,.0f}" if pd.notna(v) else "N/A")
)

fig = px.scatter(
    plot_df,
    x="umap_x", y="umap_y",
    color="category_name",
    hover_data={"title_display": True, "lang": True, "country_name": True,
                "views_fmt": True, "umap_x": False, "umap_y": False},
    color_discrete_sequence=px.colors.qualitative.D3,
    opacity=0.60,
    labels={"umap_x": "UMAP 1", "umap_y": "UMAP 2",
            "category_name": "Category", "title_display": "Title (EN)",
            "views_fmt": "Views", "lang": "Lang"},
    title="🌍 Semantic Landscape of YouTube Trending Titles (multilingual)",
)
fig.update_traces(marker=dict(size=4))
fig.update_layout(template="plotly_dark", height=680,
                  legend=dict(title="Category", itemsizing="constant", font=dict(size=10)),
                  font=dict(family="Inter, sans-serif"))
fig.show()
fig.write_html("phase2_semantic_map.html")
print("Saved → phase2_semantic_map.html")
"""))

# ── PHASE 3 ───────────────────────────────────────────────────────────────────
cells.append(md("""---
## 🎭 Phase 3 — Hook Taxonomy (Inductive LLM Approach)

Instead of imposing pre-defined categories, we **let the data speak first**:

| Step | What happens |
|------|-------------|
| **3a** Open Coding | LLM freely labels ~150 titles in 2–5 words each |
| **3b** Taxonomy Induction | LLM groups the free labels into 6–10 coherent categories |
| **3c** Manual Review | **You** edit the taxonomy JSON in the cell below — rename, merge, split |
| **3d** Closed Coding | LLM classifies a larger sample using your refined taxonomy |
| **3e** Saturation Check | Fresh batch of open coding — if <10% new labels, taxonomy is stable |
"""))

cells.append(code("""\
# ── Shared LLM client ────────────────────────────────────────
llm_client = openai.OpenAI(api_key=API_KEY, base_url=OPENAI_BASE_URL)

def llm(system: str, user: str, temperature=0.3, max_tokens=2000) -> str:
    \"\"\"Single LLM call with basic retry.\"\"\"
    for attempt in range(3):
        try:
            r = llm_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": system},
                          {"role": "user",   "content": user}],
                temperature=temperature, max_tokens=max_tokens,
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            print(f"  ⚠️  LLM attempt {attempt+1} failed: {e}")
            time.sleep(2)
    raise RuntimeError("LLM failed after 3 attempts")

def parse_json(text: str):
    \"\"\"Strip markdown fences and parse JSON.\"\"\"
    text = re.sub(r"^```(?:json)?\\n?", "", text.strip())
    text = re.sub(r"\\n?```$", "", text)
    return json.loads(text.strip())

print("✅ LLM client ready")
"""))

cells.append(code("""\
# ── 3a. Open Coding ──────────────────────────────────────────
OPEN_CACHE = Path("data/open_coding.json")

OPEN_SYSTEM = \"\"\"You are a YouTube content researcher doing qualitative coding.
For each video title, describe its RHETORICAL HOOK or TITLE STYLE in 2-5 words.
Be specific about HOW the title is crafted to attract clicks, not WHAT it is about.

Good labels: "curiosity gap withhold", "numbered warning list", "personal time challenge",
             "authority shock claim", "intimate first person", "location/object reveal"
Bad labels: "entertainment", "music video", "funny content"  (too vague)

If the title is in a non-English language, still analyse its structure — hook styles are universal.
Reply ONLY with JSON: [{\"id\": <int>, \"label\": \"<2-5 words>\"}]\"\"\"

# Stratified sample — proportional but ensures every country is represented
n_per  = max(5, LLM_OPEN_SAMPLE // df["country"].nunique())
open_sample = (df.sort_values("views", ascending=False)
               .groupby("country", group_keys=False)
               .apply(lambda g: g.sample(min(n_per, len(g)), random_state=RANDOM_SEED))
               .head(LLM_OPEN_SAMPLE)
               .reset_index(drop=True))

print(f"📋 Open coding sample: {len(open_sample)} titles from {open_sample['country'].nunique()} countries")

if OPEN_CACHE.exists():
    open_labels = json.loads(OPEN_CACHE.read_text())
    print(f"📂 Loaded {len(open_labels)} cached open labels")
else:
    print("🤖 Calling LLM for open coding (batches of 25)...")
    open_labels = {}
    batch_size  = 25
    batches     = [open_sample.iloc[i:i+batch_size] for i in range(0, len(open_sample), batch_size)]
    for b_i, batch in enumerate(tqdm(batches, desc="Open coding")):
        offset   = b_i * batch_size
        user_msg = "\\n".join(f'{offset+i}: {r["title"]}' for i, r in enumerate(batch.itertuples()))
        try:
            raw     = llm(OPEN_SYSTEM, user_msg, temperature=0.4, max_tokens=1500)
            parsed  = parse_json(raw)
            for item in parsed:
                open_labels[item["id"]] = item["label"]
        except Exception as e:
            print(f"  ⚠️  Batch {b_i} failed: {e}")
    OPEN_CACHE.parent.mkdir(exist_ok=True)
    OPEN_CACHE.write_text(json.dumps(open_labels, indent=2))
    print(f"✅ Open coding done — {len(open_labels)} labels")

open_sample["open_label"] = [open_labels.get(i, "unlabelled") for i in range(len(open_sample))]

# Show the raw labels
print("\\n📝 Sample of raw open labels:")
label_counts = open_sample["open_label"].value_counts()
print(label_counts.head(30).to_string())
"""))

cells.append(code("""\
# ── 3b. Taxonomy Induction ───────────────────────────────────
TAXONOMY_RAW_CACHE = Path("data/taxonomy_raw.json")

all_labels = list(open_labels.values())
label_freq = Counter(all_labels)

INDUCT_SYSTEM = \"\"\"You are a qualitative researcher doing thematic analysis.
Below are free-form annotations of YouTube title styles from a grounded coding exercise.
Group them into 6-10 coherent, mutually-exclusive categories (a taxonomy of rhetorical hooks).

Each category must:
- Have a concise, memorable name (2-4 words)
- Represent a distinct rhetorical strategy for attracting clicks
- Capture a meaningful cluster visible in the annotations

Return ONLY valid JSON — no markdown, no explanation:
{
  "taxonomy": [
    {
      "name": "Category Name",
      "description": "One sentence explaining the rhetorical strategy.",
      "raw_labels": ["label1", "label2", ...]
    }
  ]
}\"\"\"

label_list = "\\n".join(f"- {label} (×{count})" for label, count in label_freq.most_common())

if TAXONOMY_RAW_CACHE.exists():
    induced = json.loads(TAXONOMY_RAW_CACHE.read_text())
    print("📂 Loaded cached induced taxonomy")
else:
    print("🤖 Inducing taxonomy from open labels...")
    raw  = llm(INDUCT_SYSTEM, label_list, temperature=0.2, max_tokens=2000)
    induced = parse_json(raw)
    TAXONOMY_RAW_CACHE.write_text(json.dumps(induced, indent=2))
    print("✅ Taxonomy induced")

print(f"\\n📚 Induced {len(induced['taxonomy'])} categories:\\n")
for cat in induced["taxonomy"]:
    print(f"  [{cat['name']}]")
    print(f"    {cat['description']}")
    print(f"    Labels: {', '.join(cat['raw_labels'][:5])}{'...' if len(cat['raw_labels'])>5 else ''}")
    print()
"""))

cells.append(md("""### ✍️ Step 3c — Manual Review

**Edit the dictionary in the cell below.** The LLM gave you a starting point — now make it yours:
- **Rename** categories to be more evocative
- **Merge** two that feel too similar  
- **Split** one that feels too broad
- **Delete** any that seem like noise

Run the cell when done to save your refined taxonomy.
"""))

cells.append(code("""\
# ── 3c. Manual Review ────────────────────────────────────────
# Edit this dict to refine the taxonomy!
# Each key = final category name, value = short description

# Pre-populated from LLM induction (edit freely):
TAXONOMY = {
    cat["name"]: cat["description"]
    for cat in induced["taxonomy"]
}

# ── EDIT BELOW THIS LINE ─────────────────────────────────────
# Example edits:
#   TAXONOMY["Curiosity Gap"] = "Title withholds key info to force a click"
#   del TAXONOMY["Vague Entertainment"]
#   TAXONOMY["Shock & Awe"] = TAXONOMY.pop("Authority Shock")  # rename
# ─────────────────────────────────────────────────────────────

TAXONOMY_PATH = Path("data/taxonomy.json")
TAXONOMY_PATH.write_text(json.dumps(TAXONOMY, ensure_ascii=False, indent=2))

print("💾 Taxonomy saved to data/taxonomy.json")
print(f"   {len(TAXONOMY)} categories:\\n")
for name, desc in TAXONOMY.items():
    print(f"  [{name}]  {desc}")
"""))

cells.append(code("""\
# ── 3d. Closed Coding ────────────────────────────────────────
CLOSED_CACHE = Path("data/hook_labels_closed.json")

taxonomy_str = "\\n".join(f"{i+1}. {name}: {desc}"
                          for i, (name, desc) in enumerate(TAXONOMY.items()))
category_names = list(TAXONOMY.keys())

CLOSED_SYSTEM = f\"\"\"You are a YouTube title analyst. Classify each title into EXACTLY ONE category from this taxonomy:

{taxonomy_str}

Rules:
- Choose the category that best matches the RHETORICAL STRATEGY, not the topic
- If the title is non-English, analyse its construction (hooks are universal across languages)
- Every title MUST be assigned a category — \"Other\" is not an option

Reply ONLY with JSON: [{{"id": <int>, "category": "<exact name>", "conf": <0.0-1.0>}}]\"\"\"

# Stratified closed-coding sample
n_per_c    = max(10, LLM_CLOSED_SAMPLE // df["country"].nunique())
closed_sample = (df.sort_values("views", ascending=False)
                 .groupby("country", group_keys=False)
                 .apply(lambda g: g.head(n_per_c))
                 .head(LLM_CLOSED_SAMPLE)
                 .reset_index(drop=True))

print(f"📋 Closed coding sample: {len(closed_sample)} titles, {closed_sample['country'].nunique()} countries")

if CLOSED_CACHE.exists():
    closed_results = {int(k): v for k, v in json.loads(CLOSED_CACHE.read_text()).items()}
    print(f"📂 Loaded {len(closed_results)} cached closed labels")
else:
    print("🤖 Classifying with refined taxonomy (batches of 20)...")
    closed_results = {}
    batch_size = 20
    for b_i in tqdm(range(0, len(closed_sample), batch_size), desc="Closed coding"):
        batch  = closed_sample.iloc[b_i:b_i+batch_size]
        offset = b_i
        user_msg = "\\n".join(f'{offset+i}: {r["title"]}' for i, r in enumerate(batch.itertuples()))
        try:
            raw    = llm(CLOSED_SYSTEM, user_msg, temperature=0.1, max_tokens=1000)
            parsed = parse_json(raw)
            for item in parsed:
                # Validate category name — snap to nearest if LLM drifted
                cat = item.get("category", "")
                if cat not in category_names:
                    cat = min(category_names, key=lambda c: sum(a!=b for a,b in zip(c.lower(), cat.lower())))
                closed_results[item["id"]] = {"category": cat, "conf": item.get("conf", 1.0)}
        except Exception as e:
            print(f"  ⚠️  Batch {b_i} failed: {e}")
            for i in range(len(batch)):
                closed_results[offset+i] = {"category": category_names[0], "conf": 0.0}

    CLOSED_CACHE.write_text(json.dumps(closed_results, indent=2))
    print(f"✅ Closed coding done — {len(closed_results)} labels")

closed_sample["hook"]      = [closed_results.get(i, {}).get("category", "?") for i in range(len(closed_sample))]
closed_sample["hook_conf"] = [closed_results.get(i, {}).get("conf", 0.0)     for i in range(len(closed_sample))]

print("\\n📊 Hook distribution:")
print(closed_sample["hook"].value_counts().to_string())
"""))

cells.append(code("""\
# ── 3e. Saturation Check ─────────────────────────────────────
SAT_CACHE = Path("data/saturation_labels.json")

# Fresh batch — different from closed coding sample
sat_sample = (df[~df.index.isin(closed_sample.index)]
              .sample(min(LLM_SAT_SAMPLE, len(df) - len(closed_sample)),
                      random_state=RANDOM_SEED + 1)
              .reset_index(drop=True))

if SAT_CACHE.exists():
    sat_labels = json.loads(SAT_CACHE.read_text())
    print(f"📂 Loaded {len(sat_labels)} cached saturation labels")
else:
    print(f"🤖 Open coding {len(sat_sample)} new titles for saturation check...")
    sat_labels = {}
    batch_size = 25
    for b_i in range(0, len(sat_sample), batch_size):
        batch  = sat_sample.iloc[b_i:b_i+batch_size]
        offset = b_i
        user_msg = "\\n".join(f'{offset+i}: {r.title}' for i, r in enumerate(batch.itertuples()))
        try:
            raw    = llm(OPEN_SYSTEM, user_msg, temperature=0.4, max_tokens=1000)
            parsed = parse_json(raw)
            for item in parsed:
                sat_labels[item["id"]] = item["label"]
        except Exception as e:
            print(f"  ⚠️  Batch {b_i} failed: {e}")
    SAT_CACHE.write_text(json.dumps(sat_labels, indent=2))

# Measure saturation: ask LLM which new labels fall outside existing taxonomy
new_labels  = list(set(sat_labels.values()))
existing    = [cat["raw_labels"] for cat in induced["taxonomy"]]
flat_existing = {lbl for grp in existing for lbl in grp}

# Heuristic: if new label shares >2 words with any existing label → covered
def is_covered(label: str, existing_set: set) -> bool:
    words = set(label.lower().split())
    for ex in existing_set:
        if len(words & set(ex.lower().split())) >= 1:
            return True
    return False

covered   = [l for l in new_labels if is_covered(l, flat_existing)]
uncovered = [l for l in new_labels if not is_covered(l, flat_existing)]
sat_ratio = len(covered) / len(new_labels) if new_labels else 1.0

print(f"\\n🔬 Saturation Check")
print(f"   New labels     : {len(new_labels)}")
print(f"   Covered        : {len(covered)}  ({sat_ratio*100:.0f}%)")
print(f"   NOT covered    : {len(uncovered)}")
if uncovered:
    print(f"   → Possible new categories: {uncovered[:10]}")
    if sat_ratio < 0.90:
        print("   ⚠️  Saturation NOT reached (<90%). Consider adding categories above and re-running 3c/3d.")
    else:
        print("   ✅ Saturation reached (≥90%) — taxonomy is stable!")
else:
    print("   ✅ Perfect saturation — all new labels fit existing taxonomy!")
"""))

cells.append(code("""\
# ── 3 Visualizations ─────────────────────────────────────────
# Stacked bar: hook % by country
hook_ctry = (closed_sample.groupby(["country_name","hook"])
             .size().reset_index(name="count"))
hook_ctry["pct"] = hook_ctry.groupby("country_name")["count"].transform(
    lambda x: 100 * x / x.sum())

fig = px.bar(hook_ctry, x="country_name", y="pct", color="hook", barmode="stack",
             color_discrete_sequence=px.colors.qualitative.Pastel,
             labels={"pct":"% of titles","country_name":"Country","hook":"Hook Style"},
             title="🎭 Hook Style Distribution by Country", text_auto=".0f")
fig.update_layout(template="plotly_dark", height=520, font=dict(family="Inter"))
fig.show()
fig.write_html("phase3_hook_by_country.html")
print("Saved → phase3_hook_by_country.html")
"""))

cells.append(code("""\
# Joyplot: log(views) distribution by hook type
hook_order = closed_sample["hook"].value_counts().index.tolist()
palette    = plt.cm.Set2(np.linspace(0, 1, len(hook_order)))

fig, ax = plt.subplots(figsize=(12, 7))
fig.patch.set_facecolor("#0f0e17"); ax.set_facecolor("#0f0e17")

for i, hook in enumerate(hook_order):
    vals = np.log1p(closed_sample[closed_sample["hook"] == hook]["views"].dropna())
    if len(vals) < 5: continue
    kde     = stats.gaussian_kde(vals, bw_method="scott")
    x_range = np.linspace(vals.min(), vals.max(), 200)
    density = kde(x_range)
    offset  = i * 0.9; color = palette[i]
    ax.fill_between(x_range, offset, offset + density * 3, alpha=0.6, color=color)
    ax.plot(x_range, offset + density * 3, color=color, lw=1.5)
    ax.axhline(offset, color="white", lw=0.3, alpha=0.2)
    ax.text(vals.min() - 0.3, offset + 0.05, hook, ha="right",
            fontsize=9, color=color, fontweight="bold")

ax.set_xlabel("log(views + 1)", fontsize=11, color="white")
ax.set_yticks([])
for sp in ["top","right","left"]: ax.spines[sp].set_visible(False)
ax.spines["bottom"].set_color("#666"); ax.tick_params(colors="white")
plt.title("📈 View Distribution by Hook Type", fontsize=14, color="white", fontweight="bold")
plt.tight_layout()
plt.savefig("phase3_joyplot.png", dpi=150, bbox_inches="tight", facecolor="#0f0e17")
plt.show()
"""))

# ── PHASE 4 ───────────────────────────────────────────────────────────────────
cells.append(md("""---
## 🕸️ Phase 4 — The Tag Constellation (Network Analysis)
"""))

cells.append(code("""\
def parse_tags(tag_str: str) -> list:
    if not tag_str or str(tag_str).strip() in ("", "[none]", "none"):
        return []
    return [t.strip().strip('"').strip("'").lower()
            for t in str(tag_str).split("|")
            if t.strip().strip('"')]

all_tags  = [tag for tags in df["tags"].map(parse_tags) for tag in tags]
tag_freq  = Counter(all_tags)
top_tags  = {tag for tag, _ in tag_freq.most_common(TAG_TOP_K)}

print(f"📌 Unique tags : {len(tag_freq):,}")
print(f"   Top {TAG_TOP_K} covers {sum(tag_freq[t] for t in top_tags)/len(all_tags)*100:.1f}% of mentions")
print(f"   Top 10: {tag_freq.most_common(10)}")
"""))

cells.append(code("""\
edge_weights = defaultdict(int)
for tag_str in tqdm(df["tags"], desc="Co-occurrence"):
    video_tags = [t for t in parse_tags(tag_str) if t in top_tags]
    if len(video_tags) >= 2:
        for t1, t2 in combinations(sorted(set(video_tags)), 2):
            edge_weights[(t1, t2)] += 1

print(f"🔗 Total edges (pre-threshold): {len(edge_weights):,}")
print("   Strongest pairs:")
for (t1,t2),w in sorted(edge_weights.items(), key=lambda x: -x[1])[:5]:
    print(f"   '{t1}' ↔ '{t2}': {w}")
"""))

cells.append(code("""\
import networkx as nx

EDGE_THRESHOLD = 5
G = nx.Graph()
for tag in top_tags:
    G.add_node(tag, freq=tag_freq[tag])
for (t1,t2), w in edge_weights.items():
    if w >= EDGE_THRESHOLD:
        G.add_edge(t1, t2, weight=w)
G.remove_nodes_from(list(nx.isolates(G)))
print(f"📊 Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

try:
    import community as community_louvain
    partition = community_louvain.best_partition(G, random_state=RANDOM_SEED)
    print(f"🏘️  Louvain communities: {len(set(partition.values()))}")
except ImportError:
    from networkx.algorithms import community as nx_comm
    comms = list(nx_comm.greedy_modularity_communities(G))
    partition = {n: i for i, c in enumerate(comms) for n in c}
    print(f"🏘️  Greedy modularity communities: {len(comms)}")

bet = nx.betweenness_centrality(G, normalized=True, k=min(100, G.number_of_nodes()))
top_bridges = sorted(bet.items(), key=lambda x: -x[1])[:10]
print("\\n🌉 Top bridge tags:")
for tag, score in top_bridges:
    print(f"   {tag:25s}  {score:.4f}  (freq: {tag_freq[tag]:,})")
"""))

cells.append(code("""\
from pyvis.network import Network
from IPython.display import IFrame

COLORS = ["#e63946","#457b9d","#2a9d8f","#e9c46a","#f4a261",
          "#a8dadc","#6a4c93","#f77f00","#80b918","#e07a5f",
          "#3d405b","#81b29a","#f2cc8f","#118ab2","#06d6a0"]

net = Network(height="720px", width="100%", bgcolor="#0f0e17",
              font_color="#fffffe", notebook=True, cdn_resources="inline")

_opts = (
    '{"physics":{"solver":"forceAtlas2Based",'
    '"forceAtlas2Based":{"gravitationalConstant":-55,"centralGravity":0.01,'
    '"springLength":100,"springConstant":0.05},'
    '"stabilization":{"iterations":150}},'
    '"edges":{"smooth":{"type":"continuous"},"scaling":{"min":1,"max":6}},'
    '"interaction":{"hover":true,"tooltipDelay":80}}'
)
net.set_options(_opts)

max_freq   = max(tag_freq[t] for t in G.nodes())
bridge_set = {t for t,_ in top_bridges[:5]}

for node in G.nodes():
    freq, com = tag_freq[node], partition.get(node, 0)
    color     = COLORS[com % len(COLORS)]
    size      = 10 + 28 * (freq / max_freq) ** 0.5
    is_bridge = node in bridge_set
    net.add_node(node, label=node,
        title=f"<b>{node}</b><br>Freq: {freq:,}<br>Community: {com}<br>{'⭐ Bridge tag' if is_bridge else ''}",
        size=size, color={"background":color,"border":"#fff" if is_bridge else color},
        borderWidth=3 if is_bridge else 1,
        font={"size": max(7, int(11*(freq/max_freq)**0.3)), "color":"#fffffe"})

for t1,t2,data in G.edges(data=True):
    net.add_edge(t1, t2, value=data.get("weight",1),
                 title=f"Co-occurrences: {data.get('weight',1)}",
                 color={"color":"#ffffff18","highlight":"#ffffff88"})

net.save_graph("phase4_tag_network.html")
print("✅ Saved → phase4_tag_network.html")
IFrame("phase4_tag_network.html", width="100%", height="750px")
"""))

cells.append(md("""---
## ✅ Summary

| Phase | Output Files | Cached Data |
|-------|-------------|-------------|
| Phase 1 | `phase1_heatmap.png`, `phase1_violins.png`, `phase1_top_emojis.html` | — |
| Phase 2 | `phase2_semantic_map.html` | `data/embeddings_cache.npz`, `data/title_translations.json` |
| Phase 3 | `phase3_hook_by_country.html`, `phase3_joyplot.png` | `data/open_coding.json`, `data/taxonomy.json`, `data/hook_labels_closed.json` |
| Phase 4 | `phase4_tag_network.html` | — |

### Phase 3 iteration guide
If saturation check shows <90%:
1. Note the uncovered labels printed in 3e
2. Edit `TAXONOMY` dict in cell 3c — add/split categories
3. Delete `data/hook_labels_closed.json` (forces re-classification)
4. Re-run cells 3c → 3d → 3e
"""))

# ── Write notebook ─────────────────────────────────────────────────────────────
nb.cells = cells
out_path  = Path(__file__).parent / "youtube_analysis_2.ipynb"
with open(out_path, "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print(f"✅ Notebook written → {out_path}")
