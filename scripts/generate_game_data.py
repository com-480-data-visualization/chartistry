"""Generate public/game_data.json for the Viral Duel game.

Reads all country CSVs, deduplicates by video_id (keeps max views row),
groups by (country, category), and writes a compact JSON file.
"""
import csv
import json
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'public', 'game_data.json')

COUNTRIES = ['CA', 'DE', 'FR', 'GB', 'IN', 'JP', 'KR', 'MX', 'RU', 'US']
MIN_VIDEOS = 8   # combos with fewer videos are dropped
MAX_VIDEOS = 60  # cap per combo to keep file size sane

def load_cat_map(code):
    path = os.path.join(DATA_DIR, f'{code}_category_id.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return {item['id']: item['snippet']['title'] for item in data['items']}

def main():
    combos = {}  # (country, cat) -> {video_id: {...}}

    for code in COUNTRIES:
        cat_map = load_cat_map(code)
        csv_path = os.path.join(DATA_DIR, f'{code}videos.csv')
        print(f'Loading {code}…', file=sys.stderr)

        with open(csv_path, encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                vid_id = row.get('video_id', '').strip()
                if not vid_id or vid_id == 'video_id':
                    continue
                if row.get('video_error_or_removed', '').lower() == 'true':
                    continue

                try:
                    views = int(row.get('views') or 0)
                except ValueError:
                    views = 0

                cat_id  = row.get('category_id', '').strip()
                cat     = cat_map.get(cat_id, 'Unknown')
                title   = row.get('title', '').strip()
                channel = row.get('channel_title', '').strip()
                pub     = row.get('publish_time', '').strip()

                key = (code, cat)
                if key not in combos:
                    combos[key] = {}
                existing = combos[key].get(vid_id)
                if existing is None or existing['views'] < views:
                    combos[key][vid_id] = {
                        'video_id': vid_id,
                        'title':    title,
                        'channel':  channel,
                        'views':    views,
                        'pub':      pub,   # ISO datetime string
                    }

    output = {}
    kept = 0
    for (country, cat), vids_dict in combos.items():
        videos = list(vids_dict.values())
        if len(videos) < MIN_VIDEOS:
            continue
        # Sort by views descending; keep a spread so pairs aren't trivially easy
        videos.sort(key=lambda v: v['views'], reverse=True)
        videos = videos[:MAX_VIDEOS]
        key = f'{country}||{cat}'
        output[key] = {'country': country, 'category': cat, 'videos': videos}
        kept += 1

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, separators=(',', ':'))

    size_kb = os.path.getsize(OUT_FILE) / 1024
    print(f'✅  {kept} combos → {OUT_FILE} ({size_kb:.0f} KB)', file=sys.stderr)

if __name__ == '__main__':
    main()
