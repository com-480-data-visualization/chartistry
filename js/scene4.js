// scene4.js — Viral Duel mini-game

var _duelCombos   = [];
var _duelStreak   = 0;
var _duelAnswered = false;
var _duelPair     = null;
var _duelAppData  = null;
var _thumbCache   = {}; // videoId -> true/false

function initDuel(data) {
  if (_duelAppData) return;
  _duelAppData = data;

  var bcc = data.by_country_category || {};
  _duelCombos = [];
  Object.keys(bcc).forEach(function(country) {
    Object.keys(bcc[country]).forEach(function(category) {
      var videos = (bcc[country][category].top_videos || []).filter(function(v) {
        return v.video_id && v.views > 0;
      });
      if (videos.length >= 2) {
        _duelCombos.push({ country: country, category: category, videos: videos });
      }
    });
  });

  // Side-by-side grid, centered
  var labelEl = document.getElementById('duel-combo-label');
  labelEl.style.width = '100%';
  labelEl.style.maxWidth = '860px';
  labelEl.style.margin = '0 auto 1.25rem';
  labelEl.style.textAlign = 'center';

  var cardsEl = document.getElementById('duel-cards');
  cardsEl.style.display = 'grid';
  cardsEl.style.gridTemplateColumns = '1fr auto 1fr';
  cardsEl.style.alignItems = 'start';
  cardsEl.style.gap = '1.5rem';
  cardsEl.style.width = '100%';
  cardsEl.style.maxWidth = '860px';
  cardsEl.style.margin = '0 auto';

  document.getElementById('duel-feedback').style.display = 'none';
  document.getElementById('duel-next-btn').addEventListener('click', duelNext);
  duelNext();
}

function duelNext() {
  _duelAnswered = false;
  document.getElementById('duel-feedback').style.display = 'none';
  document.querySelectorAll('.duel-views-count').forEach(function(el) { el.style.display = 'none'; });
  document.getElementById('duel-combo-label').textContent = 'Finding a matchup…';
  document.getElementById('duel-card-a').innerHTML = '';
  document.getElementById('duel-card-b').innerHTML = '';
  tryPair(0);
}

// Try up to 20 pairs until both thumbnails are real (not grey placeholders)
function tryPair(attempt) {
  if (attempt >= 20) {
    document.getElementById('duel-combo-label').textContent = 'No valid pairs found.';
    return;
  }
  var pair = duelPick();
  if (!pair) {
    document.getElementById('duel-combo-label').textContent = 'No pairs found.';
    return;
  }
  // Check both thumbnails in parallel
  var results = [null, null];
  function onResult() {
    if (results[0] === null || results[1] === null) return;
    if (results[0] && results[1]) {
      _duelPair = pair;
      duelRender(pair);
    } else {
      tryPair(attempt + 1);
    }
  }
  thumbOk(pair.a.video_id, function(ok) { results[0] = ok; onResult(); });
  thumbOk(pair.b.video_id, function(ok) { results[1] = ok; onResult(); });
}

// Returns true if the thumbnail is a real image (not the 120×90 grey placeholder)
function thumbOk(videoId, cb) {
  if (videoId in _thumbCache) { cb(_thumbCache[videoId]); return; }
  var img = new Image();
  var done = false;
  var timer = setTimeout(function() {
    if (!done) { done = true; _thumbCache[videoId] = false; cb(false); }
  }, 3000);
  img.onload = function() {
    if (!done) {
      done = true;
      clearTimeout(timer);
      var ok = img.naturalWidth > 120; // grey placeholder is exactly 120×90
      _thumbCache[videoId] = ok;
      cb(ok);
    }
  };
  img.onerror = function() {
    if (!done) { done = true; clearTimeout(timer); _thumbCache[videoId] = false; cb(false); }
  };
  img.src = 'https://i.ytimg.com/vi/' + videoId + '/mqdefault.jpg';
}

function duelPick() {
  var shuffled = _duelCombos.slice().sort(function() { return Math.random() - 0.5; });
  for (var i = 0; i < shuffled.length; i++) {
    var combo = shuffled[i];
    var vids = combo.videos;
    for (var attempt = 0; attempt < 30; attempt++) {
      var ia = Math.floor(Math.random() * vids.length);
      var ib = Math.floor(Math.random() * vids.length);
      var a = vids[ia];
      var b = vids[ib];
      if (a.video_id !== b.video_id && a.views !== b.views) {
        return { combo: combo, a: a, b: b };
      }
    }
  }
  return null;
}

function duelRender(pair) {
  var combo = pair.combo;
  var flags = _duelAppData.country_flags || {};
  var names = _duelAppData.country_names || {};
  document.getElementById('duel-combo-label').textContent =
    (flags[combo.country] || '') + ' ' + (names[combo.country] || combo.country) +
    '  ·  ' + catIcon(combo.category) + ' ' + combo.category;

  duelCard('duel-card-a', pair.a);
  duelCard('duel-card-b', pair.b);

  document.getElementById('duel-card-a').onclick = function() { duelGuess('a'); };
  document.getElementById('duel-card-b').onclick = function() { duelGuess('b'); };
}

function duelCard(id, video) {
  var wrap = document.getElementById(id);
  wrap.className = 'duel-card';
  wrap.innerHTML = '';

  var card = document.createElement('div');
  card.className = 'vcard';

  var img = document.createElement('img');
  img.className = 'vcard-thumb';
  img.src = 'https://i.ytimg.com/vi/' + video.video_id + '/mqdefault.jpg';
  img.alt = video.title;
  img.setAttribute('loading', 'lazy');

  var info = document.createElement('div');
  info.className = 'vcard-info';
  info.innerHTML =
    '<div class="vcard-title">' + escHtml(video.title) + '</div>' +
    '<div class="vcard-views">' + escHtml(video.channel) + ' · ' + duelFmtPub(video.pub) + '</div>' +
    '<div class="duel-views-count" style="display:none">' + fmtViews(video.views) + ' views</div>';

  card.appendChild(img);
  card.appendChild(info);
  wrap.appendChild(card);
}

function duelGuess(side) {
  if (_duelAnswered) return;
  _duelAnswered = true;

  var a = _duelPair.a;
  var b = _duelPair.b;
  var winner = a.views >= b.views ? 'a' : 'b';
  var correct = side === winner;

  _duelStreak = correct ? _duelStreak + 1 : 0;
  document.getElementById('duel-streak').textContent = _duelStreak;

  document.querySelectorAll('.duel-views-count').forEach(function(el) { el.style.display = 'block'; });

  var cardA = document.getElementById('duel-card-a');
  var cardB = document.getElementById('duel-card-b');
  cardA.classList.add(winner === 'a' ? 'duel-card--winner' : 'duel-card--loser');
  cardB.classList.add(winner === 'b' ? 'duel-card--winner' : 'duel-card--loser');
  cardA.onclick = null;
  cardB.onclick = null;

  var winViews = fmtViews(winner === 'a' ? a.views : b.views);
  var msg = correct
    ? '<span class="fb-correct">✓ Correct!</span>&ensp;Streak: <strong>' + _duelStreak + '</strong> 🔥'
    : '<span class="fb-wrong">✗ Wrong!</span>&ensp;The other had <strong>' + winViews + '</strong> views. Streak reset.';
  document.getElementById('duel-feedback-text').innerHTML = msg;
  document.getElementById('duel-feedback').style.display = '';
}

function duelFmtPub(pubStr) {
  if (!pubStr) return '';
  try {
    var days = Math.floor((Date.now() - new Date(pubStr).getTime()) / 86400000);
    if (days < 1)   return 'Today';
    if (days < 31)  return days + 'd ago';
    if (days < 365) return Math.floor(days / 30) + 'mo ago';
    return Math.floor(days / 365) + 'y ago';
  } catch(e) { return ''; }
}

// Self-bootstrap using the already-cached data.json
loadData().then(function(data) {
  initDuel(data);
}).catch(function(err) {
  var el = document.getElementById('duel-combo-label');
  if (el) el.textContent = 'Load error: ' + err.message;
});
