// scene2.js — Country × Category selector

let _s2data = null;
let _selCountry  = null;
let _selCategory = null;
let _onExplore   = null;

function initScene2(data, onExplore) {
  _s2data   = data;
  _onExplore = onExplore;
  renderCountries();
  renderCategories();
  document.getElementById('explore-btn').addEventListener('click', () => {
    if (_selCountry && _selCategory) _onExplore(_selCountry, _selCategory);
  });
}

function renderCountries() {
  const grid = document.getElementById('country-grid');
  grid.innerHTML = '';
  const flags = _s2data.country_flags || {};
  const names = _s2data.country_names || {};

  _s2data.countries.forEach(code => {
    const tile = document.createElement('div');
    tile.className = 'country-tile';
    tile.dataset.code = code;
    tile.innerHTML = `<span class="ctile-flag">${flags[code]||''}</span><span class="ctile-name">${names[code]||code}</span>`;
    tile.addEventListener('click', () => {
      document.querySelectorAll('.country-tile').forEach(t => t.classList.remove('sel'));
      tile.classList.add('sel');
      _selCountry = code;
      updatePreview();
    });
    grid.appendChild(tile);
  });
}

function renderCategories() {
  const grid = document.getElementById('category-grid');
  grid.innerHTML = '';
  _s2data.categories.filter(c => c !== 'Unknown').forEach(cat => {
    const tile = document.createElement('div');
    tile.className = 'cat-tile';
    tile.dataset.cat = cat;
    tile.innerHTML = `<span class="cat-icon">${catIcon(cat)}</span><span>${cat}</span>`;
    tile.addEventListener('click', () => {
      document.querySelectorAll('.cat-tile').forEach(t => t.classList.remove('sel'));
      tile.classList.add('sel');
      _selCategory = cat;
      updatePreview();
    });
    grid.appendChild(tile);
  });
}

function updatePreview() {
  const flags = _s2data.country_flags || {};
  const names = _s2data.country_names || {};
  const prev  = document.getElementById('selection-preview');
  const btn   = document.getElementById('explore-btn');

  if (_selCountry && _selCategory) {
    prev.innerHTML = `Exploring: <strong>${flags[_selCountry]||''} ${names[_selCountry]||_selCountry}</strong> &times; <strong>${catIcon(_selCategory)} ${_selCategory}</strong>`;
    btn.disabled = false;
  } else if (_selCountry) {
    prev.innerHTML = `${flags[_selCountry]||''} <strong>${names[_selCountry]||_selCountry}</strong> selected — now pick a category`;
    btn.disabled = true;
  } else if (_selCategory) {
    prev.innerHTML = `<strong>${catIcon(_selCategory)} ${_selCategory}</strong> selected — now pick a country`;
    btn.disabled = true;
  } else {
    prev.textContent = 'Select a country and category above';
    btn.disabled = true;
  }
}

// Allow pre-selecting from Scene 1 map click
function preSelectCountry(code, cat) {
  _selCountry  = code;
  _selCategory = cat || null;
  document.querySelectorAll('.country-tile').forEach(t =>
    t.classList.toggle('sel', t.dataset.code === code));
  if (cat) {
    document.querySelectorAll('.cat-tile').forEach(t =>
      t.classList.toggle('sel', t.dataset.cat === cat));
  }
  updatePreview();
}
