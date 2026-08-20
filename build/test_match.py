"""Tests der Abgleich-Engine — kein Netz, aber die Peru-DB muss lesbar sein.

    python3 build/test_match.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'app'))

import match as M  # noqa: E402

fails = []


def check(name, cond, info=''):
    print(('  ok   ' if cond else '  FAIL ') + name + (f'  — {info}' if info and not cond else ''))
    if not cond:
        fails.append(name)


def e(fam, vor, datum, geburtsname=''):
    return {'familienname': fam, 'vorname': vor, 'vorname_norm': vor,
            'geburtsname': geburtsname, 'geburtsdatum': datum}


def qids(res):
    return [c['qid'] for c in res['candidates']]


def score(res, qid):
    return next((c['score'] for c in res['candidates'] if c['qid'] == qid), None)


print('Unscharfer Wortvergleich')
check('gleich → 1.0', M.aehnlich('mueller', 'mueller') == 1.0)
check('Tippfehler bleibt ähnlich', M.aehnlich('mikofsky', 'mikowsky') > 0.8,
      M.aehnlich('mikofsky', 'mikowsky'))
check('Initiale zählt bei gleichem Anfangsbuchstaben',
      M.aehnlich('m', 'margarete') == 0.85)
check('falsche Initiale zählt nicht', M.aehnlich('k', 'margarete') == 0.0)
check('Fremdes zählt nicht', M.aehnlich('meyer', 'schulze') == 0.0)
check('Reihenfolge egal',
      M.beste_paarung(['anna', 'marie'], ['marie', 'anna', 'elisabeth']) == 1.0)
check('Diakritika und ß gefaltet', M.fold('Gräf Straße') == 'graef strasse'
      or M.fold('Gräf Straße') == 'graf strasse', M.fold('Gräf Straße'))

print('Datumsvergleich')
d = M.datum_teile('1881-12-26')
check('tagesgleich → 1.0', M.datum_score(d, (1881, 12, 26)) == 1.0)
check('Monat gleich → 0.75', M.datum_score(d, (1881, 12, 2)) == 0.75)
check('nur Jahr gleich → 0.5', M.datum_score(d, (1881, 3, 2)) == 0.5)
check('ein Jahr daneben → 0.25', M.datum_score(d, (1882, 12, 26)) == 0.25)
check('weit weg → 0', M.datum_score(d, (1900, 12, 26)) == 0.0)
check('Item nur jahresgenau → Jahrestreffer',
      M.datum_score(d, M.item_datum('+1881-01-01T00:00:00Z', 9)) == 0.5)

print('Widerspruch im Geburtsdatum — der eine harte Ausschluss')
check('gleicher Tag ist kein Widerspruch',
      not M.datum_widerspruch(d, (1881, 12, 26)))
check('17 Tage sind kein Widerspruch',
      not M.datum_widerspruch(d, (1881, 12, 9)))
check('genau 31 Tage sind noch keiner',
      not M.datum_widerspruch(M.datum_teile('1881-12-26'), (1882, 1, 26)))
check('32 Tage sind einer',
      M.datum_widerspruch(M.datum_teile('1881-12-26'), (1882, 1, 27)))
check('ein Jahr daneben ist einer',
      M.datum_widerspruch(d, (1882, 12, 26)))
check('nur jahresgenaues Item ist keiner — fehlende Angabe, kein Widerspruch',
      not M.datum_widerspruch(d, M.item_datum('+1881-01-01T00:00:00Z', 9)))
check('nur monatsgenaues Item ist keiner',
      not M.datum_widerspruch(d, M.item_datum('+1881-03-01T00:00:00Z', 10)))
check('Eintrag ohne Geburtsdatum schließt nichts aus',
      not M.datum_widerspruch(M.datum_teile(''), (1881, 12, 26)))
check('unmögliches Datum wird übergangen, nicht beurteilt',
      not M.datum_widerspruch((1881, 2, 31), (1881, 12, 26)))

print('Abgleich gegen die Peru-DB')
m = M.Matcher()
ADR = [{'qid': 'Q497980', 'label': 'Breite Straße 22', 'exakt': True}]

r = m.match(e('Badt', 'Max', '1856-06-03'))
check('Max Badt findet Q878132', 'Q878132' in qids(r), qids(r))
check('… mit hohem Score', (score(r, 'Q878132') or 0) >= 85, score(r, 'Q878132'))

r = m.match(e('Schwabe', 'Selma', '1881-10-02', 'Mikofsky'))
check('Selma Schwabe trotz Schreibvariante des Geburtsnamens',
      'Q882696' in qids(r), qids(r))

r = m.match(e('Becker', 'Lotte', '1905-02-18', 'Bry'))
check('Lotte ↔ Lotti Becker (geb. Bry)', 'Q878147' in qids(r), qids(r))

r = m.match(e('Badt', 'B.', '1859-10-22', 'Sternberg'))
check('abgekürzter Vorname „B." findet Bertha Badt',
      'Q878133' in qids(r), qids(r))

# Ein abweichender Tag im selben Monat senkt den Score, schließt aber nicht
# aus: Q1603117 trägt den 6.10.1901, das Register den 23.10.1901 — 17 Tage,
# und genau dafür ist der Monat Spielraum da.
r = m.match(e('Baumann', 'Karl', '1901-10-23'))
s = score(r, 'Q1603117')
check('Karl Baumann mit abweichendem Tag bleibt Kandidat', s is not None, s)
check('… aber unter 85', s is None or s < 85, s)

# Weiter als einen Monat auseinander: derselbe Name, dasselbe Jahr, und
# trotzdem nicht dieselbe Person. Ohne den Ausschluss stünde Max Badt hier mit
# rund 68 Punkten (Name 50, gleiches Jahr 17,5) im Vorschlag.
r = m.match(e('Badt', 'Max', '1856-09-03'))
check('Max Badt mit drei Monaten Abstand wird ausgeschlossen',
      'Q878132' not in qids(r), qids(r))
check('… und wird als ausgeschlossen gezählt', r['ausgeschlossen'] >= 1,
      r['ausgeschlossen'])
check('mit dem richtigen Datum ist er wieder da',
      'Q878132' in qids(m.match(e('Badt', 'Max', '1856-06-03'))))

# Adresse als eigenständiges Signal
ohne = m.match(e('Müller', 'Anna', '1901-01-20'))
mit = m.match(e('Müller', 'Anna', '1901-01-20'), ADR)
check('Adresse hebt den Score', max([c['score'] for c in mit['candidates']] or [0])
      >= max([c['score'] for c in ohne['candidates']] or [0]))

check('leerer Name liefert nichts', m.match(e('', '', '1900-01-01'))['count'] == 0)

print('Teilscores')
r = m.match(e('Badt', 'Max', '1856-06-03'), ADR)
t = r['candidates'][0]['teilscores']
check('vier Kriterien ausgewiesen',
      set(t) == {'nachname', 'vorname', 'geburtsdatum', 'adresse'}, t)
check('Gewichte summieren auf 100', sum(M.GEWICHT.values()) == 100)

print()
if fails:
    print(f'{len(fails)} Test(s) fehlgeschlagen: ' + ', '.join(fails))
    sys.exit(1)
print('alle Tests bestanden')
