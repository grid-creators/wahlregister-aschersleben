"""Eigener FactGrid-Auszug für den Abgleich — aus dem tagesaktuellen Dump.

Der Abgleich liest einen **lokalen** Auszug von FactGrid, nie die lebende
Instanz (`app/match.py`). Bis zum 17.8.2026 war das die Datei des
Nachbarprojekts, `/srv/apps/peru/build/persons.sqlite`. Die stammte aus einem
Rohdump vom 20. Juli und kannte deshalb **keine** der 5.006 Personen, die aus
den Ordnern 2 bis 4 inzwischen nach FactGrid importiert worden sind. Ein
Abgleich der Ordner 5, 6 und 7 gegen diesen Stand hätte tausende Menschen als
„nicht in FactGrid" ausgewiesen, die längst dort stehen — und beim Import
Dubletten erzeugt.

Warum eine eigene Datei und nicht die von peru:

`peru/build/build_index.py` legt sein Ziel **neu an** (`DST.unlink()`). In
`persons.sqlite` stehen aber nicht nur die Personen, sondern auch peru-eigene
Tabellen — `dup_pairs`, `dup_clusters`, `custom_rules`, die Verifikationsdaten.
Ein Neubau an Ort und Stelle risse sie mit. Deshalb baut dieses Skript nach
`data/persons.sqlite` **dieses** Projekts; peru bleibt unangetastet und behält
seinen Stand. Der Dienst findet die Datei über die Umgebungsvariable
`PERU_DB`, die `app/match.py` ohnehin vor dem festen Pfad abfragt.

Gebaut wird mit peru's `build_index.py` — importiert, nicht kopiert. Ein
zweites Exemplar desselben Parsers würde über kurz oder lang auseinanderlaufen,
und das Schema muss zu dem passen, was `app/match.py` erwartet.

Zwei Quellen, beide von `fg2marc21` bereitgestellt und tagesaktuell:

- `subset_P2_Q7.json` — der auf Personen (P2 = Q7) gefilterte Dump, dasselbe
  Format, das peru erzeugt hätte.
- `subset_referenced_labels.json` — die Beschriftungen der referenzierten
  Items. Damit wird `labels` **offline** gefüllt. peru holt sie mit
  `resolve_labels.py` einzeln über die FactGrid-API; das dauert Stunden und
  belastet den Server, und gebraucht wird hier nur, was ohnehin im Dump steht.
- `dump.json.gz` — der volle Dump, für alles, was in der Label-Datei fehlt.
  Sie deckt die **Namens**items fast vollständig ab (99,5 %), die
  **Wohnorte** aber nur zu einem knappen Drittel. Gerade die tragen die
  Straßennamen, die in `adress_items` und in der Liste stehen („Aschersleben,
  Breite Straße 22"). Der zweite Durchgang kostet ein paar Minuten und holt
  sie vollständig — immer noch offline und ohne einen einzigen API-Aufruf.

    python3 build/peru_auszug.py
"""

import gzip
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, '/srv/apps/peru/build')

QUELLE = Path('/srv/apps/fg2marc21/data/subset_P2_Q7.json')
LABELS = Path('/srv/apps/fg2marc21/data/subset_referenced_labels.json')
VOLLDUMP = Path('/srv/apps/fg2marc21/data/dump.json.gz')
ZIEL = ROOT / 'data' / 'persons.sqlite'

# Die Item-Kennung steht am Zeilenanfang. Sie zuerst mit einem billigen
# Ausdruck zu prüfen, spart das Auspacken der ganzen Zeile: gebraucht wird
# nur ein Bruchteil der zwei Millionen Items.
ID_AM_ANFANG = re.compile(r'^\{"type":"item","id":"(Q\d+)"')


def labels_fuellen(db_path, quelle=LABELS):
    """`labels` aus dem Dump füllen statt aus der API.

    Gefüllt wird nur, was auch gebraucht wird: die Q-IDs, die in
    `person_qref` vorkommen. Alles andere wäre Ballast — die Tabelle dient
    dem Nachschlagen von Namen und Straßen, nicht der Vollständigkeit."""
    con = sqlite3.connect(db_path)
    gebraucht = {q for (q,) in con.execute('SELECT DISTINCT qid FROM person_qref')}
    print(f'{len(gebraucht)} referenzierte Q-IDs, suche ihre Beschriftungen …',
          flush=True)

    rows, gesehen = [], 0
    with open(quelle, encoding='utf-8') as fh:
        for zeile in fh:
            zeile = zeile.strip().rstrip(',')
            if not zeile or zeile in ('[', ']'):
                continue
            gesehen += 1
            try:
                item = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            qid = item.get('id')
            if qid not in gebraucht:
                continue
            lab = (item.get('labels') or {}).get('de') or {}
            if lab.get('value'):
                rows.append((qid, lab['value']))

    con.executemany('INSERT OR REPLACE INTO labels VALUES (?,?)', rows)
    con.commit()
    fehlend = len(gebraucht) - len(rows)
    print(f'{len(rows)} Beschriftungen aus {gesehen} Items übernommen, '
          f'{fehlend} ohne deutsches Label', flush=True)
    con.close()


def labels_nachziehen(db_path, quelle=VOLLDUMP):
    """Was die Label-Datei nicht hergibt, aus dem vollen Dump holen.

    Betrifft vor allem die Adressitems: ohne sie stünde in der Liste eine
    nackte Q-ID statt „Aschersleben, Breite Straße 22". Auf den Score wirkt
    das nicht — dort wird die Q-ID verglichen, nicht ihr Name —, aber wer
    entscheidet, will lesen können, welches Haus gemeint ist."""
    con = sqlite3.connect(db_path)
    fehlend = {q for (q,) in con.execute(
        'SELECT DISTINCT q.qid FROM person_qref q '
        'LEFT JOIN labels l ON l.qid = q.qid WHERE l.qid IS NULL')}
    if not fehlend:
        print('keine Beschriftung fehlt', flush=True)
        con.close()
        return
    print(f'{len(fehlend)} Beschriftungen fehlen noch, hole sie aus {quelle.name} …',
          flush=True)

    rows, t0 = [], time.time()
    with gzip.open(quelle, 'rt', encoding='utf-8') as fh:
        for zeile in fh:
            m = ID_AM_ANFANG.match(zeile)
            if not m or m.group(1) not in fehlend:
                continue
            try:
                item = json.loads(zeile.rstrip().rstrip(','))
            except json.JSONDecodeError:
                continue
            lab = (item.get('labels') or {}).get('de') or {}
            if lab.get('value'):
                rows.append((m.group(1), lab['value']))

    con.executemany('INSERT OR REPLACE INTO labels VALUES (?,?)', rows)
    con.commit()
    print(f'{len(rows)} nachgetragen in {time.time() - t0:.0f}s', flush=True)
    con.close()


def bauen():
    for pfad in (QUELLE, LABELS, VOLLDUMP):
        if not pfad.exists():
            raise SystemExit(f'{pfad} fehlt — ohne den Dump geht es nicht.')

    import build_index as B      # peru's Parser, unverändert

    B.SRC, B.DST = QUELLE, ZIEL
    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    print(f'{QUELLE} → {ZIEL}', flush=True)
    t0 = time.time()
    B.main()
    labels_fuellen(ZIEL)
    labels_nachziehen(ZIEL)
    bericht(ZIEL)
    print(f'insgesamt {time.time() - t0:.0f}s', flush=True)
    print(f'\nDamit der Dienst ihn nimmt:  PERU_DB={ZIEL}')


def bericht(db_path):
    con = sqlite3.connect(db_path)
    for name, sql in (
            ('Personen', 'SELECT count(*) FROM persons'),
            ('Beschriftungen', 'SELECT count(*) FROM labels'),
            ('Referenzen', 'SELECT count(*) FROM person_qref'),
            ('Wohnorte', "SELECT count(*) FROM person_qref WHERE kind='residence'"),
            ('Wahlteilnehmer Aschersleben',
             "SELECT count(*) FROM persons "
             "WHERE description_de LIKE '%Wahlteilnehmer in Aschersleben%'")):
        print(f'  {name}: {con.execute(sql).fetchone()[0]}')
    con.close()


if __name__ == '__main__':
    bauen()
