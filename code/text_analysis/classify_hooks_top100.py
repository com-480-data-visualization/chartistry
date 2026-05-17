import os, json, re, time
from pathlib import Path
from collections import Counter
import pandas as pd
import numpy as np
from tqdm.auto import tqdm
import openai
from dotenv import load_dotenv

# 1. Setup & Config
load_dotenv()
API_KEY = os.getenv("CSCS_SERVING_API")
if not API_KEY:
    raise ValueError("CSCS_SERVING_API not found in .env file!")
print(f"API Key loaded: {API_KEY[:4]}...{API_KEY[-4:]}")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.swissai.svc.cscs.ch/v1")
MODEL = os.getenv("LLM_MODEL", "swiss-ai/Apertus-8B-Instruct-2509")

DATA_DIR = Path("data")
TAXONOMY_PATH = DATA_DIR / "taxonomy.json"
CACHE_PATH = DATA_DIR / "hook_labels_elite.json"
OLD_CACHE_PATH = DATA_DIR / "hook_labels_closed.json"

client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)

def llm_call(system, user, temp=0.1):
    for i in range(3):
        try:
            res = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": f"{system}\n\nTITLES TO CLASSIFY:\n{user}"}],
                temperature=temp, max_tokens=2000,
                timeout=180,
                stream=True
            )
            full_content = ""
            for chunk in res:
                if len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    full_content += chunk.choices[0].delta.content
            
            if not full_content:
                print(f"  [Attempt {i+1}] Empty content from LLM (Stream)")
                continue
            return full_content.strip()
        except Exception as e:
            print(f"  [Attempt {i+1}] LLM Error: {e}")
            time.sleep(5)
    return None

def parse_json(text):
    text = re.sub(r"^```(?:json)?\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text.strip())
    except:
        return None

# 2. Load Taxonomy
if not TAXONOMY_PATH.exists():
    raise FileNotFoundError("Run taxonomy induction in notebook first!")
TAXONOMY = json.loads(TAXONOMY_PATH.read_text())
taxonomy_str = "\n".join(f"- {name}: {desc}" for name, desc in TAXONOMY.items())
category_names = list(TAXONOMY.keys())

SYSTEM_PROMPT = f"""You are a YouTube title analyst. Classify each title into EXACTLY ONE category from this taxonomy:

{taxonomy_str}

Rules:
- Choose the category that best matches the RHETORICAL STRATEGY, not the topic.
- If the title is non-English, analyse its construction (hooks are universal across languages).
- Every title MUST be assigned a category — "Other" is not an option.
- Return ONLY valid JSON: [{{"id": <int>, "category": "<exact name>", "conf": <0.0-1.0>}}]"""

# 3. Load Data & Identify Elite Sample (Top 100 per Ctry/Cat)
print("Loading dataset...")
# Note: Re-using the logic from the notebook to load files correctly
# Since we are in the script, I'll assume we have the raw CSVs nearby
# or I'll just look for existing combined files if any. 
# Better: use the same logic to load from .cache/kagglehub
import kagglehub
dataset_path = Path(kagglehub.dataset_download("datasnaek/youtube-new"))

def smart_read(f):
    for enc in ("utf-8", "utf-8-sig", "cp949", "shift-jis", "latin-1"):
        try: return pd.read_csv(f, encoding=enc, on_bad_lines="skip")
        except: continue
    return pd.read_csv(f, encoding="latin-1", on_bad_lines="skip")

dfs = []
for f in dataset_path.glob("**/*videos.csv"):
    df_c = smart_read(f)
    df_c["country"] = f.stem[:2].upper()
    dfs.append(df_c)
df = pd.concat(dfs, ignore_index=True)
df = df.rename(columns={"view_count": "views"})
df["views"] = pd.to_numeric(df["views"], errors="coerce").fillna(0)

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

print("Fixing double-encodings in titles...")
df["title"] = df["title"].apply(smart_fix)

# Resolve category names (re-using notebook logic)
cat_map = {}
for jf in dataset_path.glob("**/*_category_id.json"):
    country = jf.stem[:2].upper()
    data = json.loads(jf.read_bytes().decode("utf-8", errors="replace"))
    for item in data.get("items", []):
        cat_map[(country, int(item["id"]))] = item["snippet"]["title"]

df["category_name"] = df.apply(lambda r: cat_map.get((r.country, int(r.category_id))) or cat_map.get(("US", int(r.category_id)), "Unknown"), axis=1)

# Deduplicate (keep highest views version)
df = df.sort_values("views", ascending=False).drop_duplicates(subset=["video_id", "country"]).reset_index(drop=True)

# Select Elite Sample: Top 100 per (Country, Category)
elite_df = df.groupby(["country", "category_name"], group_keys=False).apply(lambda g: g.head(100)).reset_index(drop=True)
unique_titles = elite_df.drop_duplicates(subset=["title"])

print(f"Total elite videos: {len(elite_df)}")
print(f"Unique titles to classify: {len(unique_titles)}")

# 4. Classification
results = {}
if CACHE_PATH.exists():
    results = json.loads(CACHE_PATH.read_text())
    print(f"Loaded {len(results)} cached results.")

# Merge in old cache if exists
if OLD_CACHE_PATH.exists():
    old_data = json.loads(OLD_CACHE_PATH.read_text())
    # Note: old_data keys might be indices, need to match by title or similar
    # But for simplicity, we'll just run them if they aren't in 'results' by title
    pass

# We'll use 'title' as the key in our cache for robustness across runs
todo = unique_titles[~unique_titles["title"].isin(results.keys())]
print(f"Remaining to classify: {len(todo)}")

batch_size = 3
batches = [todo.iloc[i:i+batch_size] for i in range(0, len(todo), batch_size)]

def process_batch(batch):
    titles_batch = batch["title"].tolist()
    user_msg = "\n".join(f"{i}: {t}" for i, t in enumerate(titles_batch))
    
    raw = llm_call(SYSTEM_PROMPT, user_msg)
    if not raw: return []
    
    parsed = parse_json(raw)
    if not parsed: return []
    
    batch_results = []
    for i, item in enumerate(parsed):
        if not item:
            continue
        if isinstance(item, str):
            idx = i
            cat = item
            conf = 0.95
        elif isinstance(item, dict):
            idx = item.get("id")
            if idx is None:
                idx = i
            cat = item.get("category", "")
            conf = item.get("conf", 0.95)
        else:
            continue

        if idx < len(titles_batch):
            title = titles_batch[idx]
            if not cat:
                continue
            if cat not in category_names:
                import difflib
                matches = difflib.get_close_matches(cat, category_names, n=1)
                cat = matches[0] if matches else category_names[0]
            
            batch_results.append((title, {
                "category": cat,
                "conf": conf
            }))
    return batch_results

print(f"Starting sequential classification...")
try:
    batches_done = 0
    for batch in tqdm(batches, desc="Classifying Elite Hooks"):
        res = process_batch(batch)
        if not res:
            print("  ⚠️ Batch failed entirely")
        else:
            for title, info in res:
                results[title] = info
        
        # Save every 5 batches
        batches_done += 1
        if batches_done % 5 == 0:
            CACHE_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False))
            print(f"Intermediate save at {batches_done} batches. Total results: {len(results)}")

except KeyboardInterrupt:
    print("Stopped by user. Saving progress...")
finally:
    CACHE_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"Done. Total classified: {len(results)}")
