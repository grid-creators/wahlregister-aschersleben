"""Wahlregister Aschersleben 1933 — Abgleich mit FactGrid.

Eine Aufgabe: jeden Registereintrag einer FactGrid-Person zuordnen oder
festhalten, dass es dort keine gibt. Ergebnis ist eine QuickStatements-Tabelle.

Flask auf Port 8770 über `data/register.sqlite`. Die Peru-DB (`persons.sqlite`)
wird nur lesend geöffnet, es geht kein Aufruf ins Netz.

Die App ist offen: Entscheiden und Herunterladen darf jede und jeder, ohne
Anmeldung. Es gibt bewusst keine Rechteprüfung.
"""

import csv
import datetime
import io
import json
import os
import re
import secrets
import sqlite3
import threading

from flask import Flask, Response, g, jsonify, request, send_from_directory

import match as M
import quickstatements as QS
from schema import QS_DEFAULTS, ensure, quelle_key

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get('REGISTER_DB', os.path.join(ROOT, 'data', 'register.sqlite'))
PORT = int(os.environ.get('REGISTER_PORT', '8770'))
HOST = os.environ.get('REGISTER_HOST', '0.0.0.0')

app = Flask(__name__, static_folder=os.path.join(ROOT, 'app', 'static'),
            template_folder=os.path.join(ROOT, 'app', 'templates'))

_matcher_lock = threading.Lock()
_matcher = None

EINTRAG_COLS = ('e.ordner, e.lfd_id, e.akte_nr, e.familienname, e.vorname, '
                'e.vorname_norm, e.titel, e.geburtsname, e.name_voll, e.adresse, '
                'e.strasse, e.hausnr, e.geburtsdatum, e.geburtsjahr, '
                'e.geschlecht, e.geschlecht_q, e.sp4_ok, e.sp5_ok, e.sp6_ok, '
                'e.sp7_ok, e.sp8_ok, e.sp9_ok, e.spst_ok, e.bemerkung, e.bild')


def db():
    con = getattr(g, '_db', None)
    if con is None:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        ensure(con)
        g._db = con
    return con


@app.teardown_appcontext
def _close_db(_exc):
    con = getattr(g, '_db', None)
    if con is not None:
        con.close()


def matcher():
    global _matcher
    with _matcher_lock:
        if _matcher is None:
            _matcher = M.Matcher()
        return _matcher


def einstellungen():
    werte = dict(QS_DEFAULTS)
    werte.update(dict(db().execute('SELECT key, value FROM einstellungen')))
    return werte


# -------------------------------------------------------------------- Seite

@app.get('/')
def seite():
    return send_from_directory(app.template_folder, 'index.html')


# -------------------------------------------------------------- Arbeitsliste

def _filter(args):
    where, params = [], []

    q = args.get('q', '').strip()
    if q:
        where.append('e.rowid IN (SELECT rowid FROM entries_fts '
                     'WHERE entries_fts MATCH ?)')
        params.append(' OR '.join('"%s"*' % t for t in re.findall(r'\w+', q)))

    # Der Ordner des Bestands. Straßen wiederholen sich zwischen den Ordnern
    # („Liebenwerder Plan"), deshalb steht er neben dem Straßenfilter.
    ordner = str(args.get('ordner', '') or '').strip()
    if ordner.isdigit():
        where.append('e.ordner = ?')
        params.append(int(ordner))

    strasse = args.get('strasse', '').strip()
    if strasse:
        where.append('e.strasse = ?')
        params.append(strasse)

    status = args.get('status', '')
    if status == 'offen':
        where.append('d.status IS NULL')
    elif status in ('zugeordnet', 'kein_treffer'):
        where.append('d.status = ?')
        params.append(status)
    elif status == 'entschieden':
        where.append('d.status IS NOT NULL')

    treffer = args.get('treffer', '')
    if treffer == 'mit':
        where.append('IFNULL(k.n, 0) > 0')
    elif treffer == 'ohne':
        where.append('IFNULL(k.n, 0) = 0')
    elif treffer == 'sicher':
        where.append('IFNULL(k.best, 0) >= 85')

    return (' AND '.join(where) or '1', params)


# `adress_items` hängt am Ordner: dieselbe Adresse kann in zwei Ordnern stehen
# und dort verschiedene FactGrid-Items meinen (Liebenwerder Plan 20).
JOINS = ('FROM entries e '
         'LEFT JOIN entscheidungen d ON d.lfd_id = e.lfd_id '
         'LEFT JOIN (SELECT lfd_id, count(*) n, max(score) best '
         '           FROM kandidaten GROUP BY lfd_id) k ON k.lfd_id = e.lfd_id '
         'LEFT JOIN adress_items a ON a.ordner = e.ordner '
         '                        AND a.strasse = e.strasse '
         '                        AND a.hausnr = e.hausnr '
         'LEFT JOIN p120 p ON p.lfd_id = e.lfd_id '
         'LEFT JOIN (SELECT lfd_id, count(*) n, max(score) best '
         '           FROM doubletten GROUP BY lfd_id) dd ON dd.lfd_id = e.lfd_id ')

BASIS_SQL = (f'SELECT {EINTRAG_COLS}, d.status, d.qid AS entschieden_qid, '
             'd.label AS entschieden_label, d.quelle AS entschieden_quelle, '
             'd.notiz, d.geaendert_am, IFNULL(k.n, 0) AS n_kandidaten, '
             'k.best AS bester_score, a.qid AS adress_qid, '
             'a.label AS adress_label, p.qid AS p120_qid, '
             'p.label AS p120_label, IFNULL(dd.n, 0) AS n_doubletten, '
             'dd.best AS bester_doublette ' + JOINS)


@app.get('/api/liste')
def api_liste():
    where, params = _filter(request.args)
    limit = max(1, min(int(request.args.get('limit', '25')), 200))
    offset = int(request.args.get('offset', '0') or 0)
    count = db().execute(f'SELECT count(*) {JOINS} WHERE {where}',
                         params).fetchone()[0]
    rows = db().execute(BASIS_SQL + f'WHERE {where} ORDER BY e.rowid '
                        f'LIMIT ? OFFSET ?', params + [limit, offset]).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d['kandidaten'] = _kandidaten(r['lfd_id'])
        # Nur nachschlagen, wo es etwas zu holen gibt — die allermeisten
        # Einträge stehen nur einmal im Register.
        d['doubletten'] = _doubletten(r['lfd_id']) if r['n_doubletten'] else []
        out.append(d)
    return jsonify({'count': count, 'results': out, 'fortschritt': _fortschritt()})


def _kandidaten(lfd_id):
    out = []
    for k in db().execute('SELECT * FROM kandidaten WHERE lfd_id=? ORDER BY rang',
                          (lfd_id,)):
        d = dict(k)
        d['teilscores'] = json.loads(d.get('teilscores') or '{}')
        d['hinweise'] = json.loads(d.get('hinweise') or '[]')
        d['url'] = f"https://database.factgrid.de/wiki/Item:{d['qid']}"
        out.append(d)
    return out


ZAEHLER = ('gesamt', 'zugeordnet', 'kein_treffer', 'offen', 'mit_kandidaten')


def _fortschritt_sql(gruppiert=False):
    return (('SELECT e.ordner, ' if gruppiert else 'SELECT ')
            + "count(*) gesamt, "
              "sum(d.status = 'zugeordnet') zugeordnet, "
              "sum(d.status = 'kein_treffer') kein_treffer, "
              'sum(d.status IS NULL) offen, count(k.lfd_id) mit_kandidaten '
              'FROM entries e LEFT JOIN entscheidungen d ON d.lfd_id = e.lfd_id '
              'LEFT JOIN (SELECT DISTINCT lfd_id FROM kandidaten) k '
              '       ON k.lfd_id = e.lfd_id '
            + ('GROUP BY e.ordner ORDER BY e.ordner' if gruppiert else ''))


def _fortschritt():
    """Gesamtstand und derselbe Stand je Ordner — die Arbeit an einem Ordner
    soll sich nicht im Gesamtbalken der übrigen verstecken."""
    c = db()
    r = c.execute(_fortschritt_sql()).fetchone()
    stand = {k: r[k] or 0 for k in ZAEHLER}
    stand['ordner'] = [{'ordner': r['ordner'], **{k: r[k] or 0 for k in ZAEHLER}}
                       for r in c.execute(_fortschritt_sql(True))]
    stand['lauf'] = dict(c.execute('SELECT key, value FROM lauf_meta')).get('lauf')
    return stand


def _doubletten(lfd_id):
    """Dieselbe Person in einem anderen Ordner — mit ihrer Entscheidung.

    Seit Ordner 6 und 7 steht mancher Mensch zweimal im Register, weil die
    beiden zu anderen Wahlen gehören. Ist das Gegenstück schon entschieden,
    muss die Q-ID hier nicht ein zweites Mal gesucht werden; ist es das nicht,
    warnt die Anzeige davor, zweimal dieselbe Person neu anzulegen."""
    return [dict(r) for r in db().execute(
        'SELECT d.partner, d.ordner, d.score, d.grund, e.name_voll, '
        'e.geburtsdatum, e.adresse, e.bemerkung, x.status, x.qid, x.label '
        'FROM doubletten d JOIN entries e ON e.lfd_id = d.partner '
        'LEFT JOIN entscheidungen x ON x.lfd_id = d.partner '
        'WHERE d.lfd_id = ? ORDER BY d.score DESC, d.partner', (lfd_id,))]


@app.get('/api/eintrag/<lfd_id>')
def api_eintrag(lfd_id):
    r = db().execute(BASIS_SQL + 'WHERE e.lfd_id = ?', (lfd_id,)).fetchone()
    if not r:
        return jsonify({'error': 'unbekannt'}), 404
    d = dict(r)
    d['kandidaten'] = _kandidaten(lfd_id)
    d['doubletten'] = _doubletten(lfd_id)
    return jsonify(d)


@app.get('/api/neu-abgleichen/<lfd_id>')
def api_neu(lfd_id):
    """Einen Eintrag frisch rechnen — mit frei wählbarer Mindestpunktzahl,
    um bei einem Fehlschlag tiefer zu suchen."""
    e = db().execute(f'SELECT {EINTRAG_COLS} FROM entries e WHERE e.lfd_id=?',
                     (lfd_id,)).fetchone()
    if not e:
        return jsonify({'error': 'unbekannt'}), 404
    adressen = [dict(a, exakt=(a['hausnr'] == e['hausnr'])) for a in db().execute(
        'SELECT strasse, hausnr, qid, label FROM adress_items '
        'WHERE ordner=? AND strasse=?', (e['ordner'], e['strasse']))]
    try:
        min_score = int(request.args.get('min_score', M.MIN_SCORE))
        res = matcher().match(dict(e), adressen, min_score=max(20, min_score))
    except FileNotFoundError as exc:
        return jsonify({'error': str(exc)}), 503
    for c in res['candidates']:
        c['lfd_id'] = lfd_id
    return jsonify(res)


@app.get('/api/suche')
def api_suche():
    """Freie Personensuche im FactGrid-Auszug — für die Fälle, in denen der
    Abgleich die richtige Person nicht vorschlägt."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({'results': [], 'note': 'Bitte mindestens zwei Zeichen.'})
    limit = max(1, min(int(request.args.get('limit', '15')), 50))
    try:
        peru = sqlite3.connect(f'file:{M.find_peru_db()}?mode=ro', uri=True)
    except FileNotFoundError as exc:
        return jsonify({'error': str(exc)}), 503
    peru.row_factory = sqlite3.Row
    ausdruck = ' '.join('"%s"*' % t for t in re.findall(r'\w+', q))
    try:
        rows = peru.execute(
            'SELECT p.id, p.label_de, p.description_de, p.birth_date, '
            'p.birth_prec, p.death_year FROM persons_fts f '
            'JOIN persons p ON p.rowid = f.rowid '
            'WHERE persons_fts MATCH ? ORDER BY rank LIMIT ?',
            (ausdruck, limit)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    peru.close()
    return jsonify({'results': [_person(r) for r in rows]})


@app.get('/api/person/<qid>')
def api_person(qid):
    """Eine von Hand eingegebene Q-ID auflösen, damit man vor dem Zuordnen
    sieht, wen man da zuordnet."""
    qid = qid.strip().upper()
    if not re.match(r'^Q\d+$', qid):
        return jsonify({'error': 'Das ist keine Q-ID (erwartet: Q12345).'}), 400
    try:
        peru = sqlite3.connect(f'file:{M.find_peru_db()}?mode=ro', uri=True)
    except FileNotFoundError as exc:
        return jsonify({'error': str(exc)}), 503
    peru.row_factory = sqlite3.Row
    r = peru.execute(
        'SELECT id, label_de, description_de, birth_date, birth_prec, death_year '
        'FROM persons WHERE id = ?', (qid,)).fetchone()
    peru.close()
    if not r:
        # Der Auszug ist ein Abzug — neuere Items stehen noch nicht drin.
        return jsonify({'qid': qid, 'bekannt': False,
                        'url': f'https://database.factgrid.de/wiki/Item:{qid}',
                        'note': 'Im lokalen FactGrid-Auszug nicht enthalten. '
                                'Zuordnen ist möglich, bitte vorher im '
                                'FactGrid prüfen.'})
    return jsonify({**_person(r), 'bekannt': True})


def _person(r):
    return {
        'qid': r['id'], 'label': r['label_de'], 'description': r['description_de'],
        'birth_date': M._fmt(M.item_datum(r['birth_date'], r['birth_prec'])),
        'death_year': r['death_year'],
        'url': f"https://database.factgrid.de/wiki/Item:{r['id']}",
    }


@app.get('/api/strassen')
def api_strassen():
    """Straßen mit ihrem Ordner. Dieselbe Straße kann in zwei Ordnern liegen,
    deshalb steht sie hier je Ordner einmal — die Seite blendet aus, was nicht
    zum gewählten Ordner gehört."""
    return jsonify({'results': [dict(r) for r in db().execute(
        'SELECT ordner, strasse, count(*) n FROM entries '
        'GROUP BY 1, 2 ORDER BY n DESC')]})


@app.get('/api/ordner')
def api_ordner():
    """Die Ordner des Bestands, wie sie in der Datenbank stehen — mit der CSV,
    aus der sie gebaut wurden, und dem Item ihrer Primärquelle."""
    quellen = dict(db().execute("SELECT key, value FROM meta "
                                "WHERE key LIKE 'quelle_o%'"))
    cfg = einstellungen()
    return jsonify({'results': [
        {'ordner': r['ordner'], 'gesamt': r['gesamt'],
         'quelle_csv': quellen.get(f"quelle_o{r['ordner']}"),
         'qs_quelle': cfg.get(quelle_key(r['ordner'])) or None}
        for r in db().execute('SELECT ordner, count(*) gesamt FROM entries '
                              'GROUP BY 1 ORDER BY 1')]})


# -------------------------------------------------------------- Entscheidung

def _bearbeiter(data=None):
    """Freiwillige Angabe, wer gerade arbeitet — die App kennt keine
    Anmeldung. Leer ist ausdrücklich erlaubt."""
    wert = (data or {}).get('bearbeiter') or request.headers.get('X-Bearbeiter', '')
    return str(wert).strip()[:60]


def _stand(lfd):
    r = db().execute('SELECT status, qid FROM entscheidungen WHERE lfd_id=?',
                     (lfd,)).fetchone()
    return (r['status'], r['qid']) if r else (None, None)


def _protokollieren(lfd, aktion, alt, neu, quelle, bearbeiter, stapel=None):
    db().execute(
        'INSERT INTO protokoll (zeit, lfd_id, aktion, alt_status, alt_qid, '
        'neu_status, neu_qid, quelle, bearbeiter, stapel) '
        'VALUES (?,?,?,?,?,?,?,?,?,?)',
        (datetime.datetime.now().isoformat(timespec='seconds'), lfd, aktion,
         alt[0], alt[1], neu[0], neu[1], quelle, bearbeiter or None, stapel))


@app.post('/api/entscheidung')
def api_entscheidung():
    data = request.get_json(silent=True) or {}
    lfd = str(data.get('lfd_id', ''))
    status = data.get('status', '')
    qid = (data.get('qid') or '').strip().upper()
    label = (data.get('label') or '').strip()
    quelle = data.get('quelle') or 'vorschlag'
    jetzt = datetime.datetime.now().isoformat(timespec='seconds')

    if not db().execute('SELECT 1 FROM entries WHERE lfd_id=?', (lfd,)).fetchone():
        return jsonify({'error': 'unbekannter Eintrag'}), 404
    alt = _stand(lfd)
    if status == 'offen':
        db().execute('DELETE FROM entscheidungen WHERE lfd_id=?', (lfd,))
    elif status == 'zugeordnet':
        if not re.match(r'^Q\d+$', qid):
            return jsonify({'error': 'Q-ID fehlt oder ist ungültig'}), 400
        if not label:
            label = _label_zu_qid(qid) or ''
        db().execute('INSERT OR REPLACE INTO entscheidungen VALUES (?,?,?,?,?,?,?)',
                     (lfd, status, qid, data.get('notiz', ''), jetzt, label, quelle))
    elif status == 'kein_treffer':
        db().execute('INSERT OR REPLACE INTO entscheidungen VALUES (?,?,?,?,?,?,?)',
                     (lfd, status, None, data.get('notiz', ''), jetzt, None, quelle))
    else:
        return jsonify({'error': 'status muss zugeordnet|kein_treffer|offen sein'}), 400
    _protokollieren(lfd, 'entscheidung', alt,
                    (None, None) if status == 'offen' else (status, qid or None),
                    quelle, _bearbeiter(data))
    db().commit()
    return jsonify({'ok': True, 'lfd_id': lfd, 'status': status,
                    'qid': qid or None, 'fortschritt': _fortschritt()})


def _label_zu_qid(qid):
    """Beschriftung für eine Q-ID — erst aus den Vorschlägen, dann aus dem
    FactGrid-Auszug. Wird mit der Entscheidung gespeichert, damit die Liste
    lesbar bleibt, ohne bei jeder Anzeige die Peru-DB zu öffnen."""
    r = db().execute('SELECT label FROM kandidaten WHERE qid=? LIMIT 1',
                     (qid,)).fetchone()
    if r and r['label']:
        return r['label']
    try:
        peru = sqlite3.connect(f'file:{M.find_peru_db()}?mode=ro', uri=True)
    except FileNotFoundError:
        return None
    row = peru.execute('SELECT label_de FROM persons WHERE id=?', (qid,)).fetchone()
    peru.close()
    return row[0] if row else None


# ------------------------------------------- P120 „Möglicherweise identisch"

@app.post('/api/p120')
def api_p120():
    """Eine Q-ID vormerken, die zu diesem Eintrag passen könnte, ohne dass die
    Zuordnung sicher wäre. Unabhängig von der Entscheidung: der übliche Fall
    ist „keine Person in FactGrid" plus ein Verdacht. Leere Q-ID löscht.

    Wie beim Zuordnen wird eine Q-ID, die der Peru-Auszug nicht kennt, **nicht**
    abgewiesen — der Auszug ist ein Abzug, FactGrid ist weiter."""
    data = request.get_json(silent=True) or {}
    lfd = str(data.get('lfd_id', ''))
    qid = (data.get('qid') or '').strip().upper()

    if not db().execute('SELECT 1 FROM entries WHERE lfd_id=?', (lfd,)).fetchone():
        return jsonify({'error': 'unbekannter Eintrag'}), 404

    alt = _p120_stand(lfd)
    if not qid:
        db().execute('DELETE FROM p120 WHERE lfd_id=?', (lfd,))
        neu, label, bekannt = (None, None), None, None
    else:
        if not re.match(r'^Q\d+$', qid):
            return jsonify({'error': 'Das ist keine Q-ID (erwartet: Q12345).'}), 400
        if qid == (_stand(lfd)[1] or ''):
            return jsonify({'error': 'Diese Q-ID ist dem Eintrag bereits fest '
                                     'zugeordnet — P120 wäre ein Selbstbezug.'}), 400
        label = (data.get('label') or '').strip() or _label_zu_qid(qid)
        bekannt = label is not None
        db().execute('INSERT OR REPLACE INTO p120 VALUES (?,?,?,?)',
                     (lfd, qid, label,
                      datetime.datetime.now().isoformat(timespec='seconds')))
        neu = ('moeglich', qid)

    _protokollieren(lfd, 'p120', alt, neu, 'p120', _bearbeiter(data))
    db().commit()
    return jsonify({'ok': True, 'lfd_id': lfd, 'p120_qid': qid or None,
                    'p120_label': label, 'bekannt': bekannt,
                    'url': f'https://database.factgrid.de/wiki/Item:{qid}' if qid else None})


def _p120_stand(lfd):
    r = db().execute('SELECT qid FROM p120 WHERE lfd_id=?', (lfd,)).fetchone()
    return ('moeglich', r['qid']) if r else (None, None)


@app.post('/api/sammelentscheidung')
def api_sammelentscheidung():
    """Alle **noch offenen** Einträge des aktuellen Filters auf einmal
    entscheiden. Bereits Entschiedenes wird nie überschrieben — sonst wäre
    Handarbeit mit einem Klick weg."""
    data = request.get_json(silent=True) or {}
    if data.get('status') != 'kein_treffer':
        return jsonify({'error': 'Sammelentscheidung gibt es nur für '
                                 '„keine Person in FactGrid".'}), 400

    class Args(dict):
        def get(self, k, d=''):
            return dict.get(self, k, d)

    where, params = _filter(Args(data.get('filter') or {}))
    treffer = [r['lfd_id'] for r in db().execute(
        f'SELECT e.lfd_id {JOINS} WHERE ({where}) AND d.status IS NULL', params)]
    jetzt = datetime.datetime.now().isoformat(timespec='seconds')
    # Zufallssuffix, weil zwei Sammelentscheidungen in derselben Sekunde sonst
    # dieselbe Kennung bekämen — und eine Rücknahme beide träfe.
    stapel = ('S' + jetzt.replace('-', '').replace(':', '').replace('T', '-')
              + '-' + secrets.token_hex(3))
    bearbeiter = _bearbeiter(data)
    db().executemany(
        'INSERT OR REPLACE INTO entscheidungen VALUES (?,?,?,?,?,?,?)',
        [(lfd, 'kein_treffer', None, data.get('notiz', ''), jetzt, None, 'sammel')
         for lfd in treffer])
    for lfd in treffer:
        # alt ist immer (None, None) — die Sammelentscheidung fasst nur
        # Offenes an. Das macht die Rücknahme eindeutig.
        _protokollieren(lfd, 'sammel', (None, None), ('kein_treffer', None),
                        'sammel', bearbeiter, stapel)
    db().commit()
    return jsonify({'ok': True, 'geaendert': len(treffer), 'stapel': stapel,
                    'fortschritt': _fortschritt()})


@app.get('/api/protokoll')
def api_protokoll():
    """Verlauf, neueste zuerst. Optional auf einen Eintrag oder einen
    Sammel-Stapel eingegrenzt."""
    where, params = ['1'], []
    if request.args.get('lfd_id'):
        where.append('p.lfd_id = ?')
        params.append(request.args['lfd_id'])
    if request.args.get('stapel'):
        where.append('p.stapel = ?')
        params.append(request.args['stapel'])
    ordner = _ordner_arg()
    if ordner is not None:
        where.append('e.ordner = ?')
        params.append(ordner)
    limit = max(1, min(int(request.args.get('limit', '100')), 2000))
    rows = db().execute(
        'SELECT p.*, e.ordner, e.name_voll FROM protokoll p '
        'LEFT JOIN entries e ON e.lfd_id = p.lfd_id '
        f"WHERE {' AND '.join(where)} ORDER BY p.id DESC LIMIT ?",
        params + [limit]).fetchall()

    # Sammelentscheidungen, die sich noch zurücknehmen lassen. `n` und
    # `rueckholbar` zählen den **ganzen** Stapel, auch im Ordnerfilter: die
    # Rücknahme kennt keine Ordnergrenze, sie nimmt den Stapel zurück, wie er
    # gesetzt wurde. `n_ordner` sagt, wie viel davon im gewählten Ordner liegt
    # — ist das weniger, weist die Seite darauf hin.
    s_where = "p.aktion = 'sammel' AND p.stapel IS NOT NULL"
    s_params = []
    if ordner is None:
        n_ordner = 'count(*)'
    else:
        n_ordner = 'sum(CASE WHEN e.ordner = ? THEN 1 ELSE 0 END)'
        s_params.append(ordner)
        s_where += ' AND p.stapel IN (SELECT p2.stapel FROM protokoll p2 ' \
                   'JOIN entries e2 ON e2.lfd_id = p2.lfd_id ' \
                   'WHERE e2.ordner = ? AND p2.aktion = \'sammel\')'
        s_params.append(ordner)
    stapel = [dict(r) for r in db().execute(
        'SELECT p.stapel, min(p.zeit) zeit, count(*) n, '
        "max(IFNULL(p.bearbeiter,'')) bearbeiter, "
        "sum(CASE WHEN d.status = 'kein_treffer' AND d.quelle = 'sammel' "
        '         THEN 1 ELSE 0 END) rueckholbar, '
        f'{n_ordner} n_ordner '
        'FROM protokoll p LEFT JOIN entscheidungen d ON d.lfd_id = p.lfd_id '
        'LEFT JOIN entries e ON e.lfd_id = p.lfd_id '
        f'WHERE {s_where} '
        'GROUP BY p.stapel ORDER BY p.stapel DESC LIMIT 20', s_params)]

    gesamt_sql = 'SELECT count(*) FROM protokoll p'
    gesamt_params = []
    if ordner is not None:
        gesamt_sql += (' JOIN entries e ON e.lfd_id = p.lfd_id WHERE e.ordner = ?')
        gesamt_params.append(ordner)
    return jsonify({'results': [dict(r) for r in rows], 'stapel': stapel,
                    'ordner': ordner,
                    'gesamt': db().execute(gesamt_sql,
                                           gesamt_params).fetchone()[0]})


@app.post('/api/stapel-zuruecknehmen')
def api_stapel_zurueck():
    """Eine Sammelentscheidung rückgängig machen. Zurückgesetzt wird nur, was
    seither **nicht** von Hand verändert wurde — wer einen dieser Einträge
    inzwischen bewusst zugeordnet hat, behält seine Arbeit."""
    data = request.get_json(silent=True) or {}
    stapel = str(data.get('stapel', '')).strip()
    if not stapel:
        return jsonify({'error': 'Kein Stapel angegeben.'}), 400
    zeilen = db().execute(
        "SELECT lfd_id, neu_status FROM protokoll "
        "WHERE stapel = ? AND aktion = 'sammel'", (stapel,)).fetchall()
    if not zeilen:
        return jsonify({'error': 'Unbekannte Sammelentscheidung.'}), 404

    bearbeiter = _bearbeiter(data)
    zurueck, uebersprungen = 0, 0
    for z in zeilen:
        alt = _stand(z['lfd_id'])
        if alt[0] != z['neu_status'] or alt[1] is not None:
            uebersprungen += 1        # inzwischen von Hand geändert
            continue
        q = db().execute(
            "SELECT quelle FROM entscheidungen WHERE lfd_id=?", (z['lfd_id'],)
        ).fetchone()
        if not q or q['quelle'] != 'sammel':
            uebersprungen += 1
            continue
        db().execute('DELETE FROM entscheidungen WHERE lfd_id=?', (z['lfd_id'],))
        _protokollieren(z['lfd_id'], 'ruecknahme', alt, (None, None),
                        'sammel', bearbeiter, stapel)
        zurueck += 1
    db().commit()
    return jsonify({'ok': True, 'zurueckgenommen': zurueck,
                    'uebersprungen': uebersprungen,
                    'fortschritt': _fortschritt()})


@app.get('/export/protokoll.csv')
def export_protokoll():
    ordner = _ordner_arg()
    where, params = ('WHERE e.ordner = ? ', [ordner]) if ordner else ('', [])
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(['zeit', 'ordner', 'lfd_id', 'name', 'aktion', 'vorher_status',
                'vorher_qid', 'nachher_status', 'nachher_qid', 'weg',
                'bearbeiter', 'stapel'])
    for r in db().execute(
            'SELECT p.zeit, e.ordner, p.lfd_id, e.name_voll, p.aktion, '
            'p.alt_status, p.alt_qid, p.neu_status, p.neu_qid, p.quelle, '
            'p.bearbeiter, p.stapel FROM protokoll p '
            'LEFT JOIN entries e ON e.lfd_id = p.lfd_id '
            + where + 'ORDER BY p.id', params):
        w.writerow(list(r))
    name = f'protokoll-ordner{ordner}.csv' if ordner else 'protokoll.csv'
    return Response(buf.getvalue().encode('utf-8-sig'), mimetype='text/csv',
                    headers={'Content-Disposition':
                             f'attachment; filename="{name}"'})


@app.get('/api/einstellungen')
def api_einstellungen_get():
    return jsonify(einstellungen())


@app.post('/api/einstellungen')
def api_einstellungen_set():
    data = request.get_json(silent=True) or {}
    for k, v in data.items():
        if k not in QS_DEFAULTS:
            return jsonify({'error': f'unbekannte Einstellung: {k}'}), 400
        v = str(v).strip()
        if k.startswith('qs_') and k not in ('qs_beschreibung', 'qs_geschlecht'):
            if v and not re.match(r'^Q\d+$', v):
                return jsonify({'error': f'{k}: „{v}“ ist keine Q-ID'}), 400
        db().execute('INSERT OR REPLACE INTO einstellungen VALUES (?,?)', (k, v))
    db().commit()
    return jsonify(einstellungen())


# --------------------------------------------------------------------- Export

def _ordner_arg():
    """`?ordner=3` grenzt Export und Vorschau auf einen Ordner ein. Ohne
    Angabe wird alles Entschiedene ausgegeben."""
    o = str(request.args.get('ordner', '') or '').strip()
    return int(o) if o.isdigit() else None


def _export_zeilen(ordner=None):
    where, params = '', []
    if ordner is not None:
        where, params = 'WHERE e.ordner = ? ', [ordner]
    return db().execute(
        'SELECT e.*, d.status, d.qid AS ziel_qid, a.qid AS adress_qid, '
        'p.qid AS p120_qid '
        'FROM entries e JOIN entscheidungen d ON d.lfd_id = e.lfd_id '
        'LEFT JOIN adress_items a ON a.ordner = e.ordner '
        '                        AND a.strasse = e.strasse '
        '                        AND a.hausnr = e.hausnr '
        'LEFT JOIN p120 p ON p.lfd_id = e.lfd_id '
        + where + 'ORDER BY e.rowid', params).fetchall()


def _doubletten_paare():
    """{lfd_id: [(partner, score), …]} für den Export. Ungefiltert nach
    Ordner: die Warnung vor einem doppelten Item gilt gerade dann, wenn das
    Gegenstück in einem anderen Ordner steht."""
    out = {}
    for r in db().execute('SELECT lfd_id, partner, score FROM doubletten'):
        out.setdefault(r['lfd_id'], []).append((r['partner'], r['score']))
    return out


def _vorhandene_aussagen():
    """Wohnorte, die ein Ziel-Item laut Peru-Auszug schon hat — damit der
    Export P83/P208 nicht doppelt anlegt. Nur `residence` zählt: derselbe Ort
    als Geburts- oder Sterbeort ist eine andere Aussage."""
    qids = [r['qid'] for r in db().execute(
        "SELECT qid FROM entscheidungen WHERE status='zugeordnet' AND qid IS NOT NULL")]
    if not qids:
        return {}
    try:
        peru = sqlite3.connect(f'file:{M.find_peru_db()}?mode=ro', uri=True)
    except FileNotFoundError:
        return {}
    out = {}
    for i in range(0, len(qids), 900):
        teil = qids[i:i + 900]
        ph = ','.join('?' * len(teil))
        for pid, qid in peru.execute(
                f'SELECT p.id, q.qid FROM persons p '
                f'JOIN person_qref q ON q.person_rowid = p.rowid '
                f"WHERE q.kind = 'residence' AND p.id IN ({ph})", teil):
            out.setdefault(pid, set()).add(qid)
    peru.close()
    return out


@app.get('/export/quickstatements.txt')
def export_qs():
    ordner = _ordner_arg()
    zeilen = QS.bauen(_export_zeilen(ordner), einstellungen(),
                      _vorhandene_aussagen(), _doubletten_paare())
    name = f'quickstatements-ordner{ordner}.txt' if ordner else 'quickstatements.txt'
    return Response('\n'.join(zeilen) + '\n',
                    mimetype='text/plain; charset=utf-8',
                    headers={'Content-Disposition':
                             f'attachment; filename="{name}"'})


@app.get('/api/quickstatements')
def api_qs_vorschau():
    zeilen = QS.bauen(_export_zeilen(_ordner_arg()), einstellungen(),
                      _vorhandene_aussagen(), _doubletten_paare())
    return jsonify({'zeilen': zeilen, 'anzahl': len(zeilen)})


@app.get('/export/entscheidungen.csv')
def export_csv():
    ordner = _ordner_arg()
    where, params = ('WHERE e.ordner = ? ', [ordner]) if ordner else ('', [])
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(['ordner', 'lfd_id', 'akte_nr', 'name', 'geburtsname',
                'geburtsdatum', 'adresse', 'status', 'factgrid_qid', 'notiz',
                'entschieden_am', 'p120_qid'])
    for r in db().execute(
            'SELECT e.ordner, e.lfd_id, e.akte_nr, e.name_voll, e.geburtsname, '
            'e.geburtsdatum, e.adresse, d.status, d.qid, d.notiz, d.geaendert_am, '
            'p.qid '
            'FROM entries e JOIN entscheidungen d ON d.lfd_id = e.lfd_id '
            'LEFT JOIN p120 p ON p.lfd_id = e.lfd_id '
            + where + 'ORDER BY e.rowid', params):
        w.writerow(list(r))
    name = f'entscheidungen-ordner{ordner}.csv' if ordner else 'entscheidungen.csv'
    return Response(buf.getvalue().encode('utf-8-sig'), mimetype='text/csv',
                    headers={'Content-Disposition':
                             f'attachment; filename="{name}"'})


if __name__ == '__main__':
    app.run(host=HOST, port=PORT, threaded=True)
