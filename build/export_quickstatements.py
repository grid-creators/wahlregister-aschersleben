"""QuickStatements-Tabelle für mehrere Ordner auf einmal, mit zusammengeführten
Doubletten.

    python3 build/export_quickstatements.py 5,6,7 --zusammenfuehren > tabelle.txt

Die App exportiert immer **einen** Ordner (`?ordner=N`) und führt nichts
zusammen — sie warnt nur. Beides ist Absicht und bleibt so. Für den Erstimport
mehrerer Ordner reicht das nicht: wer 1928 wählen durfte, durfte es 1933
meistens auch, und dieselbe Person steht dann in Ordner 6 **und** 7. Ordnerweise
exportiert bekäme sie zwei Items, und die Doublette wäre über die Ordnergrenze
hinweg gar nicht sichtbar.

Ohne `--zusammenfuehren` verhält sich das Skript wie die App, nur über mehrere
Ordner: ein CREATE je Eintrag, dazu die Warnzeilen.
"""

import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'app'))

import match as M          # noqa: E402  — nur wegen find_peru_db()
import quickstatements as QS  # noqa: E402
from schema import QS_DEFAULTS  # noqa: E402

DB = os.path.join(ROOT, 'data', 'register.sqlite')


def eintraege(db, ordner):
    """Wie `_export_zeilen()` in server.py, nur für mehrere Ordner."""
    ph = ','.join('?' * len(ordner))
    return db.execute(
        'SELECT e.*, d.status, d.qid AS ziel_qid, a.qid AS adress_qid, '
        'p.qid AS p120_qid '
        'FROM entries e JOIN entscheidungen d ON d.lfd_id = e.lfd_id '
        'LEFT JOIN adress_items a ON a.ordner = e.ordner '
        '                        AND a.strasse = e.strasse '
        '                        AND a.hausnr = e.hausnr '
        'LEFT JOIN p120 p ON p.lfd_id = e.lfd_id '
        f'WHERE e.ordner IN ({ph}) ORDER BY e.rowid', list(ordner)).fetchall()


def doubletten(db):
    """Ungefiltert nach Ordner: das Gegenstück steht ja gerade woanders."""
    out = {}
    for r in db.execute('SELECT lfd_id, partner, score FROM doubletten'):
        out.setdefault(r['lfd_id'], []).append((r['partner'], r['score']))
    return out


def vorhandene_aussagen(db):
    """Wohnorte, die ein Ziel-Item laut Peru-Auszug schon hat."""
    qids = [r['qid'] for r in db.execute(
        "SELECT qid FROM entscheidungen WHERE status='zugeordnet' AND qid IS NOT NULL")]
    if not qids:
        return {}
    peru = sqlite3.connect(f'file:{M.find_peru_db()}?mode=ro', uri=True)
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


def main(argv):
    ordner = [int(x) for x in (argv[1] if len(argv) > 1 else '').split(',') if x.strip()]
    if not ordner:
        sys.exit(__doc__)
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    cfg = dict(QS_DEFAULTS)
    cfg.update(dict(db.execute('SELECT key, value FROM einstellungen')))
    zeilen = QS.bauen(eintraege(db, ordner), cfg, vorhandene_aussagen(db),
                      doubletten(db), zusammenfuehren='--zusammenfuehren' in argv)
    print('\n'.join(zeilen))


if __name__ == '__main__':
    main(sys.argv)
