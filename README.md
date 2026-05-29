# Chartistry — What Makes a Video Go Viral?

**COM-480 Data Visualization — EPFL**

| Student's name | SCIPER |
| -------------- | ------ |
| Nastaran Hashemisanjani | 388010 |
| Oscar Goudet | 314512 |
| Garik Sahakyan | 314372 |
| Bich Ngoc Doan | 395722 |

📄 **[Process Book](Process%20Book%20-%20Viral%20Youtube%20Videos.pdf)** • 🎬 **[Screencast](https://youtu.be/LlbGmVOgoL8)**

---

## About

Chartistry is an interactive data visualization exploring what makes YouTube videos trend across 10 countries and 18 content categories. Built on 207,000 trending videos, it guides users through four scenes: a global choropleth map, a per-niche formula explorer, and a Viral Duel mini-game where you guess which of two real videos went more viral.

**Live site:** [com-480-data-visualization.github.io/chartistry](https://com-480-data-visualization.github.io/chartistry/)

---

## Technical Setup

### Stack
- **Frontend:** Vanilla JavaScript (ES6+), D3.js v7, TopoJSON
- **Data pipeline:** Python 3 (pandas, json)
- **Hosting:** GitHub Pages (auto-deploys from `master` branch root)

### Local preview

No build step required — serve the repo root directly:

```bash
python3 -m http.server 8080
```

Open [http://localhost:8080](http://localhost:8080).

### Rebuilding the data

`public/data.json` (the precomputed dataset powering all visualisations) is committed to the repo. To rebuild it from the raw CSVs:

```bash
# Install dependencies
pip install pandas numpy

# Run the precompute pipeline
python analysis/generate_precompute.py
# or open and run analysis/precompute.ipynb
```

This reads the raw CSVs from `data/` and writes `public/data.json` to the root.

---

## Repository Structure

- **`/`** — Static website (`index.html`, `css/`, `js/`, `public/`) — deployed as-is to GitHub Pages
- **`data/`** — Raw CSV files from the Kaggle dataset (one per country)
- **`analysis/`** — Precompute pipeline (`generate_precompute.py` / `precompute.ipynb`)
- **`code/`** — NLP and hook classification code (`code/text_analysis/`)
- **`milestone1/`** — Milestone 1 deliverables
- **`milestone2/`** — Milestone 2 exploration notebooks

---

## Dataset

Based on the [YouTube Trending Video Statistics](https://www.kaggle.com/datasets/datasnaek/youtube-new) dataset by Mitchell J (Kaggle). Covers trending video metadata (title, views, likes, comments, category, publish time) for 10 countries: CA, DE, FR, GB, IN, JP, KR, MX, RU, US.

---

[Milestone 1](milestone1/) • [Milestone 2](milestone2/)