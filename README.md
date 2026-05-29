# Project of Data Visualization (COM-480)

| Student's name | SCIPER |
| -------------- | ------ |
| Nastaran Hashemisanjani | 388010 |
| Oscar Goudet | 314512 |
| Garik Sahakyan | 314372 |
| Bich Ngoc Doan | 395722 |

## How this repository is organized

- **Root folder `/`** — Static front-end website files (**`index.html`**, **`css/style.css`**, **`js/`**, and **`public/`**). Serves as the direct source of truth for automated deployment.
- **`data/`** — Raw and processed inputs for the pipeline (e.g. merged trending tables used by analysis).
- **`analysis/`** — Project-wide precompute. Run **`analysis/precompute.ipynb`** (or execute **`analysis/generate_precompute.py`**) to compile and build **`public/data.json`** directly in the root directory, powering all interactive visualizations.
- **`code/`** — Supporting code and NLP assets (e.g. **`code/text_analysis/`** containing hook labelling systems and classified data models under `code/text_analysis/data/`).
- **`milestone1/`** — Milestone 1 deliverables: **`milestone1.ipynb`**, **`milestone1.md`**, and report figures under **`milestone1/images/`**.
- **`milestone2/`** — Milestone 2 exploration: analysis notebooks, **`exploration_images/`** (exported PNG/HTML), and **`map_ui_export.py`**.

### Site preview & Automatic Deployment

**Published URL:** [com-480-data-visualization.github.io/chartistry](https://com-480-data-visualization.github.io/chartistry/)

**Local Preview (Run directly from repository root):**
```bash
python3 -m http.server 8080
```
Open [http://localhost:8080](http://localhost:8080) in your web browser.

[Milestone 1](milestone1/) • [Milestone 2](milestone2/)

### Dataset

This project is based on the [YouTube Trending Video Statistics](https://www.kaggle.com/datasets/datasnaek/youtube-new) dataset by Mitchell J, available on Kaggle.