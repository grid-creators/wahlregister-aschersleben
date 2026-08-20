"""Dieselbe Person in mehreren Ordnern finden.

Bis Ordner 5 war das Register eine Liste: jeder Mensch stand einmal darin, und
die einzige Frage war, ob FactGrid ihn schon kennt. Mit Ordner 6 und 7 ist das
vorbei. Die beiden gehören zu **anderen Wahlen** — Ordner 6 zur Reichstagswahl
und Volksabstimmung vom 12.11.1933, Ordner 7 zur Wählerliste von 1928 —, und
wer 1928 wählen durfte, durfte es 1933 meistens auch. Dieselben Straßen,
dieselben Häuser, dieselben Menschen.

Damit hat der Abgleich eine zweite Richtung bekommen. Ohne sie passiert
zweierlei, beides still:

- **Doppelte Items.** Zwei Einträge derselben Person, beide als „keine Person
  in FactGrid" entschieden, ergeben im Export zwei `CREATE` — zwei Items für
  einen Menschen. Wieder auseinanderzusortieren ist teurer als es zu
  verhindern.
- **Verschenkte Handarbeit.** Ordner 2 bis 4 sind vollständig entschieden.
  Steht dieselbe Person in Ordner 7, ist ihre Q-ID längst gefunden — sie muss
  nur noch übernommen werden, statt ein zweites Mal gesucht zu werden.

Gefunden wird mit derselben Unschärfe wie gegen FactGrid (`app/match.py`):
Namen über `aehnlich()`, Datum über `datum_score()`. Bewertet wird **nur** aus
Namen und Geburtsdatum — die Adresse bleibt bewusst draußen. Zwischen 1928 und
1933 liegen fünf Jahre, in denen Menschen umgezogen sind: Karl Thomas steht
1928 im Bäckerstieg 4 und 1933 in der Feldstraße 21a. Wer die Adresse
mitzählte, verlöre genau die Fälle, die er finden soll.

Entschieden wird hier nichts. Die Tabelle `doubletten` ist ein Hinweis, den
die Seite anzeigt; die Übernahme einer Q-ID bleibt ein Klick von Hand und
landet wie jede andere Entscheidung im Protokoll.

Läuft nach `build_register.py` und braucht weder Peru noch Netz.

    python3 build/link_doubletten.py
"""

import collections
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'app'))

from match import (aehnlich, beste_paarung, datum_teile,  # noqa: E402
                   datum_widerspruch, fold, tokens)

DB_PATH = os.path.join(ROOT, 'data', 'register.sqlite')

SCHEMA = """
DROP TABLE IF EXISTS doubletten;
CREATE TABLE doubletten (
    lfd_id  TEXT NOT NULL,
    partner TEXT NOT NULL,      -- der andere Registereintrag
    ordner  INTEGER NOT NULL,   -- sein Ordner
    score   INTEGER NOT NULL,
    grund   TEXT,               -- was übereinstimmt, in Worten
    PRIMARY KEY (lfd_id, partner)
);
CREATE INDEX IF NOT EXISTS idx_doubletten ON doubletten(lfd_id, score DESC);
"""

# Dieselben Verhältnisse wie im Abgleich gegen FactGrid, nur ohne die Adresse:
# ihre 15 Punkte gehen an den Nachnamen, der hier das tragende Merkmal ist.
GEWICHT = {'nachname': 40, 'vorname': 25, 'geburtsdatum': 35}

# Ab hier gilt ein Paar als Hinweis. 70 heißt: Name allein genügt nicht
# (40 + 25 = 65), es muss etwas vom Geburtsdatum dazukommen.
MIN_SCORE = 70

# Ab hier gilt der Hinweis als so sicher, dass die Seite ihn hervorhebt: ein
# tagesgleiches Geburtsdatum und ein passender Name.
SICHER = 90

# Paare, die die Rechnung findet und die von Hand als **zwei Menschen**
# geprüft sind. Sie stehen hier und nicht in einer Regel, weil das
# Unterscheidende in Zeilen steht, die die Rechnung gar nicht sieht: sie kennt
# Nachnamen, Vornamen und Geburtsdatum, nicht den Haushalt ringsum.
#
# Und weil jede Regel, die sie träfe, mehr kostet als sie bringt — nachgerechnet
# am 18.8.2026:
#
# - **Über die Tagesgrenze** ginge es nicht: Gertrud Berger liegt 10 Tage
#   auseinander, die belegte Doublette Otto Herrmann 15. Wer Berger verwirft,
#   verwirft Herrmann mit.
# - **Über die Ordner** auch nicht, so verlockend es aussieht: die Bände 2 bis 5
#   gehören zur selben Wahl und teilen sich fast keine Straße, ein Wähler steht
#   also in genau einem von ihnen. Aber genau an der einen Naht steht Paul
#   Meinhardt (`1663` ↔ `3-1710`, Liebenwerder Plan 20 und 21, tagesgleich) —
#   eine echte Doppelerfassung über die Bandgrenze. Eine Regel „nichts zwischen
#   Bänden derselben Wahl" würfe ihn weg.
#
# Nach `link_doubletten.py` bleibt die Liste stehen; `bericht()` sagt an, wenn
# ein Eintrag darin ins Leere greift, weil die Rechnung das Paar ohnehin nicht
# mehr findet. Dann gehört er hier heraus.
GEPRUEFT_VERSCHIEDEN = {
    # Gertrud Berger, \*30.12. ↔ \*20.12.1901. Die eine ist verheiratet — geb.
    # Konietzny, Steph. Kirchhof 5, in derselben Zeile wie Franz Berger
    # (`0919`, \*1904); die andere ledig und Tochter im Haus ihrer Eltern —
    # Eislebenerstraße 4, neben Udo Berger (\*1863) und Marie Berger geb.
    # Schröder (\*1864). Geprüft 18.8.2026.
    ('0920', '4-0159'),
}


def geprueft_verschieden(a, b):
    return tuple(sorted((a, b))) in GEPRUEFT_VERSCHIEDEN

# Was sich mit einer Verschreibung erklären lässt, ist noch so viel wert.
VERSCHRIEBEN = 0.6

# Wie weit der Tag verrutschen darf, wenn Monat und Jahr stehen bleiben. An den
# Daten abgelesen, nicht gesetzt: unter allen elf Paaren mit abweichendem Datum
# ist Otto Herrmann mit 15 Tagen die weiteste bestätigte Doublette und Selma
# Fischer mit 21 der engste bestätigte Fehlalarm.
MAX_TAGESVERSATZ = 16


def datum_paar(a, b):
    """Zwei Registerdaten vergleichen — anders als gegen FactGrid.

    Dort darf ein Datum jahres- oder monatsgenau sein; hier führen **beide**
    Seiten den Tag, abgeschrieben von derselben Verwaltung im Abstand weniger
    Jahre. Es zählt deshalb nur, was sich mit **einer** verlesenen Zahl
    erklären lässt, und die kann in jeder der drei Stellen sitzen:

    - **im Tag.** Otto Herrmann steht im Wassertor 14 zweimal, \\*21.4.1912 und
      \\*6.4.1912, der zweite als handschriftlicher Nachtrag; Hermann Kobert
      einmal \\*27.8. und einmal \\*29.8.1882.
    - **im Monat.** Ida Hofmann steht in Ordner 5 mit \\*10.9.1895 und in
      Ordner 7 mit \\*10.8.1895. Der Tag bleibt, also darf der Monat rutschen —
      die 31 Tage Abstand sind hier kein Argument.
    - **im Jahr.** Derselbe Tag im Nachbarjahr, so wie bei Margarete Hirschfeld
      in den Entscheidungen von Hand.

    Weichen dagegen **zwei** Stellen ab, ist es ein anderer Geburtstag. Bis zum
    18.8.2026 stand hier die volle Monatstoleranz aus `datum_widerspruch()`,
    und die hat genau daran zwei Paare zusammengespannt, die von Hand als zwei
    Personen bestätigt sind: Selma Fischer (\\*21.10. ↔ \\*30.9.1884) und Marta
    Grabe (\\*2.8. ↔ \\*1.9.1894). Gegen FactGrid darf die Grenze weit sein,
    weil sie dort *ausschließt* und ein weggeworfener Kandidat teuer ist; hier
    *erzeugt* sie Hinweise, und weit heißt dann falsch. Erst recht gilt das für
    einen anderen Tag im Nachbarjahr: Karl Schulze, \\*4.8.1897 in Ordner 2,
    und Karl Schulze, \\*17.7.1898 in Ordner 3, sind zwei."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a[1:] == b[1:] and abs(a[0] - b[0]) == 1:
        return VERSCHRIEBEN         # nur die Jahreszahl weicht ab
    if datum_widerspruch(a, b):
        return 0.0                  # weiter als ein Monat: ein anderer Tag
    if a[0] == b[0] and a[2] == b[2]:
        return VERSCHRIEBEN         # der Tag bleibt, nur der Monat rutscht
    if a[0] == b[0] and a[1] == b[1] and abs(a[2] - b[2]) <= MAX_TAGESVERSATZ:
        return VERSCHRIEBEN         # eine verrutschte Zahl im Tag
    return 0.0


def eintraege(con):
    return con.execute(
        'SELECT lfd_id, ordner, familienname, vorname_norm, vorname, '
        'geburtsname, geburtsdatum, adresse, geschlecht FROM entries '
        'WHERE geburtsdatum IS NOT NULL AND geburtsdatum <> ""').fetchall()


def bloecke(rows):
    """Wen es überhaupt lohnt zu vergleichen — alles andere wäre ein Vergleich
    von jedem mit jedem (48 Millionen Paare).

    Zwei Netze, weil zwei Fehlerarten vorkommen. Das **Datum** fängt Namen, die
    ganz anders geschrieben sind; der **Anfangsbuchstabe mit dem Geburtsjahr**
    fängt Daten, die um einen Tag oder ein Jahr abweichen. Was durch beide
    Netze fällt, wäre auch von Hand nicht wiederzuerkennen."""
    nach_datum = collections.defaultdict(list)
    nach_name = collections.defaultdict(list)
    for r in rows:
        nach_datum[r['geburtsdatum']].append(r)
        fam = fold(r['familienname'])
        jahr = int(r['geburtsdatum'][:4])
        for versatz in (-1, 0, 1):
            nach_name[(fam[:1], jahr + versatz)].append(r)
    return nach_datum, nach_name


def bewerte(a, b):
    """(Score, Grund) für zwei Registereinträge — oder (0, '').

    Zwei Ausschlüsse halten das Rauschen draußen, und beide haben denselben
    Grund: unter einem Dach wohnen Menschen, die einander ähnlich heißen.

    - **Verschiedenes Geschlecht.** Louis und Louise Winter stehen beide in der
      Vorderbreite 23 und tragen dasselbe Geburtsdatum — ein Ehepaar, keine
      Doublette. Der Vornamensvergleich sieht nur zwei Buchstaben Unterschied.
      Das Geschlecht ist zwar geschätzt, deshalb schließt es nur aus, wenn es
      auf **beiden** Seiten bekannt ist und sich widerspricht.
    - **Abweichendes Datum ohne makellosen Namen.** Stimmt der Tag, darf der
      Name ungenau sein („Willy Mencke" ↔ „Willy Meinecke"). Weicht der Tag ab,
      muss der Name dafür ohne Abstriche passen — sonst wird aus „Marta Köhler"
      und „Herta Köthe" eine Person."""
    if a['geschlecht'] and b['geschlecht'] and a['geschlecht'] != b['geschlecht']:
        return (0, '')

    nach = aehnlich(fold(a['familienname']), fold(b['familienname']))
    # Ein Geburtsname zählt als Nachname mit: dieselbe Frau steht in einem
    # Ordner unter dem Namen des Mannes und im anderen unter ihrem eigenen.
    for links, rechts in ((a['familienname'], b['geburtsname']),
                          (a['geburtsname'], b['familienname'])):
        if links and rechts:
            nach = max(nach, aehnlich(fold(links), fold(rechts)))
    if not nach:
        return (0, '')

    vor = beste_paarung(tokens(a['vorname_norm'] or a['vorname']),
                        tokens(b['vorname_norm'] or b['vorname']))
    # Der Vorname muss mitreden. Ohne ihn genügten Nachname und Geburtstag —
    # und genau das sind Zwillinge: Georg und Herbert Teuter stehen in der
    # Friedrichstraße 34, beide *8.5.1906, und sind zwei Menschen.
    if not vor:
        return (0, '')

    dat = datum_paar(datum_teile(a['geburtsdatum']),
                     datum_teile(b['geburtsdatum']))
    if not dat:
        return (0, '')      # ein anderer Geburtstag: zwei Menschen
    if dat < 1.0 and not (nach == 1.0 and vor == 1.0):
        return (0, '')      # weicht der Tag ab, muss der Name makellos sein

    score = round(GEWICHT['nachname'] * nach + GEWICHT['vorname'] * vor
                  + GEWICHT['geburtsdatum'] * dat)

    grund = []
    grund.append('Name gleich' if nach == 1 and vor == 1 else 'Name ähnlich')
    if a['geburtsdatum'] == b['geburtsdatum']:
        grund.append('Geburtsdatum gleich')
    else:
        grund.append(f"Geburtsdatum {a['geburtsdatum']} ↔ {b['geburtsdatum']}")
    if a['adresse'] and a['adresse'] == b['adresse']:
        grund.append('gleiche Adresse')
    return (score, ', '.join(grund))


def paare(rows):
    nach_datum, nach_name = bloecke(rows)
    gesehen, out = set(), {}
    for block in list(nach_datum.values()) + list(nach_name.values()):
        for i, a in enumerate(block):
            for b in block[i + 1:]:
                schluessel = (a['lfd_id'], b['lfd_id'])
                if schluessel in gesehen:
                    continue
                gesehen.add(schluessel)
                score, grund = bewerte(a, b)
                if score >= MIN_SCORE:
                    out[schluessel] = (score, grund, a, b)
    return out


def run(db_path=DB_PATH):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)

    rows = eintraege(con)
    gefunden = paare(rows)

    # Erst rechnen, dann die geprüften Fehlalarme herausnehmen — die Rechnung
    # bleibt so, wie sie ist, und `bericht()` sieht, welcher Eintrag der Liste
    # noch greift.
    gegriffen = {tuple(sorted(k)) for k in gefunden if geprueft_verschieden(*k)}
    gefunden = {k: v for k, v in gefunden.items()
                if not geprueft_verschieden(*k)}

    # Beide Richtungen schreiben. Ein Eintrag soll seine Gegenstücke finden,
    # ohne dass die Abfrage wissen muss, welcher von beiden zuerst kam.
    zeilen = []
    for (links, rechts), (score, grund, a, b) in gefunden.items():
        zeilen.append((links, rechts, b['ordner'], score, grund))
        zeilen.append((rechts, links, a['ordner'], score, grund))
    con.executemany('INSERT OR REPLACE INTO doubletten VALUES (?,?,?,?,?)',
                    zeilen)
    con.commit()
    bericht(con, gefunden, gegriffen)
    con.close()


def bericht(con, gefunden, gegriffen=frozenset()):
    betroffen = con.execute(
        'SELECT count(DISTINCT lfd_id) FROM doubletten').fetchone()[0]
    print(f'{len(gefunden)} Paare über {betroffen} Einträge')

    if gegriffen:
        print(f'  {len(gegriffen)} geprüfte Fehlalarme herausgenommen: '
              + ', '.join(f'{a} ↔ {b}' for a, b in sorted(gegriffen)))
    # Ein Eintrag, den die Rechnung ohnehin nicht mehr findet, soll nicht
    # stillschweigend liegen bleiben und den Eindruck erwecken, er halte etwas.
    for paar in sorted(GEPRUEFT_VERSCHIEDEN - gegriffen):
        print(f'  Hinweis: {paar[0]} ↔ {paar[1]} steht in '
              'GEPRUEFT_VERSCHIEDEN, wird aber gar nicht gefunden')

    ueber = collections.Counter()
    for (_, _), (score, _, a, b) in gefunden.items():
        ueber[tuple(sorted((a['ordner'], b['ordner'])))] += 1
    for (o1, o2), n in sorted(ueber.items()):
        wie = 'innerhalb von Ordner %d' % o1 if o1 == o2 else f'Ordner {o1} ↔ {o2}'
        print(f'  {wie}: {n}')

    sicher = sum(1 for v in gefunden.values() if v[0] >= SICHER)
    print(f'  davon {sicher} mit tagesgleichem Geburtsdatum und passendem Namen')

    # Der teure Fall: beide Seiten stehen auf „neue Person" und würden im
    # Export zwei Items für einen Menschen anlegen.
    doppelt = con.execute(
        'SELECT count(*) FROM doubletten d '
        'JOIN entscheidungen e1 ON e1.lfd_id = d.lfd_id '
        'JOIN entscheidungen e2 ON e2.lfd_id = d.partner '
        "WHERE e1.status='kein_treffer' AND e2.status='kein_treffer' "
        'AND d.lfd_id < d.partner').fetchone()[0]
    if doppelt:
        print(f'  ACHTUNG: {doppelt} Paare sind beidseits als neue Person '
              'entschieden — das ergäbe doppelte Items im Export')

    uebertragbar = con.execute(
        'SELECT count(DISTINCT d.lfd_id) FROM doubletten d '
        'JOIN entscheidungen e ON e.lfd_id = d.partner '
        "WHERE e.status='zugeordnet' AND e.qid IS NOT NULL "
        'AND d.lfd_id NOT IN (SELECT lfd_id FROM entscheidungen)').fetchone()[0]
    print(f'  {uebertragbar} noch offene Einträge haben ein Gegenstück, das '
          'bereits einem FactGrid-Item zugeordnet ist')


if __name__ == '__main__':
    run()
