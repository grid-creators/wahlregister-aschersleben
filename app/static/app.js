/* Arbeitsliste: je Registereintrag die FactGrid-Kandidaten, eine Entscheidung,
   danach der QuickStatements-Export. */

const listeEl = document.getElementById('liste');
const mehrEl = document.getElementById('mehr');
const statusTxt = document.getElementById('status_txt');
const fortschrittEl = document.getElementById('fortschritt');
const filter = ['q', 'ordner', 'strasse', 'status', 'treffer']
  .map(id => document.getElementById(id));
/* Die Primärquellen kommen je Ordner dazu (`qs_quelle_o2`, `qs_quelle_o3`, …);
   welche es gibt, sagt der Server. */
const EINST = ['qs_ort', 'qs_wahl_sp4', 'qs_wahl_sp5', 'qs_wahl_sp8',
               'qs_wahl_o6', 'qs_wahl_o7_reichstag', 'qs_wahl_o7_landtag',
               'qs_rolle', 'qs_projekt', 'qs_titel', 'qs_beschreibung',
               'qs_geschlecht', 'qs_label_en'];

const SEITE = 25;
let offset = 0, gesamt = 0;

/* Bearbeiter/in: freiwillige Angabe, bleibt im Browser. Ersetzt keine
   Anmeldung — sie macht den Verlauf nur lesbarer. */
const BEARB_KEY = 'wahlregister.bearbeiter';
const bearbFeld = document.getElementById('bearbeiter');
bearbFeld.value = localStorage.getItem(BEARB_KEY) || '';
bearbFeld.addEventListener('input', () =>
  localStorage.setItem(BEARB_KEY, bearbFeld.value.trim()));
const bearbeiter = () => bearbFeld.value.trim();

/* ------------------------------------------------------------- Darstellung */

const KRITERIUM = {nachname: 'Nachname', vorname: 'Vorname',
                   geburtsdatum: 'Geburtsdatum', adresse: 'Adresse'};
const HERKUNFT = {suche: 'über die Suche', qid: 'Q-ID von Hand',
                  sammel: 'Sammelentscheidung',
                  doublette: 'von der Doublette übernommen'};

/* Welche Wahl hinter welcher Spalte steht — **je Ordner**, weil nicht alle
   Ordner zur selben Wahl gehören. Ordner 2 bis 5 haken drei Spalten der Akte
   ab und meinen drei Wahlen des Jahres 1933. Ordner 6 und 7 führen eine
   einzige Spalte; in Ordner 7 belegt sie **zwei** Wahlen, weil Reichstag und
   Preußischer Landtag am 20.5.1928 am selben Tag gewählt wurden.

   Haken und Kreuz heißen beide „teilgenommen", nur das leere Feld heißt
   „nicht teilgenommen"; was sich nicht lesen ließ, bleibt unklar und geht gar
   nicht mit. Das gilt auch für den Stimmschein aus Ordner 6. */
const WAHLSPALTEN_STANDARD = [['sp4_ok', 'Spalte 4', 'Reichstagswahl'],
                              ['sp5_ok', 'Spalte 5', 'Stadtverordnetenversammlung'],
                              ['sp8_ok', 'Spalte 8', 'Provinziallandtag']];
const WAHLSPALTEN_ORDNER = {
  6: [['spst_ok', 'Stimmabgabe', 'Reichstagswahl u. Volksabstimmung 12.11.1933']],
  7: [['spst_ok', 'Stimmabgabe', 'Reichstagswahl 20.5.1928'],
      ['spst_ok', 'Stimmabgabe', 'Preußischer Landtag 20.5.1928']],
};

/* Aktenspalten ohne zugeordnete Wahl. Ordner 3, 4 und 5 erfassen 6, 7 und 9;
   dort steht in keiner Zeile ein Vermerk. Angezeigt werden sie deshalb nur,
   falls doch einmal einer auftaucht — exportiert wird er nicht, weil niemand
   weiß, welche Wahl gemeint wäre. */
const WAHLSPALTEN_OHNE_WAHL = [['sp6_ok', 6], ['sp7_ok', 7], ['sp9_ok', 9]];

function wahlvermerke(e) {
  const spalten = WAHLSPALTEN_ORDNER[e.ordner] || WAHLSPALTEN_STANDARD;
  const zugeordnet = spalten.map(([feld, quelle, wahl]) => {
    const v = e[feld];
    const [klasse, zeichen, was] = v === 1 ? ['ja', '✓', 'Vermerk — geht als P119 mit']
      : v === 0 ? ['nein', '·', 'leer — keine Teilnahme, keine Aussage']
      : v === 2 ? ['unklar', 'St.', 'Stimmschein — die Person durfte anderswo '
                   + 'wählen; dass sie es tat, sagt die Liste nicht, also keine Aussage']
      : ['unklar', '?', 'Vermerk unlesbar — keine Aussage'];
    return `<span class="wahl ${klasse}" title="${esc(quelle)} · ${esc(wahl)}: ${was}">
      ${zeichen}&nbsp;${esc(wahl)}</span>`;
  });
  const offen = WAHLSPALTEN_OHNE_WAHL.filter(([feld]) => e[feld] === 1)
    .map(([, nr]) => `<span class="wahl unklar" title="Spalte ${nr} der Akte trägt
      einen Vermerk, ist aber keiner Wahl zugeordnet — geht nicht in den Export">
      ✓&nbsp;Spalte ${nr}</span>`);
  return zugeordnet.concat(offen).join('');
}

/* Ein Suchtreffer bzw. eine geprüfte Q-ID — dieselbe Optik wie ein Vorschlag,
   nur ohne Score, weil es keinen gibt. */
function fund(p) {
  return `<div class="kand fund" data-qid="${esc(p.qid)}" data-label="${esc(p.label || '')}">
    <div class="kopf">
      <a class="lab" href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.label || p.qid)}</a>
      <span class="qid">${esc(p.qid)}</span>
    </div>
    <div class="meta">* ${esc(p.birth_date || '?')}${p.death_year ? ' † ' + esc(p.death_year) : ''}
      ${p.description ? '· ' + esc(p.description) : ''}</div>
    ${p.note ? `<div class="warn">⚠ ${esc(p.note)}</div>` : ''}
    <div class="acts"><button class="btn small waehlenext">diese Person</button></div>
  </div>`;
}

function scoreKlasse(s) {
  return s >= 85 ? 'hoch' : s >= 70 ? 'mittel' : 'niedrig';
}

/* Die vier Teilwerte als kleine Balken — damit sichtbar ist, worauf ein
   Vorschlag beruht, bevor jemand ihn bestätigt. */
function teilscores(t) {
  return Object.keys(KRITERIUM).map(k => `
    <span class="ts" title="${esc(KRITERIUM[k])}: ${esc(t[k] ?? 0)} %">
      <i style="width:${Math.max(2, t[k] ?? 0)}%"></i>
      <b>${esc(KRITERIUM[k].slice(0, 4))}</b></span>`).join('');
}

function kandidat(k, eintrag) {
  const gewaehlt = eintrag.status === 'zugeordnet' && eintrag.entschieden_qid === k.qid;
  return `<div class="kand ${gewaehlt ? 'gewaehlt' : ''}" data-qid="${esc(k.qid)}">
    <div class="kopf">
      <span class="score ${scoreKlasse(k.score)}">${esc(k.score)}</span>
      <a class="lab" href="${esc(k.url)}" target="_blank" rel="noopener">${esc(k.label)}</a>
      <span class="qid">${esc(k.qid)}</span>
    </div>
    <div class="meta">* ${esc(k.birth_date || '?')}${k.death_year ? ' † ' + esc(k.death_year) : ''}
      ${k.adresse_grund ? '· <b>' + esc(k.adresse_grund) + '</b>' : ''}
      ${k.description ? '· ' + esc(k.description) : ''}</div>
    <div class="tsrow">${teilscores(k.teilscores || {})}</div>
    ${(k.hinweise || []).map(h => `<div class="warn">⚠ ${esc(h)}</div>`).join('')}
    <div class="acts">
      <button class="btn small waehlen ${gewaehlt ? 'on' : ''}">
        ${gewaehlt ? '✓ zugeordnet' : 'diese Person'}</button>
    </div>
  </div>`;
}

/* Der gemerkte P120-Verdacht als Zeile unter dem Feld. Bewusst schlicht: er
   ist keine Zuordnung, sondern eine Notiz, die im Export als P120 landet. */
function p120Stand(e) {
  return `<div class="p120stand">möglicherweise identisch mit
    <a href="https://database.factgrid.de/wiki/Item:${esc(e.p120_qid)}"
       target="_blank" rel="noopener">${esc(e.p120_label || e.p120_qid)}</a>
    <span class="qid">${esc(e.p120_qid)}</span>
    <span class="muted">— geht als P120 in den Export, sobald der Eintrag
      entschieden ist</span></div>`;
}

/* Derselbe Mensch in einem anderen Ordner. Seit Ordner 6 und 7 kommt das
   regelmäßig vor: die beiden gehören zu anderen Wahlen (12.11.1933 und
   20.5.1928), und wer 1928 wählen durfte, durfte es 1933 meistens auch.

   Zwei Fälle, zwei Reaktionen. Ist das Gegenstück schon einem Item
   zugeordnet, genügt ein Klick — die Q-ID muss nicht ein zweites Mal gesucht
   werden. Ist es als neue Person entschieden, ist der Hinweis eine Warnung:
   beide Seiten neu anzulegen ergäbe zwei Items für einen Menschen. Ein Urteil
   fällt hier nichts; übernommen wird von Hand, und das Protokoll hält fest,
   dass die Q-ID aus einer Doublette stammt. */
function doublettenHTML(e) {
  if (!e.doubletten || !e.doubletten.length) return '';
  const zeilen = e.doubletten.map(d => {
    const stand = d.status === 'zugeordnet' && d.qid
      ? `<a href="https://database.factgrid.de/wiki/Item:${esc(d.qid)}"
             target="_blank" rel="noopener">${esc(d.label || d.qid)}</a>
         <span class="qid">${esc(d.qid)}</span>
         ${e.status ? '' : `<button class="btn small uebernehmen"
             data-qid="${esc(d.qid)}" data-label="${esc(d.label || '')}"
             >Q-ID übernehmen</button>`}`
      : d.status === 'kein_treffer'
      ? `<span class="warn">dort als neue Person entschieden — beide neu
           anzulegen ergäbe zwei Items für einen Menschen</span>`
      : '<span class="muted">dort noch nicht entschieden</span>';
    return `<div class="doublette">
      <span class="score ${scoreKlasse(d.score)}">${d.score}</span>
      <span class="wer">Ordner ${esc(d.ordner)} · Nr. ${esc(d.partner)} —
        ${esc(d.name_voll)}, * ${esc(d.geburtsdatum)}, ${esc(d.adresse)}</span>
      <span class="grund muted">${esc(d.grund)}</span>
      <div class="stand">${stand}</div>
    </div>`;
  }).join('');
  return `<div class="doubletten"><div class="dtitel">Derselbe Mensch im
    Register</div>${zeilen}</div>`;
}

function eintragHTML(e) {
  const entschieden = e.status === 'zugeordnet' ? `<span class="badge bestaetigt">
      zugeordnet → ${esc(e.entschieden_qid)}</span>`
    : e.status === 'kein_treffer' ? '<span class="badge verworfen">nicht in FactGrid</span>'
    : '';
  const kandidaten = e.kandidaten.length
    ? e.kandidaten.map(k => kandidat(k, e)).join('')
    : `<div class="empty">Kein Vorschlag über der Schwelle.</div>`;
  return `<section class="block eintrag ${e.status ? 'fertig' : ''}" data-lfd="${esc(e.lfd_id)}">
    <div class="zeile">
      <div class="quelle">
        <div class="name">${esc(e.name_voll)}
          ${e.titel ? `<span class="badge ident"
             title="Titel aus dem Register — steht nicht im Label, geht als P170 mit"
             >${esc(e.titel)}</span>` : ''}
          ${sexBadge(e.geschlecht)} ${entschieden}</div>
        <div class="meta">
          Ordner ${esc(e.ordner)} · Nr. ${esc(e.lfd_id)} · Akte ${esc(e.akte_nr)}
          ${e.geburtsname ? '· geb. ' + esc(e.geburtsname) : ''}
          · * ${esc(e.geburtsdatum)}
          · ${esc(e.adresse)}${e.adress_qid
              ? ` <a class="pill" href="https://database.factgrid.de/wiki/Item:${esc(e.adress_qid)}"
                   target="_blank" rel="noopener" title="${esc(e.adress_label)}">${esc(e.adress_qid)}</a>`
              : ' <span class="muted">(kein Adress-Item)</span>'}
          ${e.bild ? `<span class="muted" title="Blatt der Fotografie, auf dem dieser Eintrag steht">· ${esc(e.bild)}</span>` : ''}
        </div>
        <div class="wahlzeile">${wahlvermerke(e)}</div>
        ${e.bemerkung ? `<div class="bem">„${esc(e.bemerkung)}“</div>` : ''}
        ${doublettenHTML(e)}
        ${e.status === 'zugeordnet' ? `<div class="zugeteilt">
           zugeordnet: <a href="https://database.factgrid.de/wiki/Item:${esc(e.entschieden_qid)}"
             target="_blank" rel="noopener">${esc(e.entschieden_label || e.entschieden_qid)}</a>
           <span class="qid">${esc(e.entschieden_qid)}</span>
           ${e.entschieden_quelle && e.entschieden_quelle !== 'vorschlag'
             ? `<span class="muted">(${esc(HERKUNFT[e.entschieden_quelle] || e.entschieden_quelle)})</span>` : ''}
         </div>` : ''}
        <div class="acts">
          <button class="btn small keiner ${e.status === 'kein_treffer' ? 'on' : ''}">
            keine Person in FactGrid</button>
          ${e.status ? '<button class="btn small zurueck">Entscheidung aufheben</button>' : ''}
          <button class="btn small tiefer">tiefer suchen</button>
          <button class="btn small suchen">in FactGrid suchen</button>
        </div>
        <div class="manuell">
          <input type="text" class="qidfeld" placeholder="Q-ID direkt zuordnen, z. B. Q878132"
                 value="" spellcheck="false">
          <button class="btn small qidbtn">prüfen</button>
          <div class="qidinfo"></div>
        </div>
        <div class="manuell p120zeile">
          <span class="p120lbl" title="Möglicherweise identisch mit">P120</span>
          <input type="text" class="p120feld" spellcheck="false"
                 placeholder="möglicherweise identisch mit, z. B. Q1351615"
                 value="${esc(e.p120_qid || '')}">
          <button class="btn small p120btn">merken</button>
          ${e.p120_qid ? '<button class="btn small p120weg">entfernen</button>' : ''}
          <div class="p120info">${e.p120_qid ? p120Stand(e) : ''}</div>
        </div>
      </div>
      <div class="kandidaten">
        <div class="suchbox" hidden>
          <input type="search" class="suchfeld" placeholder="Name in FactGrid suchen"
                 value="${esc(e.familienname + ' ' + (e.vorname_norm || ''))}">
          <button class="btn small suchgo">suchen</button>
          <div class="suchergebnis"></div>
        </div>
        ${kandidaten}
      </div>
    </div>
  </section>`;
}

/* ------------------------------------------------------------------ Laden */

function params(extra = {}) {
  const p = new URLSearchParams();
  filter.forEach(f => { if (f.value) p.set(f.id, f.value); });
  Object.entries(extra).forEach(([k, v]) => p.set(k, v));
  return p;
}

async function laden(neu = true) {
  if (neu) offset = 0;
  statusTxt.textContent = 'lädt …';
  statusTxt.className = 'status loading';
  try {
    const d = await getJSON('/api/liste?' + params({limit: SEITE, offset}));
    gesamt = d.count;
    const html = d.results.map(eintragHTML).join('');
    if (neu) listeEl.innerHTML = html || '<div class="block"><div class="empty">Nichts gefunden.</div></div>';
    else listeEl.insertAdjacentHTML('beforeend', html);
    offset += d.results.length;
    mehrEl.innerHTML = offset < gesamt
      ? `<button class="btn" id="mehrBtn">weitere ${Math.min(SEITE, gesamt - offset)} laden</button>
         <span class="muted">${num(offset)} von ${num(gesamt)}</span>`
      : (gesamt ? `<span class="muted">alle ${num(gesamt)} geladen</span>` : '');
    zeigeFortschritt(d.fortschritt);
    statusTxt.textContent = `${num(gesamt)} Einträge im Filter`;
    statusTxt.className = 'status';
  } catch (err) {
    statusTxt.textContent = 'Fehler: ' + err.message;
    statusTxt.className = 'status error';
  }
}

/* Der gewählte Ordner als Anhängsel für jede Adresse — Export und Verlauf
   zeigen dasselbe wie die Liste. Leer heißt „alle Ordner". */
const gewaehlterOrdner = () => document.getElementById('ordner').value;

function mitOrdner(pfad) {
  const o = gewaehlterOrdner();
  return o ? `${pfad}${pfad.includes('?') ? '&' : '?'}ordner=${encodeURIComponent(o)}` : pfad;
}

/* Die Download-Ziele hängen am Filter, nicht an einer eigenen Auswahl: was die
   Liste zeigt, wird auch heruntergeladen. */
function exportZiele() {
  const o = gewaehlterOrdner();
  document.getElementById('qsLink').href = mitOrdner('/export/quickstatements.txt');
  document.getElementById('csvLink').href = mitOrdner('/export/entscheidungen.csv');
  document.getElementById('protokollLink').href = mitOrdner('/export/protokoll.csv');
  document.getElementById('exportOrdner').textContent =
    o ? `nur Ordner ${o}` : 'alle Ordner';
  // Eine offene Vorschau zeigte sonst den alten Ordner weiter.
  const pre = document.getElementById('vorschau');
  if (!pre.hidden) {
    pre.hidden = true;
    document.getElementById('vorschauBtn').textContent = 'Vorschau ansehen';
  }
}

/* Der Balken zeigt den gewählten Ordner, wenn einer gewählt ist — sonst wäre
   die Arbeit an einem Ordner im Gesamtstand der übrigen nicht zu sehen. */
function zeigeFortschritt(f) {
  const gewaehlt = gewaehlterOrdner();
  const teil = gewaehlt && (f.ordner || []).find(o => String(o.ordner) === gewaehlt);
  const s = teil || f;
  const fertig = s.zugeordnet + s.kein_treffer;
  const pct = s.gesamt ? Math.round(100 * fertig / s.gesamt) : 0;
  fortschrittEl.innerHTML =
    `<span class="bar"><i style="width:${pct}%"></i></span>
     <span>${teil ? 'Ordner ' + esc(teil.ordner) + ': ' : ''}${num(fertig)} / ${num(s.gesamt)} entschieden</span>
     <span class="rest">${num(s.offen)} offen</span>`;
  document.getElementById('exportInfo').textContent =
    (teil ? `Ordner ${teil.ordner}: ` : 'Alle Ordner: ')
    + `${num(s.zugeordnet)} Zuordnungen zu bestehenden Items, ${num(s.kein_treffer)} `
    + `Personen ohne FactGrid-Eintrag (werden als CREATE angelegt), `
    + `${num(s.offen)} noch offen. `
    + `Abgleich zuletzt gerechnet: ${f.lauf || '—'}.`;
}

/* ------------------------------------------------------------ Entscheidung */

async function entscheiden(block, body) {
  try {
    const d = await postJSON('/api/entscheidung', {...body, bearbeiter: bearbeiter()});
    zeigeFortschritt(d.fortschritt);
    const frisch = await getJSON('/api/eintrag/' + encodeURIComponent(body.lfd_id));
    block.outerHTML = eintragHTML(frisch);
    protokollLaden();
  } catch (err) {
    statusTxt.textContent = 'Fehler: ' + err.message;
    statusTxt.className = 'status error';
  }
}

listeEl.addEventListener('click', async ev => {
  const block = ev.target.closest('.eintrag');
  if (!block) return;
  const lfd = block.dataset.lfd;

  const waehlen = ev.target.closest('.waehlen');
  if (waehlen) {
    const qid = waehlen.closest('.kand').dataset.qid;
    const schon = waehlen.classList.contains('on');
    return entscheiden(block, {lfd_id: lfd, qid,
                               status: schon ? 'offen' : 'zugeordnet'});
  }
  const keiner = ev.target.closest('.keiner');
  if (keiner) {
    return entscheiden(block, {lfd_id: lfd,
      status: keiner.classList.contains('on') ? 'offen' : 'kein_treffer'});
  }
  if (ev.target.closest('.zurueck')) {
    return entscheiden(block, {lfd_id: lfd, status: 'offen'});
  }
  // Die Q-ID vom Gegenstück in einem anderen Ordner übernehmen. Sie ist dort
  // von Hand entschieden worden; hier wird sie ebenso von Hand übernommen und
  // im Protokoll als solche vermerkt.
  const doub = ev.target.closest('.uebernehmen');
  if (doub) {
    return entscheiden(block, {lfd_id: lfd, status: 'zugeordnet',
      qid: doub.dataset.qid, label: doub.dataset.label, quelle: 'doublette'});
  }

  // Suchtreffer oder von Hand geprüfte Q-ID zuordnen
  const ext = ev.target.closest('.waehlenext');
  if (ext) {
    const karte = ext.closest('.kand');
    return entscheiden(block, {
      lfd_id: lfd, status: 'zugeordnet', qid: karte.dataset.qid,
      label: karte.dataset.label,
      quelle: karte.classList.contains('ausqid') ? 'qid' : 'suche'});
  }

  // Freie Suche im FactGrid-Auszug
  if (ev.target.closest('.suchen')) {
    const box = block.querySelector('.suchbox');
    box.hidden = !box.hidden;
    if (!box.hidden) box.querySelector('.suchfeld').focus();
    return;
  }
  if (ev.target.closest('.suchgo')) {
    const box = block.querySelector('.suchbox');
    const ziel = box.querySelector('.suchergebnis');
    ziel.innerHTML = '<div class="muted">sucht …</div>';
    const d = await getJSON('/api/suche?q='
      + encodeURIComponent(box.querySelector('.suchfeld').value));
    ziel.innerHTML = d.results.length
      ? d.results.map(fund).join('')
      : `<div class="empty">${esc(d.note || 'Nichts gefunden.')}</div>`;
    return;
  }

  // Q-ID von Hand prüfen und dann zuordnen
  if (ev.target.closest('.qidbtn')) {
    const feld = block.querySelector('.qidfeld');
    const info = block.querySelector('.qidinfo');
    const qid = feld.value.trim().toUpperCase();
    info.innerHTML = '<div class="muted">prüft …</div>';
    try {
      const p = await getJSON('/api/person/' + encodeURIComponent(qid));
      info.innerHTML = fund(p).replace('class="kand fund"', 'class="kand fund ausqid"');
    } catch (err) {
      let msg = err.message;
      try { msg = JSON.parse(err.message).error || msg; } catch (_) { /* Klartext */ }
      info.innerHTML = `<div class="warn">${esc(msg)}</div>`;
    }
    return;
  }

  // P120 merken bzw. entfernen — unabhängig von der Entscheidung
  const p120weg = ev.target.closest('.p120weg');
  if (ev.target.closest('.p120btn') || p120weg) {
    const feld = block.querySelector('.p120feld');
    const info = block.querySelector('.p120info');
    const qid = p120weg ? '' : feld.value.trim().toUpperCase();
    info.innerHTML = '<div class="muted">speichert …</div>';
    try {
      const d = await postJSON('/api/p120',
        {lfd_id: lfd, qid, bearbeiter: bearbeiter()});
      const frisch = await getJSON('/api/eintrag/' + encodeURIComponent(lfd));
      block.outerHTML = eintragHTML(frisch);
      if (d.p120_qid && d.bekannt === false) {
        document.querySelector(`.eintrag[data-lfd="${CSS.escape(lfd)}"] .p120info`)
          .insertAdjacentHTML('beforeend',
            '<div class="warn">⚠ Im lokalen FactGrid-Auszug nicht enthalten. '
            + 'Gemerkt ist sie trotzdem — bitte im FactGrid prüfen.</div>');
      }
      protokollLaden();
    } catch (err) {
      let msg = err.message;
      try { msg = JSON.parse(err.message).error || msg; } catch (_) { /* Klartext */ }
      info.innerHTML = `<div class="warn">${esc(msg)}</div>`;
    }
    return;
  }

  const tiefer = ev.target.closest('.tiefer');
  if (tiefer) {
    tiefer.disabled = true;
    tiefer.textContent = 'sucht …';
    const e = await getJSON('/api/eintrag/' + encodeURIComponent(lfd));
    const res = await getJSON('/api/neu-abgleichen/' + encodeURIComponent(lfd)
                              + '?min_score=30');
    e.kandidaten = res.candidates.map(c => ({...c, birth_date: c.birth_date}));
    block.outerHTML = eintragHTML(e);
  }
});

/* Enter in den beiden Eingabefeldern löst den danebenstehenden Knopf aus. */
listeEl.addEventListener('keydown', ev => {
  if (ev.key !== 'Enter') return;
  const feld = ev.target.closest('.suchfeld, .qidfeld, .p120feld');
  if (!feld) return;
  ev.preventDefault();
  feld.closest('.suchbox, .manuell')
      .querySelector('.suchgo, .qidbtn, .p120btn').click();
});

mehrEl.addEventListener('click', ev => {
  if (ev.target.closest('#mehrBtn')) laden(false);
});

/* Sammelentscheidung: alles, was im aktuellen Filter noch offen ist, auf
   „keine Person in FactGrid" setzen. Überschreibt nie Entschiedenes. */
document.getElementById('sammelBtn').addEventListener('click', async () => {
  const f = {};
  filter.forEach(x => { if (x.value) f[x.id] = x.value; });
  const d = await getJSON('/api/liste?' + params({limit: 1}));
  const offen = d.fortschritt.offen;
  const txt = `Alle im aktuellen Filter noch offenen Einträge als „keine Person `
    + `in FactGrid" markieren?\n\nFilter: ${d.count} Einträge`
    + `\nInsgesamt offen: ${offen}\n\nBereits Entschiedenes bleibt unberührt. `
    + `Einzelne Entscheidungen lassen sich danach wieder aufheben.`;
  if (!confirm(txt)) return;
  try {
    const r = await postJSON('/api/sammelentscheidung',
      {status: 'kein_treffer', filter: f, bearbeiter: bearbeiter()});
    zeigeFortschritt(r.fortschritt);
    statusTxt.textContent = `${num(r.geaendert)} Einträge als „nicht in FactGrid" markiert`;
    statusTxt.className = 'status';
    laden(true);
    protokollLaden();
  } catch (err) {
    statusTxt.textContent = 'Fehler: ' + err.message;
    statusTxt.className = 'status error';
  }
});

filter.forEach(f => f.addEventListener(
  f.type === 'search' ? 'input' : 'change',
  f.type === 'search' ? debounce(() => laden(true), 250)
    /* Der Ordner bestimmt mit, welche Straßen es gibt — erst die Liste
       nachziehen, dann laden, sonst filtert eine Straße mit, die es im neuen
       Ordner nicht gibt. Export und Verlauf hängen ebenfalls daran. */
    : () => {
      if (f.id === 'ordner') { strassenFuellen(); exportZiele(); protokollLaden(); }
      laden(true);
    }));

/* -------------------------------------------------------- Export & Kontext */

document.getElementById('vorschauBtn').addEventListener('click', async ev => {
  const pre = document.getElementById('vorschau');
  if (!pre.hidden) { pre.hidden = true; ev.target.textContent = 'Vorschau ansehen'; return; }
  const d = await getJSON(mitOrdner('/api/quickstatements'));
  pre.textContent = d.zeilen.slice(0, 200).join('\n') +
    (d.anzahl > 200 ? `\n… (${num(d.anzahl)} Zeilen insgesamt)` : '');
  pre.hidden = false;
  ev.target.textContent = 'Vorschau ausblenden';
});

document.getElementById('speichernBtn').addEventListener('click', async () => {
  const s = document.getElementById('einst_status');
  const body = {};
  EINST.forEach(k => {
    const el = document.getElementById(k);
    if (el) body[k] = el.value.trim();
  });
  try {
    await postJSON('/api/einstellungen', body);
    s.textContent = 'gespeichert';
    s.className = 'status';
  } catch (err) {
    s.textContent = 'Fehler: ' + err.message;
    s.className = 'status error';
  }
});

/* ------------------------------------------------------------- Verlauf */

const AKTION = {entscheidung: 'Entscheidung', sammel: 'Sammelentscheidung',
                ruecknahme: 'Rücknahme', p120: 'P120 vorgemerkt'};
const STATUS = {zugeordnet: 'zugeordnet', kein_treffer: 'nicht in FactGrid',
                moeglich: 'möglicherweise identisch'};

function stand(status, qid) {
  if (!status) return '<span class="muted">offen</span>';
  return esc(STATUS[status] || status) + (qid ? ` <span class="qid">${esc(qid)}</span>` : '');
}

async function protokollLaden() {
  const lfd = document.getElementById('p_lfd').value.trim();
  const d = await getJSON(mitOrdner('/api/protokoll?limit=200'
    + (lfd ? '&lfd_id=' + encodeURIComponent(lfd) : '')));
  document.getElementById('protokollCount').textContent =
    `${num(d.gesamt)} Änderungen`
    + (d.ordner ? ` in Ordner ${d.ordner}` : ' insgesamt');

  /* Ein Stapel kann über Ordnergrenzen gehen, wenn er ohne Ordnerfilter
     gesetzt wurde. Die Rücknahme nimmt ihn dann ganz zurück — das muss
     dranstehen, sonst räumt ein Klick im Ordner 3 auch in Ordner 2 auf. */
  document.getElementById('stapelListe').innerHTML = d.stapel.length
    ? '<div class="stapel">' + d.stapel.map(s => `
        <div class="stapelzeile">
          <b>Sammelentscheidung</b> ${esc(s.zeit.replace('T', ', '))}
          · ${num(s.n)} Einträge${s.bearbeiter ? ' · ' + esc(s.bearbeiter) : ''}
          ${s.n_ordner < s.n
            ? `<span class="warn">davon ${num(s.n_ordner)} in diesem Ordner —
                 die Rücknahme betrifft alle ${num(s.n)}</span>` : ''}
          ${s.rueckholbar > 0
            ? `<button class="btn small stapelzurueck" data-stapel="${esc(s.stapel)}"
                 data-ganz="${s.n_ordner < s.n ? '1' : ''}">
                 ${num(s.rueckholbar)} zurücknehmen</button>`
            : '<span class="muted">nichts mehr zurückzunehmen</span>'}
        </div>`).join('') + '</div>'
    : '';

  document.getElementById('protokollTabelle').innerHTML = d.results.length
    ? '<thead><tr><th>Zeitpunkt</th><th>Eintrag</th><th>Aktion</th>'
      + '<th>vorher</th><th>nachher</th><th>Bearbeiter/in</th></tr></thead><tbody>'
      + d.results.map(r => `<tr>
          <td class="num muted">${esc(r.zeit.replace('T', ' '))}</td>
          <td>${esc(r.lfd_id)} <span class="muted">${esc(r.name_voll || '')}</span></td>
          <td>${esc(AKTION[r.aktion] || r.aktion)}</td>
          <td>${stand(r.alt_status, r.alt_qid)}</td>
          <td>${stand(r.neu_status, r.neu_qid)}</td>
          <td class="muted">${esc(r.bearbeiter || '—')}</td></tr>`).join('')
      + '</tbody>'
    : '<tbody><tr><td class="empty">Noch keine Änderungen.</td></tr></tbody>';
}

document.getElementById('p_neu').addEventListener('click', protokollLaden);
document.getElementById('p_lfd').addEventListener('input', debounce(protokollLaden, 250));

document.getElementById('stapelListe').addEventListener('click', async ev => {
  const btn = ev.target.closest('.stapelzurueck');
  if (!btn) return;
  if (!confirm('Diese Sammelentscheidung zurücknehmen?\n\nZurückgesetzt wird nur, '
      + 'was seither nicht von Hand geändert wurde — bewusste Zuordnungen bleiben.'
      + (btn.dataset.ganz
         ? '\n\nAchtung: dieser Stapel reicht über den gewählten Ordner hinaus '
           + 'und wird vollständig zurückgenommen.' : ''))) return;
  btn.disabled = true;
  const r = await postJSON('/api/stapel-zuruecknehmen',
    {stapel: btn.dataset.stapel, bearbeiter: bearbeiter()});
  statusTxt.textContent = `${num(r.zurueckgenommen)} zurückgenommen`
    + (r.uebersprungen ? `, ${num(r.uebersprungen)} übersprungen (inzwischen von Hand geändert)` : '');
  statusTxt.className = 'status';
  zeigeFortschritt(r.fortschritt);
  laden(true);
  protokollLaden();
});

/* ------------------------------------------------------- Ordner & Straßen */

let STRASSEN = [];

/* Straßen wiederholen sich zwischen den Ordnern („Liebenwerder Plan" steht in
   Ordner 2 und 3 und meint dort verschiedene Häuser). Die Liste zeigt deshalb
   nur die Straßen des gewählten Ordners. */
function strassenFuellen() {
  const sel = document.getElementById('strasse');
  const ordner = document.getElementById('ordner').value;
  const vorher = sel.value;
  sel.innerHTML = '<option value="">alle</option>';
  STRASSEN.filter(s => !ordner || String(s.ordner) === ordner).forEach(s => {
    const o = document.createElement('option');
    o.value = s.strasse;
    o.textContent = ordner ? `${s.strasse} (${s.n})`
                           : `${s.strasse} — Ordner ${s.ordner} (${s.n})`;
    sel.appendChild(o);
  });
  sel.value = [...sel.options].some(o => o.value === vorher) ? vorher : '';
}

getJSON('/api/strassen').then(d => { STRASSEN = d.results; strassenFuellen(); });

getJSON('/api/ordner').then(d => {
  const sel = document.getElementById('ordner');
  d.results.forEach(o => {
    const opt = document.createElement('option');
    opt.value = o.ordner;
    opt.textContent = `Ordner ${o.ordner} (${num(o.gesamt)})`;
    opt.title = o.quelle_csv || '';
    sel.appendChild(opt);
  });
  exportZiele();
  const ohne = d.results.filter(o => !o.qs_quelle);
  document.getElementById('quellenWarnung').innerHTML = ohne.length
    ? `<div class="warn">⚠ Ohne hinterlegte Primärquelle:
         Ordner ${ohne.map(o => esc(o.ordner)).join(', ')} — diese Einträge
         bekommen kein P51. Unten unter „Kontext-Items" nachtragen.</div>`
    : '';
});

getJSON('/api/einstellungen').then(d => {
  /* Je Ordner ein Feld für seine Primärquelle. Welche es gibt, sagen die
     Einstellungen selbst (`qs_quelle_o<N>`) — ein neuer Ordner braucht hier
     keine Änderung. */
  const quellen = Object.keys(d).filter(k => /^qs_quelle_o\d+$/.test(k)).sort();
  document.getElementById('quellenFelder').innerHTML = quellen.map(k => {
    const nr = k.slice('qs_quelle_o'.length);
    return `<label class="field tight"
             title="Primärquelle (P51) für Ordner ${esc(nr)} — das FactGrid-Item des Archivales">
      <span class="lbl">P51 Ordner ${esc(nr)}</span>
      <input type="text" id="${esc(k)}"></label>`;
  }).join('');
  EINST.push(...quellen);
  EINST.forEach(k => {
    const el = document.getElementById(k);
    if (el && d[k] != null) el.value = d[k];
  });
});

laden();
protokollLaden();
