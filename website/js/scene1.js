// scene1.js — World choropleth + Category×Country heatmap
// Use country name from properties (d.properties.name) — more reliable than d.id
// which topojson-client may convert differently across versions.
const NAME_TO_CODE = {
  'Canada': 'CA',
  'Germany': 'DE',
  'France': 'FR',
  'United Kingdom': 'GB',
  'India': 'IN',
  'Japan': 'JP',
  'South Korea': 'KR',
  'Mexico': 'MX',
  'Russia': 'RU',
  'United States of America': 'US',
};

let _s1data = null;
let _topo = null;
let _metric = 'avg_views';
let _pubHour = 0;
let _onCountryClick = null;

async function initScene1(data, onCountryClick) {
  _s1data = data;
  _onCountryClick = onCountryClick;

  _topo = await d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json');
  setupMetricToggle();

  const pubSlider = document.getElementById('pub-hour-slider');
  const pubVal = document.getElementById('pub-hour-val');
  if (pubSlider && pubVal) {
    pubSlider.addEventListener('input', () => {
      _pubHour = +pubSlider.value;
      pubVal.textContent = String(_pubHour);
      if (_metric === 'publish_time') repaintMapFills(true);
    });
  }

  function runDraw() {
    try { drawMap(); } catch (e) { console.error('drawMap error:', e); }
    try { drawCatHeatmap(); } catch (e) { console.error('drawCatHeatmap error:', e); }
  }

  // Draw when Scene 1 first scrolls into view (guarantees real layout width)
  let drawn = false;
  const obs = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting && !drawn) {
      drawn = true; obs.disconnect(); runDraw();
    }
  }, { threshold: 0.05 });
  obs.observe(document.getElementById('scene-1'));

  // Also draw immediately in case scene-1 is already visible on load
  setTimeout(() => {
    if (!drawn) {
      const rect = document.getElementById('scene-1').getBoundingClientRect();
      if (rect.top < window.innerHeight + 100) { drawn = true; obs.disconnect(); runDraw(); }
    }
  }, 500);
}

/* ── Choropleth map ── */
function drawMap() {
  const el = document.getElementById('world-map');
  el.innerHTML = '';
  const W = Math.max(el.clientWidth, el.getBoundingClientRect().width, 600);
  const H = W * 0.52;

  const svg = d3.select('#world-map').append('svg')
    .attr('viewBox', `0 0 ${W} ${H}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');

  const projection = d3.geoNaturalEarth1().scale(W / 6.3).translate([W / 2, H / 2]);
  const path = d3.geoPath().projection(projection);

  const byCountry = _s1data.global.by_country;
  const vals = Object.values(byCountry).map(d => d.avg_views).filter(Boolean);
  // Log scale so small/large differences are visible; start from #1c1c1c → bright red
  const colorScale = d3.scaleLog()
    .domain([d3.min(vals) * 0.5, d3.max(vals)])
    .range(['#3a1a1a', '#ff3333'])
    .clamp(true);

  const countries = topojson.feature(_topo, _topo.objects.countries);
  const flags = _s1data.country_flags || {};

  svg.selectAll('path')
    .data(countries.features)
    .join('path')
    .attr('class', d => {
      const code = NAME_TO_CODE[d.properties?.name];
      return `cpath${code && byCountry[code] ? ' has-data' : ''}`;
    })
    .attr('d', path)
    .attr('fill', d => {
      const code = NAME_TO_CODE[d.properties?.name];
      if (!code || !byCountry[code]) return '#1c1c1c';
      return colorScale(metricVal(code));
    })
    .on('mouseenter', (event, d) => {
      const code = NAME_TO_CODE[d.properties?.name];
      const info = code && byCountry[code];
      if (!info) return;
      showTooltip(mapCountryTooltip(code, flags), event);
    })
    .on('mousemove', moveTooltip)
    .on('mouseleave', hideTooltip)
    .on('click', (event, d) => {
      const code = NAME_TO_CODE[d.properties?.name];
      if (code && byCountry[code] && _onCountryClick) _onCountryClick(code);
    });

  // Legend
  document.getElementById('map-legend').innerHTML = `
    <span>Low</span><div class="leg-grad"></div><span>High</span>
    <span style="margin-left:auto;color:#555">${metricLabel()}</span>
  `;
  syncMapMetricDefinition();
  const pubPanel = document.getElementById('pub-hour-panel');
  if (pubPanel) pubPanel.hidden = _metric !== 'publish_time';
}

function publishHourZmax() {
  const z = _s1data.global?.publish_hour_zmax;
  return typeof z === 'number' && z > 0 ? z : 10;
}

function pubHourShare(code, h) {
  const root = _s1data.global?.publish_hour_share;
  if (!root) return 0;
  const row = root[String(h)];
  return row && typeof row[code] === 'number' ? row[code] : 0;
}

function mapCountryTooltip(code, flags) {
  const info = _s1data.global.by_country[code];
  if (!info) return '';
  let metricRows = '';
  if (_metric === 'publish_time') {
    const sh = pubHourShare(code, _pubHour);
    metricRows = `
        <div class="tt-row"><span>UTC hour</span><span class="tt-val">${_pubHour}:00</span></div>
        <div class="tt-row"><span>Share of publishes</span><span class="tt-val">${sh.toFixed(2)}%</span></div>`;
  } else if (_metric === 'avg_views') {
    metricRows = `<div class="tt-row"><span>Avg Views</span><span class="tt-val">${fmtViews(info.avg_views)}</span></div>`;
  } else if (_metric === 'video_count') {
    metricRows = `<div class="tt-row"><span>Videos</span><span class="tt-val">${info.total_videos.toLocaleString()}</span></div>`;
  } else {
    metricRows = `<div class="tt-row"><span>Engagement (avg)</span><span class="tt-val">${metricVal(code).toFixed(4)}</span></div>`;
  }
  return `
        <div class="tt-flag">${flags[code] || ''}</div>
        <div class="tt-name">${info.name}</div>
        ${metricRows}
        <div class="tt-row"><span>Top category</span><span class="tt-val">${info.top_category}</span></div>
      `;
}

function metricVal(code) {
  const d = _s1data.global.by_country[code];
  if (_metric === 'avg_views') return d?.avg_views || 0;
  if (_metric === 'video_count') return d?.total_videos || 0;
  if (_metric === 'publish_time') return pubHourShare(code, _pubHour);
  // engagement: mean across categories
  const em = _s1data.global.engage_heatmap[code] || {};
  const vals = Object.values(em);
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
}

function metricLabel() {
  return {
    avg_views: 'Avg Views',
    video_count: 'Video Count',
    engagement: 'Engagement Rate',
    publish_time: 'Publication share',
  }[_metric];
}

/** Shown under the map legend so the engagement definition is explicit. */
function metricDefinitionText() {
  if (_metric === 'engagement') {
    return (
      'Engagement rate = (likes + comments) ÷ views on each video; dislikes are not included. '
      + 'Map color for a country is the average of that rate across content categories (each category weighted equally).'
    );
  }
  if (_metric === 'publish_time') {
    return (
      'Publication time uses each video’s publish timestamp in UTC. For the selected hour, the map shows '
      + 'that country’s share of its own trending rows published in that hour (within-country %; all hours sum to 100%). '
      + 'Use the slider to see how the pattern shifts through the day.'
    );
  }
  if (_metric === 'avg_views') {
    return 'Average views among all trending videos from that country in the dataset.';
  }
  return 'Total count of trending video rows from that country in the dataset.';
}

function syncMapMetricDefinition() {
  const el = document.getElementById('map-metric-def');
  if (!el) return;
  el.textContent = metricDefinitionText();
}

function repaintMapFills(animate) {
  const apply = () => {
    let cs;
    if (_metric === 'publish_time') {
      cs = d3.scaleSequential().domain([0, publishHourZmax()])
        .interpolator(t => d3.interpolateRgb('#1c1c1c', '#ff4444')(t));
    } else {
      const vals = _s1data.countries.map(c => metricVal(c)).filter(Boolean);
      cs = d3.scaleSequential().domain([0, d3.max(vals) || 1])
        .interpolator(t => d3.interpolateRgb('#1c1c1c', '#ff4444')(t));
    }
    const sel = d3.selectAll('.has-data');
    const fillFn = (d) => {
      const code = NAME_TO_CODE[d.properties?.name];
      return code ? cs(metricVal(code)) : '#1c1c1c';
    };
    if (animate) sel.transition().duration(500).attr('fill', fillFn);
    else sel.attr('fill', fillFn);
  };
  apply();
}

function setupMetricToggle() {
  document.querySelectorAll('.tog').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tog').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      _metric = btn.dataset.metric;
      const pubPanel = document.getElementById('pub-hour-panel');
      if (pubPanel) pubPanel.hidden = _metric !== 'publish_time';
      if (_metric === 'publish_time') {
        const s = document.getElementById('pub-hour-slider');
        const v = document.getElementById('pub-hour-val');
        if (s) _pubHour = +s.value;
        if (v) v.textContent = String(_pubHour);
      }
      repaintMapFills(true);
      document.getElementById('map-legend').querySelector('span:last-child').textContent = metricLabel();
      syncMapMetricDefinition();
    });
  });
}

/* ── Category × Country heatmap ── */
function drawCatHeatmap() {
  const el = document.getElementById('cat-heatmap');
  el.innerHTML = '';

  const { count_heatmap, views_heatmap } = _s1data.global;
  const countries = _s1data.countries;
  const categories = _s1data.categories.filter(c => c !== 'Unknown');
  const flags = _s1data.country_flags || {};

  const W = el.clientWidth || 360;
  const ML = 128, MT = 22, cellH = 21, cellW = Math.max(18, (W - ML) / countries.length);
  const H = categories.length * cellH + MT + 10;

  const svg = d3.select('#cat-heatmap').append('svg')
    .attr('viewBox', `0 0 ${W} ${H}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');

  // Color: pct of country total
  const pcts = [];
  categories.forEach(cat => countries.forEach(c => {
    const tot = Object.values(count_heatmap[c] || {}).reduce((a, b) => a + b, 0);
    if (tot) pcts.push(((count_heatmap[c] || {})[cat] || 0) / tot * 100);
  }));
  const cs = d3.scaleSequential()
    .domain([0, d3.quantile(pcts.sort(d3.ascending), 0.95)])
    .interpolator(t => d3.interpolateRgb('#181818', '#ff4444')(t));

  // Country headers (flags)
  svg.selectAll('.hm-ch').data(countries).join('text')
    .attr('class', 'hm-ch')
    .attr('x', (d, i) => ML + i * cellW + cellW / 2)
    .attr('y', MT - 5)
    .attr('text-anchor', 'middle')
    .attr('font-size', 11)
    .attr('fill', '#666')
    .text(d => flags[d] || d);

  categories.forEach((cat, ci) => {
    const g = svg.append('g');

    // Row label
    g.append('text')
      .attr('x', ML - 5).attr('y', MT + ci * cellH + cellH / 2 + 4)
      .attr('text-anchor', 'end').attr('font-size', 9.5).attr('fill', '#777')
      .text(cat.length > 18 ? cat.slice(0, 17) + '…' : cat);

    countries.forEach((code, ci2) => {
      const tot = Object.values(count_heatmap[code] || {}).reduce((a, b) => a + b, 0);
      const cnt = (count_heatmap[code] || {})[cat] || 0;
      const pct = tot > 0 ? cnt / tot * 100 : 0;
      const avgV = (views_heatmap[code] || {})[cat] || 0;

      const cell = g.append('g')
        .attr('class', 'hm-cell')
        .attr('transform', `translate(${ML + ci2 * cellW},${MT + ci * cellH})`);

      cell.append('rect')
        .attr('width', cellW - 1).attr('height', cellH - 1).attr('rx', 2)
        .attr('fill', pct > 0 ? cs(pct) : '#111')
        .attr('stroke', 'transparent').attr('stroke-width', '1');

      cell.on('mouseenter', event => {
        if (!pct) return;
        showTooltip(`
          <div class="tt-name">${flags[code] || code} × ${cat}</div>
          <div class="tt-row"><span>Share</span><span class="tt-val">${pct.toFixed(1)}%</span></div>
          <div class="tt-row"><span>Avg Views</span><span class="tt-val">${fmtViews(avgV)}</span></div>
          <div class="tt-row"><span>Count</span><span class="tt-val">${cnt.toLocaleString()}</span></div>
        `, event);
      })
        .on('mousemove', moveTooltip)
        .on('mouseleave', hideTooltip)
        .on('click', () => { if (pct && _onCountryClick) _onCountryClick(code, cat); });
    });
  });
}
