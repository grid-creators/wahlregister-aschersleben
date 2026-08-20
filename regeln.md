# Wie der Abgleich rechnet

Es gibt **zwei** Abgleiche. Der eine sucht Registereinträge in FactGrid
(`app/match.py`, dieser Text bis „Was der Score nicht ist"), der andere sucht
denselben Menschen an zwei Stellen des Registers selbst
(`build/link_doubletten.py`, eigener Abschnitt weiter unten). Den zweiten gibt
es, seit Ordner 6 und 7 zu anderen Wahlen gehören als 2 bis 5.

Gilt für `app/match.py`. Vier Kriterien, alle unscharf, gewichtet zu einem
Score von 0 bis 100. Was auffällig ist, steht am Kandidaten und wird von Hand
entschieden — mit **einer** Ausnahme, dem Geburtsdatum (siehe unten).

| Kriterium | Gewicht |
|---|---|
| Nachname | 30 |
| Vorname | 20 |
| Geburtsdatum | 35 |
| Adresse | 15 |

Angeboten wird ein Kandidat ab **55 Punkten**. Das ist bewusst so gesetzt:
Nachname und Vorname zusammen ergeben höchstens 50 — ein bloßer Namensgleichklang
genügt also nicht, es muss etwas vom Geburtsdatum oder von der Adresse dazukommen.

## Namen

Verglichen wird kleingeschrieben, ohne Diakritika, ß → ss. Grundlage ist
`difflib.SequenceMatcher`; unter 0,55 Ähnlichkeit zählt ein Wortpaar als „passt
nicht" (das spart zugleich den teuren Vergleich für die große Mehrheit der
Kandidaten).

- **Reihenfolge egal**: jedes Token der Registerseite sucht sich seinen besten
  Partner, gemittelt wird über die Registerseite. „Anna Marie" ↔ „Marie Anna
  Elisabeth" ist damit ein voller Treffer.
- **Initialen**: ein einzelner Buchstabe zählt zu 0,85, wenn der Anfangs­buchstabe
  passt — im Register stehen Vornamen oft nur als „M." oder „B.".
- **Geburtsname**: FactGrid führt verheiratete Frauen als „Selma Schwabe (geb.
  Mikowsky)". Der Klammerzusatz wird abgetrennt und beidseitig verglichen —
  Register-Nachname gegen Item-Nachname *und* gegen den Mädchennamen, und
  umgekehrt. Der beste dieser vier Vergleiche zählt.
- **Titel zählen nicht mit**: „Dr. Kurt" wird schon beim Aufbau in Titel und
  Vornamen zerlegt (`split_titel()` in `build_register.py`). Verglichen wird
  „Kurt"; bliebe das „Dr." stehen, zöge es den Mittelwert über die Tokens der
  Registerseite nach unten.
- **Namensitems statt Label**: FactGrid führt Familienname (P247) und Vorname
  zusätzlich als eigene Items. Sie werden mitverglichen, und der beste Wert
  zählt. Das Label ist nur eine Schreibweise — `Q1351615` heißt „Richard
  Borstell", sein Familiennamen-Item aber `Q1193189 = "Borstel"`, genau wie im
  Register. Mehrere Vornamen-Items je Person („Jacob" *und* „Jakob") werden
  zusammengelegt.

## Geburtsdatum

| Lage | Wert |
|---|---|
| tagesgenau gleich | 1,0 |
| gleicher Monat und gleiches Jahr | 0,75 |
| gleiches Jahr | 0,5 |
| ein Jahr daneben | 0,25 |

Ist das FactGrid-Datum nur jahresgenau, kann es höchstens einen Jahrestreffer
geben — die fehlende Genauigkeit wird nicht als Widerspruch gewertet.

### Der harte Ausschluss

Führen **beide Seiten** Tag und Monat und liegen die Daten **mehr als einen
Monat** auseinander, ist es nicht dieselbe Person. Der Kandidat wird verworfen,
nicht bloß schlechter bewertet: er wird gar nicht erst bewertet, sonst trügen
ihn ein gleicher Name (50) und dieselbe Adresse (15) über die Schwelle von 55,
und ein Namensvetter stünde ganz oben im Vorschlag.

Der Monat Spielraum ist die Unschärfe, die die Quelle verlangt: eine verlesene
Monatsziffer („5." statt „6.") oder eine um eins verrutschte Zahl bleibt
erlaubt, ein anderer Tag im selben Monat ohnehin. Gerechnet wird in Tagen, die
Grenze liegt bei **31** — mehr können zwei Daten desselben Kalendertags in
benachbarten Monaten nicht auseinanderliegen.

Damit verschiebt sich auch die Tabelle oben: die Stufe **„ein Jahr daneben"
(0,25) kann zwischen zwei tagesgenauen Daten nicht mehr vorkommen** — 365 Tage
sind ein Widerspruch. Sie bleibt für die Fälle, in denen eine der beiden Seiten
ungenau ist. Genau dieser Fall ist der praktisch häufigste: gleicher Tag,
gleicher Monat, ein Jahr daneben. Er gilt jetzt als „nicht dieselbe Person".

Die Regel greift nur, wo wirklich zwei genaue Angaben aufeinandertreffen:

- ein FactGrid-Datum ohne Tag oder Monat ist eine **fehlende** Angabe, kein
  Widerspruch — solche Kandidaten bleiben
- ein Registereintrag ohne Geburtsdatum schließt nichts aus
- ein unmögliches Datum (31. Februar) wird übergangen statt beurteilt

`datum_widerspruch()` in `app/match.py`. Der Stapellauf zählt mit, wie viele
Kandidaten die Regel verworfen hat (`datum_ausgeschlossen` in `lauf_meta`).

Was die Regel **nicht** anfasst: Entscheidungen, die von Hand getroffen wurden.
Sie stehen in `entscheidungen` und bleiben, auch wenn der Abgleich denselben
Kandidaten heute nicht mehr vorschlüge. Ebenso bleibt die freie Suche offen —
wer eine Q-ID von Hand einträgt, wird nicht abgewiesen.

## Adresse

FactGrid führt Aschersleben hausnummerngenau als eigene Items
(`Q497980 = "Aschersleben, Breite Straße 22 (alte Hausnummer 190)"`), die bei
Personen als P208 stehen. Welches Item zu welcher Registeradresse gehört, steht
in der Quell-CSV; `build/link_addresses.py` überträgt es — **jede Adresse aller
sechs Ordner, alle 9.786 von 9.789 Personen**. Die drei ohne Item stehen in
Ordner 6 und haben in der Quelle keine brauchbare Wohnung (ein durchgestrichener
Eintrag ohne Adresse, einer ohne Hausnummer).

Die Zuordnung hängt an **Ordner plus Adresse**, nicht an der Adresse allein:
„Liebenwerder Plan 20" steht in Ordner 2 und in Ordner 3, und die beiden nennen
dafür verschiedene Items (`Q498464` bzw. `Q2082248`). Es ist der einzige solche
Widerspruch im Bestand — dort, wo Ordner 6 und 7 sich 44 Adressitems teilen,
stimmen sie überein.

Stand des Auszugs vom 17.8.2026:

| Ordner | Adressen | dem Auszug unbekannt | nutzbar |
|---|---|---|---|
| 2 | 230 | 0 | 230 |
| 3 | 243 | 0 | 243 |
| 4 | 235 | 0 | 235 |
| 5 | 190 | 10 | 180 |
| 6 | 177 | 163 | 14 |
| 7 | 204 | 105 | 99 |

Was der Auszug nicht kennt (FactGrid ist weiter als der Abzug), steht in
`adress_items` ohne Label und trägt zum Score nichts bei, weil dort keine
Personen hängen. Bei den Ordnern 2 bis 4 ist diese Lücke geschlossen, seit
ihre eigenen Neuanlagen in FactGrid stehen — vorher fehlten dort 29, 213 und
127 Adressen. **In Ordner 6 und 7 ist die Lücke die Regel, nicht die
Ausnahme**: die Häuser der Feldstraße, der Stephanstraße und des Zollbergs
sind in FactGrid neu, und das Adress-Kriterium hilft dort kaum. Der Abgleich
hängt dort an Name und Geburtsdatum.

Für den Export macht all das keinen Unterschied — die Q-ID kommt aus der
Quell-CSV, nicht aus dem Auszug.

| Lage | Wert |
|---|---|
| gleiches Adress-Item | 1,0 |
| anderes Haus derselben Straße | 0,6 |
| Wohnort Aschersleben (Q80706) | 0,3 |

## Kandidatensuche

Drei unabhängige Zugänge, damit ein Fehler in *einem* Feld nicht den ganzen
Treffer kostet:

1. Volltextindex über Nachname und Geburtsname — je Token exakt **und** als
   Präfix, damit „Borstel" auch „Borstell" findet. Der Präfix ergänzt, er
   verdrängt nichts: bei häufigen Tokens greift eine Obergrenze je Abfrage,
   deshalb läuft die exakte Suche zuerst. Umgekehrt hilft er nicht — steht im
   Register der längere Name, findet er den kürzeren im FactGrid nicht.
2. alle Personen, die an derselben Adresse (oder in derselben Straße) wohnen
3. alle Personen mit exakt demselben Geburtsdatum

Zugang 3 findet auch Personen, deren Name im FactGrid ganz anders geschrieben
ist. Er läuft über einen einmal aufgebauten Index Geburtsdatum → Person (~1 s).

## Der zweite Abgleich: Register gegen Register

Gilt für `build/link_doubletten.py`. Seit Ordner 6 (12.11.1933) und Ordner 7
(20.5.1928) gehören nicht mehr alle Ordner zur selben Wahl, und derselbe Mensch
steht mehrfach im Register. Gesucht wird er mit denselben unscharfen Bausteinen
wie oben, aber mit eigenen Gewichten und eigenen Ausschlüssen.

| Kriterium | Gewicht |
|---|---|
| Nachname | 40 |
| Vorname | 25 |
| Geburtsdatum | 35 |

Ein Paar gilt ab **70 Punkten** als Hinweis, ab **90** als sicher. Die 15
Punkte, die gegen FactGrid an die Adresse gehen, liegen hier beim Nachnamen —
denn:

**Die Adresse zählt nicht mit.** Zwischen 1928 und 1933 liegen fünf Jahre, in
denen Menschen umgezogen sind. Karl Thomas steht 1928 im Bäckerstieg 4 und 1933
in der Feldstraße 21a. Wer die Adresse mitzählte, verlöre genau die Fälle, die
er finden soll. Sie steht nur im Hinweistext, damit sie beim Ansehen hilft.

**Das Geburtsdatum wird anders gemessen als gegen FactGrid.** Dort kann eine
Seite jahres- oder monatsgenau sein; hier führen beide Seiten den Tag,
abgeschrieben von derselben Verwaltung im Abstand weniger Jahre.

| Lage | Wert |
|---|---|
| tagesgenau gleich | 1,0 |
| gleicher Tag, Monat daneben | 0,6 |
| gleicher Tag im Nachbarjahr | 0,6 |
| bis zu 16 Tage auseinander | 0,6 |
| alles andere | 0 (kein Paar) |

Gemeint ist mit allen drei Toleranzen **eine** verlesene Zahl — nicht ein
beliebiger Abstand. Otto Herrmann steht im Wassertor 14 zweimal, \*21.4.1912
und \*6.4.1912, der zweite als handschriftlicher Nachtrag. Der gleiche Tag im
Nachbarjahr kommt hinzu, weil eine verschriebene Jahreszahl kein zweiter Mensch
ist — so steht es auch in den Entscheidungen von Hand (Margarete Hirschfeld).
Ein *anderer* Tag im Nachbarjahr ist dagegen ein anderer Mensch: Karl Schulze,
\*4.8.1897 in Ordner 2, und Karl Schulze, \*17.7.1898 in Ordner 3, sind zwei.

**Warum nicht die volle Monatstoleranz.** Bis zum 18.8.2026 galt hier schlicht
`datum_widerspruch()` mit seinen 31 Tagen. Gegen FactGrid ist die Zahl
großzügig gewählt, weil sie dort *ausschließt* und ein weggeworfener Kandidat
teuer ist; hier *erzeugt* sie Hinweise, und großzügig heißt dann falsch. Sie
hat zwei Paare zusammengespannt, die von Hand als **zwei Personen** bestätigt
sind: Selma Fischer (`7-0466` ↔ `7-1188`, \*21.10. ↔ \*30.9.1884, Karlstr. 1
und Zollberg 31) und Marta Grabe (`1263` ↔ `5-0028`, \*2.8. ↔ \*1.9.1894, geb.
Stolze bzw. Wollschläger). Bei beiden weichen Tag **und** Monat ab — das ist
keine verlesene Zahl mehr, sondern ein anderer Geburtstag.

Die 16 Tage sind an den Daten abgelesen, nicht gesetzt: unter allen elf Paaren
mit abweichendem Datum ist Otto Herrmann mit 15 Tagen die weiteste echte
Doublette, Selma Fischer mit 21 der engste Fehlalarm. Und die Grenze gilt nur
für den Tag — Ida Hofmann (`5-0822` ↔ `7-1378`, \*10.9. ↔ \*10.8.1895) liegt
31 Tage auseinander und bleibt, weil der Tag derselbe ist und nur der Monat
rutscht. Der Geburtsname taugt für diese Trennung übrigens **nicht**: von den
sechs Paaren mit abweichendem Geburtsnamen sind fünf tagesgleich, also echte
Doubletten mit verlesenem Namen.

### Zwei Ausschlüsse

Beide haben denselben Grund: unter einem Dach wohnen Menschen, die einander
ähnlich heißen.

- **Verschiedenes Geschlecht.** Louis und Louise Winter wohnen in der
  Vorderbreite 23 und tragen dasselbe Geburtsdatum — ein Ehepaar. Weil das
  Geschlecht geschätzt ist, schließt es nur aus, wenn es auf **beiden** Seiten
  bekannt ist und sich widerspricht. (Ordner 7 führt keinen Geburtsnamen, dort
  ist es öfter unbekannt.)
- **Vorname unter der Schwelle.** Ohne den Vornamen genügten Nachname und
  Geburtstag — und das sind Zwillinge: Georg und Herbert Teuter,
  Friedrichstraße 34, beide \*8.5.1906.

Dazu die Bedingung, dass bei abweichendem Tag **beide** Namen ohne Abstriche
passen müssen. Sonst wird aus „Marta Köhler" und „Herta Köthe" eine Person.

### Was daraus folgt — und was nicht

Der Hinweis entscheidet nichts. Er zeigt an, was das Gegenstück ist und wie es
entschieden wurde, und bietet zwei Wege an:

- Ist das Gegenstück einem Item **zugeordnet**, lässt sich die Q-ID mit einem
  Klick übernehmen (`quelle='doublette'` im Protokoll).
- Sind **beide** als „keine Person in FactGrid" entschieden, würden zwei Items
  für einen Menschen entstehen. Der Export schreibt dann eine `# ACHTUNG`-Zeile
  vor das betroffene `CREATE` und zählt die Fälle im Kopf. Er verhindert nichts:
  welche der beiden Zeilen das Item anlegt und welche später daran gehängt wird,
  ist eine Entscheidung und keine Rechnung.

## Was der Score nicht ist

Er ist ein Vorschlag, keine Aussage über Richtigkeit. Entschieden wird von Hand:
ein Kandidat wird gewählt oder es wird festgehalten, dass es in FactGrid keine
solche Person gibt. Nur diese Entscheidungen gehen in den Export.

Auffälligkeiten stehen am Kandidaten, schließen ihn aber nicht aus:

- „† 1928 — vor der Wahl gestorben" (dann ist es fast sicher jemand anderes)
- „kein Geburtsdatum im Item" (dann trägt das stärkste Kriterium nichts bei)
