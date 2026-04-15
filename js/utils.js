// utils.js — shared helpers, data loading, constants

const DATA_URL = 'public/data.json';
let _data = null;

async function loadData() {
  if (_data) return _data;
  const res = await fetch(DATA_URL);
  if (!res.ok) throw new Error(`Failed to load data.json: ${res.status}`);
  _data = await res.json();
  return _data;
}

function fmtViews(n) {
  if (!n || isNaN(n)) return '—';
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return Math.round(n / 1e3) + 'K';
  return Number(n).toLocaleString();
}

function fmtPct(v, d = 1) { return (v * 100).toFixed(d) + '%'; }

// Category icons
const CAT_ICONS = {
  'Entertainment':'🎭','Music':'🎵','Gaming':'🎮','Film & Animation':'🎬',
  'News & Politics':'📰','Sports':'⚽','Science & Technology':'🔬',
  'Howto & Style':'✂️','Comedy':'😂','Education':'📚',
  'Pets & Animals':'🐾','Travel & Events':'✈️','Autos & Vehicles':'🚗',
  'People & Blogs':'👤','Nonprofits & Activism':'❤️',
  'Shows':'📺','Trailers':'🎥','Unknown':'❓',
};
function catIcon(cat) { return CAT_ICONS[cat] || '📌'; }

// Hook badge color palette
const HOOK_PALETTE = [
  { bg:'rgba(255,68,68,0.15)',   color:'#ff6666' },
  { bg:'rgba(100,180,255,0.15)', color:'#64b4ff' },
  { bg:'rgba(120,220,160,0.15)', color:'#78dca0' },
  { bg:'rgba(255,200,80,0.15)',  color:'#ffc850' },
  { bg:'rgba(200,140,255,0.15)', color:'#c88cff' },
  { bg:'rgba(255,160,80,0.15)',  color:'#ffa050' },
];
const _hookColorCache = {};
function hookColor(hook) {
  if (!_hookColorCache[hook]) {
    const n = Object.keys(_hookColorCache).length;
    _hookColorCache[hook] = HOOK_PALETTE[n % HOOK_PALETTE.length];
  }
  return _hookColorCache[hook];
}

// Tooltip helper
const tt = document.getElementById('tooltip');
function showTooltip(html, event) {
  tt.innerHTML = html;
  tt.style.opacity = 1;
  moveTooltip(event);
}
function moveTooltip(event) {
  const x = event.clientX + 14, y = event.clientY - 10;
  tt.style.left = Math.min(x, window.innerWidth - 240) + 'px';
  tt.style.top  = y + 'px';
}
function hideTooltip() { tt.style.opacity = 0; }

// ISO numeric → country code (for TopoJSON)
const ISO_NUM = {
  124:'CA',276:'DE',250:'FR',826:'GB',356:'IN',
  392:'JP',410:'KR',484:'MX',643:'RU',840:'US'
};
