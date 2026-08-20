# CLAUDE.md

Hinweise für Claude in diesem Repo. Antworten und Code-Kommentare auf Deutsch,
der Code selbst in Englisch — wie im Nachbarprojekt `peru`.

## Was ist das

Ein Werkzeug für **eine** Aufgabe: die Einträge der Wählerverzeichnisse
Aschersleben (1933 und, seit Ordner 7, auch 1928) gegen FactGrid abgleichen,
von Hand entscheiden, als QuickStatements exportieren. Eine Seite, keine
weiteren Auswertungen.

Das ist der Zuschnitt, auf den das Werkzeug bewusst zurückgebaut wurde. Register-
Suche, Adressansicht und Statistik gab es einmal und sind wieder entfernt worden
— nicht wieder einbauen, ohne dass jemand danach fragt.

## Sieben Ordner — und nicht alle zur selben Wahl

Das Verzeichnis liegt in Ordnern des Bestands I-14-149. Seit dem 17.8.2026 hält
die App **sechs** davon (2 bis 7) mit zusammen **9.789** Einträgen. Sie stehen
in derselben Tabelle `entries`, unterschieden durch die Spalte `ordner`, und
die Seite hat dafür einen Filter.

| Ordner | Einträge | Wahl | Archivale (P51) |
|---|---|---|---|
| 2 | 1.669 | Reichstagswahl 5.3.1933 (drei Spalten) | `Q2080842` |
| 3 | 1.730 | dieselben drei | `Q2084011` |
| 4 | 1.681 | dieselben drei | `Q2086743` |
| 5 | 1.604 | dieselben drei | `Q2088480` |
| 6 | 1.658 | Reichstagswahl u. Volksabstimmung **12.11.1933** | `Q2088500` |
| 7 | 1.447 | Reichstagswahl **und** Preuß. Landtag **20.5.1928** | `Q2088502` |

**Ordner 6 und 7 gehören zu anderen Wahlen als 2 bis 5.** Das ist der
wichtigste Unterschied im ganzen Bestand, und er zieht sich durch alles:

- **Ordner 7 ist die Wählerliste von 1928**, nicht von 1933. Sein Stichtag ist
  deshalb 1928 (`STICHTAG_ORDNER` in `build_register.py`,
  `WAHLJAHR_ORDNER` in `app/schema.py`). Daran hängen das Alter am Wahltag, das
  Jahrhundert der zweistelligen Jahreszahlen, der Qualifikator P106 an Ort und
  Adresse und das Jahr in der Beschreibung. Eine Probe darauf, dass der
  Stichtag stimmt: unter 1.447 Einträgen ist mit ihm **kein einziger** jünger
  als 20.
- **Ordner 7 belegt mit einem Haken zwei Wahlen.** Reichstag (`Q2088496`) und
  Preußischer Landtag (`Q2088498`) wurden am 20.5.1928 am selben Tag gewählt
  und in einer Liste abgehakt. Ein Vermerk erzeugt daher zwei P119.
- **Ordner 6 und 7 haben nur eine Stimmabgabe-Spalte** statt der nummerierten
  Aktenspalten. Sie heißt in der Datenbank `spst`.

Was die Ordner sonst trennt:

- **Eigene Straßen** und **eigene Adressitems**. `adress_items` hängt an
  **Ordner plus Adresse**, und jeder Join dorthin führt `a.ordner = e.ordner`
  mit. Wer das wegnimmt, hängt einem Ordner stillschweigend das falsche Haus an
  (P208). Der Fall, der es zeigt: „Liebenwerder Plan 20" meint in Ordner 2
  `Q498464`, in Ordner 3 aber `Q2082248` — die einzige widersprüchliche Adresse
  im ganzen Bestand.
- **Eigene Primärquelle** (P51), siehe Tabelle. Ein Ordner ohne hinterlegtes
  Item bekommt **kein** P51 — ein falscher wäre schlimmer.
- **Eigenes Tabellenformat.** Siehe `lies()` in `build_register.py`.

Die laufenden Nummern von Ordner 2 bleiben nackt (`0001`), weil Entscheidungen,
P120 und jede Protokollzeile daran hängen. Jeder weitere Ordner trägt ein
Präfix (`3-0001` … `7-0001`). Das steht in `QUELLEN` — ein neuer Ordner ist
dort eine Zeile.

### Straßen und Adressen überschneiden sich jetzt

Solange alle Ordner zur selben Wahl gehörten, hatte jeder seine eigenen
Straßen. Mit Ordner 6 und 7 ist das vorbei: die beiden teilen sich **44
Adressitems** in fünf Straßen (Bäckerstieg, Auf der Burg, Unter der Burg, Über
den Brücken, Theodor-Körner-Straße). Dass es dieselben sind, ist nicht geraten
— die Schreibweisen tragen für dasselbe Haus dieselbe Q-ID. „U. d. Birken" in
Ordner 6 und „Ueb.d.Brücken" in Ordner 7 stehen an denselben Häusern
(`Q498251` u. a., Label „Über den Brücken"): die Lesung „Birken" ist eine
Verschreibung der Akte, keine zweite Straße. `STREET_MAP` legt sie zusammen.

Zwei Straßen bleiben bewusst unaufgelöst, weil mehrdeutig und ohne Beleg im
Auszug: „a. d. Postberg" (an oder auf?) und „Margar.Kirchh.".

Und die Gegenprobe, die immer gilt: **Umbenennungen gehören nicht in
`STREET_MAP`.** Das Item der Mauerstraße (Ordner 5) trägt im Auszug das Label
„Eselsgasse" — das ist der heutige Name, so wie „Bestehornstr." des Registers
heute Hecknerstraße heißt. Aufgelöst werden Abkürzungen, umbenannt wird nichts.

### Der Ordnerfilter gilt für die ganze Seite

Liste, Fortschrittsbalken, **Export** und **Verlauf** zeigen denselben Ordner.
Es gibt dafür genau eine Auswahl oben; die Downloads hängen ihren `?ordner=`
selbst an (`mitOrdner()` in `app.js`), niemand wählt zweimal. Ohne Auswahl
bleibt alles wie zuvor: alle Ordner zusammen.

Eine Ausnahme, die bleiben muss: **`POST /api/stapel-zuruecknehmen` kennt
keinen Ordner.** Eine Sammelentscheidung wird zurückgenommen, wie sie gesetzt
wurde — sonst bliebe die Hälfte eines Stapels stehen, und das Protokoll
behauptete etwas anderes. Ein Stapel, der über den gewählten Ordner
hinausreicht, wird deshalb in der Liste ausgewiesen (`n_ordner < n`) und die
Rückfrage sagt es noch einmal.

## Der Abgleich hat zwei Richtungen

Bis Ordner 5 war das Register eine Liste: jeder Mensch stand einmal darin, und
die einzige Frage war, ob FactGrid ihn schon kennt. Weil Ordner 6 und 7 zu
anderen Wahlen gehören, steht mancher Mensch nun **zweimal** im Register — wer
1928 wählen durfte, durfte es 1933 meistens auch. `build/link_doubletten.py`
findet diese Paare und schreibt sie nach `doubletten` (beide Richtungen, damit
jeder Eintrag seine Gegenstücke findet). Stand 18.8.2026: **314 Paare**, 299
davon mit tagesgleichem Geburtsdatum.

Ohne das passiert zweierlei, beides still:

- **Doppelte Items.** Zwei Einträge derselben Person, beide als „keine Person
  in FactGrid" entschieden, ergeben zwei `CREATE` — zwei Items für einen
  Menschen. Der Export verhindert das nicht, aber er **sagt** es: eine
  `# ACHTUNG`-Zeile vor dem betroffenen `CREATE` und eine Zählung im Kopf
  (`doppelte_neuanlagen()` in `quickstatements.py`). Welche der beiden Zeilen
  das Item anlegt, ist eine Entscheidung und keine Rechnung.
- **Verschenkte Handarbeit.** Ordner 2 bis 5 sind vollständig entschieden.
  Steht dieselbe Person in Ordner 6 oder 7, ist ihre Q-ID längst gefunden —
  die Seite zeigt sie an und bietet „Q-ID übernehmen" (`quelle='doublette'`
  im Protokoll).

Gerechnet wird mit derselben Unschärfe wie gegen FactGrid (`app/match.py`),
aber mit drei eigenen Regeln. Alle drei stammen aus echten Fehlalarmen und
stehen als Testfälle in `build/test_doubletten.py`:

- **Die Adresse zählt nicht mit.** Zwischen 1928 und 1933 sind Menschen
  umgezogen: Karl Thomas steht 1928 im Bäckerstieg 4 und 1933 in der Feldstraße
  21a. Wer die Adresse mitzählte, verlöre genau die Fälle, die er sucht.
- **Verschiedenes Geschlecht schließt aus.** Louis und Louise Winter wohnen
  beide in der Vorderbreite 23 und tragen dasselbe Geburtsdatum — ein Ehepaar.
  Weil das Geschlecht geschätzt ist, schließt es nur aus, wenn es auf **beiden**
  Seiten bekannt ist und sich widerspricht.
- **Der Vorname muss mitreden, das Datum genau passen.** Ohne den Vornamen
  genügten Nachname und Geburtstag — und das sind Zwillinge (Georg und Herbert
  Teuter, Friedrichstraße 34, beide \*8.5.1906). Und weicht der Tag ab, muss
  der Name ohne Abstriche passen, sonst wird aus „Marta Köhler" und „Herta
  Köthe" eine Person. Beim Datum zählt nur, was sich mit **einer** verlesenen
  Zahl erklären lässt: der Tag bis zu 16 Tage daneben (`MAX_TAGESVERSATZ`), der
  Monat nur bei gleichem Tag, das Jahr nur bei gleichem Tag und Monat. Weichen
  **zwei** Stellen ab, sind es zwei Menschen: Karl Schulze, \*4.8.1897 in
  Ordner 2, und Karl Schulze, \*17.7.1898 in Ordner 3 — und ebenso die beiden
  Selma Fischer in Ordner 7 (`7-0466` \*21.10., `7-1188` \*30.9.1884). Bis zum
  18.8.2026 galt hier die volle Monatstoleranz aus `datum_widerspruch()`; die
  ist gegen FactGrid richtig, weil sie dort **ausschließt**, und hier falsch,
  weil sie Hinweise **erzeugt**. Sie hat zwei bestätigte Fehlalarme produziert
  (siehe `korrekturen.md`).

Entschieden wird dabei nichts. `doubletten` ist ein Hinweis; die Übernahme
einer Q-ID bleibt ein Klick von Hand und landet im Protokoll.

## Was schon in FactGrid steht, sagt FactGrid selbst

Der Abgleich rät über Namen und Daten. Die importierten Personen tragen
dagegen eine **Angabe**: `P51` nennt das Archivale des Ordners, `P499` die
laufende Nummer in der Akte. Daraus wird die Zuordnung Registereintrag → Q-ID
exakt statt unscharf. `build/p51_bericht.py` zieht sie aus dem Dump und
schreibt `data/p51-zuordnung.csv`; geändert wird dabei **nichts**.

Zwei Dinge hat sie am 17.8.2026 zutage gefördert:

- **5.006 Einträge der Ordner 2 bis 4 stehen auf „keine Person in FactGrid",
  obwohl ihr Item existiert.** Die Entscheidung stimmte, als sie getroffen
  wurde; seither ist der Export gelaufen. Wer ihn heute wiederholt, legt jede
  dieser Personen ein zweites Mal an. Die Doubletten-Warnung greift dort
  nicht — die erkennt zwei *Registereinträge* derselben Person, nicht einen
  Eintrag, dessen Item schon da ist. Umgestellt wurde bewusst nichts: das sind
  5.006 Entscheidungen von Hand.
- **Nr. 1031, Hedwig Bendix**, ist von Hand `Q878146` zugeordnet. Dieses Item
  ist inzwischen eine **Weiterleitung** auf `Q982860` — die beiden wurden in
  FactGrid zusammengeführt. Die einzige der 73 Zuordnungen, deren Q-ID im
  aktuellen Auszug fehlt. Ein Grund, `nicht_in_factgrid` und
  `zugeordnet_abweichend` im Bericht ernst zu nehmen: dahinter steckt kein
  Fehler des Abgleichs, sondern eine Veränderung an FactGrid.

Der Bericht taugt außerdem als **Prüfung des Abgleichs**: gegen diese 5.079
belegten Zuordnungen liegt der Top-Vorschlag in 5.078 Fällen richtig und in
keinem falsch. Die einzige Lücke ist Nr. 1117 (Margarete Hirschfeld), die der
harte Datumsausschluss verwirft — siehe oben.

## Wichtige Pfade

- `app/server.py` — API + die eine Seite
- `app/match.py` — Abgleich: vier unscharfe Kriterien, ein Score, **ein**
  harter Ausschluss (widersprüchliches Geburtsdatum, siehe unten)
- `app/quickstatements.py` — Export nach dem Muster von Q1257714
- `data/register.sqlite` — Register, Kandidaten, Entscheidungen, Einstellungen
- `wahlregister 2 - register2_new.csv` — Ordner 2. Achtung: **zwei Spalten
  ohne Überschrift** — vorn die laufende Nummer (`lfd_id`, daran hängen die
  Entscheidungen), hinter „Adresse" das FactGrid-Adressitem. `csv.DictReader`
  legt beide auf denselben Schlüssel und verliert die laufende Nummer; deshalb
  benennt `build_register.py` namenlose Spalten nach ihrer Position.
- `wahlregister  - register3.csv` — Ordner 3 (zwei Leerzeichen im Namen).
  Andere Tabelle: benannte Spalten, Datum `25.10.76`, Vermerke `1`/`0`,
  **sechs** Wahlspalten `sp4…sp9`, dazu `quelle` mit dem Blatt der Fotografie.
- `wahlregister_register4_korrigiert.csv` — Ordner 4, dasselbe Format wie
  Ordner 3 mit zwei Abweichungen: die Q-ID-Spalte heißt „Wohnung QID", und die
  Adresse schreibt die Hausnummer ohne Leerzeichen an die Straße
  („Eislebenerstr.7a"). Dieselbe Straße kommt in bis zu fünf Schreibweisen vor;
  dass es dieselbe ist, ist nicht geraten, sondern steht in der Quelle — die
  Varianten tragen für dasselbe Haus dieselbe Q-ID. `STREET_MAP` legt sie
  zusammen, `split_address()` trennt die Hausnummer ab.
- `wahlregister_register5_korrigiert.csv` — Ordner 5, wie Ordner 4; die
  Q-ID-Spalte heißt hier „wohnung qid" (klein). Deshalb sucht `_qid_spalte()`
  ohne Rücksicht auf Groß- und Kleinschreibung. Neu ist der Hausnummern­bereich
  ohne jede Lücke („Ritterstr.9/10").
- `wahlregister_register6_korrigiert.csv` — Ordner 6 (12.11.1933). **Anderes
  Format**: Familienname in `zuname`, Straße und Hausnummer **getrennt**, eine
  einzige Spalte `stimmabgabe` mit ✓/X/leer — und 43-mal `St.`
- `wahlregister_register7_korrigiert.csv` — Ordner 7 (**1928**). Wie Ordner 6,
  aber `name` statt `zuname`, `hausnummer` statt `hausnr`, `1`/`0` statt ✓/X —
  und **ohne Geburtsnamen**. Bei verheirateten Frauen fehlt damit das stärkste
  Merkmal für das Geschlecht und der Klammerzusatz im Label; geschätzt wird
  dort allein über die Vornamensliste (1.382 von 1.447).
- `build/link_doubletten.py` — findet denselben Menschen in mehreren Ordnern
- `regeln.md` — wie der Score zustande kommt; erst hier ändern, dann im Code

## Server

Die App läuft **öffentlich** als systemd-Dienst. Der Dienst selbst lauscht auf
Port 8770; nach außen steht er zweimal: über
`https://wahlregister.grid-creators.com/` hinter dem nginx-proxy-manager, und
weiterhin unverschlüsselt unter `http://185.162.251.195:8770/` am Proxy vorbei.
Wer TLS erzwingen will, schließt den Port nach außen — die Adresse mit dem Port
steht aber in Notizen und Lesezeichen, sie fällt also nicht lautlos weg.

Nicht mit `nohup` daneben starten — der Port ist belegt, und der Dienst startet
sich nach `kill` selbst neu:

```bash
systemctl restart wahlregister     # nach Änderungen an server.py / match.py
journalctl -u wahlregister -n 50
```

## Kein Rechtesystem — Absicht, kein Versäumnis

Die App ist offen: `POST /api/entscheidung`, `/api/sammelentscheidung` und
`/api/einstellungen` prüfen **nichts**, und der Export ist frei abrufbar. Das
ist so gewollt und war vorher anders (Kurator-Token) — die Mechanik wurde
bewusst wieder ausgebaut. Nicht ohne Auftrag wieder einbauen.

Als Ausgleich gibt es das **Änderungsprotokoll**: `protokoll` hält jede
Änderung an `entscheidungen` fest, mit dem Stand davor. Wer einen schreibenden
Pfad ergänzt, ruft `_protokollieren()` mit auf — sonst entsteht eine Lücke, die
später niemand mehr schließen kann. Das Feld `bearbeiter` ist eine freiwillige
Angabe aus dem Browser, keine Identität; leer ist erlaubt.

Sammelentscheidungen tragen eine Stapelkennung (Zeit **plus Zufallssuffix** —
ohne den bekämen zwei Läufe in derselben Sekunde dieselbe Kennung, und eine
Rücknahme träfe beide). `POST /api/stapel-zuruecknehmen` setzt nur zurück, was
seither unverändert und mit `quelle='sammel'` markiert ist.

## Jede Entscheidung muss möglich bleiben

Der Abgleich schlägt nur für einen kleinen Teil der Einträge etwas vor (in
Ordner 2 für 318 von 1.669). Seit Ordner 6 und 7 kommt eine zweite Quelle
hinzu: das eigene Register (siehe „Der Abgleich hat zwei Richtungen"). Deshalb
hängt
die Entscheidbarkeit **nicht** an den Vorschlägen: freie Suche
(`/api/suche`), Q-ID von Hand (`/api/person/<qid>` zur Kontrolle) und die
Sammelentscheidung (`/api/sammelentscheidung`) gehören zum Kern, nicht zur
Kür. Wer an der Liste arbeitet, darf nie in eine Lage geraten, in der ein
Eintrag nicht entschieden werden kann.

Zwei Regeln dazu:

- Eine Q-ID, die im Peru-Auszug fehlt, wird **nicht** abgewiesen — der Auszug
  ist ein Abzug, FactGrid ist weiter. Stattdessen Hinweis in der UI.
- Die Sammelentscheidung fasst nur `d.status IS NULL` an. Handarbeit darf ein
  Klick nicht überschreiben.

## Der eine harte Ausschluss: das Geburtsdatum

Seit dem 12.8.2026 wirft der Abgleich einen Kandidaten weg, wenn **beide
Seiten** ein tagesgenaues Geburtsdatum führen und die beiden **mehr als einen
Monat** auseinanderliegen (`datum_widerspruch()`, Grenze `DATUM_TOLERANZ_TAGE
= 31`). Das ist der einzige Punkt, an dem der Abgleich etwas ausschließt statt
zu bewerten — davor gab es keinen, und das steht so auch in `regeln.md`.

Der Grund, weggeworfen statt abgewertet: Nachname und Vorname zusammen ergeben
50, dieselbe Adresse noch einmal 15. Ein Namensvetter im selben Haus stünde
sonst mit 65 Punkten ganz oben, obwohl sein Geburtsdatum ihn ausschließt.

Was die Regel **nicht** anfasst — und nicht anfassen darf:

- **Entscheidungen von Hand.** Sie stehen in `entscheidungen` und bleiben.
  Eine davon widerspricht der Regel: Ordner 2, Nr. `1117` (Margarete
  Hirschfeld, \*15.10.1868 → `Q878136`, \*15.10.1867 — gleicher Tag, gleicher
  Monat, ein Jahr daneben). Das ist Handarbeit vom 5.8.2026 und keine
  Aufräumaufgabe für ein Skript.
- **Die freie Suche und die Q-ID von Hand.** Wer eine Q-ID einträgt, wird nicht
  abgewiesen — sonst wäre ein Eintrag nicht mehr entscheidbar.
- **Ungenaue Daten.** Ein nur jahres- oder monatsgenaues FactGrid-Datum ist
  eine fehlende Angabe, kein Widerspruch.

## Datenbank

Eine Datei, drei Lebensdauern:

- `entries` / `entries_fts` — von `build_register.py` neu angelegt, aus **allen**
  Ordnern in `QUELLEN` auf einmal
- `adress_items` — von `link_addresses.py` neu angelegt, aus der Q-ID-Spalte
  derselben CSVs (`meta.quelle_o<N>` verbindet beide, damit sie nicht
  auseinanderlaufen). Erst `build_register.py`, dann `link_addresses.py`.
- `kandidaten` — von `match_factgrid.py` geleert und neu befüllt. Gelöscht wird
  erst **am Ende**, nach dem Rechnen: die DB läuft im Rollback-Journal, und ein
  Löschen zu Beginn sperrte die öffentliche App über die ganze Laufzeit.
- `doubletten` — von `link_doubletten.py` neu angelegt. Braucht weder Peru noch
  Netz und läuft in Sekunden; nach jedem `build_register.py` neu.
- `entscheidungen` / `p120` / `einstellungen` — **Handarbeit, überleben alles**.
  Nie in einem Build-Skript droppen. Sie hängen an `lfd_id`, nicht an einer
  rowid.

`p120` hält die Vormerkung „Möglicherweise identisch mit" (P120): eine Q-ID,
die passen könnte, ohne dass die Zuordnung sicher wäre. Sie steht **neben** der
Entscheidung, nicht in ihr — der häufige Fall ist `kein_treffer` (neues Item)
plus ein Verdacht. `POST /api/p120` schreibt sie, leere Q-ID löscht, und
`_protokollieren()` läuft mit (`aktion='p120'`).

## Der FactGrid-Auszug

`app/match.py` öffnet `persons.sqlite` über `PERU_DB` mit `mode=ro`. Kein
Schreiben, **kein Netzaufruf** — anders als peru selbst, das live gegen
FactGrid geht. Abgeglichen wird also immer gegen einen **Abzug**, nie gegen
die lebende Instanz. Wie alt er ist, entscheidet mit, was der Abgleich finden
kann.

**Seit dem 17.8.2026 baut dieses Projekt seinen Auszug selbst**
(`build/peru_auszug.py` → `data/persons.sqlite`), und der systemd-Dienst zeigt
mit `Environment=PERU_DB=…` darauf. Der Grund ist ein Fehler, der beinahe
passiert wäre: Der Auszug des Nachbarprojekts stammte aus einem Rohdump vom
**20. Juli** und kannte deshalb keine der **5.006 Personen**, die aus den
Ordnern 2 bis 4 inzwischen nach FactGrid importiert worden sind (1.590 →
6.596 „Wahlteilnehmer in Aschersleben"). Ein Abgleich der Ordner 5 bis 7
gegen diesen Stand hätte tausende Menschen als „nicht in FactGrid" ausgewiesen,
die längst dort stehen — und beim Import Dubletten erzeugt. Mit dem Dump vom
17.8. findet der Abgleich sie mit Score 87–90.

Gebaut wird mit **peru's** `build_index.py`, importiert statt kopiert: ein
zweiter Parser liefe über kurz oder lang auseinander, und das Schema muss zu
dem passen, was `match.py` erwartet. Peru's eigene Datei bleibt unangetastet —
sein `build_index.py` legt das Ziel neu an (`DST.unlink()`) und risse dabei
`dup_pairs`, `dup_clusters`, `custom_rules` und die Verifikationsdaten mit.

Die Quellen liegen in `/srv/apps/fg2marc21/data/` und werden dort
tagesaktuell gehalten: `subset_P2_Q7.json` (Personen), `dump.json.gz` (alles).
Die Beschriftungen kommen aus beiden — `subset_referenced_labels.json` deckt
die Namensitems zu 99,5 % ab, bei den **Wohnorten** aber nur ein knappes
Drittel, und gerade die tragen die Straßennamen der Liste. Was fehlt, holt
`labels_nachziehen()` aus dem Volldump. Alles offline; peru's
`resolve_labels.py` fragt dafür die API einzeln ab und braucht Stunden.

Ein neuer Dump ist damit:

```bash
python3 build/peru_auszug.py        # ~3 min, schreibt data/persons.sqlite
python3 build/link_addresses.py     # Labels und Bewohnerzahlen neu
python3 build/match_factgrid.py     # der lange Lauf
```

Drei Dinge aus dieser DB tragen den Abgleich:

- `person_qref.kind = 'residence'` sagt, welche FactGrid-Personen an einem
  Adressitem hängen (`Aschersleben, Breite Straße 22 …`). Daran hängt das
  Adress-Kriterium und der P208-Export. **Welches Item zu welcher
  Registeradresse gehört, kommt seit dem 7.8.2026 aus der Quell-CSV** und wird
  nicht mehr über Label-Vergleiche geraten — siehe `link_addresses.py`.

  Das ist keine Bequemlichkeit: das Register nennt die Straße **von 1933**, das
  FactGrid-Item trägt den **heutigen** Namen, und dazwischen liegen Umbenennungen.
  „Bestehornstr. 1–6" des Registers ist die heutige *Heckner*straße (1949
  Poststraße, 1998 Hecknerstraße; die Nr. 6 ist das Bestehornhaus). Die heutige
  Bestehornstraße heißt erst seit 1991 so und liegt 80 m weiter östlich — ihr Item
  `Q1783881 = „Aschersleben, Bestehornstraße 2"` sieht wie der richtige Treffer aus
  und ist der falsche. Ebenso „Wilhelmsplatz" → Realschulplatz bzw.
  Dr.-Wilhelm-Külz-Platz. Wer die Zuordnung wieder über Labels raten lässt, baut
  genau diese Fehler ein.

  Wie viel dieses Kriterium trägt, hängt am Ordner — und am Alter des Auszugs.
  Mit dem Stand vom 17.8.2026 kennt er **alle** Adressitems der Ordner 2, 3
  und 4 (vorher fehlten 29, 213 und 127): dort wohnen jetzt die eigenen
  Importe. Für die neuen Ordner ändert der frische Dump dagegen fast nichts —
  unbekannt bleiben 10 der 190 Adressen von Ordner 5, **163 der 177** von
  Ordner 6 und **105 der 204** von Ordner 7. Die Feldstraße, die Stephanstraße
  und der Zollberg sind in FactGrid unbesiedelt; in Ordner 6 trägt die Adresse
  also so gut wie nichts bei, und der Abgleich hängt dort an Name und Datum.
  Der Export ist davon unberührt: die Q-ID kommt aus der CSV, nicht aus dem
  Auszug.
- der Index Geburtsdatum → Person in `Matcher.bdate_index()` findet Personen,
  deren Name ganz anders geschrieben ist.
- `person_qref.kind IN ('family', 'given')` sind die Namensitems (P247 für den
  Familiennamen). `Matcher._namen()` vergleicht sie mit, weil das Label nur
  *eine* Schreibweise ist: `Q1351615` heißt „Richard Borstell", das
  Familiennamen-Item dazu ist `Q1193189 = "Borstel"`.

## Regeln ändern

Erst `regeln.md`, dann `app/match.py`. Danach:

```bash
python3 build/match_factgrid.py       # ~7 h für alle sieben Ordner, rechnet alles neu
python3 build/test_register.py        # Einlesen aller Tabellenformate
python3 build/test_match.py
python3 build/test_doubletten.py      # derselbe Mensch in mehreren Ordnern
python3 build/test_quickstatements.py
python3 build/test_against_app.py     # gegen den laufenden Server — SCHREIBT!
```

Und nach jeder Änderung am Register — nicht nur an den Regeln:

```bash
python3 build/build_register.py       # entries neu aus allen QUELLEN
python3 build/link_addresses.py       # dann die Adressitems
python3 build/link_doubletten.py      # dann die Doubletten (Sekunden)
```

**Vorher `data/register.sqlite` sichern.** `test_against_app.py` läuft gegen
den produktiven Dienst und geht durch dieselben offenen Schreibpfade wie jeder
Browser: es entscheidet, sammelentscheidet und nimmt zurück.

Bis zum 7.8.2026 setzte die Aufräumzeile am Ende *alle* entschiedenen Einträge
der Teststraße auf `offen` — auch die, die schon vorher von Hand entschieden
waren. So ging die Entscheidung zu `0011` zweimal verloren. Der Test merkt sich
jetzt mit `stand_von()` den Stand vor dem Lauf und stellt ihn mit
`herstellen()` wieder her; er nimmt nur noch zurück, was er selbst gesetzt hat.
Wer dort neue Fälle ergänzt, hält sich daran — sonst löscht ein Testlauf wieder
Handarbeit.

Die Fälle in `test_match.py` sind echte Beispiele aus den Daten (Tippfehler im
Geburtsnamen, abgekürzter Vorname, Lotte↔Lotti, widersprüchlicher Geburtstag).
Wer sie löscht, verliert die Absicherung dafür, dass die Unschärfe in beide
Richtungen funktioniert.

**Die Ordner 2, 3 und 4 sind vollständig entschieden** (Stand 17.8.2026: 5.080
Entscheidungen, kein offener Eintrag; 73 zugeordnet, der Rest Neuanlage).
`test_against_app.py` kann sich seine Testfälle deshalb nicht mehr suchen:
`freiraeumen()` merkt sich eine ganze Straße, setzt sie auf `offen` und stellt
sie ganz unten wieder her. Wer dort eine Straße ergänzt, nimmt sie in dieselbe
Schleife mit auf — auch die aus Ordner 3 (`Salzkoth`).

**Der Test schreibt in den produktiven Bestand.** `freiraeumen('Salzkoth')`
setzt eine ganze Straße auf `offen` und stellt am Ende den Stand wieder her,
den sie **beim Start des Laufs** hatte. Entscheidet jemand in genau diesem
Fenster einen Eintrag dieser Straße, ist seine Arbeit hinterher weg — dieselbe
Falle wie am 7.8.2026, nur durch Gleichzeitigkeit statt durch die Aufräumzeile.
Solange an einem Ordner gearbeitet wird: den Test nicht nebenher laufen lassen,
und vorher `data/register.sqlite` sichern. Das gilt jetzt für die Ordner 5, 6
und 7.

**Ordner 4 ist seit dem 12.8.2026 da**, Ordner **5, 6 und 7 seit dem
17.8.2026** — zusammen 4.709 Einträge ohne eine einzige Entscheidung. Der
E2E-Test fasst sie nicht an; wer dort eine Teststraße ergänzt, nimmt sie in
dieselbe Schleife auf wie `Salzkoth`.

Der E2E-Test prüft seit dem 17.8.2026 die **Mechanik** der Ordner statt ihrer
Zahlen (vorher stand dort fest `[2, 3]`, was schon mit Ordner 4 nicht mehr
stimmte). Ein neuer Ordner soll durch den Test laufen, nicht ihn brechen.

`build/test_register.py` prüft das Einlesen ohne Datenbank. Zwei Fälle darin
sind wichtiger, als sie aussehen:

- **Das Jahrhundert der zweistelligen Jahre.** Ordner 3 bis 7 schreiben
  `25.10.76`. Aufgelöst wird über das Wahlalter — wer wählen durfte, war
  mindestens 20 —, aber **nicht** über das Wahlalter allein. Bis zum 17.8.2026
  galt schlicht „ab `'14` ist es das 19. Jahrhundert"; mit Ordner 6 wurde das
  falsch. Dort steht unter Nr. 369 ein Kurt Hering, \*25.5.14, durchgestrichen,
  mit dem Vermerk „noch nicht wahlfähig". Die alte Regel hätte daraus lautlos
  einen 119-Jährigen gemacht. Jetzt werden beide Lesarten abgewogen: zu jung
  zum Wählen kommt vor (der Eintrag wurde ja gestrichen), über hundert nicht
  (`MAX_ALTER`). Und der Stichtag gehört dazu, weil Ordner 7 zu 1928 gehört.
  Der Test prüft nur, **wo geraten wird**, und lässt zu junge Jahrgänge nur
  dort durch, wo die Quelle den Eintrag selbst zurücknimmt. Vierstellige
  Angaben werden nie angezweifelt: Ordner 2 führt mit Nr. 1662 („Nachtrag",
  \*1915) einen, der 1933 erst 18 war — ein Befund der Akte, kein Lesefehler.
- **`0` heißt leer, nicht unlesbar.** Ordner 3, 4, 5 und 7 schreiben `1`/`0`,
  wo Ordner 2 und 6 `✓`/`X` und das leere Feld setzen. Fiele `0` unter
  „unklar", wäre der Unterschied zwischen „nicht teilgenommen" und „nicht
  lesbar" dahin.
- **Ein Komma in der Bemerkung frisst das Blatt.** In 19 Zeilen (12 in Ordner
  5, 3 in Ordner 6, 4 in Ordner 7) enthält die Bemerkung ein Komma und steht
  ohne Anführungszeichen — die zweite Hälfte landet dann in der Spalte, wo
  sonst das Blatt der Fotografie steht. `blatt()` setzt sie wieder zusammen.
  Ohne das ginge ein halber Satz verloren und ein Bildname entstünde, den es
  nie gab.

## QuickStatements

Das Modell steht in `app/quickstatements.py` im Docstring und folgt Q1257714.

Die Primärquelle steht **je Ordner**, weil jeder ein eigenes Archivale ist
(siehe die Tabelle oben). Der Schlüssel heißt `qs_quelle_o<N>` und steht in
`QS_DEFAULTS` (`app/schema.py`); `quickstatements.py` sucht ihn über
`entries.ordner`. Ein Ordner ohne hinterlegtes Item bekommt **kein** P51 statt
eines falschen, und die Seite weist im Export-Block darauf hin. (Vor Ordner 3
gab es nur `qs_quelle`; davor stand dort `Q1214165`, Ordner 1, weil es zu
Ordner 2 noch kein Item gab.)

**Auch die Wahl steht je Ordner** — seit Ordner 6 und 7, die nicht zur Wahl vom
5.3.1933 gehören. `wahlspalten(ordner)` in `app/schema.py` sagt, welche Spalte
welche Wahl meint, `wahljahr(ordner)` gibt das Jahr für P106 und die
Beschreibung. Wer eine Wahl fest im Code verdrahtet, hängt sie allen sieben
Ordnern an.

Ein neuer Ordner braucht seinen Schlüssel **in `QS_DEFAULTS`**, sonst weist
`POST /api/einstellungen` ihn als unbekannt ab — die Seite kann ihn dann nicht
setzen. Bringt er eine eigene Wahl mit, kommt er zusätzlich in
`WAHLSPALTEN_ORDNER`, und gehört er zu einem anderen Jahr, in
`WAHLJAHR_ORDNER`.

Alles davon ist über `einstellungen` änderbar. Nicht raten und fest verdrahten.

### Zusammenführen ist ein Schalter, kein Verhalten

`bauen(..., zusammenfuehren=True)` legt für eine Gruppe von Doubletten **ein**
Item an statt eines je Registereintrag. Der Schalter ist seit dem 18.8.2026 da,
und er ist **aus**, wo nicht ausdrücklich anders verlangt: die App exportiert
weiter einen Ordner und warnt nur. Beides steht nebeneinander, weil die Frage,
welche Zeile das Item anlegt, eine Entscheidung ist — mit dem Schalter ist sie
beantwortet, und zwar so:

- Es führt die **reichste Namensform** (`_fuehrend()`): Geburtsname schlägt
  alles, dann der ausgeschriebene Vorname vor der Abkürzung, dann der längere
  Name; Ordner und laufende Nummer entscheiden nur noch den Gleichstand, damit
  dieselbe Eingabe dieselbe Tabelle ergibt. Weil Ordner 7 keine Geburtsnamen
  führt, gewinnt bei 6↔7 fast immer Ordner 6.
- Die Gruppe wird **transitiv** geschlossen (`gruppen()`). Walter Kneucker
  steht in den Ordnern 5, 6 und 7 — drei Einträge, ein Item.
- Am Item steht **jede** Fundstelle: P51/P499 kommt von jedem beteiligten
  Eintrag, sonst wäre nicht mehr nachvollziehbar, worauf es beruht. Ebenso
  bleiben beide Adressen und alle Wahlen; wortgleiche Aussagen fallen weg.
  Mensch, Geburtsdatum, Geschlecht und Titel sagt nur der Anleger.
- Die abweichenden Schreibweisen werden **Alias** (`Ade`) — „Marie Both" am
  Item „Maria Roth (geb. Haase)". Die Beschreibung nennt beide Wahljahre
  („1928 und 1933 Wahlteilnehmer"), sonst behauptete sie die halbe Wahrheit.

`build/export_quickstatements.py 5,6,7 --zusammenfuehren` erzeugt die Tabelle
über mehrere Ordner; die App kann das nicht und soll es nicht können. Ohne den
Schalter verhält sich das Skript wie die App, nur über mehrere Ordner.

### Die drei Wahlspalten sind drei Wahlen

Das gilt für die Ordner **2 bis 5**. `sp4` / `sp5` / `sp8` sind dort nicht eine
Wahl in drei Schreibweisen, sondern drei Wahlen. So steht es schon bei den
Personen aus **Ordner 1** in FactGrid:

| Item | Ordner 1 | Spalte | Vermerke hier |
|---|---|---|---|
| `Q1207285` Deutsche Reichstagswahl 5.3.1933 | 1460 | 4 (✓) | 1474 |
| `Q1214187` Stadtverordnetenversammlung Aschersleben | 1362 | 5 (X) | 1411 |
| `Q1214186` Provinziallandtag der Provinz Sachsen | 1337 | 8 (X) | 1369 |

Die Reihenfolge der Häufigkeiten stimmt überein; daraus ist die Zuordnung
erschlossen, **nicht** aus der Akte belegt. Wer sie ändert, ändert
`qs_wahl_sp4/sp5/sp8` in den Einstellungen, nicht den Code.

Ordner 3, 4 und 5 erfassen zusätzlich die Aktenspalten **6, 7 und 9**. Dort
steht in keiner ihrer 5.015 Zeilen ein Vermerk. Sie stehen trotzdem in `entries`
(`sp6`, `sp7`, `sp9`) — die Quelle hat sie geprüft, und „geprüft und leer" ist
eine Angabe. Exportiert wird nichts daraus: welche Wahl sie meinen, weiß
niemand. Taucht dort doch einmal ein Vermerk auf, zeigt ihn die Seite als
„Spalte N" ohne Wahlnamen an, damit er nicht unbemerkt liegen bleibt.

**Ordner 6 und 7 haben nur eine Spalte.** Sie heißt `spst`, und welche Wahl sie
meint, muss nicht erschlossen werden — es steht im Archivale. In Ordner 7 sind
es zwei Wahlen an einer Spalte (siehe oben).

**Haken und Kreuz heißen beide „teilgenommen".** Nur das leere Feld heißt
„nicht teilgenommen", und dann entsteht **keine** Aussage — P119 sagt nichts
Negatives. Was `tick()` nicht lesen konnte (`—`, `⍯`), ist `None` und erzeugt
ebenfalls nichts. Bis zum 9.8.2026 hing an *jedem* Eintrag ein `P119 Q1214187`,
auch an den 130 ohne jeden Vermerk.

**Der Stimmschein ist ein dritter Wert.** Ordner 6 vermerkt bei 43 Einträgen
`St.`, von der Quelle selbst aufgelöst („Vermerk 'St.' (Stimmschein)"). Er
steht als `2` in der Spalte (`TICK_STIMMSCHEIN`) und ist weder Teilnahme noch
leeres Feld: der Stimmschein belegt, dass jemand **anderswo** wählen durfte,
nicht dass er gewählt hat. Erfasst und in der Liste sichtbar, im Export keine
P119. Das ist eine Festlegung vom 17.8.2026 und ließe sich umdrehen — dann
zählte `TICK_STIMMSCHEIN` in `quickstatements.py` wie eine `1`.

Die Bemerkung der Akte hängt als `P520` an der **ersten** erzeugten P119. Sie
gilt dem Registereintrag, nicht einer einzelnen Wahl; dreimal derselbe Text
wäre nur Rauschen. Entsteht keine P119, entfällt sie.

Die Rolle `P277 Q1207476` („Subject has role" → Wahlberechtigte(r)) hängt
dagegen an **jeder** P119 — sie sagt etwas über die einzelne Teilnahme, nicht
über den Eintrag. Sie steht als `qs_rolle` in den Einstellungen; leer heißt
kein Qualifikator.

Weiter **nicht** verifiziert und als Warnung in der UI: `Q1214187` und
`Q1214186` datieren beide auf den 5. März 1933, die Bemerkungen dieses
Registers nennen durchweg den 12. März 1933 („am 12.3.33 noch nicht 6 Mon.
Wohnsitz").

### Zwei Labels, ein Unterschied

Neue Personen bekommen `Lde` **und** `Len`. Beide tragen denselben Namen — nur
der Klammerzusatz zum Geburtsnamen wechselt: „(geb. Hahn)" → „(nee Hahn)".
Das steht in `GEB_ZUSATZ` in `app/quickstatements.py`; im FactGrid-Auszug gibt
es dafür keinen Präzedenzfall (7.272 von 318.228 Labels haben überhaupt ein
englisches, bei Personen genau vier, keins mit Klammerzusatz), die Schreibweise
ist also eine Festlegung und keine Übernahme.

**Nur bei der Neuanlage.** Ein zugeordnetes Item bekommt kein Label: `Len`
würde dort ein vorhandenes englisches überschreiben, und ob es eins hat, führt
der Auszug nicht mit. Abschaltbar über `qs_label_en`.

### Akademische Titel gehören nicht ins Label

„Dr." steht im Register vor dem Vornamen (`0292 Fürste, Dr. Kurt`).
`split_titel()` in `build_register.py` löst ihn heraus: `vorname` bleibt roh wie
im Register, `vorname_norm` und damit Label und Namensvergleich sind ihn los,
und die Spalte `titel` hält ihn. Im Export wird daraus `P170 Q22218` („Dr.",
der Titel ohne Fachangabe) — wie `P154` nur bei der Neuanlage, weil der
Peru-Auszug `P170` nicht mitführt und ein Doppel an einem bestehenden Item
nicht auszuschließen wäre.

## Geschätzte Angaben

Das Geschlecht steht nicht in der Quelle (Geburtsname → weiblich, sonst
Vornamensliste in `build_register.py`). In der UI und im CSV ist es als
Schätzung ausgewiesen; im QuickStatements-Export wäre es das nicht mehr,
deshalb ist es dort abschaltbar. Ebenso ist der Ort Aschersleben erschlossen —
aus Straßennamen und FactGrid-Beschreibungen, nicht aus der Quelle.

## Style

- Python: 4 Spaces, Modul-Docstring oben, Funktions-Docstring nur, wenn der
  Name das Verhalten nicht schon sagt.
- Frontend: Plain DOM, kein Framework, kein Build-Step. `style.css` hält die
  Tokens, `seiten.css` das Seiten-Spezifische.
- Keine `requirements.txt` — Standard-Python plus `flask`.
