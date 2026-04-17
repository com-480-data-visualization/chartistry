// scene3.js — The Formula: word cloud, emojis, thumbnails, hooks

function renderFormula(data, country, category) {
  const combo = (data.by_country_category[country] || {})[category];
  const flags = data.country_flags || {};
  const names = data.country_names || {};

  if (!combo) {
    document.getElementById('formula-title').textContent = 'No data for this combination.';
    return;
  }

  // Header
  document.getElementById('formula-title').textContent =
    `${flags[country]||''} ${names[country]||country} × ${catIcon(category)} ${category}`;
  document.getElementById('nav-formula').classList.add('unlocked');

  // Stat ribbon
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
  drawVideos(combo.top_videos || []);
  drawHooks(combo.hook_examples || []);
}

/* ── Word cloud ── */
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

/* ── Emoji bar chart ── */
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
  // Animate bars after paint
  requestAnimationFrame(() => {
    el.querySelectorAll('.emoji-fill').forEach(bar => {
      bar.style.width = bar.dataset.w;
    });
  });
}

/* ── Thumbnail video grid ── */
function drawVideos(videos) {
  const grid = document.getElementById('video-grid');
  grid.innerHTML = '';
  if (!videos.length) { grid.innerHTML = '<p style="color:#555;font-style:italic">No video data</p>'; return; }

  videos.forEach(v => {
    const thumbUrl = `https://i.ytimg.com/vi/${v.video_id}/mqdefault.jpg`;
    const card = document.createElement('div');
    card.className = 'vcard';
    card.innerHTML = `
      <img class="vcard-thumb" src="${thumbUrl}" alt="${escHtml(v.title)}"
           onerror="this.outerHTML='<div class=\\'vcard-thumb-err\\'>🎬</div>'"
           loading="lazy">
      <div class="vcard-info">
        <div class="vcard-title">${escHtml(v.title)}</div>
        <div class="vcard-views">${fmtViews(v.views)} views</div>
      </div>
    `;
    grid.appendChild(card);
  });
}

/* ── Hook examples ── */
function drawHooks(hooks) {
  const list = document.getElementById('hook-list');
  const card = document.getElementById('hooks-card');
  list.innerHTML = '';
  card.style.display = '';

  if (!hooks.length) {
    list.innerHTML =
      '<p class="hook-empty">No hook-style examples in this data export. ' +
      'They fill in after you run <code>analysis/precompute.ipynb</code> with ' +
      '<code>code/text_analysis/data/hook_labels_closed.json</code> present (from the text-analysis labelling step).</p>';
    return;
  }

  list.innerHTML = '<div class="hook-list">' +
    hooks.map(h => {
      const col = hookColor(h.hook);
      return `
        <div class="hook-item">
          <span class="hook-badge" style="background:${col.bg};color:${col.color}">${escHtml(h.hook)}</span>
          <div class="hook-body">
            <div class="hook-title">${escHtml(h.title)}</div>
            ${h.views ? `<div class="hook-views">${fmtViews(h.views)} views</div>` : ''}
          </div>
        </div>`;
    }).join('') + '</div>';
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
