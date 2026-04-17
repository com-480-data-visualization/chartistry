# Milestone 2 — exploratory workspace

This folder holds **milestone 2 exploration**: long-form analysis notebooks, exported figures, and standalone HTML prototypes. It is separate from the **milestone 1** submission (`milestone1/`) and from the **shared site + pipeline** at the repo root (`website/`, `analysis/`, `data/`, `code/`).

| What | Where |
|------|--------|
| **Milestone 1 deliverables** | `../milestone1/` (`milestone1.ipynb`, `milestone1.md`, figures in `milestone1/images/`) |
| **Kaggle / merged CSVs** | `../data/` (repo root) |
| **Precompute → site `data.json`** | `../analysis/precompute.ipynb` → `../website/public/data.json` |
| **Production static site** | `../website/` |
| **Text analysis / hook labelling** | `../code/text_analysis/` |
| **Deploy GitHub Pages** | from repo root: `../scripts/deploy-gh-pages.sh` (or copy `../website/` to `gh-pages` as documented in the main README) |

## What is in `milestone2/`

| File / folder | Role |
|---------------|------|
| **`datastory.ipynb`** | Data-story style static figures (pandas, matplotlib, seaborn); writes PNGs under `exploration_images/`. |
| **`datastory_interactive.ipynb`** | Interactive Plotly charts; exports several `datastory_interactive_*.html` files and a combined dashboard into `exploration_images/`. **Requires `plotly`** (see below). |
| **`datastory_map.ipynb`** | Map-focused narrative; can invoke **`map_ui_export.py`** to regenerate choropleth HTML. |
| **`category_analysis.ipynb`** | Category-centric exploration (country mix within category, channel overlap, etc.). |
| **`country_analysis.ipynb`** | Country-centric exploration (category mix, overlaps, NLP-style title summaries where applicable). |
| **`map_ui_export.py`** | Builds self-contained map HTML (Plotly.js via CDN + vanilla controls). Reads CSVs from `../data/`, writes e.g. `exploration_images/datastory_interactive_map_controls.html`. Run from this folder: `python map_ui_export.py`. |
| **`exploration_images/`** | Exported **PNG** plots and **HTML** prototypes (maps, dashboards, interactive slices). Safe to regenerate from the notebooks / script. |

## Paths and working directory

- Notebooks assume **`data = "../data/"`** (Kaggle-style `XXvideos.csv` and related files at the **repo root** `data/`).
- Run Jupyter with **kernel cwd = `milestone2/`** (open the notebook from this directory or `cd milestone2` before starting Jupyter) so relative paths resolve correctly.
- `map_ui_export.py` uses `ROOT.parent / "data"` for the same `../data/` layout.

## Dependencies

Minimal stack used across most notebooks:

```text
pandas, numpy, matplotlib, seaborn
```

Additional install for **`datastory_interactive.ipynb`**:

```bash
pip install plotly
```

Optional (only if you use Plotly’s static PNG export in that notebook): `pip install kaleido`.

`map_ui_export.py` only needs **pandas** (plus the standard library) to run; exported HTML loads Plotly from a CDN in the browser.

## Local site preview (final visualization)

From the repo root:

```bash
cd website
python3 -m http.server 8080
```

Then open the URL shown in the terminal (not the milestone 2 HTML exports—those are separate prototypes under `exploration_images/`).
