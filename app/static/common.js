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

/* Der Link auf peru stand einmal auf `localhost:8765` und wurde hier an den
   aufgerufenen Host angepasst — solange beide Apps auf demselben Server unter
   ihrer IP zu erreichen waren, ging das auf. Mit den eigenen Subdomains nicht
   mehr: die Umschreibung machte aus dem Aufruf über
   wahlregister.grid-creators.com ein wahlregister.grid-creators.com:8765,
   also den falschen Host auf einem Port, den der Proxy nicht bedient. peru hat
   jetzt eine feste Adresse; sie steht in index.html, geraten wird nichts. */
