# Offene Korrekturen aus der Durchsicht

Gesammelt seit dem 18.8.2026. Abgearbeitet wird gebündelt: erst die CSVs
ändern, dann einmal neu bauen (siehe unten). Bis dahin steht hier der Stand.

## Zu ändern in den Quell-CSVs

| Ordner | Nr. | Person | Feld | steht | richtig | Beleg |
|---|---|---|---|---|---|---|
| 7 | 1378 | Ida Hofmann, Zollberg 58 | `geboren_am` | `10.8.95` | `10.9.95` | falsch transkribiert, bestätigt 18.8.2026 |
| 6 | 257 | Margarete Kindler, Baumgartenstr. 29 | `geboren_am` | `9.12.89` | `19.12.89` | falsch transkribiert, bestätigt 18.8.2026 |
| 6 | 1106 | Elisabeth Ustofski, Schützenstr. 1 | `geboren_am` | `10.11.99` | `15.11.99` | falsch transkribiert, bestätigt 18.8.2026 |
| 6 | 149 | Franz Spengler, Bäckerstieg 5 | `geboren_am` | `26.2.72` | `25.2.72` | falsch transkribiert, bestätigt 18.8.2026 |
| 6 | 256 | Ewald Kindler, Baumgartenstr. 29 | `geboren_am` | `8.3.89` | `7.3.89` | falsch transkribiert, bestätigt 18.8.2026 |

Wirkung von Nr. 1378: die Doublette `5-0822` ↔ `7-1378` wird tagesgleich und
steigt von 86 auf 100 — dieselbe Person, die der Abgleich trotz des Lesefehlers
noch gefangen hat. An den Entscheidungen ändert sich nichts, beide Seiten
stehen auf `kein_treffer`.

Wirkung von Nr. 256: die Doublette `4-0056` ↔ `6-0256` wird tagesgleich und
steigt von 86 auf 100. Belegt ist das Datum doppelt, wie bei seiner Frau: durch
Ordner 4 und durch das zugeordnete Item `Q2086818` („*07.03.1889"). Am Export
ändert sich nichts — `6-0256` ist zugeordnet, `P77` geht nur bei der Neuanlage
mit.

### Vier Lesefehler, alle in Ordner 6

Alle vier bestätigten Korrekturen betreffen **Ordner 6**, und in allen vier
Fällen stand die richtige Lesart bereits auf der anderen Seite — in Ordner 4
oder 7, zweimal zusätzlich im schon zugeordneten FactGrid-Item. Wer weitere
Datumsfehler sucht, sucht sie also am ehesten dort. Das Ehepaar Kindler
(`6-0256`/`6-0257`) steht dabei auf **einem** Blatt (`IMG_8827_R`) und war
zweimal falsch; Spengler auf `IMG_8825_L` liegt zwei Aufnahmen daneben.

Aufgefallen sind alle vier über die Doubletten mit kleinem Tagesversatz — die
Gegenprobe-Tabelle unten war die Suchliste. Aus ihr ist damit nur noch Berger
(`0920` ↔ `4-0159`, 10 d) ungeprüft, dazu die beiden Paare innerhalb von
Ordner 4. Was in Ordner 6 kein Gegenstück in einem anderen Ordner hat, fällt
mit dieser Methode nicht auf.

Wirkung von Nr. 149: die Doublette `6-0149` ↔ `7-0028` wird tagesgleich und
steigt von 86 auf 100. Das Paar war ohnehin das bestbelegte der Gegenprobe —
beide Seiten führen den Bäckerstieg 5, eine der fünf Straßen, die sich Ordner 6
und 7 teilen. Beide stehen auf `kein_treffer` und beide durch `sammel`; sie
ergäben zwei Items für einen Menschen, die `# ACHTUNG`-Zeile im Export weist
darauf hin.

Wirkung von Nr. 1106: die Doublette `6-1106` ↔ `7-0651` wird tagesgleich und
steigt von 86 auf 100. Beide Seiten stehen auf `kein_treffer`, das Paar ergäbe
also zwei Items für einen Menschen — gewarnt wird davor aber schon vorher,
denn `doppelte_neuanlagen()` fragt nicht nach dem Score, sondern danach, ob
überhaupt ein Paar in `doubletten` steht. Die Korrektur macht den Hinweis
eindeutig, sie schafft ihn nicht.

Wirkung von Nr. 257: die Doublette `4-0057` ↔ `6-0257` wird tagesgleich. Zwei
Belege dafür, dass 19.12. das richtige Datum ist und nicht 9.12.: Ordner 4
führt Margarete Kindler geb. Schwarz so, und das FactGrid-Item `Q2086819`
(„*19.12.1889") ebenfalls. Am Export ändert die Korrektur nichts — `6-0257`
ist diesem Item bereits zugeordnet, und `P77` geht nur bei der Neuanlage mit.

## Vier Zuordnungen von Hand — erledigt am 18.8.2026

Beim Vorbereiten des Exports der Ordner 5 bis 7 aufgefallen: vier Einträge
standen auf „keine Person in FactGrid", obwohl ihr Doublettenpartner aus
Ordner 3 oder 4 dort längst ein Item hat — über P51/P499 belegt, nicht
geraten. Ein `CREATE` hätte für jeden davon eine Dublette zu einem
existierenden Item angelegt. Gesetzt mit `quelle='doublette'` und im Protokoll
vermerkt:

| Eintrag | → Item | über | Person |
|---|---|---|---|
| `6-0430`, `7-0161` | `Q2085823` | `3-1523` | Wilhelm Thiede |
| `6-0974` | `Q2086927` | `4-0167` | Frieda Witzel |
| `7-0665` | `Q2088374` | `4-1628` | Hilde Hengstmann |

Das ist derselbe Befund wie bei den 5.006 Einträgen der Ordner 2 bis 4 (siehe
CLAUDE.md), nur andersherum: dort steht die Entscheidung „neue Person" neben
einem Item, das der eigene Export erst erzeugt hat. Hier zeigt die Doublette
auf ein solches Item. Die vier waren die einzigen dieser Art — kein weiterer
Eintrag aus 5/6/7 hat einen Partner mit bekannter Q-ID.

## Bestätigte Fehlalarme des Doubletten-Abgleichs

Alle am 18.8.2026 von Hand geprüft und als **zwei Personen** bestätigt:

- **`7-0466` ↔ `7-1188`, Selma Fischer** (*21.10. ↔ *30.9.1884, Karlstr. 1 /
  Zollberg 31, zwei Blätter). In Ordner 7 fehlt der Geburtsname, die Adresse
  zählt nicht mit, also blieben Name (65) und die halbierte Datumswertung
  (21) = 86.
- **`1263` ↔ `5-0028`, Marta Grabe** (*2.8. ↔ *1.9.1894), verschiedene
  Geburtsnamen: Stolze / Wollschläger.
- **`3-0631` ↔ `6-0340`, Gustav Müller** (*6.7. ↔ *10.7.1888, Heinrichstr. 61 /
  Baumgartenstr. 39), Score 86.

Der Müller ist der erste bestätigte Fehlalarm, der **stehen bleibt**. Fischer
und Grabe hat die engere `datum_paar()`-Regel weggeräumt; hier geht das nicht.
Vier Tage Abstand bei gleichem Namen ist genau der Fall, den die Regel fangen
soll — die dichtesten echten Paare der Gegenprobe liegen bei 1 und 2 Tagen. Wer
`MAX_TAGESVERSATZ` so weit senkte, dass Müller fiele, verlöre `4-0056` ↔
`6-0256`, `6-0149` ↔ `7-0028` und den Testfall `4-0575` ↔ `4-1115` mit.

Warum die Regel hier nichts ausrichten kann, sagen die Daten: 141 Müller im
Register, davon fünf mit Vornamen Gustav. Bei einem so häufigen Namen und ohne
Geburtsnamen — Männer tragen keinen — bleiben nur Datum und Adresse, und die
Adresse zählt zwischen zwei Wahlen absichtlich nicht mit (Umzüge).

Der Hinweis steht also weiter in `doubletten`, und weil beide Seiten auf
`kein_treffer` stehen, trägt der Export für dieses Paar eine `# ACHTUNG`-Zeile,
die hier **falsch** ist: zwei Items sind hier richtig. Wer den Export
durchsieht, überliest diese eine Zeile. Eine Liste bestätigter Nicht-Paare, die
`link_doubletten.py` überspringt, gibt es bewusst noch nicht — bei drei Fällen
wäre sie mehr Mechanik als Nutzen. Kommen mehr dazu, ist sie fällig.

## `datum_paar()` enger gezogen — erledigt am 18.8.2026

In `build/link_doubletten.py`. Bis dahin galt die volle Monatstoleranz aus
`datum_widerspruch()` (31 Tage) in jede Richtung. Jetzt gilt sie nur noch, wenn
**der Tag gleich bleibt** (verschobener Monat) oder der **Abstand klein** ist
(verrutschte Zahl, `MAX_TAGESVERSATZ = 16`). Fischer, Grabe und Hofmann stehen
als Testfälle in `build/test_doubletten.py`, die Regel in `regeln.md`; der Lauf
findet seither **314** statt 316 Paare, die 299 tagesgleichen unverändert.

Gegenprobe über alle elf Paare mit abweichendem Datum — mehr gibt es unter den
316 nicht:

| Δ | Paar | Person | Daten | Urteil |
|---|---|---|---|---|
| 31 d | `5-0822` ↔ `7-1378` | Ida Hofmann | 10.9. ↔ 10.8. | bleibt (Tag gleich) — und ist ein Transkriptionsfehler, siehe oben |
| 30 d | `1263` ↔ `5-0028` | Marta Grabe | 2.8. ↔ 1.9. | **fällt weg** — richtig so |
| 21 d | `7-0466` ↔ `7-1188` | Selma Fischer | 21.10. ↔ 30.9. | **fällt weg** — richtig so |
| 15 d | `4-1195` ↔ `4-1674` | Otto Herrmann | 21.4. ↔ 6.4. | bleibt (engste Kante) |
| 10 d | `0920` ↔ `4-0159` | Gertrud Berger | 30.12. ↔ 20.12. | bleibt |
| 10 d | `4-0057` ↔ `6-0257` | Margarete Kindler | 19.12. ↔ 9.12. | bleibt — und ist ein Transkriptionsfehler, siehe oben |
| 5 d | `6-1106` ↔ `7-0651` | Elisabeth Ustofski | 10.11. ↔ 15.11. | bleibt |
| 4 d | `3-0631` ↔ `6-0340` | Gustav Müller | 6.7. ↔ 10.7. | bleibt — aber **Fehlalarm**, siehe oben |
| 2 d | `4-0575` ↔ `4-1115` | Hermann Kobert | 27.8. ↔ 29.8. | bleibt (Testfall) |
| 1 d | `6-0149` ↔ `7-0028` | Franz Spengler | 26.2. ↔ 25.2. | bleibt |
| 1 d | `4-0056` ↔ `6-0256` | Ewald Kindler | 7.3. ↔ 8.3. | bleibt |

Die Änderung trifft damit genau die zwei bestätigten Fehlalarme und keinen der
übrigen 314 Hinweise. Nachgerechnet nach dem Lauf: es blieb bei genau diesen
beiden.

### Der Geburtsname taugt **nicht** als Ausschluss

Naheliegend nach Marta Grabe, aber die Zahlen sprechen dagegen. Nur 11 der 316
Paare führen beidseitig einen Geburtsnamen, bei 6 weicht er ab — und fünf davon
haben ein tagesgleiches Geburtsdatum, sind also echte Doubletten mit verlesenem
Geburtsnamen:

| Paar | Person | geb. | Datum |
|---|---|---|---|
| `0122` ↔ `6-1185` | Luise Zschiesche | Stude / Stade | tagesgleich |
| `1174` ↔ `6-0888` | Elsbeth Thomas | Sinner / Zimmer | tagesgleich |
| `4-0167` ↔ `6-0974` | Frieda Witzel | Rieche / Werner | tagesgleich |
| `4-1026` ↔ `6-0276` | Hedwig Diessner | Hesat / Hecht | tagesgleich |
| `5-0807` ↔ `6-1266` | Anna Sagebaum | Lostermann / Buhtermann(?) | tagesgleich |
| `1263` ↔ `5-0028` | Marta Grabe | Stolze / Wollschläger | 30 Tage |

Das Fragezeichen bei Anna Sagebaum steht so in der Quelle. Eine Regel
„verschiedener Geburtsname schließt aus" würfe fünf richtige Treffer weg, um
einen falschen zu fangen — und die Datumsregel oben fängt Grabe ohnehin.

## Wenn abgearbeitet wird

`data/register.sqlite` **vorher sichern**, dann:

```bash
python3 build/build_register.py
python3 build/link_addresses.py
python3 build/link_doubletten.py
```

Entscheidungen, `p120` und `einstellungen` bleiben unberührt — sie hängen an
`lfd_id`. Der FactGrid-Abgleich bleibt für geänderte Einträge veraltet;
`match_factgrid.py` kennt keinen selektiven Lauf, und 7 Stunden lohnen für ein
einzelnes Datum nicht.
