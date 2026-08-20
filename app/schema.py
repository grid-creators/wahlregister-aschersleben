"""Schema der Abgleichs-Tabellen in data/register.sqlite.

`build/match_factgrid.py` legt sie an und füllt `kandidaten` neu; `app/server.py`
stellt beim Start sicher, dass sie existieren.

Alles hängt an der Registernummer `lfd_id`, nicht an einer rowid — die kann sich
beim Neuaufbau des Registers verschieben, die Nummer nicht. `entscheidungen`,
`p120` und `einstellungen` werden von keinem Build-Skript angefasst.
"""

MATCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS kandidaten (
    lfd_id        TEXT NOT NULL,
    rang          INTEGER NOT NULL,
    qid           TEXT NOT NULL,
    label         TEXT,
    description   TEXT,
    birth_date    TEXT,
    death_year    INTEGER,
    score         INTEGER,
    teilscores    TEXT,        -- JSON: nachname/vorname/geburtsdatum/adresse
    adresse_grund TEXT,
    hinweise      TEXT,        -- JSON-Liste
    PRIMARY KEY (lfd_id, qid)
);
CREATE INDEX IF NOT EXISTS idx_kandidaten ON kandidaten(lfd_id, rang);

-- Dieselbe Person in mehreren Ordnern. Gefüllt von
-- `build/link_doubletten.py`; hier nur angelegt, damit die Seite auch dann
-- läuft, wenn das Skript noch nie gelaufen ist. Kein Urteil, nur ein Hinweis
-- — die Übernahme einer Q-ID bleibt eine Entscheidung von Hand.
CREATE TABLE IF NOT EXISTS doubletten (
    lfd_id  TEXT NOT NULL,
    partner TEXT NOT NULL,
    ordner  INTEGER NOT NULL,
    score   INTEGER NOT NULL,
    grund   TEXT,
    PRIMARY KEY (lfd_id, partner)
);
CREATE INDEX IF NOT EXISTS idx_doubletten ON doubletten(lfd_id, score DESC);

CREATE TABLE IF NOT EXISTS entscheidungen (
    lfd_id       TEXT PRIMARY KEY,
    status       TEXT NOT NULL,      -- 'zugeordnet' | 'kein_treffer'
    qid          TEXT,               -- nur bei 'zugeordnet'
    notiz        TEXT,
    geaendert_am TEXT,
    label        TEXT,               -- Beschriftung des gewählten Items
    quelle       TEXT                -- 'vorschlag' | 'suche' | 'qid' | 'sammel'
);

-- P120 „Möglicherweise identisch mit": eine Q-ID, die zu diesem Eintrag passen
-- könnte, ohne dass die Zuordnung sicher wäre. Steht bewusst *neben* der
-- Entscheidung und nicht in ihr — der häufige Fall ist „keine Person in
-- FactGrid" (also ein neues Item) mit einem Verdacht daneben. Handarbeit wie
-- `entscheidungen`: hängt an `lfd_id` und überlebt jeden Neuaufbau.
CREATE TABLE IF NOT EXISTS p120 (
    lfd_id       TEXT PRIMARY KEY,
    qid          TEXT NOT NULL,
    label        TEXT,               -- Beschriftung, damit die Liste lesbar ist
    geaendert_am TEXT
);

-- Jede Änderung an `entscheidungen` und `p120` landet hier — die App kennt
-- keine Anmeldung, also ist dies die einzige Möglichkeit nachzuvollziehen, was
-- wann passiert ist und was vorher galt.
CREATE TABLE IF NOT EXISTS protokoll (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    zeit        TEXT NOT NULL,
    lfd_id      TEXT NOT NULL,
    aktion      TEXT NOT NULL,   -- 'entscheidung' | 'sammel' | 'ruecknahme' | 'p120'
    alt_status  TEXT,
    alt_qid     TEXT,
    neu_status  TEXT,
    neu_qid     TEXT,
    quelle      TEXT,
    bearbeiter  TEXT,            -- freiwillige Angabe, keine Anmeldung
    stapel      TEXT             -- klammert eine Sammelentscheidung zusammen
);
CREATE INDEX IF NOT EXISTS idx_protokoll_zeit ON protokoll(id DESC);
CREATE INDEX IF NOT EXISTS idx_protokoll_lfd ON protokoll(lfd_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_protokoll_stapel ON protokoll(stapel);

CREATE TABLE IF NOT EXISTS einstellungen (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS lauf_meta   (key TEXT PRIMARY KEY, value TEXT);
"""

# Spalten, die später dazugekommen sind. SQLite kennt kein
# "ADD COLUMN IF NOT EXISTS" — deshalb einzeln versuchen und Fehler schlucken.
NACHRUESTEN = (
    'ALTER TABLE entscheidungen ADD COLUMN label TEXT',
    'ALTER TABLE entscheidungen ADD COLUMN quelle TEXT',
)


def ensure(con):
    """Schema anlegen und fehlende Spalten nachrüsten."""
    con.executescript(MATCH_SCHEMA)
    for sql in NACHRUESTEN:
        try:
            con.execute(sql)
        except Exception:
            pass


# Kontext-Items für den QuickStatements-Export. Vorbelegt nach dem Muster von
# Q1257714 (Georg Obermüller) — ein Eintrag aus Ordner 1 desselben Bestands.
#
# Die drei Wahlspalten der Akte sind drei Wahlen, nicht eine. So steht es schon
# bei den 1.590 Personen aus Ordner 1 in FactGrid: 1.460 tragen Q1207285,
# 1.362 Q1214187, 1.337 Q1214186 — dieselbe Reihenfolge und fast dieselben
# Anteile wie die Vermerke in den Spalten 4, 5 und 8 dieses Registers.
#
# Die Primärquelle (P51) steht **je Ordner**: jeder Ordner des Bestands
# I-14-149 ist ein eigenes Archivale mit eigenem Item. Ein neuer Ordner bringt
# hier eine Zeile `qs_quelle_o<N>` mit — `quickstatements.py` sucht sie über
# `entries.ordner`, ohne den Code zu ändern.
QS_DEFAULTS = {
    'qs_ort':       'Q80706',    # P83  Ort der Adresse: Aschersleben
    'qs_quelle_o2': 'Q2080842',  # P51  Primärquelle Ordner 2
    'qs_quelle_o3': 'Q2084011',  # P51  Primärquelle Ordner 3
    'qs_quelle_o4': 'Q2086743',  # P51  Primärquelle Ordner 4
    'qs_quelle_o5': 'Q2088480',  # P51  Primärquelle Ordner 5
    'qs_quelle_o6': 'Q2088500',  # P51  Primärquelle Ordner 6
    'qs_quelle_o7': 'Q2088502',  # P51  Primärquelle Ordner 7 („Wählerliste 1928")
    'qs_wahl_sp4':  'Q1207285',  # P119 Spalte 4: Deutsche Reichstagswahl
    'qs_wahl_sp5':  'Q1214187',  # P119 Spalte 5: Stadtverordnetenversammlung
    'qs_wahl_sp8':  'Q1214186',  # P119 Spalte 8: Provinziallandtag Prov. Sachsen
    # Ordner 6 und 7 gehören zu anderen Wahlen und haben nur **eine**
    # Stimmabgabe-Spalte. In Ordner 7 stehen hinter dem einen Haken **zwei**
    # Wahlen: Reichstag und Preußischer Landtag wurden am 20.5.1928 am selben
    # Tag gewählt und in derselben Liste abgehakt.
    'qs_wahl_o6':          'Q1207474',  # Reichstagswahl u. Volksabstimmung 12.11.1933
    'qs_wahl_o7_reichstag': 'Q2088496',  # Reichstagswahl 20.5.1928
    'qs_wahl_o7_landtag':   'Q2088498',  # Preußischer Landtag 20.5.1928
    'qs_rolle':     'Q1207476',  # P277 Rolle je Teilnahme: Wahlberechtigte(r)
    'qs_projekt':   'Q497317',   # P131 Forschungsprojekt: Aschersleben in FactGrid
    'qs_titel':     'Q22218',    # P170 „Dr." — akademischer Titel ohne Fachangabe
    'qs_beschreibung': 'ja',     # Dde erzeugen
    'qs_geschlecht':   'ja',     # P154 setzen (geschätzt!)
    'qs_label_en':     'ja',     # Len zusätzlich zu Lde (nur bei Neuanlage)
}


def quelle_key(ordner):
    """Einstellungsschlüssel der Primärquelle eines Ordners."""
    return f'qs_quelle_o{ordner}'


# Das Jahr, auf das sich die Angaben eines Ordners beziehen. Es hängt als
# Qualifikator (P106) an Ort und Adresse, steht in der Beschreibung neuer
# Personen und bestimmt beim Einlesen das Jahrhundert der zweistelligen
# Jahreszahlen. Ordner 7 ist die Wählerliste von **1928**, alle übrigen
# gehören zu 1933. Steht hier und nicht in `build_register.py`, damit Einlesen
# und Export nicht auseinanderlaufen können.
WAHLJAHR_STANDARD = 1933
WAHLJAHR_ORDNER = {7: 1928}


def wahljahr(ordner):
    return WAHLJAHR_ORDNER.get(ordner, WAHLJAHR_STANDARD)


# Welche Wahl hinter welcher Spalte steht — je Ordner. Ordner 2 bis 5 haken
# drei Aktenspalten ab und meinen damit drei Wahlen des Jahres 1933; Ordner 6
# und 7 führen eine einzige Spalte `spst`. Dass in Ordner 7 **eine** Spalte
# **zwei** Wahlen belegt, ist kein Fehler: am 20.5.1928 wurde der Reichstag
# und der Preußische Landtag am selben Tag gewählt.
WAHLSPALTEN_STANDARD = (('sp4_ok', 'qs_wahl_sp4'),
                        ('sp5_ok', 'qs_wahl_sp5'),
                        ('sp8_ok', 'qs_wahl_sp8'))
WAHLSPALTEN_ORDNER = {
    6: (('spst_ok', 'qs_wahl_o6'),),
    7: (('spst_ok', 'qs_wahl_o7_reichstag'),
        ('spst_ok', 'qs_wahl_o7_landtag')),
}


def wahlspalten(ordner):
    return WAHLSPALTEN_ORDNER.get(ordner, WAHLSPALTEN_STANDARD)
