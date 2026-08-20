"""Welcher Registereintrag steht schon als Item in FactGrid?

Der Abgleich rät über Namen und Daten. Die importierten Personen sagen es
dagegen selbst: jede trägt ihre Herkunft als `P51` (das Archivale des Ordners)
mit `P499` (die laufende Nummer in der Akte). Das ist keine Ähnlichkeit,
sondern eine Angabe — und damit die härteste Zuordnung, die es hier gibt.

Gebraucht wird sie aus einem unangenehmen Grund. Die Ordner 2 bis 4 sind
vollständig als **„keine Person in FactGrid"** entschieden; das stimmte, als
entschieden wurde. Inzwischen sind ihre 5.078 Items angelegt. Wer den Export
heute noch einmal zieht, legt jede dieser Personen ein zweites Mal an — die
Doubletten-Warnung greift dort nicht, denn die erkennt zwei *Registereinträge*
derselben Person, nicht einen Eintrag, dessen Item bereits existiert.

Dieses Skript **ändert nichts**. Es schreibt eine CSV, in der jeder Eintrag
neben seiner Entscheidung die Q-ID stehen hat, die FactGrid ihm selbst
zuschreibt, dazu den Vorschlag des Abgleichs zum Vergleich. Was daraus folgt,
entscheidet ein Mensch.

Die Spalte `befund` fasst jede Zeile in einem Wort zusammen:

- `bereits_angelegt` — Item existiert, Eintrag steht aber auf „neue Person".
  Ein erneuter Export erzeugt hier eine Dublette.
- `zugeordnet_gleich` / `zugeordnet_abweichend` — Eintrag ist zugeordnet; die
  Q-ID stimmt mit der des Items überein oder eben nicht.
- `nicht_in_factgrid` — kein Item trägt diese Ordner-Nummer.
- `offen` — noch nicht entschieden; hier ist die Q-ID ein Geschenk.

    python3 build/p51_bericht.py [ziel.csv]
"""

import csv
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'app'))

from schema import QS_DEFAULTS, quelle_key  # noqa: E402

DB_PATH = os.path.join(ROOT, 'data', 'register.sqlite')
SUBSET = '/srv/apps/fg2marc21/data/subset_P2_Q7.json'
ZIEL = os.path.join(ROOT, 'data', 'p51-zuordnung.csv')

SPALTEN = ('ordner', 'lfd_id', 'akte_nr', 'name', 'geburtsdatum', 'adresse',
           'status', 'entschieden_qid', 'qid_laut_factgrid', 'vorschlag_qid',
           'vorschlag_score', 'befund')


def archivalien(con):
    """{Q-ID des Archivales: Ordner} — aus den Einstellungen, nicht fest
    verdrahtet: welcher Ordner welche Primärquelle hat, steht dort."""
    cfg = dict(QS_DEFAULTS)
    cfg.update(dict(con.execute('SELECT key, value FROM einstellungen')))
    out = {}
    for (ordner,) in con.execute('SELECT DISTINCT ordner FROM entries ORDER BY 1'):
        q = cfg.get(quelle_key(ordner))
        if q:
            out[q] = ordner
    return out


def zuordnung(quellen, subset=SUBSET):
    """{(Ordner, Aktennummer): Q-ID} aus den P51/P499-Angaben des Dumps.

    Gelesen wird zeilenweise und nur dort ausgepackt, wo eine der Q-IDs
    überhaupt vorkommt — sonst wären es 674.000 JSON-Dokumente."""
    marker = [f'"{q}"' for q in quellen]
    out, mehrdeutig = {}, {}
    with open(subset, encoding='utf-8') as fh:
        for zeile in fh:
            if not any(m in zeile for m in marker):
                continue
            try:
                item = json.loads(zeile.strip().rstrip(','))
            except json.JSONDecodeError:
                continue
            for c in item.get('claims', {}).get('P51', []):
                v = c.get('mainsnak', {}).get('datavalue', {}).get('value')
                if not isinstance(v, dict) or v.get('id') not in quellen:
                    continue
                ordner = quellen[v['id']]
                for q in c.get('qualifiers', {}).get('P499', []):
                    roh = q.get('datavalue', {}).get('value')
                    nr = (roh.get('amount', '').lstrip('+')
                          if isinstance(roh, dict) else str(roh))
                    if not nr.isdigit():
                        continue
                    schluessel = (ordner, int(nr))
                    if schluessel in out and out[schluessel] != item['id']:
                        mehrdeutig.setdefault(schluessel, {out[schluessel]}).add(item['id'])
                    out[schluessel] = item['id']
    return out, mehrdeutig


def befund(status, entschieden_qid, wahr):
    if not wahr:
        return 'nicht_in_factgrid'
    if status is None:
        return 'offen'
    if status == 'kein_treffer':
        return 'bereits_angelegt'
    return 'zugeordnet_gleich' if entschieden_qid == wahr else 'zugeordnet_abweichend'


def run(ziel=ZIEL, db_path=DB_PATH):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    quellen = archivalien(con)
    print(f'Archivalien: {", ".join(f"{q}=Ordner {o}" for q, o in quellen.items())}')
    wahrheit, mehrdeutig = zuordnung(quellen)
    print(f'{len(wahrheit)} Einträge tragen in FactGrid ihre Ordner-Nummer')
    for schluessel, qs in mehrdeutig.items():
        print(f'  mehrdeutig: Ordner {schluessel[0]} Nr. {schluessel[1]} → {sorted(qs)}')

    rows = con.execute("""
        SELECT e.ordner, e.lfd_id, e.akte_nr, e.name_voll, e.geburtsdatum,
               e.adresse, d.status, d.qid AS entschieden_qid,
               (SELECT qid FROM kandidaten k WHERE k.lfd_id = e.lfd_id
                 ORDER BY rang LIMIT 1) AS vorschlag_qid,
               (SELECT max(score) FROM kandidaten k WHERE k.lfd_id = e.lfd_id)
                 AS vorschlag_score
        FROM entries e LEFT JOIN entscheidungen d ON d.lfd_id = e.lfd_id
        ORDER BY e.rowid""").fetchall()

    zaehler = {}
    with open(ziel, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(SPALTEN)
        for r in rows:
            wahr = wahrheit.get((r['ordner'], r['akte_nr']))
            b = befund(r['status'], r['entschieden_qid'], wahr)
            zaehler[b] = zaehler.get(b, 0) + 1
            w.writerow([r['ordner'], r['lfd_id'], r['akte_nr'], r['name_voll'],
                        r['geburtsdatum'], r['adresse'], r['status'] or 'offen',
                        r['entschieden_qid'] or '', wahr or '',
                        r['vorschlag_qid'] or '', r['vorschlag_score'] or '', b])

    print(f'\n{ziel}')
    for b in sorted(zaehler, key=lambda k: -zaehler[k]):
        print(f'  {b:24} {zaehler[b]:>5}')
    if zaehler.get('bereits_angelegt'):
        print(f"\nACHTUNG: {zaehler['bereits_angelegt']} Einträge stehen auf "
              '„keine Person in FactGrid", obwohl ihr Item existiert. Ein '
              'Export dieser Ordner legt sie ein zweites Mal an.')
    con.close()


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else ZIEL)
