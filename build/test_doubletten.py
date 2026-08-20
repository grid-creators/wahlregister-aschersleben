"""Tests des register-internen Abgleichs — reine Rechnung, keine DB.

Die Fälle sind echte Beispiele aus den Daten. Sie stehen hier, weil die Regel
in beide Richtungen scharf sein muss: Sie soll denselben Menschen in zwei
Ordnern erkennen, auch wenn er umgezogen ist oder der Schreiber sich vertan
hat — und sie darf aus Eheleuten, Zwillingen und Namensvettern keine Doublette
machen. Wer einen Fall löscht, verliert die Absicherung dafür.

    python3 build/test_doubletten.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import link_doubletten as D  # noqa: E402

fails = []


def check(name, cond, info=''):
    print(('  ok   ' if cond else '  FAIL ') + name
          + (f'  — {info}' if info and not cond else ''))
    if not cond:
        fails.append(name)


def e(nam, vor, dat, adr='', geb='', sex=None, ordner=6, lfd='x'):
    return {'lfd_id': lfd, 'ordner': ordner, 'familienname': nam,
            'vorname': vor, 'vorname_norm': vor, 'geburtsname': geb,
            'geburtsdatum': dat, 'adresse': adr, 'geschlecht': sex}


def score(a, b):
    return D.bewerte(a, b)[0]


print('Derselbe Mensch')
# Ordner 6 (12.11.1933) und Ordner 7 (20.5.1928) teilen sich fünf Straßen.
# Fritz Lehmann wohnt in beiden im Bäckerstieg 1.
check('gleicher Name, gleicher Tag, gleiches Haus',
      score(e('Lehmann', 'Fritz', '1898-06-13', 'Bäckerstieg 1', sex='m'),
            e('Lehmann', 'Fritz', '1898-06-13', 'Bäckerstieg 1', sex='m',
              ordner=7)) == 100)
# Zwischen 1928 und 1933 liegen fünf Jahre. Karl Thomas ist in dieser Zeit vom
# Bäckerstieg in die Feldstraße gezogen — die Adresse darf deshalb nicht
# mitzählen, sonst gingen gerade diese Fälle verloren.
check('Umzug zwischen den Wahlen ändert nichts',
      score(e('Thomas', 'Karl', '1897-03-11', 'Feldstraße 21a', sex='m'),
            e('Thomas', 'Karl', '1897-03-11', 'Bäckerstieg 4', sex='m',
              ordner=7)) == 100)
# Ein verlesener Tag bleibt derselbe Mensch: Otto Herrmann steht im Wassertor
# 14 zweimal, der zweite als handschriftlicher Nachtrag.
check('verlesener Tag (21.4. ↔ 6.4.) bleibt eine Person',
      score(e('Herrmann', 'Otto', '1912-04-21', 'Wassertor 14', sex='m'),
            e('Herrmann', 'Otto', '1912-04-06', 'Wassertor 14', sex='m',
              ordner=4)) >= D.MIN_SCORE)
check('… und zwei Tage Abstand erst recht',
      score(e('Kobert', 'Hermann', '1882-08-27', sex='m'),
            e('Kobert', 'Hermann', '1882-08-29', sex='m', ordner=4))
      >= D.MIN_SCORE)
# Ida Hofmann steht in Ordner 5 mit *10.9.1895 und in Ordner 7 mit *10.8.1895 —
# 31 Tage Abstand, und trotzdem eine Person: der Tag bleibt, nur der Monat
# rutscht. Sie ist der Grund, warum die Tagesgrenze nicht für den Monat gilt.
check('gleicher Tag im Nachbarmonat bleibt eine Person',
      score(e('Hofmann', 'Ida', '1895-09-10', 'Ritterstr.11', sex='w',
              ordner=5),
            e('Hofmann', 'Ida', '1895-08-10', 'Zollberg 58', sex='w',
              ordner=7)) >= D.MIN_SCORE)
# Verschriebene Jahreszahl bei gleichem Tag — so steht es auch in den
# Entscheidungen von Hand (Margarete Hirschfeld).
check('gleicher Tag im Nachbarjahr bleibt eine Person',
      score(e('Hirschfeld', 'Margarete', '1868-10-15', sex='w'),
            e('Hirschfeld', 'Margarete', '1867-10-15', sex='w', ordner=7))
      >= D.MIN_SCORE)
# Der Name darf ungenau sein, solange der Tag stimmt.
check('Tippfehler im Nachnamen bei gleichem Tag',
      score(e('Mencke', 'Willy', sex='m', dat='1896-08-13'),
            e('Meinecke', 'Willy', sex='m', dat='1896-08-13', ordner=3))
      >= D.MIN_SCORE)
# Eine Frau steht in einem Ordner unter dem Namen des Mannes, im anderen unter
# ihrem eigenen.
check('Geburtsname zählt als Nachname mit',
      score(e('Stezmann', 'Anna', '1899-04-18', geb='Schmidt', sex='w'),
            e('Schmidt', 'Anna', '1899-04-18', sex='w', ordner=7))
      >= D.MIN_SCORE)

print('Zwei Menschen')
# Louis und Louise Winter wohnen in der Vorderbreite 23 und tragen dasselbe
# Geburtsdatum. Der Vornamensvergleich sieht zwei Buchstaben Unterschied —
# das Geschlecht sieht mehr.
check('Eheleute mit gleichem Datum sind keine Doublette',
      score(e('Winter', 'Louis', '1861-01-23', 'Vorderbreite 23', sex='m'),
            e('Winter', 'Louise', '1861-01-23', 'Vorderbreite 23', sex='w')) == 0)
# Georg und Herbert Teuter, Friedrichstraße 34, beide *8.5.1906: Zwillinge.
# Ohne den Vornamen genügten Nachname und Geburtstag.
check('Zwillinge sind keine Doublette',
      score(e('Teuter', 'Georg', '1906-05-08', 'Friedrichstr. 34', sex='m'),
            e('Teuter', 'Herbert', '1906-05-08', 'Friedrichstr. 34',
              sex='m')) == 0)
# Zwei Karl Schulze, ein Jahr auseinander, aber an ganz anderen Tagen geboren.
check('Namensvetter im Nachbarjahr ist ein anderer Mensch',
      score(e('Schulze', 'Karl', '1897-08-04', sex='m'),
            e('Schulze', 'Karl', '1898-07-17', sex='m', ordner=3)) == 0)
# Weicht der Tag ab, muss der Name ohne Abstriche passen.
check('ähnlicher Name **und** abweichender Tag ergibt nichts',
      score(e('Köhler', 'Marta', '1908-03-22', sex='w'),
            e('Köthe', 'Herta', '1908-03-05', sex='w', ordner=7)) == 0)
check('fremder Name bei gleichem Tag ergibt nichts',
      score(e('Bahrmann', 'Walter', '1891-03-14', sex='m'),
            e('Bachmann', 'Elise', '1891-03-14', sex='w')) == 0)
# Zwei Selma Fischer in Ordner 7, Karlstr. 1 und Zollberg 31, auf zwei
# Blättern. 21 Tage Abstand — aber Tag *und* Monat weichen ab, und das ist
# keine verlesene Zahl mehr. Am 18.8.2026 von Hand als zwei Personen bestätigt.
check('Tag und Monat weichen ab: zwei Menschen',
      score(e('Fischer', 'Selma', '1884-10-21', 'Karlstr. 1', sex='w',
              ordner=7),
            e('Fischer', 'Selma', '1884-09-30', 'Zollberg 31', sex='w',
              ordner=7)) == 0)
# Derselbe Fall über zwei Ordner: Marta Grabe, geb. Stolze bzw. Wollschläger.
# Der abweichende Geburtsname taugt dafür nicht als Regel — fünf der sechs
# Paare mit abweichendem Geburtsnamen sind tagesgleich und damit echt.
check('… auch über Ordnergrenzen hinweg',
      score(e('Grabe', 'Marta', '1894-08-02', 'h.d.Turm 22', geb='Stolze',
              sex='w', ordner=2),
            e('Grabe', 'Marta', '1894-09-01', 'Fleischh.Str.5',
              geb='Wollschläger', sex='w', ordner=5)) == 0)

print('Vorsicht bei geschätzten Angaben')
# Das Geschlecht ist geschätzt. Ist es auf einer Seite unbekannt, darf es
# nicht ausschließen — sonst verlöre Ordner 7 Fälle, weil ihm der
# Geburtsname fehlt, aus dem es sonst folgt.
check('unbekanntes Geschlecht schließt nicht aus',
      score(e('Lehmann', 'Fritz', '1898-06-13', sex=None),
            e('Lehmann', 'Fritz', '1898-06-13', sex='m', ordner=7)) == 100)

print('Datumsvergleich')
check('tagesgleich zählt voll', D.datum_paar((1900, 5, 4), (1900, 5, 4)) == 1.0)
check('verrutschter Tag zählt gemindert',
      D.datum_paar((1912, 4, 21), (1912, 4, 6)) == D.VERSCHRIEBEN)
check('gleicher Tag im Nachbarmonat ebenso',
      D.datum_paar((1895, 9, 10), (1895, 8, 10)) == D.VERSCHRIEBEN)
check('gleicher Tag im Nachbarjahr ebenso',
      D.datum_paar((1868, 10, 15), (1867, 10, 15)) == D.VERSCHRIEBEN)
check('ein anderer Tag zählt gar nicht',
      D.datum_paar((1897, 8, 4), (1898, 7, 17)) == 0.0)
# Tag und Monat zugleich daneben — Selma Fischer und Marta Grabe.
check('Tag und Monat zugleich daneben zählt nicht',
      D.datum_paar((1884, 10, 21), (1884, 9, 30)) == 0.0)
check('… auch bei nur einem Tag Abstand im Nachbarmonat',
      D.datum_paar((1894, 8, 2), (1894, 9, 1)) == 0.0)
# Die Grenze selbst: 15 Tage sind Otto Herrmann, 21 sind Selma Fischer.
check('16 Tage im selben Monat zählen noch',
      D.datum_paar((1900, 5, 1), (1900, 5, 17)) == D.VERSCHRIEBEN)
check('17 Tage im selben Monat nicht mehr',
      D.datum_paar((1900, 5, 1), (1900, 5, 18)) == 0.0)
check('ohne Datum kein Urteil', D.datum_paar(None, (1900, 1, 1)) == 0.0)

print('Blöcke')
# Die Blockbildung darf keinen Fall verlieren, den die Bewertung fände.
rows = [e('Lehmann', 'Fritz', '1898-06-13', sex='m', lfd='6-0121'),
        e('Lemann', 'Fritz', '1898-06-13', sex='m', lfd='7-0001', ordner=7),
        e('Kobert', 'Hermann', '1882-08-27', sex='m', lfd='4-0575', ordner=4),
        e('Kobert', 'Hermann', '1882-08-29', sex='m', lfd='4-1115', ordner=4)]
gefunden = D.paare(rows)
check('anders geschriebener Name wird über das Datum gefunden',
      ('6-0121', '7-0001') in gefunden, sorted(gefunden))
check('abweichender Tag wird über Name und Jahr gefunden',
      ('4-0575', '4-1115') in gefunden, sorted(gefunden))
check('kein Paar zu sich selbst',
      not any(a == b for a, b in gefunden))

print('Geprüfte Fehlalarme')
# Gertrud Berger: die eine verheiratet (geb. Konietzny, im Haus ihres Mannes),
# die andere ledig im Haus ihrer Eltern. Die Rechnung sieht davon nichts — sie
# kennt nur Namen und Datum und kommt auf 86. Deshalb die Liste von Hand.
check('die Rechnung findet Gertrud Berger weiterhin',
      score(e('Berger', 'Gertrud', '1901-12-30', 'Steph. Kirchh. 5',
              geb='Konietzny', sex='w', ordner=2),
            e('Berger', 'Gertrud', '1901-12-20', 'Eislebenerstr.4', sex='w',
              ordner=4)) >= D.MIN_SCORE)
check('… und die Liste nimmt sie heraus',
      D.geprueft_verschieden('0920', '4-0159'))
check('… in beiden Richtungen',
      D.geprueft_verschieden('4-0159', '0920'))
check('ein anderes Paar bleibt unberührt',
      not D.geprueft_verschieden('1663', '3-1710'))
# Paul Meinhardt steht an der Naht zwischen Ordner 2 und 3 (Liebenwerder Plan
# 20 und 21) und ist tagesgleich — eine echte Doppelerfassung über die
# Bandgrenze. Er ist der Grund, warum die Ordner keinen Ausschluss hergeben.
check('Doppelerfassung über die Bandgrenze bleibt eine Person',
      score(e('Meinhardt', 'Paul', '1907-10-28', 'Liebenw. Plan 20', sex='m',
              ordner=2),
            e('Meinhardt', 'Paul', '1907-10-28', 'Liebenw. Plan 21', sex='m',
              ordner=3)) == 100)

print()
if fails:
    print(f'{len(fails)} Test(s) fehlgeschlagen: ' + ', '.join(fails))
    sys.exit(1)
print('alle Tests bestanden')
