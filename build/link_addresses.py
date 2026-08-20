"""Register-Adressen → FactGrid-Adressitems, Ordner für Ordner.

FactGrid führt Aschersleben hausnummerngenau: `Q497980 = "Aschersleben, Breite
Straße 22 (alte Hausnummer 190)"`. Diese Items stehen bei Personen als P208
(Adresse/Liegenschaft) und liegen im Peru-Auszug als `person_qref.kind =
'residence'`. Damit wird die Adresse im Abgleich zu einem harten Signal — und
im QuickStatements-Export zur eigentlichen Aussage.

Die Zuordnung kommt aus der **Quell-CSV**: jeder Ordner führt neben der Adresse
eine Spalte mit dem Adressitem. Das ist Handarbeit am Register und damit die
bessere Quelle als das frühere Raten über Label-Vergleiche — die Q-ID steht
dort auch für Häuser, die der Peru-Auszug noch nicht kennt.

`adress_items` hängt an **Ordner plus Adresse**, nicht an der Adresse allein:
`Liebenwerder Plan 20` steht in Ordner 2 und in Ordner 3, und die beiden Ordner
nennen dafür verschiedene Items (`Q498464` bzw. `Q2082248`). Ohne den Ordner im
Schlüssel bekäme einer der beiden im Export das falsche Haus.

Der Auszug liefert nur noch Beiwerk: Label und Bewohnerzahl. Fehlt die Q-ID
dort, wird die Zeile trotzdem geschrieben (`label` bleibt leer) — der Auszug
ist ein Abzug, FactGrid ist weiter.

Schreibt `adress_items` in data/register.sqlite neu. Erst
`build/build_register.py`, dann dieses Skript.

    python3 build/link_addresses.py
"""

import collections
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'app'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_register import QUELLEN, lfd_id, lies, split_address  # noqa: E402
from match import find_peru_db  # noqa: E402

DB_PATH = os.path.join(ROOT, 'data', 'register.sqlite')

SCHEMA = """
DROP TABLE IF EXISTS adress_items;
CREATE TABLE adress_items (
    ordner     INTEGER NOT NULL,
    schluessel TEXT NOT NULL,      -- normalisierte Straße + Hausnummer
    strasse    TEXT,
    hausnr     TEXT,
    qid        TEXT NOT NULL,
    label      TEXT,               -- aus dem Auszug, leer wenn dort unbekannt
    n_personen INTEGER,            -- so viele FactGrid-Personen wohnen dort
    PRIMARY KEY (ordner, schluessel)
);
CREATE INDEX IF NOT EXISTS idx_adress_str ON adress_items(ordner, strasse);
"""

QID_RE = re.compile(r'^Q\d+$')


def norm(s):
    """Vergleichsschlüssel: Klammerzusätze weg, Straße vereinheitlicht."""
    s = (s or '').lower().replace('ß', 'ss')
    s = re.sub(r'\(.*?\)', ' ', s)
    s = re.sub(r'^aschersleben,\s*', '', s.strip())
    s = re.sub(r'stra(ss|)e\b', 'str', s)
    s = re.sub(r'str\.?\b', 'str', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip(' ,.')


def pruefe_quelle(con, ordner, datei):
    """`build_register.py` hält fest, aus welcher CSV ein Ordner gebaut wurde.
    Weicht sie ab, sind Register und Adressen auseinandergelaufen."""
    r = con.execute('SELECT value FROM meta WHERE key=?',
                    (f'quelle_o{ordner}',)).fetchone()
    if not r:
        raise SystemExit(f'Ordner {ordner} fehlt in der Datenbank — erst '
                         'build/build_register.py laufen lassen.')
    if r[0] != datei:
        raise SystemExit(f'Ordner {ordner} wurde aus „{r[0]}" gebaut, hier steht '
                         f'„{datei}" — erst build/build_register.py laufen lassen.')


def run(db_path=DB_PATH):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    peru = sqlite3.connect(f'file:{find_peru_db()}?mode=ro', uri=True)
    con.executescript(SCHEMA)

    for ordner, datei, praefix in QUELLEN:
        pruefe_quelle(con, ordner, datei)
        zeilen = lies(os.path.join(ROOT, datei))

        # Je Adresse stimmen die Zeilen normalerweise überein. Wo nicht, gewinnt
        # die Mehrheit — ein Vertipper in einer von sechs Zeilen soll das Haus
        # nicht verlieren. Der Fall wird gemeldet, damit er nachgesehen wird.
        proAdr = collections.defaultdict(collections.Counter)
        ungueltig, ohne_qid = set(), 0
        for e in zeilen:
            q = e['adress_qid']
            if not q:
                ohne_qid += 1
                continue
            if not QID_RE.match(q):
                ungueltig.add(q)
                continue
            proAdr[split_address(e['adresse'])][q] += 1

        rows, uneinig, ohne_bewohner = [], [], 0
        for (strasse, hausnr), zaehler in sorted(proAdr.items()):
            qid, _ = zaehler.most_common(1)[0]
            if len(zaehler) > 1:
                uneinig.append((strasse, hausnr, dict(zaehler), qid))
            lab = peru.execute('SELECT label_de FROM labels WHERE qid=?',
                               (qid,)).fetchone()
            n = peru.execute("SELECT count(*) FROM person_qref WHERE kind='residence' "
                             'AND qid=?', (qid,)).fetchone()[0]
            if not n:
                ohne_bewohner += 1
            rows.append((ordner, norm(f'{strasse} {hausnr}'), strasse, hausnr,
                         qid, lab[0] if lab else None, n))

        con.executemany('INSERT OR REPLACE INTO adress_items VALUES (?,?,?,?,?,?,?)',
                        rows)
        con.commit()

        gesamt, personen, n_reg = con.execute(
            'SELECT count(DISTINCT e.strasse || " " || e.hausnr), '
            'count(a.qid), count(*) FROM entries e LEFT JOIN adress_items a '
            'ON a.ordner = e.ordner AND a.strasse = e.strasse '
            'AND a.hausnr = e.hausnr WHERE e.ordner = ?', (ordner,)).fetchone()
        print(f'Ordner {ordner}: {len(rows)} von {gesamt} Register-Adressen mit '
              f'FactGrid-Item ({personen} von {n_reg} Personen), Quelle {datei}')
        print(f'  dem Peru-Auszug unbekannt: {ohne_bewohner} — die tragen nichts '
              'zum Adress-Kriterium bei')
        if ohne_qid:
            print(f'  ohne Q-ID in der Quelle: {ohne_qid} Zeilen')
        if ungueltig:
            print(f'  keine Q-ID, übergangen: {sorted(ungueltig)[:5]}')
        for strasse, hausnr, z, gewinner in uneinig:
            print(f'  uneinig: {strasse} {hausnr} → {z}, genommen {gewinner}')

    # Dieselbe Adresse in zwei Ordnern mit verschiedenen Items: kein Fehler,
    # aber der Grund, warum `adress_items` am Ordner hängt. Sichtbar machen.
    doppelt = con.execute(
        'SELECT schluessel, count(DISTINCT qid) n, group_concat(ordner || "=" || qid) '
        'FROM adress_items GROUP BY schluessel HAVING n > 1').fetchall()
    for r in doppelt:
        print(f'  Hinweis: „{r[0]}" steht in mehreren Ordnern mit '
              f'verschiedenen Items ({r[2]})')
    con.close()


if __name__ == '__main__':
    run()
