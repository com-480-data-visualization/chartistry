// main.js — App bootstrap, scene management, routing

(async () => {
  let appData;
  try {
    appData = await loadData();
  } catch (e) {
    document.body.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;gap:1rem;font-family:Inter,sans-serif;color:#888">
        <div style="font-size:3rem">⚠️</div>
        <h2 style="color:#f0f0f0">Couldn't load data</h2>
        <p>Run a local server from the <code>website/</code> folder:</p>
        <code style="background:#1a1a1a;padding:0.5rem 1rem;border-radius:8px;color:#ff8888">python -m http.server 8080</code>
        <p>Then open <a href="http://localhost:8080" style="color:#ff4444">http://localhost:8080</a></p>
      </div>`;
    return;
  }

  document.querySelector('.nav-logo').addEventListener('click', () => {
    navigateTo('scene-0');
    history.replaceState(null, "", window.location.pathname);
  });

  // ── Hero stats ──────────────────────────────────────────────
  const stats = [
    { val: appData.meta.n_videos_total.toLocaleString(), label: 'Trending Videos' },
    { val: appData.meta.n_countries, label: 'Countries' },
    { val: appData.meta.n_categories, label: 'Categories' },
  ];
  const heroStats = document.getElementById('hero-stats');
  stats.forEach(s => {
    heroStats.insertAdjacentHTML('beforeend', `
      <div class="hstat fade-up">
        <div class="hstat-val">${s.val}</div>
        <div class="hstat-label">${s.label}</div>
      </div>`);
  });

  // ── Init scenes ─────────────────────────────────────────────
  await initScene1(appData, (code, cat) => {
    navigateTo('scene-2');
    preSelectCountry(code, cat);
  });

  initScene2(appData, (country, category) => {
    renderFormula(appData, country, category);

    setTimeout(() => {
      navigateTo('scene-3');
    }, 0);
  });

  // Back button
  document.getElementById('back-btn').addEventListener('click', () => navigateTo('scene-2'));

  // ── Navigation ──────────────────────────────────────────────
  function navigateTo(id) {
    document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
  }

  // Active nav link highlight on scroll
  const scenes = ['scene-0', 'scene-1', 'scene-2', 'scene-3'];
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const id = entry.target.id;
      const sceneNum = id.split('-')[1];
      document.querySelectorAll('.nav-link').forEach(l => {
        l.classList.toggle('active', l.dataset.scene === sceneNum);
      });
    });
  }, { threshold: 0.4 });

  scenes.forEach(id => {
    const el = document.getElementById(id);
    if (el) observer.observe(el);
  });
})();
