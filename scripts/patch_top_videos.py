"""Add publish_time to every top_video entry in public/data.json using the raw CSVs."""
import csv, json, os, sys

ROOT     = os.path.join(os.path.dirname(__file__), '..')
DATA_DIR = os.path.join(ROOT, 'data')
OUT_FILE = os.path.join(ROOT, 'public', 'data.json')

COUNTRIES = ['CA','DE','FR','GB','IN','JP','KR','MX','RU','US']

# Build video_id -> publish_time lookup from CSVs
print('Building lookup table…', file=sys.stderr)
pub_map = {}
for code in COUNTRIES:
    path = os.path.join(DATA_DIR, f'{code}videos.csv')
    with open(path, encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            vid = row.get('video_id','').strip()
            pub = row.get('publish_time','').strip()
            if vid and pub and vid not in pub_map:
                pub_map[vid] = pub

print(f'Lookup ready: {len(pub_map):,} unique video IDs', file=sys.stderr)

with open(OUT_FILE, encoding='utf-8') as f:
    data = json.load(f)

patched = 0
for country in data.get('by_country_category', {}).values():
    for combo in country.values():
        for v in combo.get('top_videos', []):
            if 'pub' not in v:
                v['pub'] = pub_map.get(v['video_id'], '')
                patched += 1

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

print(f'✅  Patched {patched} top_video entries → {OUT_FILE}', file=sys.stderr)
