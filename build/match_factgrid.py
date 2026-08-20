"""Batch-Abgleich aller Register-Einträge gegen die Peru-DB.

Füllt `kandidaten` in data/register.sqlite neu; `entscheidungen` und
`einstellungen` bleiben unangetastet. Kein Netz.

    python3 build/match_factgrid.py [--min-score 40]
"""

import argparse
import datetime
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'app'))

import match as M  # noqa: E402
from schema import MATCH_SCHEMA  # noqa: E402

DB_PATH = os.path.join(ROOT, 'data', 'register.sqlite')


def adressen_map(con):
    """lfd_id → Adressitems: exaktes Haus zuerst, dann die übrigen Häuser
    derselben Straße (schwächeres Signal, hilft bei falscher Hausnummer).

    Der Ordner gehört in den Schlüssel: dieselbe Adresse steht in zwei Ordnern
    und meint dort verschiedene Häuser (Liebenwerder Plan 20)."""
    exakt = {}
    for r in con.execute('SELECT ordner, schluessel, strasse, hausnr, qid, label '
                         'FROM adress_items'):
        exakt[(r['ordner'], r['strasse'], r['hausnr'])] = dict(r)
    nach_strasse = {}
    for (ordner, strasse, _hn), a in exakt.items():
        nach_strasse.setdefault((ordner, strasse), []).append(a)

    out = {}
    for r in con.execute('SELECT ordner, lfd_id, strasse, hausnr FROM entries'):
        liste = []
        haus = exakt.get((r['ordner'], r['strasse'], r['hausnr']))
        if haus:
            liste.append({**haus, 'exakt': True})
        for a in nach_strasse.get((r['ordner'], r['strasse']), []):
            if not haus or a['qid'] != haus['qid']:
                liste.append({**a, 'exakt': False})
        out[r['lfd_id']] = liste
    return out


def run(db_path=DB_PATH, min_score=M.MIN_SCORE, verbose=True):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.executescript(MATCH_SCHEMA)

    matcher = M.Matcher()
    adressen = adressen_map(con)
    eintraege = con.execute(
        'SELECT lfd_id, familienname, vorname, vorname_norm, geburtsname, '
        'geburtsdatum, geschlecht FROM entries ORDER BY rowid').fetchall()

    rows, mit_kandidat, ausgeschlossen = [], 0, 0
    for e in eintraege:
        res = matcher.match(dict(e), adressen.get(e['lfd_id'], []),
                            min_score=min_score)
        ausgeschlossen += res.get('ausgeschlossen', 0)
        if res['candidates']:
            mit_kandidat += 1
        for rang, c in enumerate(res['candidates'], 1):
            rows.append((e['lfd_id'], rang, c['qid'], c['label'], c['description'],
                         c['birth_date'], c['death_year'], c['score'],
                         json.dumps(c['teilscores']), c['adresse_grund'],
                         json.dumps(c['hinweise'], ensure_ascii=False)))

    # Erst rechnen, dann in einem Zug schreiben. Die Datenbank läuft im
    # Rollback-Journal: würde hier oben gelöscht, hielte dieser Lauf eine
    # Schreibsperre über seine ganze Dauer, und die öffentliche App wäre
    # solange blockiert. So dauert das Schreibfenster Sekunden.
    con.execute('DELETE FROM kandidaten')
    con.executemany('INSERT OR REPLACE INTO kandidaten VALUES (' +
                    ','.join('?' * 11) + ')', rows)
    meta = {
        'lauf': datetime.datetime.now().isoformat(timespec='seconds'),
        'peru_db': matcher.path,
        'gewichte': json.dumps(M.GEWICHT),
        'min_score': str(min_score),
        'eintraege': str(len(eintraege)),
        'kandidaten': str(len(rows)),
        'mit_kandidat': str(mit_kandidat),
        'datum_ausgeschlossen': str(ausgeschlossen),
    }
    con.executemany('INSERT OR REPLACE INTO lauf_meta VALUES (?,?)',
                    list(meta.items()))
    con.commit()

    if verbose:
        print(f'{len(eintraege)} Einträge, {len(rows)} Kandidaten, '
              f'{mit_kandidat} Einträge mit mindestens einem Vorschlag')
        print(f'  wegen widersprüchlichem Geburtsdatum verworfen: {ausgeschlossen} '
              f'(mehr als {M.DATUM_TOLERANZ_TAGE} Tage Abstand, beide tagesgenau)')
        for lo, hi, lbl in ((90, 101, '90–100'), (75, 90, '75–89'),
                            (60, 75, '60–74'), (min_score, 60, f'{min_score}–59')):
            n = con.execute(
                'SELECT count(*) FROM (SELECT lfd_id, max(score) s FROM kandidaten '
                'GROUP BY lfd_id) WHERE s >= ? AND s < ?', (lo, hi)).fetchone()[0]
            print(f'  bester Score {lbl}: {n} Einträge')
    con.close()
    return len(rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-score', type=int, default=M.MIN_SCORE)
    a = ap.parse_args()
    run(min_score=a.min_score)
