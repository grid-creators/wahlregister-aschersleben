/* Gemeinsame Helfer (kein Build-Step, kein Framework). */

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
    {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function postJSON(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)});
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || r.status);
  return d;
}

function num(n) { return (n == null ? '—' : Number(n).toLocaleString('de-DE')); }

function sexBadge(g) {
  if (g === 'w') return '<span class="badge w">w</span>';
  if (g === 'm') return '<span class="badge m">m</span>';
  return '';
}

/* peru läuft auf demselben Host, Port 8765 — Link an die aufgerufene
   Adresse anpassen, damit er auch von außerhalb funktioniert. */
document.querySelectorAll('a.ext[href*="8765"]').forEach(a => {
  a.href = `${location.protocol}//${location.hostname}:8765/`;
});
