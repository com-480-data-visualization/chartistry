# Milestone 2 — exploratory workspace

This folder is **only** for notebooks and assets that are **not** the milestone 1 submission and **not** the shared site/pipeline at the repo root.

| What | Where |
|------|--------|
| **Milestone 1 deliverables** | `milestone1/` (`milestone1.ipynb`, `milestone1.md`, six figures in `milestone1/images/`) |
| **Kaggle CSVs** | `../data/` (repo root) |
| **Precompute → `data.json`** | `../analysis/precompute.ipynb` |
| **Static website** | `../website/` |
| **Text-analysis / hooks code** | `../code/text_analysis/` |

### In this folder (`milestone2/`)

- **Notebooks:** `datastory.ipynb`, `datastory_interactive.ipynb`, `datastory_map.ipynb`, `category_analysis.ipynb`, `country_analysis.ipynb`
- **`exploration_images/`** — extra plots and standalone HTML from exploration
- **`map_ui_export.py`** — choropleth HTML export (writes into `exploration_images/`)

Run these notebooks with **working directory = `milestone2/`** so `data = "../data/"` resolves to the repo `data/` folder.

**Local site preview:** from repo root, `cd website` then `python3 -m http.server 8080`.

**Deploy (GitHub Pages):** copy from `website/` at repo root (`index.html`, `css/`, `js/`, `public/data.json`).
