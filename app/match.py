"""Abgleich Wahlregister ↔ FactGrid-Personen (Peru-Datenbank).

Vier Kriterien, alle unscharf: **Vorname, Nachname, Geburtsdatum, Adresse**.
Jedes liefert eine Ähnlichkeit zwischen 0 und 1, gewichtet ergibt das einen
Score von 0 bis 100. Was auffällig ist (etwa ein Sterbedatum vor der Wahl),
steht am Kandidaten dran und wird von Hand entschieden.

Ein einziger harter Ausschluss: **zwei tagesgenaue Geburtsdaten, die mehr als
einen Monat auseinanderliegen** (`datum_widerspruch()`). Das sind zwei
Personen, und kein noch so gleicher Name macht daraus eine.

Die Peru-DB (`persons.sqlite`) wird ausschließlich lesend geöffnet, es geht
kein Aufruf ins Netz.
"""

import datetime
import difflib
import os
import re
import sqlite3
import threading
import unicodedata

PERU_DB_CANDIDATES = [
    os.environ.get('PERU_DB', ''),
    '/srv/apps/peru/build/persons.sqlite',
]

# Gewichte der vier Kriterien (Summe 100).
GEWICHT = {'nachname': 30, 'vorname': 20, 'geburtsdatum': 35, 'adresse': 15}

# Ab hier wird ein Kandidat überhaupt angeboten. 55 heißt: ein bloßer
# Namensgleichklang (Nachname + Vorname = 50) genügt nicht — es muss etwas
# vom Geburtsdatum oder von der Adresse dazukommen.
MIN_SCORE = 55
MAX_KANDIDATEN = 10

_MAIDEN_RE = re.compile(r'\(\s*(?:geb\.?|verw\.?|verh\.?)\s*([^)]*)\)', re.I)


def find_peru_db():
    for p in PERU_DB_CANDIDATES:
        if p and os.path.exists(p):
            return p
    raise FileNotFoundError('Peru-DB nicht gefunden — PERU_DB setzen.')


def fold(s):
    """Kleinschreibung ohne Diakritika, ß→ss — Basis jedes Vergleichs."""
    s = (s or '').lower().replace('ß', 'ss')
    s = ''.join(c for c in unicodedata.normalize('NFKD', s)
                if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9 ]+', ' ', s).strip()


def tokens(s):
    return [t for t in fold(s).split() if t]


def split_label(label):
    """'Selma Schwabe (geb. Mikowsky)' → ('Selma Schwabe', 'Mikowsky')."""
    if not label:
        return ('', '')
    m = _MAIDEN_RE.search(label)
    if not m:
        return (label.strip(), '')
    return (_MAIDEN_RE.sub('', label).strip(), m.group(1).strip())


AEHNLICH_MIN = 0.55   # darunter zählt ein Wortvergleich als „passt nicht"


def aehnlich(a, b):
    """Unscharfer Wortvergleich 0…1. Eine Initiale („M.") zählt als Treffer,
    wenn der Anfangsbuchstabe passt — im Register sind Vornamen oft gekürzt.

    Unter `AEHNLICH_MIN` wird 0 zurückgegeben: solche Paare tragen im Score
    ohnehin nichts bei, und die beiden Schnellschätzer von SequenceMatcher
    sparen den teuren Vergleich für die große Mehrheit der Kandidaten."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if len(a) == 1 or len(b) == 1:
        return 0.85 if a[0] == b[0] else 0.0
    sm = difflib.SequenceMatcher(None, a, b)
    if sm.real_quick_ratio() < AEHNLICH_MIN or sm.quick_ratio() < AEHNLICH_MIN:
        return 0.0
    r = sm.ratio()
    return r if r >= AEHNLICH_MIN else 0.0


def beste_paarung(links, rechts):
    """Bester Treffer je Token der linken Seite, gemittelt. So schlägt
    „Anna Marie" ↔ „Marie Anna Elisabeth" nicht wegen der Reihenfolge fehl."""
    if not links or not rechts:
        return 0.0
    werte = [max(aehnlich(l, r) for r in rechts) for l in links]
    return sum(werte) / len(werte)


def datum_teile(s):
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', (s or '').strip())
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def item_datum(date_str, prec):
    """(y, m, d) aus dem Wikibase-Zeitstring; Monat/Tag 0, wenn ungenau."""
    m = re.match(r'^\+(\d{1,4})-(\d{2})-(\d{2})', date_str or '')
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if prec is not None and prec < 11:
        d = 0
    if prec is not None and prec < 10:
        mo = 0
    return (y, mo, d)


# Zwei tagesgenaue Geburtsdaten dürfen um einen Monat auseinanderliegen — so
# weit reicht ein verlesener Monat („5." statt „6.") oder eine um eins
# verrutschte Zahl. Weiter nicht: 31 Tage sind der größte Abstand, den zwei
# Daten desselben Kalendertags in benachbarten Monaten haben können.
DATUM_TOLERANZ_TAGE = 31


def datum_widerspruch(a, b):
    """Sind beide Daten tagesgenau und mehr als einen Monat auseinander, sind
    es **zwei verschiedene Personen** — der einzige harte Ausschluss im
    Abgleich.

    Nur wenn beide Seiten Tag *und* Monat führen. Ein bloß jahresgenaues
    FactGrid-Datum ist kein Widerspruch, sondern eine fehlende Angabe, und ein
    Eintrag ohne Geburtsdatum sagt gar nichts."""
    if not a or not b:
        return False
    if not (a[1] and a[2] and b[1] and b[2]):
        return False
    try:
        abstand = datetime.date(*a) - datetime.date(*b)
    except ValueError:      # 31. Februar und Ähnliches — kein Urteil möglich
        return False
    return abs(abstand.days) > DATUM_TOLERANZ_TAGE


def datum_score(a, b):
    """1.0 tagesgleich · 0.75 Monat+Jahr · 0.5 Jahr · 0.25 ±1 Jahr."""
    if not a or not b:
        return 0.0
    if a[1] and b[1] and a[2] and b[2] and a == b:
        return 1.0
    if a[0] == b[0]:
        if a[1] and b[1] and a[1] == b[1]:
            return 1.0 if (not a[2] or not b[2]) else 0.75
        return 0.5
    if abs(a[0] - b[0]) == 1:
        return 0.25
    return 0.0


class Matcher:
    """Kandidatensuche und Bewertung. Connection je Thread, weil sqlite3-
    Verbindungen nicht zwischen Threads geteilt werden dürfen."""

    def __init__(self, peru_db=None):
        self.path = peru_db or find_peru_db()
        self._local = threading.local()
        self._bdate_index = None
        self._lock = threading.Lock()

    @property
    def db(self):
        con = getattr(self._local, 'con', None)
        if con is None:
            con = sqlite3.connect(f'file:{self.path}?mode=ro', uri=True,
                                  check_same_thread=False)
            con.row_factory = sqlite3.Row
            self._local.con = con
        return con

    def bdate_index(self):
        """Geburtsdatum → rowids. Einmal aufgebaut (~2 s), danach findet der
        Abgleich auch Personen, deren Name im FactGrid ganz anders geschrieben
        ist — das Geburtsdatum allein reicht als Einstieg."""
        with self._lock:
            if self._bdate_index is None:
                idx = {}
                for rid, bd, prec in self.db.execute(
                        'SELECT rowid, birth_date, birth_prec FROM persons '
                        'WHERE birth_date IS NOT NULL AND birth_prec >= 11'):
                    d = item_datum(bd, prec)
                    if d:
                        idx.setdefault(d, []).append(rid)
                self._bdate_index = idx
            return self._bdate_index

    # ------------------------------------------------------------- Blocking
    def kandidaten_rowids(self, eintrag, adress_qids=()):
        """Drei unabhängige Zugänge, damit ein Fehler in *einem* Feld nicht
        den ganzen Treffer kostet: Name, Adresse, Geburtsdatum."""
        rowids = []

        for name in (eintrag.get('familienname'), eintrag.get('geburtsname')):
            for t in {t for t in tokens(name) if len(t) >= 3}:
                # Erst exakt, dann als Präfix: „Borstel" findet so auch
                # „Borstell". Die Reihenfolge ist nicht beliebig — bei häufigen
                # Tokens („fried", „peter") greift das LIMIT, und dann soll der
                # exakte Treffer schon drin sein. Der Präfix ergänzt nur.
                for muster in ('"%s"' % t, '"%s"*' % t):
                    try:
                        rowids += [r['rowid'] for r in self.db.execute(
                            'SELECT rowid FROM persons_fts WHERE persons_fts MATCH ? '
                            'LIMIT 6000', (muster,))]
                    except sqlite3.OperationalError:
                        pass

        if adress_qids:
            ph = ','.join('?' * len(adress_qids))
            rowids += [r['person_rowid'] for r in self.db.execute(
                f'SELECT person_rowid FROM person_qref WHERE kind = ? '
                f'AND qid IN ({ph})', ['residence'] + list(adress_qids))]

        d = datum_teile(eintrag.get('geburtsdatum'))
        if d:
            rowids += self.bdate_index().get(d, [])

        return list(dict.fromkeys(rowids))

    # ------------------------------------------------------------ Bewertung
    def match(self, eintrag, adressen=None, limit=MAX_KANDIDATEN,
              min_score=MIN_SCORE):
        """`adressen`: Liste von {qid, label, strasse} für diesen Eintrag —
        exakte Adresse zuerst, dann die Straße."""
        adressen = adressen or []
        adr_exakt = {a['qid'] for a in adressen if a.get('exakt')}
        adr_strasse = {a['qid'] for a in adressen} - adr_exakt

        e_fam = tokens(eintrag.get('familienname'))
        e_geb = tokens(eintrag.get('geburtsname'))
        e_vor = tokens(eintrag.get('vorname_norm') or eintrag.get('vorname'))
        e_datum = datum_teile(eintrag.get('geburtsdatum'))

        rowids = self.kandidaten_rowids(eintrag, adr_exakt | adr_strasse)
        if not rowids:
            return {'count': 0, 'candidates': [], 'ausgeschlossen': 0}

        personen = []
        for i in range(0, len(rowids), 900):
            teil = rowids[i:i + 900]
            ph = ','.join('?' * len(teil))
            personen += self.db.execute(
                f'SELECT rowid, id, label_de, description_de, aliases_de, '
                f'birth_year, death_year, birth_date, birth_prec, sex_q '
                f'FROM persons WHERE rowid IN ({ph})', teil).fetchall()

        wohnorte = self._wohnorte([p['rowid'] for p in personen])
        namen = self._namen([p['rowid'] for p in personen])

        out, ausgeschlossen = [], 0
        for p in personen:
            i_datum = item_datum(p['birth_date'], p['birth_prec'])
            kern, maiden = split_label(p['label_de'])
            t = tokens(kern)
            i_fam = t[-1:] if t else []
            i_vor = t[:-1] if len(t) > 1 else t
            i_maiden = tokens(maiden)
            n_fam, n_vor = namen.get(p['rowid'], ([], []))

            # Nachname: gegen den Nachnamen *und* den „geb."-Teil, in beide
            # Richtungen — im Register steht mal der Ehe-, mal der Mädchenname.
            # Dazu das Familiennamen-Item: es trägt oft die richtige Form, wo
            # das Label eine Variante hat („Richard Borstell" → „Borstel").
            s_nach = max(beste_paarung(e_fam, i_fam),
                         beste_paarung(e_fam, i_maiden),
                         beste_paarung(e_geb, i_maiden),
                         beste_paarung(e_geb, i_fam),
                         beste_paarung(e_fam, n_fam),
                         beste_paarung(e_geb, n_fam))
            s_vor = max(beste_paarung(e_vor, i_vor),
                        beste_paarung(e_vor, n_vor))
            s_datum = datum_score(e_datum, i_datum)

            qids = wohnorte.get(p['rowid'], set())
            if adr_exakt & qids:
                s_adr, adr_grund = 1.0, 'gleiches Adress-Item'
            elif adr_strasse & qids:
                s_adr, adr_grund = 0.6, 'gleiche Straße'
            elif any(q == ORT_QID for q in qids):
                s_adr, adr_grund = 0.3, 'Wohnort Aschersleben'
            else:
                s_adr, adr_grund = 0.0, ''

            score = round(GEWICHT['nachname'] * s_nach + GEWICHT['vorname'] * s_vor
                          + GEWICHT['geburtsdatum'] * s_datum
                          + GEWICHT['adresse'] * s_adr)
            if score < min_score:
                continue

            # Der harte Ausschluss steht **hinter** der Schwelle, nicht davor.
            # Vorgeblockt werden je Eintrag Tausende Personen; würde hier jede
            # gezählt, die ein anderes Geburtsdatum trägt, käme eine Zahl in
            # Millionenhöhe heraus, die nichts aussagt. Gezählt wird, was ohne
            # die Regel tatsächlich im Vorschlag gestanden hätte — und genau
            # das ist der Schaden, den sie verhindert: ein gleicher Name (50)
            # und dieselbe Adresse (15) tragen einen Namensvetter sonst nach
            # oben.
            if datum_widerspruch(e_datum, i_datum):
                ausgeschlossen += 1
                continue

            hinweise = []
            if p['death_year'] and p['death_year'] < 1933:
                hinweise.append(f"† {p['death_year']} — vor der Wahl gestorben")
            if not p['birth_date']:
                hinweise.append('kein Geburtsdatum im Item')

            out.append({
                'qid': p['id'], 'label': p['label_de'],
                'description': p['description_de'],
                'birth_date': _fmt(i_datum),
                'death_year': p['death_year'], 'sex': p['sex_q'],
                'url': f"https://database.factgrid.de/wiki/Item:{p['id']}",
                'score': score,
                'teilscores': {
                    'nachname': round(100 * s_nach), 'vorname': round(100 * s_vor),
                    'geburtsdatum': round(100 * s_datum), 'adresse': round(100 * s_adr),
                },
                'adresse_grund': adr_grund,
                'wohnorte': sorted(qids),
                'hinweise': hinweise,
            })

        out.sort(key=lambda c: -c['score'])
        # `ausgeschlossen` zählt, was das Geburtsdatum verworfen hat — die Zahl
        # geht in den Bericht des Stapellaufs, damit die Regel nachweisbar ist.
        return {'count': len(out), 'candidates': out[:limit],
                'ausgeschlossen': ausgeschlossen}

    def _namen(self, rowids):
        """rowid → (Familiennamen, Vornamen) als Tokens. FactGrid führt beides
        als eigene Items (P247 für den Familiennamen); sie stehen oft richtig,
        wo das Label eine Schreibvariante trägt. Mehrere Vornamen-Items je
        Person sind normal („Jacob" *und* „Jakob") und werden zusammengelegt."""
        out = {}
        for i in range(0, len(rowids), 900):
            teil = rowids[i:i + 900]
            ph = ','.join('?' * len(teil))
            for r in self.db.execute(
                    f'SELECT pq.person_rowid, pq.kind, l.label_de FROM person_qref pq '
                    f'JOIN labels l ON l.qid = pq.qid '
                    f"WHERE pq.kind IN ('family', 'given') AND l.label_de IS NOT NULL "
                    f'AND pq.person_rowid IN ({ph})', teil):
                fam, vor = out.setdefault(r['person_rowid'], ([], []))
                (fam if r['kind'] == 'family' else vor).extend(tokens(r['label_de']))
        return out

    def _wohnorte(self, rowids):
        out = {}
        for i in range(0, len(rowids), 900):
            teil = rowids[i:i + 900]
            ph = ','.join('?' * len(teil))
            for r in self.db.execute(
                    f'SELECT person_rowid, qid FROM person_qref '
                    f"WHERE kind = 'residence' AND person_rowid IN ({ph})", teil):
                out.setdefault(r['person_rowid'], set()).add(r['qid'])
        return out


ORT_QID = 'Q80706'      # Aschersleben


def _fmt(d):
    if not d:
        return None
    if d[1] and d[2]:
        return '%04d-%02d-%02d' % d
    if d[1]:
        return '%04d-%02d' % d[:2]
    return '%04d' % d[0]
