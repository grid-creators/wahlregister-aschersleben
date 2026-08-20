"""Tests des QuickStatements-Generators — reine Textprüfung, keine DB.

    python3 build/test_quickstatements.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'app'))

import quickstatements as QS  # noqa: E402
from schema import QS_DEFAULTS  # noqa: E402

fails = []


def check(name, cond, info=''):
    print(('  ok   ' if cond else '  FAIL ') + name + (f'  — {info}' if info and not cond else ''))
    if not cond:
        fails.append(name)


def eintrag(**kw):
    basis = {'ordner': 2, 'lfd_id': '0042', 'akte_nr': 42, 'familienname': 'Müller',
             'vorname': 'M.', 'vorname_norm': 'Margarete', 'titel': '',
             'geburtsname': 'Hahn',
             'geburtsdatum': '1881-12-26', 'geschlecht': 'w', 'bemerkung': '',
             'adresse': 'Breitestr. 22', 'adress_qid': 'Q497980',
             'sp4_ok': 1, 'sp5_ok': 1, 'sp8_ok': 1,
             'status': 'kein_treffer', 'ziel_qid': None}
    basis.update(kw)
    return basis


CFG = dict(QS_DEFAULTS)

print('Neues Item')
z = QS.bauen([eintrag()], CFG)
txt = '\n'.join(z)
check('CREATE vorhanden', 'CREATE' in z)
check('Label mit aufgelöstem Vornamen und Geburtsname',
      'LAST\tLde\t"Margarete Müller (geb. Hahn)"' in z, [l for l in z if 'Lde' in l])
check('Geburtsname auch als Alias', 'LAST\tAde\t"Hahn"' in z)
check('englisches Label daneben, „geb." wird „nee"',
      'LAST\tLen\t"Margarete Müller (nee Hahn)"' in z, [l for l in z if 'Len' in l])
check('Beschreibung nach Muster Q1257714',
      'LAST\tDde\t"*26.12.1881; 1933 Wahlteilnehmer in Aschersleben"' in z,
      [l for l in z if 'Dde' in l])
check('P2 = Q7', 'LAST\tP2\tQ7' in z)
check('Geburtsdatum tagesgenau',
      'LAST\tP77\t+1881-12-26T00:00:00Z/11' in z, [l for l in z if 'P77' in l])
check('Geschlecht weiblich', 'LAST\tP154\tQ17' in z)
check('Ort mit Jahresqualifikator',
      'LAST\tP83\tQ80706\tP106\t+1933-00-00T00:00:00Z/9' in z, [l for l in z if 'P83' in l])
check('Adress-Item als P208',
      'LAST\tP208\tQ497980\tP106\t+1933-00-00T00:00:00Z/9' in z, [l for l in z if 'P208' in l])
check('Primärquelle des Ordners mit Position in Folge',
      'LAST\tP51\tQ2080842\tP499\t42' in z, [l for l in z if 'P51' in l])
check('Forschungsprojekt', 'LAST\tP131\tQ497317' in z)

print('Wahlspalten — drei Spalten, drei Wahlen')
# Die Rolle (P277) hängt an jeder einzelnen Teilnahme, anders als die Bemerkung
# der Akte, die dem Registereintrag gilt und nur einmal geschrieben wird.
ROLLE = '\tP277\tQ1207476'
check('alle drei Wahlen bei drei Vermerken, je mit Rolle',
      ['LAST\tP119\tQ1207285' + ROLLE, 'LAST\tP119\tQ1214187' + ROLLE,
       'LAST\tP119\tQ1214186' + ROLLE]
      == [l for l in z if '\tP119\t' in l], [l for l in z if 'P119' in l])
z_ohne = QS.bauen([eintrag()], {**CFG, 'qs_rolle': ''})
check('Rolle abschaltbar', not any('P277' in l for l in z_ohne)
      and [l for l in z_ohne if '\tP119\t' in l]
      == ['LAST\tP119\tQ1207285', 'LAST\tP119\tQ1214187', 'LAST\tP119\tQ1214186'],
      [l for l in z_ohne if 'P119' in l])

# Das Kreuz ist ein Vermerk wie der Haken — beide sind in der DB `1`. Nur das
# leere Feld (`0`) heißt „nicht teilgenommen", Unlesbares (None) sagt nichts.
z = QS.bauen([eintrag(sp8_ok=0)], CFG)
check('leere Spalte erzeugt keine Aussage',
      [l for l in z if '\tP119\t' in l]
      == ['LAST\tP119\tQ1207285' + ROLLE, 'LAST\tP119\tQ1214187' + ROLLE],
      [l for l in z if 'P119' in l])
# Geprüft werden die Datenzeilen, nicht der Kopf: der nennt die Wahlen des
# Ordners und enthält das Wort P119 immer.
z = QS.bauen([eintrag(sp4_ok=0, sp5_ok=0, sp8_ok=0)], CFG)
check('ohne jeden Vermerk gar kein P119', not any('\tP119\t' in l for l in z))
z = QS.bauen([eintrag(sp4_ok=None, sp5_ok=None, sp8_ok=None)], CFG)
check('unlesbarer Vermerk erzeugt keine Aussage',
      not any('\tP119\t' in l for l in z))
z = QS.bauen([eintrag(sp4_ok=0, sp5_ok=1, sp8_ok=0)], CFG)
check('nur die markierte Spalte',
      [l for l in z if '\tP119\t' in l] == ['LAST\tP119\tQ1214187' + ROLLE],
      [l for l in z if 'P119' in l])

print('Bemerkungen')
z = QS.bauen([eintrag(bemerkung='Am 12.3.33 noch nicht 6 Monate Wohnsitz')], CFG)
check('Bemerkung als Notiz des Originals — nur an der ersten Aussage',
      [l for l in z if '\tP119\t' in l]
      == ['LAST\tP119\tQ1207285' + ROLLE
          + '\tP520\t"Am 12.3.33 noch nicht 6 Monate Wohnsitz"',
          'LAST\tP119\tQ1214187' + ROLLE, 'LAST\tP119\tQ1214186' + ROLLE],
      [l for l in z if 'P119' in l])
z = QS.bauen([eintrag(sp4_ok=0, bemerkung='Abgd. M')], CFG)
check('Bemerkung wandert an die erste tatsächlich erzeugte Aussage',
      'LAST\tP119\tQ1214187' + ROLLE + '\tP520\t"Abgd. M"' in z,
      [l for l in z if 'P119' in l])
z = QS.bauen([eintrag(sp4_ok=0, sp5_ok=0, sp8_ok=0, bemerkung='Abgd. M')], CFG)
check('ohne P119 entfällt die Bemerkung', not any('P520' in l for l in z))
z = QS.bauen([eintrag(bemerkung='(Keine Stimmabgabekreuze)')], CFG)
check('Editorische Anmerkung wird nicht als Quellennotiz exportiert',
      not any('P520' in l for l in z), [l for l in z if 'P119' in l])
z = QS.bauen([eintrag(bemerkung='Er sagte "nein"')], CFG)
check('Anführungszeichen maskiert', r'\"nein\"' in '\n'.join(z), [l for l in z if 'P520' in l])

print('Englisches Label')
# Der Name ist keine Übersetzungssache: beide Labels sind gleich, bis auf den
# Klammerzusatz zum Geburtsnamen.
z = QS.bauen([eintrag(geburtsname='')], CFG)
check('ohne Geburtsnamen sind beide Labels gleich',
      'LAST\tLde\t"Margarete Müller"' in z and 'LAST\tLen\t"Margarete Müller"' in z,
      [l for l in z if '\tL' in l])
z = QS.bauen([eintrag()], {**CFG, 'qs_label_en': 'nein'})
check('englisches Label abschaltbar',
      not any('\tLen\t' in l for l in z) and any('\tLde\t' in l for l in z))
# An einem bestehenden Item würde `Len` ein vorhandenes englisches Label
# überschreiben — und ob es eins hat, führt der Peru-Auszug nicht mit.
z = QS.bauen([eintrag(status='zugeordnet', ziel_qid='Q878132')], CFG)
check('kein Label an bestehenden Items',
      not any('\tLen\t' in l or '\tLde\t' in l for l in z), z)

print('Akademischer Titel')
z = QS.bauen([eintrag(vorname='Dr. Kurt', vorname_norm='Kurt', titel='Dr.',
                      familienname='Fürste', geburtsname='', geschlecht='m')], CFG)
check('Titel steht nicht im Label', 'LAST\tLde\t"Kurt Fürste"' in z,
      [l for l in z if 'Lde' in l])
check('Titel als P170', 'LAST\tP170\tQ22218' in z, [l for l in z if 'P170' in l])
z = QS.bauen([eintrag(vorname='Dr.', vorname_norm='', titel='Dr.',
                      familienname='Fürste', geburtsname='')], CFG)
check('ohne Vornamen fällt das Label nicht auf den Titel zurück',
      'LAST\tLde\t"Fürste"' in z, [l for l in z if 'Lde' in l])
z = QS.bauen([eintrag(titel='Dr.')], {**CFG, 'qs_titel': ''})
check('P170 abschaltbar', not any('P170' in l for l in z))
z = QS.bauen([eintrag(titel='Dr.', status='zugeordnet', ziel_qid='Q878132')], CFG)
check('kein P170 an bestehenden Items', not any('P170' in l for l in z))

print('Bestehendes Item ergänzen')
e = eintrag(status='zugeordnet', ziel_qid='Q878132')
z = QS.bauen([e], CFG)
check('Zeilen laufen auf die Q-ID', all(l.startswith(('Q878132', '#', '')) for l in z))
check('kein CREATE', 'CREATE' not in z)
check('keine Neuanlage-Aussagen (P2/P77/Lde)',
      not any(('\tP2\t' in l or '\tP77\t' in l or 'Lde' in l) for l in z), z)
check('Adresse wird ergänzt', 'Q878132\tP208\tQ497980\tP106\t+1933-00-00T00:00:00Z/9' in z)
check('Quelle wird ergänzt', 'Q878132\tP51\tQ2080842\tP499\t42' in z)

z = QS.bauen([e], CFG, {'Q878132': {'Q497980', 'Q80706', 'Q497317'}})
check('vorhandene Aussagen werden nicht doppelt angelegt',
      not any(p in '\n'.join(z) for p in ('\tP208\t', '\tP83\t', '\tP131\t')), z)

print('Einstellungen')
z = QS.bauen([eintrag()], {**CFG, 'qs_geschlecht': 'nein', 'qs_beschreibung': 'nein'})
check('Geschlecht abschaltbar', not any('P154' in l for l in z))
check('Beschreibung abschaltbar', not any('Dde' in l for l in z))
z = QS.bauen([eintrag(adress_qid=None)], CFG)
check('ohne Adress-Item kein P208', not any('P208' in l for l in z))

print('Ordner')
# Jeder Ordner des Bestands ist ein eigenes Archivale mit eigenem Item. Der
# Export nimmt das Item des Ordners, in dem der Eintrag steht.
z = QS.bauen([eintrag(ordner=3, lfd_id='3-0042')], CFG)
check('Ordner 3 trägt seine eigene Primärquelle',
      'LAST\tP51\tQ2084011\tP499\t42' in z, [l for l in z if 'P51' in l])
z = QS.bauen([eintrag(ordner=4, lfd_id='4-0042')], CFG)
check('Ordner 4 trägt seine eigene Primärquelle',
      'LAST\tP51\tQ2086743\tP499\t42' in z, [l for l in z if 'P51' in l])
z = QS.bauen([eintrag(), eintrag(ordner=3, lfd_id='3-0042'),
              eintrag(ordner=4, lfd_id='4-0042')], CFG)
check('drei Ordner, drei Primärquellen',
      [l.split('\t')[2] for l in z if '\tP51\t' in l]
      == ['Q2080842', 'Q2084011', 'Q2086743'], [l for l in z if 'P51' in l])
check('der Kopf nennt jeden Ordner',
      all(any(f'Ordner {o}' in l and q in l for l in z)
          for o, q in ((2, 'Q2080842'), (3, 'Q2084011'), (4, 'Q2086743'))), z[:6])
# Ein Ordner ohne hinterlegtes Item bekommt kein P51 — ein falscher Ordner
# wäre schlimmer als gar keine Angabe.
z = QS.bauen([eintrag(ordner=9)], CFG)
check('unbekannter Ordner erzeugt kein P51', not any('\tP51\t' in l for l in z),
      [l for l in z if 'P51' in l])
check('… der Rest wird trotzdem exportiert', any('\tP2\tQ7' in l for l in z))

print('Ordner mit anderer Wahl')
# Ordner 6 und 7 gehören nicht zur Wahl vom 5.3.1933. Sie haben eine einzige
# Stimmabgabe-Spalte, und in Ordner 7 belegt sie zwei Wahlen — Reichstag und
# Preußischer Landtag wurden am 20.5.1928 am selben Tag gewählt.
def stimme(**kw):
    e = eintrag(**kw)
    for f in ('sp4_ok', 'sp5_ok', 'sp8_ok'):
        e[f] = None
    e.setdefault('spst_ok', 1)
    return e


z = QS.bauen([stimme(ordner=6, lfd_id='6-0042')], CFG)
check('Ordner 6: eine Wahl aus einer Spalte',
      [l for l in z if '\tP119\t' in l]
      == ['LAST\tP119\tQ1207474\tP277\tQ1207476'], [l for l in z if 'P119' in l])
check('Ordner 6 rechnet weiter mit 1933',
      any('+1933-00-00T00:00:00Z/9' in l for l in z if '\tP83\t' in l))
check('Ordner 6 trägt sein eigenes Archivale',
      'LAST\tP51\tQ2088500\tP499\t42' in z, [l for l in z if 'P51' in l])

z = QS.bauen([stimme(ordner=7, lfd_id='7-0042')], CFG)
check('Ordner 7: ein Vermerk, zwei Wahlen desselben Tages',
      [l.split('\t')[2] for l in z if '\tP119\t' in l] == ['Q2088496', 'Q2088498'],
      [l for l in z if 'P119' in l])
check('Ordner 7 datiert auf 1928, nicht 1933',
      'LAST\tP83\tQ80706\tP106\t+1928-00-00T00:00:00Z/9' in z,
      [l for l in z if '\tP83\t' in l])
check('… auch die Adresse',
      'LAST\tP208\tQ497980\tP106\t+1928-00-00T00:00:00Z/9' in z,
      [l for l in z if '\tP208\t' in l])
check('… und die Beschreibung',
      'LAST\tDde\t"*26.12.1881; 1928 Wahlteilnehmer in Aschersleben"' in z,
      [l for l in z if 'Dde' in l])
check('der Kopf nennt beide Jahre',
      'Aschersleben 1928' in z[0], z[0])
# Der Stimmschein aus Ordner 6 ist weder Teilnahme noch leeres Feld.
z = QS.bauen([stimme(ordner=6, lfd_id='6-0039', spst_ok=2)], CFG)
check('Stimmschein erzeugt keine Teilnahme',
      not any('\tP119\t' in l for l in z), [l for l in z if 'P119' in l])
check('… der Eintrag entsteht trotzdem', any('\tP2\tQ7' in l for l in z))
# Eine einzelne Wahl lässt sich abschalten, ohne die andere zu verlieren.
z = QS.bauen([stimme(ordner=7, lfd_id='7-0042')],
             dict(CFG, qs_wahl_o7_landtag=''))
check('eine der beiden Wahlen abschaltbar',
      [l.split('\t')[2] for l in z if '\tP119\t' in l] == ['Q2088496'],
      [l for l in z if 'P119' in l])

print('Doppelte Neuanlagen')
# Zwei Registereinträge derselben Person, beide als „neue Person" entschieden,
# ergäben zwei Items für einen Menschen. Verhindert wird nichts — aber der
# Export sagt es, und zwar an der Zeile, um die es geht.
paar = [stimme(ordner=6, lfd_id='6-0121'), stimme(ordner=7, lfd_id='7-0001')]
doub = {'6-0121': [('7-0001', 100)], '7-0001': [('6-0121', 100)]}
z = QS.bauen(paar, CFG, {}, doub)
check('beide Seiten werden gewarnt',
      len([l for l in z if l.startswith('# ACHTUNG 6-0121')
           or l.startswith('# ACHTUNG 7-0001')]) == 2,
      [l for l in z if 'ACHTUNG' in l])
check('die Warnung steht vor dem CREATE',
      z.index('# ACHTUNG 6-0121 Margarete Müller (geb. Hahn): derselbe Mensch '
              'steht als 7-0001 in diesem Export und würde ein zweites Item '
              'bekommen (Übereinstimmung 100)') + 1 == z.index('CREATE'),
      [l for l in z if 'ACHTUNG' in l or l == 'CREATE'][:3])
check('der Kopf zählt sie', any('ACHTUNG: 2' in l for l in z[:8]), z[:8])
check('beide Einträge bleiben im Export',
      len([l for l in z if l == 'CREATE']) == 2)
# Ist eine Seite bereits zugeordnet, entsteht kein zweites Item — also auch
# keine Warnung.
z = QS.bauen([paar[0], dict(paar[1], status='zugeordnet', ziel_qid='Q1')],
             CFG, {}, doub)
check('keine Warnung, wenn eine Seite zugeordnet ist',
      not any('ACHTUNG' in l for l in z), [l for l in z if 'ACHTUNG' in l])
# Und ohne Doubletten-Tabelle bleibt alles beim Alten.
check('ohne Doublettenwissen keine Warnung',
      not any('ACHTUNG' in l for l in QS.bauen(paar, CFG)))

print('Doubletten zusammenführen')
# Die Fälle sind echt: Ordner 6 und 7 führen dieselben Menschen, weil wer 1928
# wählen durfte, es 1933 meistens auch durfte. Ordner 7 führt dabei **keine**
# Geburtsnamen — deshalb gewinnt beim Label in aller Regel die andere Seite.
paar6 = stimme(ordner=6, lfd_id='6-0121', akte_nr=121, adress_qid='Q6')
paar7 = stimme(ordner=7, lfd_id='7-0001', akte_nr=1, adress_qid='Q7',
               geburtsname='', vorname='Marg.', vorname_norm='Marg.')
doub = {'6-0121': [('7-0001', 95)], '7-0001': [('6-0121', 95)]}
z = QS.bauen([paar6, paar7], CFG, {}, doub, zusammenfuehren=True)
check('ein Item statt zwei', len([l for l in z if l == 'CREATE']) == 1,
      [l for l in z if l == 'CREATE'])
check('es führt die reichste Namensform',
      'LAST\tLde\t"Margarete Müller (geb. Hahn)"' in z, [l for l in z if 'Lde' in l])
check('die andere Schreibweise wird Alias',
      'LAST\tAde\t"Marg. Müller"' in z, [l for l in z if 'Ade' in l])
check('der Geburtsname bleibt Alias', 'LAST\tAde\t"Hahn"' in z)
check('die Beschreibung nennt beide Wahljahre',
      'LAST\tDde\t"*26.12.1881; 1928 und 1933 Wahlteilnehmer in Aschersleben"' in z,
      [l for l in z if 'Dde' in l])
check('Mensch, Geburtsdatum und Geschlecht nur einmal',
      [len([l for l in z if f'\t{p}\t' in l]) for p in ('P2', 'P77', 'P154')]
      == [1, 1, 1], [l for l in z if '\tP2\t' in l or '\tP77\t' in l])
check('beide Fundstellen bleiben erhalten',
      sorted(l for l in z if '\tP51\t' in l)
      == ['LAST\tP51\tQ2088500\tP499\t121', 'LAST\tP51\tQ2088502\tP499\t1'],
      [l for l in z if 'P51' in l])
check('beide Adressen mit ihrem eigenen Jahr',
      sorted(l for l in z if '\tP208\t' in l)
      == ['LAST\tP208\tQ6\tP106\t+1933-00-00T00:00:00Z/9',
          'LAST\tP208\tQ7\tP106\t+1928-00-00T00:00:00Z/9'],
      [l for l in z if 'P208' in l])
check('der Ort steht je Jahr einmal',
      len([l for l in z if '\tP83\t' in l]) == 2, [l for l in z if 'P83' in l])
check('alle drei Wahlen der beiden Ordner',
      sorted(l.split('\t')[2] for l in z if '\tP119\t' in l)
      == ['Q1207474', 'Q2088496', 'Q2088498'], [l for l in z if 'P119' in l])
check('das Forschungsprojekt nur einmal',
      len([l for l in z if '\tP131\t' in l]) == 1, [l for l in z if 'P131' in l])
check('die Zusammenführung steht als Kommentar vor dem CREATE',
      z[z.index('CREATE') - 1].startswith('# ZUSAMMENGEFÜHRT')
      and '6-0121' in z[z.index('CREATE') - 1]
      and '7-0001' in z[z.index('CREATE') - 1], z[z.index('CREATE') - 1])
check('der Kopf zählt die eingegangenen Einträge',
      any('1 weitere Registereinträge' in l for l in z[:9]), z[:9])
check('und warnt nicht mehr vor dem, was er erledigt hat',
      not any('ACHTUNG' in l for l in z))
# Ohne den Schalter bleibt es beim dokumentierten Verhalten: zwei Items, Warnung.
z = QS.bauen([paar6, paar7], CFG, {}, doub)
check('ohne Schalter unverändert zwei Items',
      len([l for l in z if l == 'CREATE']) == 2 and any('ACHTUNG' in l for l in z))
# Wilhelm Thiede steht in drei Ordnern — wer A=B und B=C sagt, hat A=C gesagt.
drei = [stimme(ordner=5, lfd_id='5-0014', akte_nr=14),
        stimme(ordner=6, lfd_id='6-0342', akte_nr=342),
        stimme(ordner=7, lfd_id='7-0080', akte_nr=80)]
kette = {'5-0014': [('6-0342', 100)], '6-0342': [('5-0014', 100), ('7-0080', 100)],
         '7-0080': [('6-0342', 100)]}
z = QS.bauen(drei, CFG, {}, kette, zusammenfuehren=True)
check('die Gruppe wird transitiv geschlossen',
      len([l for l in z if l == 'CREATE']) == 1, [l for l in z if l == 'CREATE'])
check('… und alle drei Fundstellen stehen am Item',
      len([l for l in z if '\tP51\t' in l]) == 3, [l for l in z if 'P51' in l])
check('… die Beschreibung nennt beide Jahre einmal',
      'LAST\tDde\t"*26.12.1881; 1928 und 1933 Wahlteilnehmer in Aschersleben"' in z,
      [l for l in z if 'Dde' in l])
# Eine zugeordnete Seite gehört nicht in die Gruppe: ihr Item steht schon fest.
z = QS.bauen([paar6, dict(paar7, status='zugeordnet', ziel_qid='Q9')],
             CFG, {}, doub, zusammenfuehren=True)
check('zugeordnete Einträge werden nicht eingemeindet',
      len([l for l in z if l == 'CREATE']) == 1
      and any(l.startswith('Q9\t') for l in z)
      and not any('ZUSAMMENGEFÜHRT' in l for l in z),
      [l for l in z if l == 'CREATE' or l.startswith('Q9')][:3])

print('Gemischt')
z = QS.bauen([eintrag(), eintrag(lfd_id='0043', status='zugeordnet',
                                ziel_qid='Q1')], CFG)
check('Kopfzeile zählt beide Fälle',
      '1 neue Personen (CREATE), 1 bestehende Items ergänzt' in z[1], z[1])
check('nur entschiedene Einträge',
      QS.bauen([eintrag(status=None)], CFG)[-1] == '')   # nur der Kopf

print()
if fails:
    print(f'{len(fails)} Test(s) fehlgeschlagen: ' + ', '.join(fails))
    sys.exit(1)
print('alle Tests bestanden')
