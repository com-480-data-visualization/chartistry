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
  
  // Video Shuffle Logic
  const allVideos = combo.top_videos || [];
  const shuffleBtn = document.getElementById('shuffle-videos-btn');
  const doDraw = () => {
    // Show 10 videos to scroll through for a rich, explorative user experience
    const shuffled = [...allVideos].sort(() => Math.random() - 0.5).slice(0, 10);
    drawVideos(shuffled);
  };
  if (shuffleBtn) {
    shuffleBtn.onclick = () => {
      const grid = document.getElementById('video-grid');
      grid.style.opacity = 0;
      setTimeout(() => {
        doDraw();
        grid.style.opacity = 1;
      }, 200);
    };
  }
  doDraw();

  drawHookDistribution(combo.hook_distribution || {}, combo.hook_examples || []);
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

/* ── Hook distribution chart ── */
function drawHookDistribution(dist, examples) {
  const el = document.getElementById('hook-distribution');
  el.innerHTML = '';
  
  // Filter out 0% and sort
  const entries = Object.entries(dist)
    .filter(([_, pct]) => pct > 0)
    .sort((a,b) => b[1] - a[1]);

  if (!entries.length) {
    el.innerHTML = '<p class="hook-empty">No distribution data available yet.</p>';
    return;
  }

  // Draw rows
  entries.forEach(([name, pct]) => {
    const col = hookColor(name);
    const displayPct = (pct * 100).toFixed(0) + '%';
    
    const row = document.createElement('div');
    row.className = 'hook-dist-row';
    row.dataset.hook = name;
    
    row.innerHTML = `
      <div class="hook-dist-main">
        <span class="hook-dist-label" title="${name}">${name}</span>
        <div class="hook-dist-bar-wrap">
          <div class="hook-dist-bar" style="width:0%; background:${col.color}" data-w="${pct*100}%"></div>
        </div>
        <span class="hook-dist-val">${displayPct}</span>
      </div>
      <div class="hook-dropdown-container"></div>
    `;

    // Click handler for interactive drilldown
    row.addEventListener('click', (e) => {
      // If user clicked directly on an example link inside, don't toggle
      if (e.target.closest('.hook-ex-item')) return;

      const dropdownContainer = row.querySelector('.hook-dropdown-container');
      const isActive = row.classList.contains('active');

      // Collapse all other active rows first
      el.querySelectorAll('.hook-dist-row.active').forEach(r => {
        if (r !== row) {
          r.classList.remove('active');
          r.querySelector('.hook-dropdown-container').innerHTML = '';
        }
      });

      if (isActive) {
        row.classList.remove('active');
        dropdownContainer.innerHTML = '';
      } else {
        row.classList.add('active');
        
        // Find all examples for this specific hook
        const hookEx = examples.filter(ex => ex.hook === name);
        if (!hookEx.length) {
          dropdownContainer.innerHTML = `
            <div class="hook-dist-ex-header">
              <span>Video examples</span>
              <span>0 found</span>
            </div>
            <div class="hook-examples-dropdown">
              <div style="font-size:0.7rem; color:var(--muted); padding:0.4rem 0.6rem; font-style:italic">
                No classification samples found in the top 100 for this combination.
              </div>
            </div>
          `;
          return;
        }

        // Render scrollable dropdown
        const itemsHtml = hookEx.map(ex => `
          <a class="hook-ex-item" href="https://youtube.com/watch?v=${ex.video_id}" target="_blank" title="Watch on YouTube">
            <span class="hook-ex-title">“${escHtml(ex.title)}”</span>
            <span class="hook-ex-views">
              <span>👁️</span>
              <span>${fmtViews(ex.views)}</span>
            </span>
          </a>
        `).join('');

        dropdownContainer.innerHTML = `
          <div class="hook-dist-ex-header">
            <span>Video examples (Click to watch)</span>
            <span>${hookEx.length} videos</span>
          </div>
          <div class="hook-examples-dropdown">
            ${itemsHtml}
          </div>
        `;
      }
    });

    el.appendChild(row);
  });

  // Animate bars
  requestAnimationFrame(() => {
    el.querySelectorAll('.hook-dist-bar').forEach(bar => {
      bar.style.width = bar.dataset.w;
    });
  });
}


/* ── Hook list (legacy / hidden) ── */
function drawHooks() {
  // Integrated into distribution now
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
