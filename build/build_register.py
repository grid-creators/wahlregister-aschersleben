"""CSVs des Wahlregisters → data/register.sqlite.

Das Wählerverzeichnis liegt in Ordnern. Jeder Ordner ist eine eigene CSV mit
eigenen Straßen und eigenen FactGrid-Adressitems; alle landen in derselben
Tabelle `entries` und werden durch die Spalte `ordner` unterschieden.

Idempotent: legt `entries` / `entries_fts` / `meta` neu an, lässt Abgleich und
Handarbeit (`kandidaten`, `entscheidungen`, `p120`, `protokoll`,
`einstellungen`) unangetastet. Reine stdlib.

    python3 build/build_register.py
"""

import csv
import os
import re
import sqlite3
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, 'data', 'register.sqlite')

# Die Ordner des Bestands: (Nummer, CSV, Präfix der laufenden Nummer).
#
# Ordner 2 bekommt **keinen** Präfix. An seinen nackten Nummern („0001") hängen
# die Entscheidungen, die Vormerkungen und jede Zeile des Protokolls — wer sie
# umbenennt, kappt sie alle. Jeder weitere Ordner bringt seinen Präfix mit,
# damit sich die laufenden Nummern zweier Ordner nicht ins Gehege kommen.
QUELLEN = (
    (2, 'wahlregister 2 - register2_new.csv', ''),
    (3, 'wahlregister  - register3.csv', '3-'),
    (4, 'wahlregister_register4_korrigiert.csv', '4-'),
    (5, 'wahlregister_register5_korrigiert.csv', '5-'),
    (6, 'wahlregister_register6_korrigiert.csv', '6-'),
    (7, 'wahlregister_register7_korrigiert.csv', '7-'),
)

# Stichtag der zweiten Stimmabgabe-Spalte; steht so in den Bemerkungen
# ("am 12.3.33 noch nicht 6 Mon. Wohnsitz").
STICHTAG_JAHR = 1933

# **Nicht alle Ordner gehören zur selben Wahl.** Ordner 2 bis 5 sind das
# Verzeichnis zur Reichstagswahl vom 5.3.1933, Ordner 6 gehört zur
# Reichstagswahl und Volksabstimmung vom 12.11.1933 — beide Male ist 1933 der
# Stichtag. Ordner 7 ist die Wählerliste von **1928** (Reichstagswahl und
# Preußischer Landtag am 20.5.1928); das steht im Titel seines Archivales
# (Q2088502, „Wählerliste 1928 Ordner 7").
#
# Der Stichtag ist keine Beschriftung: an ihm hängen das Alter am Wahltag und
# das Jahrhundert der zweistelligen Jahreszahlen (siehe `iso_datum()`).
STICHTAG_ORDNER = {7: 1928}

# Aktives Wahlrecht ab 20 Jahren. Daraus folgt das Jahrhundert der
# zweistelligen Jahreszahlen in Ordner 3 bis 7 — siehe `iso_datum()`.
WAHLALTER = 20

# Grenze der anderen Deutung: Wer im 19. Jahrhundert geboren wäre, müsste am
# Wahltag über hundert sein. Die Jahrgänge reichen in den Ordnern von '41
# (92 Jahre) bis '13; darüber hinaus ist 18xx keine Lesart mehr, sondern ein
# Rechenfehler. Siehe `iso_datum()`.
MAX_ALTER = 110


def stichtag(ordner):
    return STICHTAG_ORDNER.get(ordner, STICHTAG_JAHR)

# ---------------------------------------------------------------- Adressen

# Nur Abkürzungen werden aufgelöst, keine Straße wird umbenannt: das Register
# nennt die Namen von 1933, und zwischen ihnen und den heutigen liegen
# Umbenennungen, die hier nichts zu suchen haben. Welches FactGrid-Item zu
# welcher Adresse gehört, steht in der Quell-CSV (siehe link_addresses.py).
STREET_MAP = {
    'breitestr.': 'Breite Straße',
    'breite straße': 'Breite Straße',
    'badstr.': 'Badstraße',
    'taubenstr.': 'Taubenstraße',
    'bestehornstr.': 'Bestehornstraße',
    'h.d.turm': 'Hinter dem Turm',
    'h.d. turm': 'Hinter dem Turm',
    'h.d.tor': 'Hinter dem Tor',
    'steph. kirchh.': 'Stephanikirchhof',
    'steph. kirchhof': 'Stephanikirchhof',
    'liebenw. plan': 'Liebenwerder Plan',
    # Ordner 3
    'bürgerstr.': 'Bürgerstraße',
    'bürgerstraße': 'Bürgerstraße',
    'friedrichstr.': 'Friedrichstraße',
    'heinrichstr.': 'Heinrichstraße',
    'kreuzstr.': 'Kreuzstraße',
    'leopoldstr.': 'Leopoldstraße',
    'lindenstr.': 'Lindenstraße',
    'schierstedter str.': 'Schierstedter Straße',
    'schillerstr.': 'Schillerstraße',
    'wilhelmstr.': 'Wilhelmstraße',
    'worthstr.': 'Worthstraße',
    # Ordner 4. Dieser Ordner schreibt dieselbe Straße auf mehrere Weisen —
    # „Eislebenerstr.", „Eisleberstr.", „Eislebstr.", „Eilsleben.Str.". Dass es
    # dieselbe ist, steht nicht hier zur Vermutung an, sondern in der Quelle:
    # die Schreibweisen tragen für dasselbe Haus dieselbe Q-ID (Nr. 1 ist in
    # allen dreien `Q497993`). Wo der Peru-Auszug das Item kennt, ist die
    # ausgeschriebene Form von dort bestätigt — „Eisleber Straße" (Q497993),
    # „Albert-Drosihn-Straße" (Q1211270), „Westdorfer Straße".
    'albrechtstr.': 'Albrechtstraße',
    'a.drosihnstr.': 'Albert-Drosihn-Straße',
    'alb.drosihnstr.': 'Albert-Drosihn-Straße',
    'drosihnstr.': 'Albert-Drosihn-Straße',
    'apothekergr.': 'Apothekergraben',
    'apothekergrab.': 'Apothekergraben',
    'eisleb.str.': 'Eisleber Straße',
    'eislebstr.': 'Eisleber Straße',
    'eisleberstr.': 'Eisleber Straße',
    'eislebenerstr.': 'Eisleber Straße',
    # „Eislebenerstr29" — ohne Punkt vor der Hausnummer bleibt die Straße auch
    # ohne ihn zurück.
    'eislebenerstr': 'Eisleber Straße',
    'eilsleben.str.': 'Eisleber Straße',
    'fr.ebertst.': 'Friedrich-Ebert-Straße',
    'fr.ebertstr.': 'Friedrich-Ebert-Straße',
    'gartenstr.': 'Gartenstraße',
    'holtz-str.': 'Holtzstraße',
    'holtzstr.': 'Holtzstraße',
    'mehringerstr.': 'Mehringer Straße',
    'westdorferstr.': 'Westdorfer Straße',
    # Zwei Verschreibungen, ebenfalls über die Q-ID belegt: „Peilergraben 6"
    # und „Pfeilergraben 6" sind `Q2086709`, „Wasserstr.30" und „Wassertor 30"
    # sind `Q497854`. Vor der Pechhütte und hinter ihr ist in dieser Quelle
    # dasselbe Haus (`Q2086703`).
    'peilergraben': 'Pfeilergraben',
    'wasserstr.': 'Wassertor',
    'h.d.pechhütte': 'Pechhütte',
    # Ordner 5. Wieder gilt: dieselbe Q-ID an derselben Hausnummer belegt, dass
    # zwei Schreibweisen dasselbe meinen — „Schulstieg" und „Schuhstieg" sind
    # beide `Q498661`, „Zipfelmarkt" und „Zippelmarkt" beide `Q497910`,
    # „Jüdenberg"/„Jüdenstr." stehen an Häusern des Jüdendorfs. Die
    # ausgeschriebenen Formen sind, wo der Auszug das Item kennt, von dort
    # bestätigt („Fleischhauerstraße", „Großer Halken", „Kleiner Halken",
    # „Über dem Wasser", „Ritterstraße").
    'fleisch.str.': 'Fleischhauerstraße',
    'fleischh.str.': 'Fleischhauerstraße',
    'fleischhauerstr.': 'Fleischhauerstraße',
    'gr.halken': 'Großer Halken',
    'grosser halken': 'Großer Halken',
    'kl.halken': 'Kleiner Halken',
    'jüdenberg': 'Jüdendorf',
    'jüdenstr.': 'Jüdendorf',
    'ritterstr.': 'Ritterstraße',
    'ritterst.': 'Ritterstraße',
    'schulstieg': 'Schuhstieg',
    'zipfelmarkt': 'Zippelmarkt',
    'u.d.wasser': 'Über dem Wasser',
    'ü.d.wasser': 'Über dem Wasser',
    'ü.d.wassen': 'Über dem Wasser',
    'ü.d.wesser': 'Über dem Wasser',
    # „Mauerstr." bleibt die Mauerstraße. Ihr Item trägt im Auszug das Label
    # „Eselsgasse" — das ist der heutige Name, und der gehört hier so wenig hin
    # wie die Hecknerstraße bei „Bestehornstr.". Nur die Abkürzung wird
    # aufgelöst.
    'mauerstr.': 'Mauerstraße',
    # Ordner 6 und 7. Diese beiden überschneiden sich in fünf Straßen, und ohne
    # gemeinsame Schreibweise fiele die Überschneidung nicht auf. Alle fünf
    # sind über die Q-ID belegt: „U. d. Birken" (Ordner 6) und „Ueb.d.Brücken"
    # (Ordner 7) stehen an denselben Häusern (`Q498251` u. a., Label „Über den
    # Brücken") — die Lesung „Birken" ist eine Verschreibung der Akte, keine
    # zweite Straße. Ebenso „Theod. Körnerstr." = „Körnerstr." (`Q2088520`),
    # „U. d. Burg" = „U.d.Burg" (`Q2088541`), „Auf d. Burg" = „A.d.Burg"
    # (`Q2082056`). „Körtestraße" ist über `Q998923` bestätigt.
    'u. d. birken': 'Über den Brücken',
    'ueb.d.brücken': 'Über den Brücken',
    'u. d. burg': 'Unter der Burg',
    'u.d.burg': 'Unter der Burg',
    'auf d. burg': 'Auf der Burg',
    'a.d.burg': 'Auf der Burg',
    'theod. körnerstr.': 'Theodor-Körner-Straße',
    'körnerstr.': 'Theodor-Körner-Straße',
    'kortestr.': 'Körtestraße',
    'askanierstr.': 'Askanierstraße',
    'baumgartenstr.': 'Baumgartenstraße',
    'hennestr.': 'Hennestraße',
    'schützenstr.': 'Schützenstraße',
    'stephanstr.': 'Stephanstraße',
    'zeppelinstr.': 'Zeppelinstraße',
    'berlinerstr.': 'Berliner Straße',
    'einestr.': 'Einestraße',
    'ermsleberstr.': 'Ermsleber Straße',
    'karlstr.': 'Karlstraße',
    'lauestr.': 'Lauestraße',
    # Nicht aufgelöst, weil mehrdeutig: „a. d. Postberg" (an oder auf?) und
    # „Margar.Kirchh." — für beide führt der Auszug kein Label, und geraten
    # wird hier nichts.
}


def norm_street(roh):
    """Straßenname → einheitliche Schreibweise. Ordner 6 und 7 führen die
    Straße in einer eigenen Spalte, kommen also nie durch `split_address()`."""
    s = re.sub(r'\s+', ' ', (roh or '').strip()).strip(' ,')
    return STREET_MAP.get(s.lower(), s)


def split_address(raw):
    """'Breitestr. 22' → ('Breite Straße', '22'). Hausnummer kann fehlen.

    Ordner 4 schreibt sie ohne Leerzeichen an die Straße („Eislebenerstr.7a",
    „Apothekergraben1"); fehlt die Lücke, wird sie vorn eingesetzt. Auf einen
    Bindestrich folgt sie **nicht** — dort steht ein Bereich („Bestehornstr.
    1-6"), und der gehört als Ganzes in die Hausnummer. Ein mit Schrägstrich
    angehängter Bereich zählt dagegen mit: Ordner 5 schreibt „Ritterstr.9/10"
    ohne jede Lücke, und ohne diesen Fall bliebe die ganze Angabe Straßenname."""
    s = (raw or '').strip()
    if not s:
        return ('', '')
    s = re.sub(r'(?<=[^\s\d\-/])(\d+[a-zA-Z]?(?:\s*/\s*\d+[a-zA-Z]?)?)\s*$',
               r' \1', s)
    m = re.search(r'\s(\d+[a-zA-Z]?(?:\s*[-/]\s*\d+[a-zA-Z]?)?)\s*$', s)
    street, nr = (s[:m.start()], m.group(1)) if m else (s, '')
    return (norm_street(street), re.sub(r'\s*', '', nr))


def sort_key_house(nr):
    """Hausnummern numerisch sortierbar machen ('12a' → 12)."""
    m = re.match(r'(\d+)', nr or '')
    return int(m.group(1)) if m else 9999


# ----------------------------------------------------------------- Datum

def iso_datum(roh, jahr_stichtag=STICHTAG_JAHR):
    """'25.10.76' → '1876-10-25'. ISO bleibt ISO.

    Ordner 3 bis 7 nennen das Jahr zweistellig, das Jahrhundert steht nicht in
    der Quelle. Es folgt aber aus dem Register selbst: wer wählen durfte, war
    mindestens 20 — für 1933 kann '14 also kaum noch das 20. Jahrhundert
    meinen. Der Stichtag gehört deshalb dazu: in Ordner 7 wurde 1928 gewählt,
    dort liegt dieselbe Grenze fünf Jahre früher.

    Die Regel entscheidet aber **nicht** allein nach dem Wahlalter, sondern
    wägt beide Lesarten ab. Ordner 6 führt unter Nr. 369 einen Kurt Hering,
    \\*25.5.14 — durchgestrichen, mit dem Vermerk „noch nicht wahlfähig". Genau
    dieser Fall gehört ins 20. Jahrhundert: als 1814 wäre der Mann 119 Jahre
    alt, und *das* ist keine Lesart mehr. Zu jung zum Wählen kommt vor (der
    Eintrag wurde ja gestrichen), über hundert nicht. Deshalb gewinnt 18xx nur,
    solange es ein plausibles Alter ergibt — bis `MAX_ALTER`."""
    s = (roh or '').strip()
    if not s:
        return ''
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        return s
    m = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{2}|\d{4})$', s)
    if not m:
        return ''
    tag, monat, jahr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if len(m.group(3)) == 2:
        wahlfaehig = jahr_stichtag - (1900 + jahr) >= WAHLALTER
        zu_alt = jahr_stichtag - (1800 + jahr) > MAX_ALTER
        jahr += 1900 if (wahlfaehig or zu_alt) else 1800
    return '%04d-%02d-%02d' % (jahr, monat, tag)


# ---------------------------------------------------------------- Vornamen

# Abkürzungen, die im Register vorkommen. Nur eindeutige werden aufgelöst;
# alles Mehrdeutige (Fr. = Friedrich/Frieda, Joh. = Johann/Johanne, Aug. =
# August/Auguste) bleibt bewusst stehen.
ABBREV = {
    'marg.': 'Margarete', 'margar.': 'Margarete',
    'elisab.': 'Elisabeth', 'elis.': 'Elisabeth', 'elisabt.': 'Elisabeth',
    'eli.': 'Elisabeth', 'gertr.': 'Gertrud', 'charl.': 'Charlotte',
    'elsb.': 'Elsbeth', 'irmg.': 'Irmgard', 'hedw.': 'Hedwig',
    'elfr.': 'Elfriede', 'magd.': 'Magdalena', 'doroth.': 'Dorothea',
    'hild.': 'Hildegard', 'hildeg.': 'Hildegard', 'kath.': 'Katharina',
    'mari.': 'Marie', 'alw.': 'Alwine', 'annel.': 'Anneliese',
    'math.': 'Mathilde', 'ther.': 'Therese', 'henr.': 'Henriette',
    'gottfr.': 'Gottfried', 'wilh.': 'Wilhelm', 'frdr.': 'Friedrich',
}

FEMALE = {
    'anna', 'marie', 'ida', 'gertrud', 'marta', 'martha', 'emma', 'frida',
    'frieda', 'minna', 'luise', 'louise', 'helene', 'hedwig', 'else', 'elsa',
    'margarete', 'erna', 'elisabeth', 'berta', 'bertha', 'selma', 'auguste',
    'charlotte', 'ilse', 'ella', 'lina', 'johanne', 'johanna', 'alwine',
    'alvine', 'elise', 'alma', 'elsbeth', 'lucie', 'luzie', 'agnes', 'olga',
    'therese', 'elly', 'elli', 'clara', 'klara', 'herta', 'hertha', 'alice',
    'käthe', 'käte', 'kate', 'hildegard', 'elfriede', 'emmy', 'emmi',
    'amanda', 'emilie', 'grete', 'hanna', 'edith', 'mathilde', 'hilde',
    'hilda', 'marianne', 'friederike', 'erika', 'magdalena', 'magdalene',
    'pauline', 'rosa', 'paula', 'wally', 'anni', 'anny', 'irmgard', 'sophie',
    'antonie', 'irene', 'annelene', 'anneliese', 'annaliese', 'annemarie',
    'liselotte', 'lotte', 'cäcilie', 'henny', 'ruth', 'dorothea', 'dorothee',
    'doris', 'herma', 'hermine', 'betty', 'meta', 'traude', 'ina', 'josepha',
    'jenny', 'agathe', 'gerda', 'maria', 'thea', 'laura', 'katharina',
    'katharine', 'adele', 'edelgard', 'liesel', 'lieska', 'ernestine',
    'henriette', 'hilla', 'hani',
    # aus Ordner 3
    'adelheid', 'amalie', 'apollonia', 'edita', 'fanny', 'henrietta', 'irma',
    'karoline', 'liddy', 'liesbeth', 'lieselotte', 'lisbeth', 'lore',
    'margret', 'nanny', 'ruta', 'ursula', 'wilhelmine',
}

MALE = {
    'otto', 'karl', 'carl', 'paul', 'wilhelm', 'walter', 'friedrich',
    'hermann', 'richard', 'gustav', 'fritz', 'ernst', 'kurt', 'curt', 'franz',
    'willi', 'willy', 'august', 'erich', 'robert', 'hans', 'alfred',
    'heinrich', 'rudolf', 'emil', 'max', 'albert', 'georg', 'oskar',
    'herbert', 'bruno', 'louis', 'hugo', 'ludwig', 'eduard', 'adolf',
    'gerhard', 'bernhard', 'reinhold', 'artur', 'arthur', 'gottfried',
    'heinz', 'arno', 'gottlieb', 'werner', 'johannes', 'johann', 'julius',
    'heino', 'oswald', 'christian', 'udo', 'theodor', 'hilmar', 'andreas',
    'edmund', 'adam', 'martin', 'feodor', 'theo', 'gottlob', 'albin',
    'niklaus', 'felix', 'berthold', 'michael', 'hellmuth', 'helmuth',
    'moritz', 'josef', 'ewald', 'gotthold', 'günter', 'clemens', 'willmar',
    'gotthard', 'wilko', 'norbert', 'erwin', 'eitel', 'peter', 'hartmut',
    'stanislaus', 'arnim', 'wendt',
    # aus Ordner 3. „Ronuald" steht so im Register (wohl Romuald) und wird
    # deshalb in dieser Schreibung geführt.
    'aloys', 'anton', 'arwed', 'benno', 'conrad', 'dietrich', 'eberhard',
    'elmar', 'erhard', 'ferdinand', 'günther', 'helmar', 'horst', 'joachim',
    'joseph', 'konrad', 'manfred', 'nikolaus', 'ottomar', 'ronuald',
    'siegfried', 'thilo', 'ulrich', 'waldemar', 'wilfried',
}


def strip_diacritics(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s)
                   if not unicodedata.combining(c))


# Akademische Titel stehen im Register vor dem Vornamen („Dr. Kurt"). Sie
# gehören nicht in den Namen: FactGrid führt sie als eigene Aussage (P170), und
# im Label hätten sie nichts zu suchen. Erkannt wird nur, was **vorn** und als
# eigenes Wort steht — „Drewes" bleibt ein Familienname.
TITEL = {'dr.', 'dr', 'prof.', 'prof'}

# Fachzusätze zählen nur unmittelbar hinter einem Titel dazu, damit aus
# „Dr. med. Kurt" der Titel „Dr. med." wird und nicht der Vorname „med.".
TITEL_FACH = {'med.', 'phil.', 'ph.', 'jur.', 'jur', 'ing.', 'theol.', 'rer.',
              'nat.', 'oec.', 'dent.', 'vet.', 'h.', 'c.'}


def split_titel(raw):
    """'Dr. med. Kurt' → ('Dr. med.', 'Kurt'). Ohne Titel bleibt links leer."""
    toks = [t for t in re.split(r'\s+', (raw or '').strip()) if t]
    i = 0
    while i < len(toks) and (toks[i].lower() in TITEL
                             or (i and toks[i].lower() in TITEL_FACH)):
        i += 1
    return (' '.join(toks[:i]), ' '.join(toks[i:]))


def expand_vorname(raw):
    """Abkürzungen auflösen; Initialen ('A.') bleiben stehen."""
    parts = []
    for tok in re.split(r'[\s]+', (raw or '').strip()):
        if not tok:
            continue
        full = ABBREV.get(tok.lower())
        parts.append(full or tok)
    return ' '.join(parts)


def guess_sex(vorname_norm, geburtsname):
    """('w'|'m'|None, Quelle). Ein Geburtsname im Register bezeichnet den
    Mädchennamen einer verheirateten Frau — das ist das härtere Signal."""
    if (geburtsname or '').strip():
        return ('w', 'geburtsname')
    for tok in re.split(r'[\s-]+', (vorname_norm or '').lower()):
        t = tok.strip('.')
        if not t or len(t) < 2:
            continue
        if t in FEMALE:
            return ('w', 'vorname')
        if t in MALE:
            return ('m', 'vorname')
    return (None, None)


# ---------------------------------------------------------------- Wahlspalten

# Die Spalten tragen die Nummern der Akte. Ordner 2 wurde nur in den Spalten 4,
# 5 und 8 erfasst; Ordner 3 führt zusätzlich 6, 7 und 9 — dort steht in jeder
# Zeile eine Null, die Akte trägt in diesen Spalten also keinen Vermerk. Welche
# Wahl gemeint ist, ist nur für 4, 5 und 8 erschlossen (siehe regeln.md); die
# übrigen werden mitgeschrieben, aber nicht exportiert.
# Dazu `'st'` für Ordner 6 und 7: die beiden führen **eine** Spalte
# „stimmabgabe" statt der nummerierten Aktenspalten, weil sie zu anderen Wahlen
# gehören (12.11.1933 bzw. 20.5.1928). Sie trägt keine Aktennummer, deshalb
# kein Zahlenschlüssel — die Datenbankspalte heißt `spst`.
SPALTEN_AKTE = (4, 5, 6, 7, 8, 9)
SPALTEN = SPALTEN_AKTE + ('st',)

SPALTEN_NAME = {'st': 'Stimmabgabe'}

# Ordner 2 und 6 haken mit ✓ und X ab, Ordner 3, 4, 5 und 7 schreiben 1 und 0.
TICK_TRUE = {'✓', '✔', 'x', 'X', '+', '1'}
TICK_FALSE = {'0'}

# Ordner 6 vermerkt bei 43 Einträgen „St.". Die Quelle löst das selbst auf —
# in den Bemerkungen steht „Vermerk 'St.' (Stimmschein)". Ein Stimmschein
# belegt, dass jemand anderswo wählen durfte, **nicht** dass er gewählt hat.
# Deshalb ein eigener Wert: erfasst und in der Liste sichtbar, im Export aber
# keine Teilnahme — dort zählt allein die 1.
TICK_STIMMSCHEIN = 2
TICK_SONDER = {'st.': TICK_STIMMSCHEIN, 'st': TICK_STIMMSCHEIN}


def tick(raw):
    """Roh-Zeichen → 1 (Vermerk vorhanden) / 0 (leer) / 2 (Stimmschein) /
    None (unklar)."""
    s = (raw or '').strip()
    if not s or s in TICK_FALSE:
        return 0
    if s in TICK_TRUE:
        return 1
    if s.lower() in TICK_SONDER:
        return TICK_SONDER[s.lower()]
    return None  # '—', '⍯' u. Ä.: gesetzt, aber nicht als Ja lesbar


# ---------------------------------------------------------------- Einlesen

def _kopf(roh):
    """Kopfzeile mit Namen für die namenlosen Spalten. Ordner 2 hat zwei davon:
    vorn die laufende Nummer, hinter „Adresse" das FactGrid-Adressitem.
    `csv.DictReader` legt beide auf denselben Schlüssel '' — die hintere
    gewinnt, und die laufende Nummer wäre weg. Sie trägt aber die
    Entscheidungen, also werden namenlose Spalten nach ihrer Position benannt."""
    kopf = [h.strip() for h in roh[0]]
    return [h or f'spalte{i}' for i, h in enumerate(kopf)]


def _qid_spalte(kopf):
    """Die Spalte mit dem FactGrid-Adressitem. Jeder Ordner nennt sie anders:
    Ordner 2 gar nicht — sie steht namenlos **hinter** „Adresse" und wird über
    die Position gefunden —, Ordner 3 „Adresse QID", Ordner 4 „Wohnung QID",
    Ordner 5 „wohnung qid", Ordner 6 „Wohnung qid", Ordner 7 „Wohnung Qid".
    Gesucht wird deshalb ohne Rücksicht auf Groß- und Kleinschreibung."""
    if 'Familienname' in kopf:
        return kopf[kopf.index('Adresse') + 1]
    return next((h for h in kopf if h.lower().endswith('qid')), 'Adresse QID')


def blatt(bemerkung, quelle):
    """Bemerkung und Blatt der Fotografie, notfalls wieder zusammengesetzt.

    In einigen Zeilen enthält die Bemerkung ein Komma und steht in der Quelle
    **ohne** Anführungszeichen — „Doppeleintrag: gleicher Name … wie lfd. Nr.
    382, dort Ermsleberstr. 22". Der Leser schiebt die zweite Hälfte dann in
    die nächste Spalte, wo sonst das Blatt steht („IMG_8400_R"). Was dort nicht
    nach einem Blatt aussieht, gehört an die Bemerkung zurück; sonst geht der
    halbe Satz verloren und ein Bildname entsteht, den es nie gab. Betrifft 12
    Zeilen in Ordner 5, 3 in Ordner 6 und 4 in Ordner 7."""
    if quelle and not quelle.upper().startswith('IMG'):
        return (', '.join(x for x in (bemerkung, quelle) if x), '')
    return (bemerkung, quelle)


def lies(csv_path):
    """CSV → Zeilen mit einheitlichen Schlüsseln, egal in welchem der drei
    Tabellenformate der Ordner kommt.

    - **Ordner 2**: deutsche Überschriften, ISO-Datum, ✓/X, drei Wahlspalten.
    - **Ordner 3, 4, 5**: kurze technische Namen, deutsches Datum, 1/0, sechs
      Wahlspalten, dazu `quelle` mit dem Blatt der Fotografie. Sie
      unterscheiden sich nur im Namen der Q-ID-Spalte.
    - **Ordner 6 und 7**: gehören zu anderen Wahlen und haben deshalb nur
      **eine** Spalte `stimmabgabe` statt der nummerierten. Straße und
      Hausnummer stehen getrennt, was den ganzen Ratevorgang von
      `split_address()` erspart. Ordner 6 nennt den Familiennamen „zuname",
      Ordner 7 führt **keinen Geburtsnamen** — dort fehlt bei verheirateten
      Frauen also das stärkste Merkmal für das Geschlecht und der
      Klammerzusatz im Label."""
    with open(csv_path, encoding='utf-8-sig', newline='') as fh:
        roh = list(csv.reader(fh))
    kopf = _kopf(roh)
    rows = [dict(zip(kopf, r)) for r in roh[1:]]
    alt = 'Familienname' in kopf
    stimme = 'stimmabgabe' in kopf
    qid_spalte = _qid_spalte(kopf)

    def col(row, name, default=''):
        return (row.get(name) or default).strip()

    out = []
    for r in rows:
        if stimme:
            bem, bild = blatt(col(r, 'bemerkungen'), col(r, 'quelle'))
            strasse = col(r, 'strasse')
            hausnr = col(r, 'hausnr') or col(r, 'hausnummer')
            e = {
                'lfd': col(r, 'lfd_nr'),
                'akte': col(r, 'lfd_nr'),
                'familienname': col(r, 'zuname') or col(r, 'name'),
                'vorname': col(r, 'vorname'),
                'geburtsname': col(r, 'geburtsname'),
                # Rohform bleibt, was die Quelle zusammengenommen sagt; die
                # zerlegte Fassung kommt aus den beiden Spalten und nicht aus
                # einem Trennversuch.
                'adresse': ' '.join(x for x in (strasse, hausnr) if x),
                'strasse_roh': strasse,
                'hausnr_roh': hausnr,
                'adress_qid': col(r, qid_spalte),
                'geburtsdatum': col(r, 'geboren_am'),
                'bemerkung': bem,
                'bild': bild,
                'spst': col(r, 'stimmabgabe'),
            }
        elif alt:
            e = {
                'lfd': col(r, 'spalte0') or col(r, 'Lfd. Nr. in Akte'),
                'akte': col(r, 'Lfd. Nr. in Akte'),
                'familienname': col(r, 'Familienname'),
                'vorname': col(r, 'Vorname'),
                'geburtsname': col(r, 'Geburtsname'),
                'adresse': col(r, 'Adresse'),
                'adress_qid': col(r, qid_spalte),
                'geburtsdatum': col(r, 'Geburtsdatum'),
                'bemerkung': col(r, 'Bemerkungen'),
                'bild': '',
                'sp4': col(r, 'Wahl 1. Spalte'),
                'sp5': col(r, 'Wahl 2. Spalte'),
                'sp8': col(r, 'Wahl 3. Spalte'),
            }
        else:
            bem, bild = blatt(col(r, 'bemerkungen'), col(r, 'quelle'))
            e = {
                # In Ordner 3 ist die laufende Nummer zugleich die Nummer in
                # der Akte — wie in Ordner 2, wo beide Spalten nie abweichen.
                'lfd': col(r, 'lfd_nr'),
                'akte': col(r, 'lfd_nr'),
                'familienname': col(r, 'name'),
                'vorname': col(r, 'vorname'),
                'geburtsname': col(r, 'geburtsname'),
                'adresse': col(r, 'wohnung'),
                'adress_qid': col(r, qid_spalte),
                'geburtsdatum': col(r, 'geboren_am'),
                'bemerkung': bem,
                'bild': bild,
            }
            # Nur die nummerierten Spalten — `spst` bleibt hier ungesetzt und
            # damit None. Das ist der Unterschied zwischen „in dieser Spalte
            # steht nichts" und „diese Spalte gibt es in diesem Ordner nicht".
            e.update({f'sp{n}': col(r, f'sp{n}') for n in SPALTEN_AKTE})
        if not any((e['lfd'], e['familienname'], e['vorname'])):
            continue        # Leerzeile am Tabellenende
        out.append(e)
    return out


# ---------------------------------------------------------------- Schema

SP_SPALTEN = ',\n    '.join(f'sp{n} TEXT, sp{n}_ok INTEGER' for n in SPALTEN)

SCHEMA = f"""
DROP TABLE IF EXISTS entries;
CREATE TABLE entries (
    rowid         INTEGER PRIMARY KEY,
    ordner        INTEGER NOT NULL,       -- Ordner des Bestands I-14-149
    lfd_id        TEXT UNIQUE NOT NULL,   -- '0001' bzw. '3-0001'
    akte_nr       INTEGER,                -- Lfd. Nr. in der Akte
    familienname  TEXT NOT NULL,
    vorname       TEXT,                   -- wie im Register, mit Titel
    vorname_norm  TEXT,                   -- Abkürzungen aufgelöst, ohne Titel
    titel         TEXT,                   -- 'Dr.' — geht als P170, nie ins Label
    geburtsname   TEXT,
    name_voll     TEXT,                   -- 'Vorname Familienname'
    adresse       TEXT,                   -- Rohform
    strasse       TEXT,                   -- normalisiert
    hausnr        TEXT,
    hausnr_sort   INTEGER,
    geburtsdatum  TEXT,                   -- ISO, aus der Quelle umgesetzt
    geburtsjahr   INTEGER,
    alter_wahl    INTEGER,                -- Jahresdifferenz zum Stichtag des
                                          -- Ordners: 1933, in Ordner 7 aber 1928
    geschlecht    TEXT,                   -- 'w'|'m'|NULL — geschätzt
    geschlecht_q  TEXT,                   -- Quelle der Schätzung
    {SP_SPALTEN},
    bemerkung     TEXT,
    bild          TEXT                    -- Blatt der Fotografie, wenn genannt
);
CREATE INDEX idx_entries_fam    ON entries(familienname);
CREATE INDEX idx_entries_str    ON entries(ordner, strasse, hausnr_sort);
CREATE INDEX idx_entries_byear  ON entries(geburtsjahr);
CREATE INDEX idx_entries_ordner ON entries(ordner);

DROP TABLE IF EXISTS entries_fts;
CREATE VIRTUAL TABLE entries_fts USING fts5(
    familienname, vorname, geburtsname, adresse, bemerkung,
    content='entries', content_rowid='rowid', tokenize='unicode61'
);

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""

FELDER = (['ordner', 'lfd_id', 'akte_nr', 'familienname', 'vorname',
           'vorname_norm', 'titel', 'geburtsname', 'name_voll', 'adresse',
           'strasse', 'hausnr', 'hausnr_sort', 'geburtsdatum', 'geburtsjahr',
           'alter_wahl', 'geschlecht', 'geschlecht_q']
          + [f'sp{n}{s}' for n in SPALTEN for s in ('', '_ok')]
          + ['bemerkung', 'bild'])


def lfd_id(praefix, roh):
    """Laufende Nummer der Quelle → Schlüssel in der Datenbank. Ordner 2 hat
    keinen Präfix (siehe QUELLEN), jeder weitere trägt ihn vorn."""
    if not praefix:
        return roh
    return praefix + ('%04d' % int(roh) if roh.isdigit() else roh)


def zeile(ordner, praefix, e):
    titel, vor_ohne_titel = split_titel(e['vorname'])
    vor_norm = expand_vorname(vor_ohne_titel)
    # Ordner 6 und 7 führen Straße und Hausnummer getrennt — dort gibt es
    # nichts zu trennen und also auch nichts falsch zu trennen.
    if e.get('strasse_roh') is not None:
        street, nr = norm_street(e['strasse_roh']), e['hausnr_roh'].strip()
    else:
        street, nr = split_address(e['adresse'])
    gebdat = iso_datum(e['geburtsdatum'], stichtag(ordner))
    byear = int(gebdat[:4]) if gebdat else None
    sex, sex_src = guess_sex(vor_norm, e['geburtsname'])

    werte = {
        'ordner': ordner, 'lfd_id': lfd_id(praefix, e['lfd']),
        'akte_nr': int(e['akte']) if e['akte'].isdigit() else None,
        'familienname': e['familienname'], 'vorname': e['vorname'],
        'vorname_norm': vor_norm, 'titel': titel,
        'geburtsname': e['geburtsname'],
        'name_voll': ' '.join(x for x in (vor_norm, e['familienname']) if x),
        'adresse': e['adresse'], 'strasse': street, 'hausnr': nr,
        'hausnr_sort': sort_key_house(nr),
        'geburtsdatum': gebdat, 'geburtsjahr': byear,
        'alter_wahl': (stichtag(ordner) - byear) if byear else None,
        'geschlecht': sex, 'geschlecht_q': sex_src,
        'bemerkung': e['bemerkung'], 'bild': e['bild'] or None,
    }
    for n in SPALTEN:
        roh = e.get(f'sp{n}')
        werte[f'sp{n}'] = roh
        werte[f'sp{n}_ok'] = tick(roh) if roh is not None else None
    return tuple(werte[f] for f in FELDER)


def build(db_path=DB_PATH, quellen=QUELLEN):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)

    for ordner, datei, praefix in quellen:
        pfad = os.path.join(ROOT, datei)
        rows = [zeile(ordner, praefix, e) for e in lies(pfad)]
        con.executemany(
            f"INSERT INTO entries ({','.join(FELDER)}) VALUES ("
            + ','.join('?' * len(FELDER)) + ')', rows)
        con.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',
                    (f'quelle_o{ordner}', datei))
        con.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',
                    (f'zeilen_o{ordner}', str(len(rows))))

    con.execute("INSERT INTO entries_fts(entries_fts) VALUES('rebuild')")
    con.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',
                ('zeilen', str(con.execute('SELECT count(*) FROM entries')
                              .fetchone()[0])))
    con.commit()
    bericht(con)
    con.close()


def bericht(con):
    for ordner, datei, _ in QUELLEN:
        n, n_sex, n_str, n_dat = con.execute(
            'SELECT count(*), count(geschlecht), count(DISTINCT strasse), '
            "count(NULLIF(geburtsdatum, '')) FROM entries WHERE ordner=?",
            (ordner,)).fetchone()
        print(f'Ordner {ordner} ({datei}): {n} Einträge, {n_str} Straßen, '
              f'Geschlecht geschätzt für {n_sex}, {n - n_dat} ohne Geburtsdatum')
        titel = con.execute("SELECT titel, count(*) FROM entries WHERE titel <> '' "
                            'AND ordner=? GROUP BY 1 ORDER BY 2 DESC',
                            (ordner,)).fetchall()
        print('  Titel abgetrennt: '
              + (', '.join(f'{t} ({k})' for t, k in titel) or 'keine'))
        for n_sp in SPALTEN:
            ja, leer, schein, gesetzt = con.execute(
                f'SELECT sum(sp{n_sp}_ok = 1), sum(sp{n_sp}_ok = 0), '
                f'sum(sp{n_sp}_ok = {TICK_STIMMSCHEIN}), count(sp{n_sp}) '
                'FROM entries WHERE ordner=?', (ordner,)).fetchone()
            if not gesetzt:
                continue        # in diesem Ordner nicht erfasst
            name = SPALTEN_NAME.get(n_sp, f'Spalte {n_sp}')
            unklar = gesetzt - (ja or 0) - (leer or 0) - (schein or 0)
            print(f'  {name}: {ja or 0} mit Vermerk, {leer or 0} leer, '
                  + (f'{schein} Stimmschein, ' if schein else '')
                  + f'{unklar} unklar')
    print(f"insgesamt {con.execute('SELECT count(*) FROM entries').fetchone()[0]} "
          'Einträge')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        sys.exit('build_register.py kennt seine Quellen selbst (QUELLEN). '
                 'Ein neuer Ordner wird dort eingetragen, nicht übergeben.')
    build()
