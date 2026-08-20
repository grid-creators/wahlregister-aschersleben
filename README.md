# wahlregister — Abgleich Wählerverzeichnisse Aschersleben ↔ FactGrid

Ein Werkzeug für **eine** Aufgabe: die Einträge der Wählerverzeichnisse mit
FactGrid abgleichen und daraus eine QuickStatements-Tabelle erzeugen. Die
Ordner 2 bis 6 gehören zu den Wahlen des Jahres 1933, Ordner 7 zur Wahl vom
20. Mai 1928.

[https://wahlregister.grid-creators.com/](https://wahlregister.grid-creators.com/)

Offen für alle: Entscheiden und Herunterladen brauchen keine Anmeldung und
kein besonderes Recht.

## Sechs Ordner, drei Wahltage

Das Verzeichnis liegt in Ordnern des Bestands I-14-149. Die App hält **alle
sechs** in einer Liste; oben filtert ein Feld **Ordner**. Diese eine Auswahl gilt
für die ganze Seite: Liste, Fortschrittsbalken, **Export** und **Verlauf**
zeigen denselben Ordner, und die Downloads liefern genau das, was gerade zu
sehen ist. Ohne Auswahl bleiben alle Ordner zusammen.

| Ordner | Einträge | Wahltag | Quelle | Primärquelle (P51) |
|---|---|---|---|---|
| 2 | 1.669 | 5.3.1933 | `wahlregister 2 - register2_new.csv` | [Q2080842](https://database.factgrid.de/wiki/Item:Q2080842) |
| 3 | 1.730 | 5.3.1933 | `wahlregister  - register3.csv` | [Q2084011](https://database.factgrid.de/wiki/Item:Q2084011) |
| 4 | 1.681 | 5.3.1933 | `wahlregister_register4_korrigiert.csv` | [Q2086743](https://database.factgrid.de/wiki/Item:Q2086743) |
| 5 | 1.604 | 5.3.1933 | `wahlregister_register5_korrigiert.csv` | [Q2088480](https://database.factgrid.de/wiki/Item:Q2088480) |
| 6 | 1.658 | **12.11.1933** | `wahlregister_register6_korrigiert.csv` | [Q2088500](https://database.factgrid.de/wiki/Item:Q2088500) |
| 7 | 1.447 | **20.5.1928** | `wahlregister_register7_korrigiert.csv` | [Q2088502](https://database.factgrid.de/wiki/Item:Q2088502) |

Zusammen 9.789 Einträge.

**Ordner 6 und 7 gehören zu anderen Wahlen als 2 bis 5**, und daran hängt
mehr als ein Datum: eine andere Wahl im Export, ein anderes Jahr an Ort und
Adresse, für Ordner 7 ein anderer Stichtag beim Lesen der zweistelligen
Jahreszahlen — und, weil dieselben Menschen 1928 und 1933 wählen durften,
**Überschneidungen zwischen den Ordnern**. Die Straßen sind nicht mehr
getrennt: Ordner 6 und 7 teilen sich 44 Adressitems in fünf Straßen. Deshalb
gibt es neben dem Abgleich gegen FactGrid einen zweiten gegen das Register
selbst (siehe „Derselbe Mensch in zwei Ordnern").

Die einzige Adresse, die in zwei Ordnern verschiedene FactGrid-Häuser meint,
ist „Liebenwerder Plan 20" (Ordner 2 und 3). Adressen werden deshalb je Ordner
geführt, und die Straßenliste zeigt nur die Straßen des gewählten Ordners.

Die laufenden Nummern von Ordner 2 bleiben, wie sie waren (`0001`) — daran
hängen die bisherigen Entscheidungen. Jeder weitere Ordner trägt ein Präfix
(`3-0001` bis `7-0001`).

## Ablauf

1. **Vorschläge ansehen.** Zu jedem Eintrag stehen die FactGrid-Kandidaten mit
   einem Score von 0 bis 100 und den vier Teilwerten, aus denen er sich ergibt.
2. **Entscheiden.** Für jeden Eintrag ist eine Entscheidung möglich — auch
   dann, wenn der Abgleich nichts oder das Falsche vorschlägt:

   | Weg | wofür |
   |---|---|
   | **diese Person** | einen der Vorschläge übernehmen |
   | **keine Person in FactGrid** | es gibt dort niemanden — der Eintrag wird später als `CREATE` angelegt |
   | **tiefer suchen** | denselben Eintrag mit abgesenkter Schwelle neu rechnen |
   | **in FactGrid suchen** | freie Namenssuche im FactGrid-Auszug, Treffer direkt zuordenbar |
   | **Q-ID direkt zuordnen** | Q-ID eintippen, „prüfen" zeigt Label und Lebensdaten zur Kontrolle |
   | **Sammelentscheidung** | alle im aktuellen Filter noch **offenen** Einträge auf „keine Person in FactGrid" setzen |
   | **P120** | eine Q-ID vormerken, die passen *könnte* — „möglicherweise identisch mit" |

   Das P120-Feld steht neben der Entscheidung, nicht in ihr: der übliche Fall
   ist „keine Person in FactGrid" (also ein neues Item) mit einem Verdacht
   daneben, der für eine Zuordnung nicht gereicht hat. Es lässt sich unabhängig
   setzen und mit leerem Feld wieder entfernen.

   Jede Entscheidung lässt sich einzeln wieder aufheben; die Sammelentscheidung
   überschreibt nie etwas bereits Entschiedenes. Die App merkt sich, auf
   welchem Weg eine Zuordnung zustande kam (Vorschlag, Suche, Q-ID, Sammel).
   Eine Q-ID, die im lokalen Auszug fehlt, lässt sich trotzdem zuordnen —
   die App weist dann darauf hin, dass sie nicht prüfen konnte, wer das ist.
3. **Exportieren.** Aus den Entscheidungen entsteht die
   QuickStatements-Tabelle — `CREATE`-Blöcke für die noch fehlenden Personen,
   ergänzende Aussagen für die zugeordneten Items.

## Verlauf

Jede Änderung an einer Entscheidung wird festgehalten: Zeitpunkt, Eintrag, was
vorher galt, was jetzt gilt und auf welchem Weg. Weil die App keine Anmeldung
kennt, gibt es oben ein freiwilliges Feld **Bearbeiter/in** — was dort steht,
landet im Verlauf und bleibt im Browser gespeichert.

Der Verlauf steht unten auf der Seite und ist als `protokoll.csv` herunterladbar.
Wie der Export folgt er dem gewählten **Ordner**. Nichts wird überschrieben:
Auch wenn zwei Leute denselben Eintrag anfassen, bleibt jede Zwischenstufe
nachlesbar.

**Sammelentscheidungen lassen sich zurücknehmen.** Jede bekommt eine Kennung;
im Verlauf steht ein Knopf dafür. Zurückgesetzt wird nur, was seither *nicht*
von Hand geändert wurde — wer einen dieser Einträge inzwischen bewusst
zugeordnet hat, behält seine Arbeit. Die Rücknahme selbst steht wieder im
Verlauf.

Ein Stapel wird immer **ganz** zurückgenommen, auch wenn er über den gewählten
Ordner hinausreicht — er wurde ja auch als Ganzes gesetzt. Solche Stapel sind
im Verlauf als solche gekennzeichnet, und die Rückfrage weist noch einmal
darauf hin.

## Abgleich

Vier Kriterien, alle unscharf: **Vorname, Nachname, Geburtsdatum, Adresse**.
Details in **`regeln.md`**. Kurz:

- Namen unscharf (Tippfehler, abgekürzte Vornamen, „geb."-Namen beidseitig)
- Geburtsdatum gestuft (Tag / Monat / Jahr / ±1 Jahr)
- Adresse über die FactGrid-Adressitems: Aschersleben ist dort
  hausnummerngenau erfasst (`Q497980 = "Aschersleben, Breite Straße 22"`);
  jede Adresse jedes Ordners hat ein solches Item

Ein einziger **harter Ausschluss**: tragen Registereintrag und FactGrid-Person
beide ein tagesgenaues Geburtsdatum und liegen die beiden mehr als **einen
Monat** auseinander, ist es nicht dieselbe Person — der Kandidat wird gar nicht
erst angeboten. Ein verlesener Tag oder Monat bleibt damit erlaubt, ein anderes
Geburtsdatum nicht. Von Hand getroffene Entscheidungen berührt das nicht.

Dass ein Eintrag wenige oder keine Vorschläge bekommt, ist der Normalfall,
aber seltener als früher: in FactGrid stehen inzwischen **6.596** Personen mit
„1933 Wahlteilnehmer in Aschersleben" — Ordner 1 und die importierten Ordner 2
bis 4. Für die Ordner 5 bis 7 heißt das, dass ein Teil der Menschen dort schon
ein Item hat, weil dieselbe Person auch in einem früheren Ordner steht.

Dafür muss der lokale Auszug aktuell sein. Er wird mit
`build/peru_auszug.py` aus dem tagesaktuellen FactGrid-Dump gebaut; der Dienst
findet ihn über `PERU_DB`. Ein veralteter Auszug ist kein kleiner Mangel: mit
dem Stand vom 20.7.2026 waren die 5.006 importierten Personen unsichtbar, und
der Abgleich hätte sie alle ein zweites Mal anlegen lassen.

Dazu kommt, dass ein Teil der Adressitems im lokalen FactGrid-Auszug noch
fehlt — dort hängen keine Personen, und das Adress-Kriterium trägt für sie
nichts bei. Der Export ist davon unberührt: die Adress-Q-ID kommt aus der
Quelltabelle, nicht aus dem Auszug.

| Ordner | Adressitems | dem Auszug unbekannt |
|---|---|---|
| 2 | 230 | 0 |
| 3 | 243 | 0 |
| 4 | 235 | 0 |
| 5 | 190 | 10 |
| 6 | 177 | 163 |
| 7 | 204 | 105 |

## Derselbe Mensch in zwei Ordnern

Weil Ordner 6 und 7 zu anderen Wahlen gehören, steht mancher Mensch **zweimal**
im Register: wer 1928 wählen durfte, durfte es 1933 meistens auch. Fritz
Lehmann etwa wohnt in beiden Listen im Bäckerstieg 1. Ein zweiter Abgleich
sucht solche Paare — nicht in FactGrid, sondern im Register selbst. Zurzeit
sind es **316 Paare**, 299 davon mit tagesgleichem Geburtsdatum.

Am Eintrag steht dann, wo der Mensch noch vorkommt und wie er dort entschieden
wurde. Zwei Fälle:

- Das Gegenstück ist einem FactGrid-Item **zugeordnet** → ein Klick auf
  „Q-ID übernehmen" reicht; die Suche muss nicht ein zweites Mal gemacht
  werden. Der Verlauf hält fest, dass die Q-ID aus einer Doublette stammt.
- Beide sind als **„keine Person in FactGrid"** entschieden → beide anzulegen
  ergäbe zwei Items für einen Menschen. Der Export schreibt darum eine
  `# ACHTUNG`-Zeile vor den betroffenen Eintrag und zählt die Fälle im Kopf.
  Verhindert wird nichts: welcher der beiden Einträge das Item anlegt und
  welcher später daran gehängt wird, ist eine Entscheidung.

Gesucht wird über Name und Geburtsdatum, **nicht** über die Adresse — zwischen
1928 und 1933 sind Menschen umgezogen. Eheleute mit gleichem Geburtsdatum,
Zwillinge und Namensvettern werden ausgeschlossen; wie genau, steht in
[regeln.md](regeln.md).

## QuickStatements

Das Datenmodell folgt
[Q1257714](https://database.factgrid.de/wiki/Item:Q1257714) (Georg Obermüller),
einem bereits importierten Eintrag aus Ordner 1:

| Property | Wert | Qualifikator |
|---|---|---|
| P2 | Q7 (Mensch) | |
| P77 | Geburtsdatum, tagesgenau | |
| P154 | Geschlecht | |
| P170 | akademischer Grad | nur wo die Quelle einen Titel nennt |
| P83 | Q80706 Aschersleben | P106 = 1933 |
| P208 | das Adress-Item | P106 = 1933 |
| P119 | je Wahlspalte mit Vermerk eine Aussage | P277 = Rolle (jede Aussage), P520 = Bemerkung der Akte |
| P51 | Primärquelle | P499 = Nummer in der Akte |
| P131 | Forschungsprojekt | |
| P120 | die vorgemerkte Q-ID | nur wenn von Hand gesetzt |

### Welche Wahl gemeint ist, hängt am Ordner

Die Ordner **2 bis 5** führen drei Wahlspalten, und jede meint eine eigene
Wahl — so steht es schon bei den Personen aus Ordner 1 in FactGrid:

| Spalte der Akte | Wahl | O2 | O3 | O4 | O5 |
|---|---|---|---|---|---|
| 4 | [Q1207285](https://database.factgrid.de/wiki/Item:Q1207285) Deutsche Reichstagswahl | 1.474 | 1.619 | 1.545 | 1.468 |
| 5 | [Q1214187](https://database.factgrid.de/wiki/Item:Q1214187) Stadtverordnetenversammlung Aschersleben | 1.411 | 1.523 | 1.407 | 1.346 |
| 8 | [Q1214186](https://database.factgrid.de/wiki/Item:Q1214186) Provinziallandtag der Provinz Sachsen | 1.369 | 1.480 | 1.386 | 1.324 |

Die Ordner **6 und 7** haben statt dessen eine einzige Stimmabgabe-Spalte, und
welche Wahl sie meint, muss nicht erschlossen werden — es steht in ihrem
Archivale:

| Ordner | Wahl | mit Vermerk |
|---|---|---|
| 6 | [Q1207474](https://database.factgrid.de/wiki/Item:Q1207474) Reichstagswahl u. Volksabstimmung 12.11.1933 | 1.545 |
| 7 | [Q2088496](https://database.factgrid.de/wiki/Item:Q2088496) Reichstagswahl 20.5.1928 | 1.219 |
| 7 | [Q2088498](https://database.factgrid.de/wiki/Item:Q2088498) Preußischer Landtag 20.5.1928 | 1.219 |

In Ordner 7 belegt **ein** Haken **zwei** Wahlen: beide fanden am 20. Mai 1928
statt und wurden in derselben Liste abgehakt. Mit dem Ordner wechselt auch das
Jahr an Ort und Adresse (P106 = 1928 statt 1933) und in der Beschreibung.

**Haken und Kreuz heißen beide „teilgenommen"** — sie stehen nur in
verschiedenen Spalten; die Ordner 3, 4, 5 und 7 schreiben dieselbe Angabe als
`1` und `0`. Nur das leere Feld heißt „nicht teilgenommen", und dann entsteht
gar keine Aussage: 130 Einträge in Ordner 2, 98 in Ordner 3, 118 in Ordner 4
und 70 in Ordner 6 tragen in keiner Spalte einen Vermerk und bekommen deshalb
kein P119. Die Bemerkung der Akte hängt als P520 an der ersten erzeugten
Aussage.

Ordner 6 kennt einen dritten Wert: **43-mal steht dort „St."**, von der Quelle
selbst als *Stimmschein* aufgelöst. Er wird erfasst und angezeigt, erzeugt aber
kein P119 — der Stimmschein belegt, dass jemand anderswo wählen durfte, nicht
dass er gewählt hat.

Jede Teilnahme trägt dazu die Rolle als Qualifikator:
`P277 = `[Q1207476](https://database.factgrid.de/wiki/Item:Q1207476)
(Wahlberechtigte(r)). Anders als die Bemerkung gilt sie der einzelnen Wahl und
steht deshalb an jeder P119; über die Einstellung `qs_rolle` änderbar, leer
heißt: kein Qualifikator.

Die Ordner 3, 4 und 5 erfassen zusätzlich die Aktenspalten **6, 7 und 9**. Dort
steht in keiner Zeile ein Vermerk. Sie sind gespeichert — „geprüft und leer" ist eine
Angabe —, gehen aber nicht in den Export: welche Wahl sie meinen, ist nicht
bekannt.

Ein akademischer Titel („Dr." vor dem Vornamen) steht **nicht** im Label — er
wird beim Aufbau abgetrennt und geht als P170 mit.

`P120` („Möglicherweise identisch mit") steht nicht im Muster-Item — es kommt
nur mit, wo jemand am Eintrag eine Q-ID vorgemerkt hat. Zeigt die Vormerkung
auf das Item, dem der Eintrag ohnehin zugeordnet ist, wird sie übersprungen.

Neue Personen bekommen zusätzlich ein deutsches (`Lde`) und ein englisches
Label (`Len`), den Geburtsnamen als Alias und eine Beschreibung im Muster
`*26.12.1881; 1933 Wahlteilnehmer in Aschersleben`. Die beiden Labels
unterscheiden sich in genau einem Wort — der Name selbst ist keine
Übersetzungssache:

| | |
|---|---|
| `Lde` | `Margarete Müller (geb. Hahn)` |
| `Len` | `Margarete Müller (nee Hahn)` |

Labels entstehen **nur bei der Neuanlage**. Ein zugeordnetes Item bekommt
keins: `Len` würde dort ein vorhandenes englisches Label überschreiben, und ob
es eins hat, führt der Peru-Auszug nicht mit. Das englische Label lässt sich
unter „Kontext-Items des Exports" abschalten.

Bei zugeordneten Items werden Wohnort-Aussagen weggelassen, die das Item laut
Peru-Auszug schon hat.

Die Primärquelle steht **je Ordner**, weil jeder Ordner ein eigenes Archivale
ist (siehe die Tabelle ganz oben).
Ist für einen Ordner keins hinterlegt, entsteht kein P51 statt eines falschen,
und der Export-Block weist darauf hin. Änderbar unter „Kontext-Items des
Exports" auf der Seite — der Schlüssel heißt `qs_quelle_o<Ordner>`.

**Vor dem Import prüfen:** `Q1214187` und `Q1214186` datieren beide auf den
**5. März 1933**, die Bemerkungen dieses Registers durchweg auf den **12. März
1933**. Welche Spalte welche Wahl meint, ist aus dem Muster von Ordner 1
erschlossen und nicht aus der Akte belegt; änderbar unter „Kontext-Items des
Exports".

Das **Geschlecht ist geschätzt** (Geburtsname bzw. Vornamensliste) und in
FactGrid später nicht mehr als Schätzung erkennbar. Es lässt sich in den
Kontext-Einstellungen abschalten.

## Aufbau

Das Repo hält Code und Dokumentation. **Die Daten liegen nicht darin**: weder
die Quell-CSVs des Bestands I-14-149 noch die beiden Datenbanken. Der
FactGrid-Auszug ist mit rund 500 MB zu groß für GitHub, und `register.sqlite`
hält die Entscheidungen von Hand — eine Arbeitsdatei, die sich stündlich
ändert. Beide entstehen aus den Skripten unter `build/`; die CSVs kommen aus
dem Archiv. Ohne sie lässt sich die App lesen, aber nicht starten.

```
wahlregister 2 - register2_new.csv     Ordner 2 (unverändert)
wahlregister  - register3.csv          Ordner 3 (unverändert)
wahlregister_register4_korrigiert.csv  Ordner 4
wahlregister_register5_korrigiert.csv  Ordner 5
wahlregister_register6_korrigiert.csv  Ordner 6 (12.11.1933)
wahlregister_register7_korrigiert.csv  Ordner 7 (20.5.1928)
data/register.sqlite                Register, Kandidaten, Entscheidungen
build/build_register.py             CSVs → SQLite (Ordner in QUELLEN)
build/link_addresses.py             Registeradressen → FactGrid-Adressitems
build/link_doubletten.py            derselbe Mensch in mehreren Ordnern
build/peru_auszug.py                FactGrid-Dump → data/persons.sqlite
build/p51_bericht.py                welcher Eintrag schon ein Item hat (P51/P499)
data/persons.sqlite                 der Auszug, gegen den abgeglichen wird
build/match_factgrid.py             Batch-Abgleich (~7 h für sieben Ordner)
build/test_register.py              Einlesen aller Tabellenformate (ohne DB)
build/test_match.py                 Regeltests (braucht die Peru-DB, kein Netz)
build/test_doubletten.py            Regeltests des Register-Abgleichs (ohne DB)
build/test_quickstatements.py       Export-Tests (ohne DB)
build/test_against_app.py           E2E gegen den laufenden Server
app/match.py                        Abgleich
app/quickstatements.py              Export
app/schema.py                       Tabellen, Kontext-Items, Wahl je Ordner
app/server.py                       Flask-API + Seite (Port 8770)
regeln.md                           wie beide Abgleiche rechnen
```

Ein weiterer Ordner ist eine Zeile in `QUELLEN` (`build/build_register.py`) und
eine in `QS_DEFAULTS` (`app/schema.py`) für seine Primärquelle. Gehört er zu
einer anderen Wahl, kommt er zusätzlich in `WAHLSPALTEN_ORDNER`; gehört er zu
einem anderen Jahr, in `WAHLJAHR_ORDNER` (beide in `app/schema.py`). Bringt er
ein weiteres Tabellenformat mit, kommt ein Zweig in `lies()` dazu.

## Betrieb

```bash
python3 build/peru_auszug.py        # neuer FactGrid-Dump (~3 min)
python3 build/build_register.py     # nach Änderung einer Quelle oder neuem Ordner
python3 build/link_addresses.py     # danach immer — liest dieselben CSVs
python3 build/link_doubletten.py    # danach immer — dauert Sekunden
python3 build/match_factgrid.py     # nach Änderungen an den Regeln
systemctl restart wahlregister      # nach Änderungen an server.py / match.py
journalctl -u wahlregister -f
```

Abhängigkeiten: Standard-Python plus `flask` (für den Bau des Auszugs
zusätzlich `ijson`). Der FactGrid-Auszug wird über `PERU_DB` gefunden — der
systemd-Dienst setzt die Variable auf `data/persons.sqlite`, das
`build/peru_auszug.py` erzeugt. Ohne die Variable fiele die App auf den Auszug
des Nachbarprojekts zurück, der einen älteren Stand hat. Geschrieben wird in
den Auszug nie; er wird ausschließlich lesend geöffnet, und es geht kein
Aufruf ins Netz.

**Kein Rechtesystem.** Jede und jeder darf entscheiden, ändern, aufheben und
exportieren — auch die Sammelentscheidung. Wer etwas getan hat, steht nur dort,
wo jemand freiwillig einen Namen einträgt; *was wann* passiert ist, hält der
Verlauf dagegen lückenlos fest. Der Arbeitsstand lässt sich über
`entscheidungen.csv` und `protokoll.csv` sichern.

Die Subdomain hinter dem nginx-proxy-manager hat den fehlenden TLS behoben:
`https://wahlregister.grid-creators.com/` ist verschlüsselt. Zwei Dinge bleiben.
Flasks eingebauter Server ist weiterhin kein produktiver WSGI-Server, der Proxy
ändert daran nichts. Und der alte Weg steht offen: `http://185.162.251.195:8770/`
antwortet unverschlüsselt am Proxy vorbei — wer TLS erzwingen will, schließt den
Port nach außen.
