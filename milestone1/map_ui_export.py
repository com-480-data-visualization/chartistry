"""
Build self-contained interactive map HTML (Plotly.js + vanilla controls).
Run from milestone1/: python map_ui_export.py
Or from notebook: %run map_ui_export.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

try:
    ROOT = Path(__file__).resolve().parent
except NameError:
    ROOT = Path.cwd()

OUT_DIR = ROOT / "images"
OUT_HTML = OUT_DIR / "datastory_interactive_map_controls.html"
DATA_DIR = ROOT.parent / "data"

COUNTRY_ORDER = ["US", "GB", "CA", "DE", "FR", "IN", "KR", "MX", "JP", "RU"]
ISO3 = {c: x for c, x in zip(COUNTRY_ORDER, ["USA", "GBR", "CAN", "DEU", "FRA", "IND", "KOR", "MEX", "JPN", "RUS"])}
COUNTRY_FULL_NAME = {
    "US": "United States",
    "GB": "United Kingdom",
    "CA": "Canada",
    "DE": "Germany",
    "FR": "France",
    "IN": "India",
    "KR": "South Korea",
    "MX": "Mexico",
    "JP": "Japan",
    "RU": "Russia",
}
LOCATIONS = [ISO3[c] for c in COUNTRY_ORDER]
HOVER_NAMES = [COUNTRY_FULL_NAME[c] for c in COUNTRY_ORDER]

MIN_CAT_GLOBAL = 4000


def load_df() -> pd.DataFrame:
    frames = []
    for fname, code in [
        ("USvideos.csv", "US"),
        ("CAvideos.csv", "CA"),
        ("DEvideos.csv", "DE"),
        ("FRvideos.csv", "FR"),
        ("GBvideos.csv", "GB"),
        ("INvideos.csv", "IN"),
        ("JPvideos.csv", "JP"),
        ("KRvideos.csv", "KR"),
        ("MXvideos.csv", "MX"),
        ("RUvideos.csv", "RU"),
    ]:
        p = DATA_DIR / fname
        kw = {}
        if code in ("JP", "KR", "MX", "RU"):
            kw = dict(encoding="utf-8-sig", encoding_errors="replace", engine="python")
        d = pd.read_csv(p, **kw)
        d["country"] = code
        frames.append(d)
    df = pd.concat(frames, ignore_index=True).drop_duplicates()
    category_map = {
        1: "Film & Animation",
        2: "Autos & Vehicles",
        10: "Music",
        15: "Pets & Animals",
        17: "Sports",
        18: "Short Movies",
        19: "Travel & Events",
        20: "Gaming",
        21: "Videoblogging",
        22: "People & Blogs",
        23: "Comedy",
        24: "Entertainment",
        25: "News & Politics",
        26: "Howto & Style",
        27: "Education",
        28: "Science & Technology",
        29: "Nonprofits & Activism",
        30: "Movies",
        43: "Shows",
        44: "Trailers",
    }
    df["category"] = df["category_id"].map(category_map).fillna("Other")
    df["publish_time"] = pd.to_datetime(df["publish_time"], errors="coerce").dt.tz_localize(None)
    df["publish_hour"] = df["publish_time"].dt.hour
    df["like_rate"] = df["likes"] / df["views"]
    df["dislike_rate"] = df["dislikes"] / df["views"]
    df["comment_rate"] = df["comment_count"] / df["views"]
    df["like_dislike_ratio"] = df["likes"] / (df["dislikes"] + 1)
    return df


def build_payload(df: pd.DataFrame) -> dict:
    cat_totals = df.groupby("category").size().sort_values(ascending=False)

    cc = df.groupby(["category", "country"]).size().unstack(fill_value=0)
    for c in COUNTRY_ORDER:
        if c not in cc.columns:
            cc[c] = 0
    cc = cc[COUNTRY_ORDER]
    pct = cc.div(cc.sum(axis=1), axis=0).replace([float("inf"), float("-inf")], 0).fillna(0) * 100
    cats = [c for c in cat_totals.index if c in pct.index and cat_totals[c] >= 1][:24]

    categories: dict = {}
    hover_cat: dict = {}
    zmax_cat: dict = {}
    title_cat: dict = {}
    for cat in cats:
        row = pct.loc[cat]
        z = [float(row[c]) for c in COUNTRY_ORDER]
        categories[cat] = z
        mx = max(z) if z else 1.0
        zmax_cat[cat] = min(100.0, max(mx * 1.08, 4.0))
        n = int(cat_totals.get(cat, 0))
        extra = " · Few trending rows globally" if n < MIN_CAT_GLOBAL else ""
        title_cat[cat] = f"Category: {cat}{extra}"
        hover_cat[cat] = [
            f"{nm}<br><b>Share: {zv:.1f}%</b>" for nm, zv in zip(HOVER_NAMES, z)
        ]

    ENG = [
        ("like_rate", "Like rate"),
        ("dislike_rate", "Dislike rate"),
        ("comment_rate", "Comment rate"),
        ("like_dislike_ratio", "Like/dislike ratio"),
    ]
    engagement: dict = {}
    hover_eng: dict = {}
    zmax_eng: dict = {}
    title_eng: dict = {}
    for col, short in ENG:
        med = df.groupby("country")[col].median().reindex(COUNTRY_ORDER)
        z = [float(x) if pd.notna(x) else 0.0 for x in med.tolist()]
        engagement[col] = z
        mx = max(z) if z else 1e-9
        zmax_eng[col] = max(mx * 1.08, 1e-12)
        title_eng[col] = f"Engagement: median {short.lower()}"
        fmt = (lambda v: f"{v:.2f}") if col == "like_dislike_ratio" else (lambda v: f"{v:.5f}")
        hover_eng[col] = [f"{nm}<br><b>Median: {fmt(zv)}</b>" for nm, zv in zip(HOVER_NAMES, z)]

    hour_tab = df.groupby(["country", "publish_hour"]).size().unstack(fill_value=0)
    hour_tab = hour_tab.reindex(columns=list(range(24)), fill_value=0)
    hour_tab = hour_tab.reindex(index=COUNTRY_ORDER, fill_value=0)
    hour_pct = hour_tab.div(hour_tab.sum(axis=1), axis=0).replace([float("inf"), float("-inf")], 0).fillna(0) * 100

    hours: dict[str, list[float]] = {}
    hover_hour: dict[str, list[str]] = {}
    for h in range(24):
        z = [float(hour_pct.loc[c, h]) for c in COUNTRY_ORDER]
        hours[str(h)] = z
        hover_hour[str(h)] = [
            f"{nm}<br><b>Share: {zv:.2f}%</b>" for nm, zv in zip(HOVER_NAMES, z)
        ]

    all_hour_z = [hours[str(h)] for h in range(24)]
    flat = [x for row in all_hour_z for x in row]
    zmax_hour = max(flat) * 1.05 if flat else 10.0
    zmax_hour = min(100.0, max(zmax_hour, 1.0))

    return {
        "locations": LOCATIONS,
        "categories": categories,
        "hover_cat": hover_cat,
        "zmax_cat": zmax_cat,
        "title_cat": title_cat,
        "engagement": engagement,
        "hover_eng": hover_eng,
        "zmax_eng": zmax_eng,
        "title_eng": title_eng,
        "eng_labels": {k: v for k, v in ENG},
        "hours": hours,
        "hover_hour": hover_hour,
        "zmax_hour": zmax_hour,
        "cat_keys": cats,
        "eng_keys": [e[0] for e in ENG],
    }


def html_page(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=False)
    data_json = data_json.replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Trending map — category, engagement, or publish time</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <style>
    :root {{
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      background: #f8fafc;
    }}
    body {{ margin: 0; padding: 16px 20px 28px; max-width: 1100px; margin-left: auto; margin-right: auto; }}
    h1 {{ font-size: 1.35rem; margin: 0 0 8px; }}
    .sub {{ color: #475569; font-size: 0.95rem; margin-bottom: 16px; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 12px; }}
    .mode-btn {{
      padding: 10px 18px; border: 1px solid #cbd5e1; border-radius: 8px;
      background: #fff; cursor: pointer; font-size: 0.95rem; font-weight: 600;
    }}
    .mode-btn:hover {{ background: #f1f5f9; }}
    .mode-btn.active {{ background: #1d4ed8; color: #fff; border-color: #1d4ed8; }}
    .hidden {{ display: none !important; }}
    .panel {{ margin-top: 8px; min-height: 42px; }}
    select {{
      padding: 8px 12px; font-size: 0.95rem; border-radius: 8px; border: 1px solid #cbd5e1;
      min-width: 260px; max-width: 100%; background: #fff;
    }}
    .slider-wrap {{
      margin-top: 18px; padding: 14px 16px; background: #fff; border-radius: 10px;
      border: 1px solid #e2e8f0;
    }}
    .slider-wrap label {{ display: block; margin-bottom: 8px; font-weight: 600; color: #334155; }}
    input[type=range] {{ width: 100%; max-width: 520px; }}
    #map {{ width: 100%; height: 560px; margin-top: 8px; }}
    .title-line {{ font-size: 1.05rem; font-weight: 700; color: #0f172a; margin: 10px 0 4px; }}
    .hint {{ font-size: 0.85rem; color: #64748b; }}
  </style>
</head>
<body>
  <h1>Where does trending traffic sit on the map?</h1>
  <p class="sub">Choose <strong>Category</strong> or <strong>Engagement</strong> (then pick from the menu), or <strong>Publication time</strong> and scrub the day in <strong>UTC</strong>.</p>

  <div class="toolbar">
    <button type="button" class="mode-btn" id="btnCat">Category</button>
    <button type="button" class="mode-btn" id="btnEng">Engagement</button>
    <button type="button" class="mode-btn" id="btnTime">Publication time</button>
  </div>

  <div class="panel hidden" id="panelCat">
    <label for="selCat">Category</label><br/>
    <select id="selCat"><option value="">— Select —</option></select>
  </div>
  <div class="panel hidden" id="panelEng">
    <label for="selEng">Metric</label><br/>
    <select id="selEng"><option value="">— Select —</option></select>
  </div>

  <div class="title-line" id="dynTitle">Select a mode above</div>
  <div id="map"></div>

  <div class="panel hidden" id="panelTime">
    <div class="slider-wrap">
      <label for="hourSlider">Hour of publication (UTC): <span id="hourVal">0</span></label>
      <input type="range" id="hourSlider" min="0" max="23" value="0" step="1" />
      <p class="hint">Colour = share of that country’s trending rows published in this hour (within-country %).</p>
    </div>
  </div>

  <script>
  const DATA = {data_json};
  const ISO = DATA.locations;
  const EMPTY = ISO.map(() => null);

  const layout = {{
    geo: {{
      showframe: false,
      showcoastlines: true,
      coastlinecolor: "rgba(70,70,70,0.35)",
      projection: {{ type: "natural earth" }},
      bgcolor: "rgba(0,0,0,0)",
      landcolor: "rgba(228,228,228,0.95)",
      showocean: true,
      oceancolor: "rgba(245,248,252,1)",
    }},
    margin: {{ l: 0, r: 10, t: 10, b: 0 }},
    height: 520,
    font: {{ family: "system-ui, sans-serif", size: 13 }},
  }};

  function emptyTrace() {{
    return {{
      type: "choropleth",
      locationmode: "ISO-3",
      locations: ISO,
      z: EMPTY,
      text: ISO.map(() => ""),
      hoverinfo: "text",
      colorscale: [[0, "#e2e8f0"], [1, "#e2e8f0"]],
      showscale: false,
      marker: {{ line: {{ width: 0.5, color: "#fff" }} }},
    }};
  }}

  const plotDiv = document.getElementById("map");
  Plotly.newPlot(plotDiv, [emptyTrace()], layout, {{ displayModeBar: true, displaylogo: false, scrollZoom: true }});

  const selCat = document.getElementById("selCat");
  const selEng = document.getElementById("selEng");
  const panelCat = document.getElementById("panelCat");
  const panelEng = document.getElementById("panelEng");
  const panelTime = document.getElementById("panelTime");
  const btnCat = document.getElementById("btnCat");
  const btnEng = document.getElementById("btnEng");
  const btnTime = document.getElementById("btnTime");
  const dynTitle = document.getElementById("dynTitle");
  const hourSlider = document.getElementById("hourSlider");
  const hourVal = document.getElementById("hourVal");

  for (const c of DATA.cat_keys) {{
    const o = document.createElement("option");
    o.value = c; o.textContent = c;
    selCat.appendChild(o);
  }}
  for (const k of DATA.eng_keys) {{
    const o = document.createElement("option");
    o.value = k;
    o.textContent = DATA.eng_labels[k] || k;
    selEng.appendChild(o);
  }}

  let mode = null;

  function setActive(btn) {{
    [btnCat, btnEng, btnTime].forEach(b => b.classList.remove("active"));
    if (btn) btn.classList.add("active");
  }}

  function showEmptyMap() {{
    Plotly.react(plotDiv, [emptyTrace()], layout, {{ displayModeBar: true, displaylogo: false, scrollZoom: true }});
    dynTitle.textContent = "Map cleared — choose an option";
  }}

  function drawCategory(name) {{
    const z = DATA.categories[name];
    const text = DATA.hover_cat[name];
    const zmax = DATA.zmax_cat[name];
    const t = DATA.title_cat[name];
    dynTitle.textContent = t;
    Plotly.react(plotDiv, [{{
      type: "choropleth",
      locationmode: "ISO-3",
      locations: ISO,
      z: z,
      text: text,
      hoverinfo: "text",
      colorscale: "Blues",
      reversescale: true,
      zmin: 0,
      zmax: zmax,
      marker: {{ line: {{ width: 0.6, color: "#fff" }} }},
      colorbar: {{ title: {{ text: "% of category rows", side: "right" }} }},
    }}], layout, {{ displayModeBar: true, displaylogo: false, scrollZoom: true }});
  }}

  function drawEngagement(key) {{
    const z = DATA.engagement[key];
    const text = DATA.hover_eng[key];
    const zmax = DATA.zmax_eng[key];
    dynTitle.textContent = DATA.title_eng[key];
    Plotly.react(plotDiv, [{{
      type: "choropleth",
      locationmode: "ISO-3",
      locations: ISO,
      z: z,
      text: text,
      hoverinfo: "text",
      colorscale: "Blues",
      reversescale: true,
      zmin: 0,
      zmax: zmax,
      marker: {{ line: {{ width: 0.6, color: "#fff" }} }},
      colorbar: {{ title: {{ text: "Median (per country)", side: "right" }} }},
    }}], layout, {{ displayModeBar: true, displaylogo: false, scrollZoom: true }});
  }}

  function drawHour(h) {{
    const key = String(h);
    const z = DATA.hours[key];
    const text = DATA.hover_hour[key];
    const zmax = DATA.zmax_hour;
    dynTitle.textContent = "Publication time (UTC) — hour " + h;
    Plotly.react(plotDiv, [{{
      type: "choropleth",
      locationmode: "ISO-3",
      locations: ISO,
      z: z,
      text: text,
      hoverinfo: "text",
      colorscale: "YlGnBu",
      reversescale: true,
      zmin: 0,
      zmax: zmax,
      marker: {{ line: {{ width: 0.6, color: "#fff" }} }},
      colorbar: {{ title: {{ text: "% within country", side: "right" }} }},
    }}], layout, {{ displayModeBar: true, displaylogo: false, scrollZoom: true }});
  }}

  btnCat.onclick = () => {{
    mode = "cat";
    setActive(btnCat);
    panelCat.classList.remove("hidden");
    panelEng.classList.add("hidden");
    panelTime.classList.add("hidden");
    selEng.value = "";
    hourSlider.value = 0;
    hourVal.textContent = "0";
    showEmptyMap();
  }};
  btnEng.onclick = () => {{
    mode = "eng";
    setActive(btnEng);
    panelEng.classList.remove("hidden");
    panelCat.classList.add("hidden");
    panelTime.classList.add("hidden");
    selCat.value = "";
    showEmptyMap();
  }};
  btnTime.onclick = () => {{
    mode = "time";
    setActive(btnTime);
    panelTime.classList.remove("hidden");
    panelCat.classList.add("hidden");
    panelEng.classList.add("hidden");
    selCat.value = "";
    selEng.value = "";
    const h = parseInt(hourSlider.value, 10);
    hourVal.textContent = String(h);
    drawHour(h);
  }};

  selCat.onchange = () => {{
    const v = selCat.value;
    if (!v) {{ showEmptyMap(); return; }}
    drawCategory(v);
  }};
  selEng.onchange = () => {{
    const v = selEng.value;
    if (!v) {{ showEmptyMap(); return; }}
    drawEngagement(v);
  }};

  hourSlider.oninput = () => {{
    const h = parseInt(hourSlider.value, 10);
    hourVal.textContent = String(h);
    if (mode === "time") drawHour(h);
  }};
  </script>
</body>
</html>
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_df()
    payload = build_payload(df)
    html = html_page(payload)
    OUT_HTML.write_text(html, encoding="utf-8")
    print("Wrote", OUT_HTML.resolve())
    alt = OUT_DIR / "datastory_interactive_map.html"
    alt.write_text(html, encoding="utf-8")
    print("Wrote", alt.resolve())


if __name__ == "__main__":
    main()
