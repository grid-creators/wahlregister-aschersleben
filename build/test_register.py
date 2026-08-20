"""Tests des Register-Aufbaus — reine Textprüfung, keine DB.

Geprüft wird, was beim Einlesen still schiefgehen könnte: das Jahrhundert der
zweistelligen Jahreszahlen, der Unterschied zwischen „leer" und „unlesbar",
die laufenden Nummern zweier Ordner und die Straßenschreibung.

    python3 build/test_register.py
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZWEISTELLIG = re.compile(r'^\d{1,2}\.\d{1,2}\.\d{2}$')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_register as B  # noqa: E402

fails = []


def check(name, cond, info=''):
    print(('  ok   ' if cond else '  FAIL ') + name + (f'  — {info}' if info and not cond else ''))
    if not cond:
        fails.append(name)


print('Geburtsdatum')
check('ISO bleibt ISO', B.iso_datum('1873-07-10') == '1873-07-10')
check('deutsches Datum wird ISO', B.iso_datum('25.10.76') == '1876-10-25',
      B.iso_datum('25.10.76'))
check('einstellige Tage und Monate', B.iso_datum('8.3.80') == '1880-03-08',
      B.iso_datum('8.3.80'))
# Wer 1933 wählen durfte, war mindestens 20 — bis '13 ist die Sache klar.
check("'13 ist 1913 (gerade noch wahlberechtigt)",
      B.iso_datum('17.2.13') == '1913-02-17', B.iso_datum('17.2.13'))
check("'41 ist 1841", B.iso_datum('1.1.41') == '1841-01-01', B.iso_datum('1.1.41'))
# Darüber hinaus entscheidet nicht das Wahlalter allein, sondern der Vergleich
# beider Lesarten. Ordner 6 führt unter Nr. 369 einen Kurt Hering, *25.5.14 —
# durchgestrichen, „noch nicht wahlfähig". Als 1814 wäre er 119 Jahre alt; zu
# jung zum Wählen kommt vor, über hundert nicht.
check("'14 ist 1914 — zu jung kommt vor, 119 Jahre nicht",
      B.iso_datum('25.5.14') == '1914-05-25', B.iso_datum('25.5.14'))
check("'30 ist 1830 — dort ist 18xx die plausible Lesart",
      B.iso_datum('1.1.30') == '1830-01-01', B.iso_datum('1.1.30'))
# Der Stichtag gehört zur Regel: Ordner 7 ist die Wählerliste von 1928.
check("'08 ist 1908, auch mit Stichtag 1928",
      B.iso_datum('1.1.08', 1928) == '1908-01-01', B.iso_datum('1.1.08', 1928))
check("'10 wäre 1928 zu jung — aber 1810 wäre 118",
      B.iso_datum('1.1.10', 1928) == '1910-01-01', B.iso_datum('1.1.10', 1928))
check('Stichtag je Ordner: 7 ist 1928, 6 nicht',
      (B.stichtag(7), B.stichtag(6), B.stichtag(2)) == (1928, 1933, 1933),
      (B.stichtag(7), B.stichtag(6)))
check('vierstelliges Jahr bleibt', B.iso_datum('12.3.1899') == '1899-03-12')
check('leer bleibt leer', B.iso_datum('') == '' and B.iso_datum(None) == '')
check('Unlesbares wird nicht geraten', B.iso_datum('?') == '')

print('Wahlvermerke')
check('Haken ist ein Vermerk', B.tick('✓') == 1)
check('Kreuz ist derselbe Vermerk', B.tick('X') == 1)
check('Eins ist derselbe Vermerk', B.tick('1') == 1)
check('leeres Feld heißt „nicht teilgenommen"', B.tick('') == 0)
check('Null heißt dasselbe wie leer', B.tick('0') == 0)
check('Unlesbares ist weder ja noch nein', B.tick('—') is None and B.tick('⍯') is None)
# Ordner 6 vermerkt bei 43 Einträgen „St.", von der Quelle selbst als
# Stimmschein aufgelöst. Er ist weder Teilnahme noch leeres Feld: die Person
# durfte anderswo wählen, ob sie es tat, sagt die Liste nicht.
check('Stimmschein ist ein eigener Wert', B.tick('St.') == B.TICK_STIMMSCHEIN)
check('… und zählt nicht als Teilnahme', B.tick('St.') != 1)
check('… und nicht als leeres Feld', B.tick('St.') != 0)

print('Straßen')
check('Abkürzung wird aufgelöst',
      B.split_address('Lindenstr. 54/56') == ('Lindenstraße', '54/56'),
      B.split_address('Lindenstr. 54/56'))
check('ausgeschriebene Form fällt mit der abgekürzten zusammen',
      B.split_address('Bürgerstraße 1')[0] == B.split_address('Bürgerstr. 1')[0]
      == 'Bürgerstraße')
check('Straße ohne Abkürzung bleibt',
      B.split_address('Im Busch 5') == ('Im Busch', '5'))
check('Hausnummer mit Buchstabe',
      B.split_address('Liebenw. Plan 13a') == ('Liebenwerder Plan', '13a'))
# Ordner 4 schreibt die Hausnummer ohne Leerzeichen an die Straße. Bliebe sie
# dort, wäre `hausnr` leer, jede Adresse ihre eigene „Straße" — und der Join
# nach `adress_items` fände nichts.
check('Hausnummer ohne Leerzeichen wird abgetrennt',
      B.split_address('Eislebenerstr.7a') == ('Eisleber Straße', '7a'),
      B.split_address('Eislebenerstr.7a'))
check('… auch ganz ohne Trennzeichen',
      B.split_address('Apothekergraben1') == ('Apothekergraben', '1'),
      B.split_address('Apothekergraben1'))
check('… auch hinter einem Bindestrich im Namen',
      B.split_address('Holtz-Str.4') == ('Holtzstraße', '4'),
      B.split_address('Holtz-Str.4'))
# Der Bindestrich zwischen zwei Zahlen trennt keine Hausnummer ab, er verbindet
# einen Bereich — „1-6" gehört als Ganzes in die Hausnummer.
check('Hausnummernbereich bleibt zusammen',
      B.split_address('Bestehornstr. 1-6') == ('Bestehornstraße', '1-6'),
      B.split_address('Bestehornstr. 1-6'))
# Dieselbe Straße, vier Schreibweisen — dass es dieselbe ist, sagt die Q-ID der
# Quelle (Nr. 1 ist in allen `Q497993`).
check('Schreibvarianten derselben Straße fallen zusammen',
      len({B.split_address(a)[0] for a in
           ('Eislebenerstr.1', 'Eisleberstr.1', 'Eilsleben.Str.1',
            'Eislebstr.18a', 'Eislebenerstr29')}) == 1,
      {B.split_address(a)[0] for a in
       ('Eislebenerstr.1', 'Eisleberstr.1', 'Eilsleben.Str.1',
        'Eislebstr.18a', 'Eislebenerstr29')})

# Ordner 5 hängt einen Hausnummernbereich mit Schrägstrich direkt an die
# Straße. Ohne diesen Fall bliebe „Ritterstr.9/10" ganz und gar Straßenname.
check('Bereich mit Schrägstrich ohne Leerzeichen',
      B.split_address('Ritterstr.9/10') == ('Ritterstraße', '9/10'),
      B.split_address('Ritterstr.9/10'))
# Ordner 6 und 7 überschneiden sich in fünf Straßen — sie müssen unter
# demselben Namen zusammenfallen, sonst fällt die Überschneidung nicht auf.
# Belegt ist sie jeweils über dieselbe Q-ID an denselben Häusern.
for a, b, name in (('U. d. Birken', 'Ueb.d.Brücken', 'Über den Brücken'),
                   ('Theod. Körnerstr.', 'Körnerstr.', 'Theodor-Körner-Straße'),
                   ('U. d. Burg', 'U.d.Burg', 'Unter der Burg'),
                   ('Auf d. Burg', 'A.d.Burg', 'Auf der Burg')):
    check(f'„{a}" und „{b}" sind {name}',
          B.norm_street(a) == B.norm_street(b) == name,
          (B.norm_street(a), B.norm_street(b)))
# Und die Gegenprobe: das Item der Mauerstraße heißt im Auszug „Eselsgasse".
# Das ist der heutige Name — aufgelöst wird die Abkürzung, umbenannt nichts.
check('Umbenennungen bleiben draußen',
      B.norm_street('Mauerstr.') == 'Mauerstraße', B.norm_street('Mauerstr.'))

print('Bemerkung und Blatt')
# In einigen Zeilen enthält die Bemerkung ein Komma und steht ohne
# Anführungszeichen — die zweite Hälfte landet dann in der Blattspalte.
check('halbierte Bemerkung wird wieder zusammengesetzt',
      B.blatt('Doppeleintrag: … wie lfd. Nr. 382', 'dort Ermsleberstr. 22')
      == ('Doppeleintrag: … wie lfd. Nr. 382, dort Ermsleberstr. 22', ''),
      B.blatt('Doppeleintrag: … wie lfd. Nr. 382', 'dort Ermsleberstr. 22'))
check('ein echtes Blatt bleibt ein Blatt',
      B.blatt('Nachtrag', 'IMG_8400_R') == ('Nachtrag', 'IMG_8400_R'))

print('Titel')
check('Fachzusatz gehört zum Titel',
      B.split_titel('Dr. ph. Hermann') == ('Dr. ph.', 'Hermann'),
      B.split_titel('Dr. ph. Hermann'))
check('kein Titel, kein Abtrennen',
      B.split_titel('Drewes') == ('', 'Drewes'))

print('Laufende Nummern')
check('Ordner 2 behält seine nackten Nummern', B.lfd_id('', '0001') == '0001')
check('Ordner 3 bekommt Präfix und Auffüllung', B.lfd_id('3-', '7') == '3-0007')
check('… und bleibt vierstellig', B.lfd_id('3-', '1730') == '3-1730')
check('Ordner 4 ebenso', B.lfd_id('4-', '7') == '4-0007')
check('die Ordner können sich nicht überschneiden',
      len({B.lfd_id('', '0007'), B.lfd_id('3-', '7'), B.lfd_id('4-', '7')}) == 3)

print('Alle Quellen einlesen')
FELDER = {'lfd', 'akte', 'familienname', 'vorname', 'geburtsname', 'adresse',
          'adress_qid', 'geburtsdatum', 'bemerkung', 'bild'}
for ordner, datei, praefix in B.QUELLEN:
    zeilen = B.lies(os.path.join(ROOT, datei))
    stichtag = B.stichtag(ordner)
    check(f'Ordner {ordner} liefert Zeilen', len(zeilen) > 1000, len(zeilen))
    check(f'Ordner {ordner}: einheitliche Felder',
          FELDER <= set(zeilen[0]), sorted(map(str, zeilen[0])))
    check(f'Ordner {ordner}: jede Zeile hat eine laufende Nummer',
          all(z['lfd'] for z in zeilen))
    check(f'Ordner {ordner}: laufende Nummern sind eindeutig',
          len({B.lfd_id(praefix, z['lfd']) for z in zeilen}) == len(zeilen))
    check(f'Ordner {ordner}: jede Zeile nennt ein Adressitem',
          all(z['adress_qid'].startswith('Q') for z in zeilen),
          [z['lfd'] for z in zeilen if not z['adress_qid'].startswith('Q')][:5])
    # Ein Eintrag ohne Geburtsdatum ist kein Lesefehler, wenn die Quelle es
    # sagt: Ordner 6 führt unter Nr. 378 einen Hans Joachim Seeligmann,
    # „vollständig durchgestrichen, ohne Geburtsdatum und Wohnung;
    # versehentlich eingetragen". Unlesbar wäre ein Datum, das dasteht und
    # nicht aufgeht — das darf es nicht geben.
    ohne = [z for z in zeilen if not B.iso_datum(z['geburtsdatum'], stichtag)]
    check(f'Ordner {ordner}: jedes vorhandene Geburtsdatum ist lesbar',
          all(not z['geburtsdatum'].strip() for z in ohne),
          [z['lfd'] for z in ohne if z['geburtsdatum'].strip()][:5])
    check(f'Ordner {ordner}: fehlende Daten sind in der Quelle vermerkt',
          all(z['bemerkung'] for z in ohne),
          [z['lfd'] for z in ohne if not z['bemerkung']][:5])
    # Wo das Jahrhundert **geraten** wird, muss die Regel aufgehen: niemand mit
    # nur zweistelliger Jahresangabe darf 1933 zu jung zum Wählen sein. Sonst
    # hat `iso_datum()` ein Jahr ins falsche Jahrhundert gelegt.
    #
    # Vierstellige Angaben stehen so in der Quelle und werden nicht
    # angezweifelt: Ordner 2 führt mit Nr. 1662 („Nachtrag") einen, der 1933
    # erst 18 war. Das ist ein Befund der Akte, kein Lesefehler.
    geraten = [(z, int(B.iso_datum(z['geburtsdatum'], stichtag)[:4]))
               for z in zeilen if ZWEISTELLIG.match(z['geburtsdatum'].strip())]
    if geraten:
        # Zu jung zum Wählen darf vorkommen — aber nur, wo die Quelle den
        # Eintrag selbst zurücknimmt. Ordner 6 hat zwei solche Fälle, beide
        # durchgestrichen („noch nicht wahlfähig", „versehentlich
        # eingetragen"). Ein zu junger Jahrgang ohne jede Bemerkung wäre
        # dagegen ein Jahr im falschen Jahrhundert.
        zu_jung = [z for z, j in geraten if stichtag - j < B.WAHLALTER]
        check(f'Ordner {ordner}: zu junge Jahrgänge nimmt die Quelle zurück',
              all(z['bemerkung'] for z in zu_jung),
              [z['lfd'] for z in zu_jung if not z['bemerkung']][:5])
        check(f'Ordner {ordner}: kein geratenes Geburtsjahr vor 1830',
              min(j for _, j in geraten) >= 1830, min(j for _, j in geraten))
    else:
        print(f'  --   Ordner {ordner} nennt die Jahre vierstellig, nichts zu raten')

print()
if fails:
    print(f'{len(fails)} Test(s) fehlgeschlagen: ' + ', '.join(fails))
    sys.exit(1)
print('alle Tests bestanden')
