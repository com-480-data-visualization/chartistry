// scene3.js

function renderFormula(data, country, category) {
  const combo = (data.by_country_category[country] || {})[category];
  const flags = data.country_flags || {};
  const names = data.country_names || {};

  if (!combo) {
    document.getElementById('formula-title').textContent = 'No data for this combination.';
    return;
  }

  document.getElementById('formula-title').textContent =
    `${flags[country]||''} ${names[country]||country} × ${catIcon(category)} ${category}`;

  document.getElementById('s-videos').textContent  = combo.video_count.toLocaleString();
  document.getElementById('s-views').textContent   = fmtViews(combo.avg_views);
  document.getElementById('s-emoji').textContent   = combo.emoji_count_avg.toFixed(1);
  document.getElementById('s-caps').textContent    = fmtPct(combo.caps_ratio_avg);
  document.getElementById('s-timing').textContent  =
    combo.best_day && combo.best_hour != null
      ? `${combo.best_day.slice(0,3)} ${combo.best_hour}:00`
      : '—';

  drawWordCloud(combo.top_words || []);
  drawEmojiChart(combo.top_emojis || []);
  drawTimingHeatmap(combo.timing_heatmap || [], combo.best_day, combo.best_hour);
  drawEngagementBars(combo.avg_views, combo.avg_likes, combo.avg_comments, data, country, category);
  drawDaysHistogram(combo.days_to_trend_hist || []);

  const allVideos = combo.top_videos || [];
  const shuffleBtn = document.getElementById('shuffle-videos-btn');
  const doDraw = (restoreOpacity = false) => {
    const grid = document.getElementById('video-grid');
    grid.innerHTML = '<p style="color:#555;font-style:italic;padding:1rem">Loading…</p>';
    const candidates = [...allVideos].sort(() => Math.random() - 0.5).slice(0, 30);
    filterValidThumbs(candidates, 6, valid => {
      drawVideos(valid.length ? valid : candidates.slice(0, 4));
      if (restoreOpacity) grid.style.opacity = 1;
    });
  };
  if (shuffleBtn) {
    shuffleBtn.onclick = () => {
      const grid = document.getElementById('video-grid');
      grid.style.opacity = 0;
      setTimeout(() => doDraw(true), 200);
    };
  }
  doDraw();

  drawHookDistribution(combo.hook_distribution || {}, combo.hook_examples || []);
}

function drawWordCloud(words) {
  const el = document.getElementById('word-cloud');
  el.innerHTML = '';
  if (!words.length) { el.innerHTML = '<p style="color:#555;font-style:italic;padding:1rem">No word data</p>'; return; }

  const W = el.clientWidth || 450, H = 280;
  const maxFreq = d3.max(words, w => w.freq);
  const sizeScale = d3.scaleLog().domain([1, maxFreq]).range([12, 52]).clamp(true);

  const colorPool = ['#ff6666','#ff9944','#ffcc44','#88ddaa','#66aaff','#cc88ff','#ff88cc'];
  const rng = d3.randomLcg(42);

  d3.layout.cloud()
    .size([W, H])
    .words(words.map(w => ({ text: w.text, size: sizeScale(w.freq), freq: w.freq })))
    .padding(4)
    .font('Plus Jakarta Sans')
    .fontWeight('700')
    .rotate(() => (rng() > 0.75 ? 90 : 0))
    .fontSize(d => d.size)
    .on('end', drawn => {
      const svg = d3.select('#word-cloud').append('svg')
        .attr('viewBox', `${-W/2} ${-H/2} ${W} ${H}`)
        .attr('preserveAspectRatio', 'xMidYMid meet')
        .style('width', '100%');

      svg.selectAll('text')
        .data(drawn)
        .join('text')
        .attr('transform', d => `translate(${d.x},${d.y}) rotate(${d.rotate})`)
        .attr('text-anchor', 'middle')
        .attr('font-size', d => d.size)
        .attr('font-family', 'Plus Jakarta Sans')
        .attr('font-weight', 700)
        .attr('fill', (_, i) => colorPool[i % colorPool.length])
        .attr('opacity', d => 0.5 + 0.5 * (d.freq / (d3.max(drawn, w => w.freq) || 1)))
        .text(d => d.text)
        .on('mouseenter', function(event, d) {
          showTooltip(`<div class="tt-name">${d.text}</div><div class="tt-row"><span>Frequency</span><span class="tt-val">${d.freq}</span></div>`, event);
        })
        .on('mousemove', moveTooltip)
        .on('mouseleave', hideTooltip);
    })
    .start();
}

function drawEmojiChart(emojis) {
  const el = document.getElementById('emoji-chart');
  el.innerHTML = '';
  if (!emojis.length) { el.innerHTML = '<p style="color:#555;font-style:italic">No emoji data</p>'; return; }

  const maxCount = emojis[0].count;
  emojis.forEach(e => {
    const pct = (e.count / maxCount * 100).toFixed(1);
    el.insertAdjacentHTML('beforeend', `
      <div class="emoji-row">
        <span class="emoji-glyph">${e.emoji}</span>
        <div class="emoji-track"><div class="emoji-fill" style="width:0%" data-w="${pct}%"></div></div>
        <span class="emoji-count">${e.count}</span>
      </div>
    `);
  });
  requestAnimationFrame(() => {
    el.querySelectorAll('.emoji-fill').forEach(bar => { bar.style.width = bar.dataset.w; });
  });
}

function filterValidThumbs(candidates, maxCount, cb) {
  if (!candidates.length) { cb([]); return; }
  const results = new Array(candidates.length).fill(null);
  let returned = false;
  candidates.forEach((v, i) => {
    thumbOk(v.video_id, ok => {
      results[i] = ok;
      if (returned) return;
      const valid = candidates.filter((_, j) => results[j] === true);
      if (valid.length >= maxCount || results.every(r => r !== null)) {
        returned = true;
        cb(valid.slice(0, maxCount));
      }
    });
  });
}

function drawVideos(videos) {
  const grid = document.getElementById('video-grid');
  grid.innerHTML = '';
  grid.style.transition = 'opacity 0.3s ease';
  if (!videos.length) { grid.innerHTML = '<p style="color:#555;font-style:italic">No video data</p>'; return; }

  videos.forEach(v => {
    const thumbUrl = `https://i.ytimg.com/vi/${v.video_id}/mqdefault.jpg`;
    const card = document.createElement('div');
    card.className = 'vcard';
    card.style.cursor = 'pointer';
    card.setAttribute('title', 'Click to watch on YouTube');

    card.innerHTML = `
      <div class="vcard-thumb-container" style="position:relative; overflow:hidden;">
        <img class="vcard-thumb" src="${thumbUrl}" alt="${escHtml(v.title)}"
             onerror="this.outerHTML='<div class=\\'vcard-thumb-err\\'>🎬</div>'"
             loading="lazy">
        <div class="vcard-play-overlay">
          <span>▶ Watch</span>
        </div>
      </div>
      <div class="vcard-info">
        <div class="vcard-title">${escHtml(v.title)}</div>
        <div class="vcard-views">${fmtViews(v.views)} views</div>
      </div>
    `;

    card.addEventListener('click', () => {
      window.open(`https://youtube.com/watch?v=${v.video_id}`, '_blank');
    });

    grid.appendChild(card);
  });
}

function drawHookDistribution(dist, examples) {
  const el = document.getElementById('hook-distribution');
  el.innerHTML = '';

  const entries = Object.entries(dist)
    .filter(([_, pct]) => pct > 0)
    .sort((a,b) => b[1] - a[1]);

  if (!entries.length) {
    el.innerHTML = '<p class="hook-empty">No distribution data available yet.</p>';
    return;
  }

  const container = document.createElement('div');
  container.className = 'hook-stacked-container';

  const barWrapper = document.createElement('div');
  barWrapper.className = 'hook-stacked-bar-wrap';

  const stackedBar = document.createElement('div');
  stackedBar.className = 'hook-stacked-bar';

  const detailsLayout = document.createElement('div');
  detailsLayout.className = 'hook-details-layout';

  const legendSide = document.createElement('div');
  legendSide.className = 'hook-legend-side';

  const examplesSide = document.createElement('div');
  examplesSide.className = 'hook-examples-side';

  let activeHook = entries[0][0];

  entries.forEach(([name, pct]) => {
    const col = hookColor(name);
    const displayPct = (pct * 100).toFixed(0) + '%';

    const segment = document.createElement('div');
    segment.className = 'hook-bar-segment';
    segment.style.width = '0%';
    segment.style.backgroundColor = col.color;
    segment.dataset.w = (pct * 100) + '%';
    segment.dataset.hook = name;

    segment.addEventListener('mouseenter', (event) => {
      showTooltip(`
        <div class="tt-name">${name}</div>
        <div class="tt-row"><span>Niche Share</span><span class="tt-val">${displayPct}</span></div>
        <div class="tt-row"><span style="font-size:0.7rem; color:var(--red);">Click to explore examples</span></div>
      `, event);
    });
    segment.addEventListener('mousemove', moveTooltip);
    segment.addEventListener('mouseleave', hideTooltip);
    segment.addEventListener('click', () => selectHook(name));

    stackedBar.appendChild(segment);

    const legendItem = document.createElement('div');
    legendItem.className = 'hook-legend-item';
    legendItem.dataset.hook = name;
    legendItem.innerHTML = `
      <span class="hook-legend-dot" style="background-color: ${col.color};"></span>
      <span class="hook-legend-name">${name}</span>
      <span class="hook-legend-pct">${displayPct}</span>
    `;
    legendItem.addEventListener('click', () => selectHook(name));
    legendSide.appendChild(legendItem);
  });

  barWrapper.appendChild(stackedBar);
  container.appendChild(barWrapper);
  detailsLayout.appendChild(legendSide);
  detailsLayout.appendChild(examplesSide);
  container.appendChild(detailsLayout);
  el.appendChild(container);

  function selectHook(name) {
    activeHook = name;

    stackedBar.querySelectorAll('.hook-bar-segment').forEach(seg => {
      seg.classList.toggle('active', seg.dataset.hook === name);
      seg.style.opacity = seg.dataset.hook === name ? '1' : '0.35';
    });

    legendSide.querySelectorAll('.hook-legend-item').forEach(item => {
      item.classList.toggle('active', item.dataset.hook === name);
    });

    const hookEx = examples.filter(ex => ex.hook === name);
    const col = hookColor(name);

    examplesSide.innerHTML = `
      <div class="hook-ex-header-bar" style="border-left: 3px solid ${col.color};">
        <span class="hook-ex-header-title">🎥 Samples: ${name}</span>
        <span class="hook-ex-header-badge" style="background-color: ${col.bg}; color: ${col.color};">${hookEx.length} videos</span>
      </div>
      <div class="hook-ex-grid">
        ${hookEx.length ? hookEx.map(ex => `
          <a class="hook-ex-card" href="https://youtube.com/watch?v=${ex.video_id}" target="_blank" title="Watch on YouTube">
            <span class="hook-ex-card-play">▶</span>
            <div class="hook-ex-card-info">
              <div class="hook-ex-card-title">"${escHtml(ex.title)}"</div>
              <div class="hook-ex-card-views">${fmtViews(ex.views)} views</div>
            </div>
          </a>
        `).join('') : `
          <div class="hook-ex-empty">
            No active samples found in the top 100 for this hook category.
          </div>
        `}
      </div>
    `;
  }

  selectHook(activeHook);

  requestAnimationFrame(() => {
    stackedBar.querySelectorAll('.hook-bar-segment').forEach(seg => {
      seg.style.width = seg.dataset.w;
    });
  });
}

function drawTimingHeatmap(heatmapData, bestDay, bestHour) {
  const el = document.getElementById('timing-heatmap');
  el.innerHTML = '';
  if (!heatmapData.length) {
    el.innerHTML = '<p style="color:#555;font-style:italic;padding:0.5rem">No timing data</p>';
    return;
  }

  const DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
  const HOURS = Array.from({length: 24}, (_, i) => i);

  const lookup = {};
  DAYS.forEach(d => { lookup[d] = {}; });
  heatmapData.forEach(e => { if (lookup[e.day]) lookup[e.day][e.hour] = e.avg_views; });

  const maxVal = d3.max(heatmapData, e => e.avg_views) || 1;

  // Inferno avoids the all-red look while still reading as a heat map
  const colorScale = d3.scaleSequential([0, maxVal], d3.interpolateInferno);

  const containerW = el.clientWidth || 560;
  const cellW = Math.max(12, Math.floor((containerW - 52) / 24));
  const cellH = 30;
  const marginL = 36, marginT = 22, marginB = 38;
  const W = marginL + 24 * cellW;
  const H = marginT + 7 * cellH + marginB;

  const svg = d3.select('#timing-heatmap').append('svg')
    .attr('viewBox', `0 0 ${W} ${H}`)
    .attr('preserveAspectRatio', 'xMinYMin meet')
    .style('width', '100%');

  HOURS.filter(h => h % 3 === 0).forEach(h => {
    svg.append('text')
      .attr('x', marginL + h * cellW + cellW / 2)
      .attr('y', marginT - 5)
      .attr('text-anchor', 'middle')
      .attr('font-size', 11)
      .attr('fill', '#aaa')
      .text(`${h}h`);
  });

  DAYS.forEach((day, di) => {
    svg.append('text')
      .attr('x', marginL - 4)
      .attr('y', marginT + di * cellH + cellH / 2 + 3.5)
      .attr('text-anchor', 'end')
      .attr('font-size', 11)
      .attr('fill', '#bbb')
      .text(day.slice(0, 3));

    HOURS.forEach(h => {
      const val = lookup[day][h];
      const isBest = day === bestDay && h === bestHour;
      const hasData = val != null;

      svg.append('rect')
        .attr('x', marginL + h * cellW + 1)
        .attr('y', marginT + di * cellH + 1)
        .attr('width', cellW - 2)
        .attr('height', cellH - 2)
        .attr('rx', 2)
        .attr('fill', hasData ? colorScale(val) : '#111')
        .style('cursor', hasData ? 'pointer' : 'default')
        .on('mouseenter', hasData ? (event) => {
          showTooltip(`
            <div class="tt-name">${day}, ${h}:00 UTC</div>
            <div class="tt-row"><span>Avg Views</span><span class="tt-val">${fmtViews(val)}</span></div>
            ${isBest ? '<div style="color:#fcd34d;font-size:0.72rem;margin-top:0.3rem">★ Best window</div>' : ''}
          `, event);
        } : null)
        .on('mousemove', hasData ? moveTooltip : null)
        .on('mouseleave', hasData ? hideTooltip : null);

      if (isBest) {
        svg.append('rect')
          .attr('x', marginL + h * cellW)
          .attr('y', marginT + di * cellH)
          .attr('width', cellW)
          .attr('height', cellH)
          .attr('rx', 3)
          .attr('fill', 'none')
          .attr('stroke', '#fcd34d')
          .attr('stroke-width', 2)
          .style('pointer-events', 'none');
      }
    });
  });

  const legW = 120, legH = 8;
  const legX = marginL + 24 * cellW - legW;
  const legY = H - marginB + 14;
  const legGrad = svg.append('defs').append('linearGradient')
    .attr('id', 'timing-legend-grad')
    .attr('x1', '0%').attr('x2', '100%');
  [0, 0.25, 0.5, 0.75, 1].forEach(t => {
    legGrad.append('stop').attr('offset', `${t * 100}%`).attr('stop-color', d3.interpolateInferno(t));
  });
  svg.append('rect')
    .attr('x', legX).attr('y', legY)
    .attr('width', legW).attr('height', legH)
    .attr('rx', 3)
    .attr('fill', 'url(#timing-legend-grad)')
    .attr('stroke', '#333').attr('stroke-width', 0.5);
  svg.append('text').attr('x', legX).attr('y', legY + legH + 11)
    .attr('font-size', 10).attr('fill', '#999').text('fewer views');
  svg.append('text').attr('x', legX + legW).attr('y', legY + legH + 11)
    .attr('text-anchor', 'end').attr('font-size', 10).attr('fill', '#ddd').text('more views');
}

function drawEngagementBars(avgViews, avgLikes, avgComments, data, country, category) {
  const el = document.getElementById('engage-chart');
  el.innerHTML = '';

  const flag = (data.country_flags || {})[country] || '';
  const name = (data.country_names || {})[country] || country;
  const thisLabel  = `${flag} ${name} ${category}`;
  const worldLabel = `${category} worldwide`;

  const countryList = data.countries || [];
  const worldViews    = d3.mean(countryList.map(c => data.by_country_category[c]?.[category]?.avg_views).filter(v => v != null));
  const worldLikes    = d3.mean(countryList.map(c => data.by_country_category[c]?.[category]?.avg_likes).filter(v => v != null));
  const worldComments = d3.mean(countryList.map(c => data.by_country_category[c]?.[category]?.avg_comments).filter(v => v != null));

  const metrics = [
    { label: 'Avg Views',    niche: avgViews,    world: worldViews    },
    { label: 'Avg Likes',    niche: avgLikes,    world: worldLikes    },
    { label: 'Avg Comments', niche: avgComments, world: worldComments },
  ];

  metrics.forEach(({ label, niche, world }) => {
    const maxVal = Math.max(niche || 0, world || 0) || 1;
    const nicheW = ((niche || 0) / maxVal * 100).toFixed(1);
    const worldW = ((world || 0) / maxVal * 100).toFixed(1);

    el.insertAdjacentHTML('beforeend', `
      <div class="engage-group">
        <div class="engage-group-label">${label}</div>
        <div class="engage-bar-row">
          <div class="engage-bar-name">${thisLabel}</div>
          <div class="engage-bar-track">
            <div class="engage-bar-fill niche" style="width:0%" data-w="${nicheW}%"></div>
          </div>
          <div class="engage-val">${fmtViews(niche || 0)}</div>
        </div>
        <div class="engage-bar-row">
          <div class="engage-bar-name engage-bar-name-world">${worldLabel}</div>
          <div class="engage-bar-track">
            <div class="engage-bar-fill baseline" style="width:0%" data-w="${worldW}%"></div>
          </div>
          <div class="engage-val" style="color:var(--muted)">${fmtViews(world || 0)}</div>
        </div>
      </div>
    `);
  });

  requestAnimationFrame(() => {
    el.querySelectorAll('.engage-bar-fill').forEach(bar => { bar.style.width = bar.dataset.w; });
  });
}

function drawDaysHistogram(histData) {
  const el = document.getElementById('days-hist');
  el.innerHTML = '';
  const visible = histData.filter(d => d.count > 0);
  if (!visible.length) {
    el.innerHTML = '<p style="color:#555;font-style:italic">No data</p>';
    return;
  }

  const margin = { top: 12, right: 14, bottom: 38, left: 38 };
  const totalW = el.clientWidth || 320;
  const totalH = Math.max(el.clientHeight || 0, 280);
  const W = totalW - margin.left - margin.right;
  const H = totalH - margin.top - margin.bottom;

  const svg = d3.select('#days-hist').append('svg')
    .attr('width', '100%')
    .attr('height', totalH);

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const maxCount = d3.max(histData, d => d.count) || 1;

  const x = d3.scaleBand()
    .domain(histData.map(d => d.day))
    .range([0, W])
    .padding(0.08);

  const y = d3.scaleLinear().domain([0, maxCount]).range([H, 0]);

  g.selectAll('rect')
    .data(histData)
    .join('rect')
    .attr('x', d => x(d.day))
    .attr('y', d => y(d.count))
    .attr('width', x.bandwidth())
    .attr('height', d => H - y(d.count))
    .attr('fill', d => d.count === 0 ? 'transparent' : '#ff4444')
    .attr('rx', 2)
    .style('cursor', d => d.count > 0 ? 'pointer' : 'default')
    .on('mouseenter', (event, d) => {
      if (!d.count) return;
      showTooltip(`
        <div class="tt-name">${d.day === 30 ? '30+ days' : `${d.day} day${d.day !== 1 ? 's' : ''}`}</div>
        <div class="tt-row"><span>Videos</span><span class="tt-val">${d.count.toLocaleString()}</span></div>
      `, event);
    })
    .on('mousemove', moveTooltip)
    .on('mouseleave', hideTooltip);

  histData.filter(d => d.day % 5 === 0).forEach(d => {
    g.append('text')
      .attr('x', x(d.day) + x.bandwidth() / 2)
      .attr('y', H + 14)
      .attr('text-anchor', 'middle')
      .attr('font-size', 10.5)
      .attr('fill', '#aaa')
      .text(d.day === 30 ? '30+' : String(d.day));
  });

  g.append('line').attr('x1', 0).attr('x2', W).attr('y1', H).attr('y2', H).attr('stroke', '#2a2a2a');

  g.append('text')
    .attr('x', W / 2).attr('y', H + 30)
    .attr('text-anchor', 'middle')
    .attr('font-size', 10.5).attr('fill', '#999')
    .text('days from publish');

  g.append('text')
    .attr('x', -4).attr('y', 4)
    .attr('text-anchor', 'end')
    .attr('font-size', 10).attr('fill', '#888')
    .text(maxCount.toLocaleString());
  g.append('line').attr('x1', 0).attr('x2', 0).attr('y1', 0).attr('y2', H).attr('stroke', '#2a2a2a');
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
