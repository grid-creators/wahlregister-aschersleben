"""QuickStatements-V1-Tabelle aus den Entscheidungen.

Das Datenmodell folgt Q1257714 (Georg Obermüller) — einem Eintrag aus Ordner 1
desselben Bestands, der bereits in FactGrid steht:

    P2   Q7                                 Ist ein(e): Mensch
    P77  +1896-03-06T00:00:00Z/11           Geburtsdatum
    P83  Q80706          P106 1933          Ort der Adresse: Aschersleben
    P208 Q497991         P106 1933          Adresse/Liegenschaft: das Hausitem
    P119 Q1207285   P277 Q1207476   P520 "…"  Teilgenommen an: Spalte 4 der
    P119 Q1214187   P277 Q1207476             Akte; Spalte 5; Spalte 8. Rolle
    P119 Q1214186   P277 Q1207476             dabei: Wahlberechtigte(r). Notiz
                                              des Originals: die Bemerkung
    P51  Q2080842        P499 267           Primärquelle — der Ordner, in dem
                                            der Eintrag steht; Position in Folge
    P131 Q497317                            Forschungsprojekt
    P154 Q18                                Geschlecht

Dazu, wo die Quelle es hergibt (nicht im Muster-Item):

    P170 Q22218                             Akademischer Grad — der „Dr.", der
                                            im Register vor dem Vornamen steht
                                            und deshalb nicht ins Label gehört
    P120 Qxxxx                              Möglicherweise identisch mit —
                                            der Verdacht, der für eine
                                            Zuordnung nicht gereicht hat

Welche Wahlen ein Eintrag belegt, hängt am **Ordner**, nicht am Register: die
Ordner 2 bis 5 gehören zur Reichstagswahl vom 5.3.1933 und haken drei Spalten
ab, Ordner 6 zur Reichstagswahl und Volksabstimmung vom 12.11.1933, Ordner 7
zur **Wählerliste von 1928** — dort belegt der eine Haken zwei Wahlen, weil
Reichstag und Preußischer Landtag am 20.5.1928 am selben Tag gewählt wurden.
Mit dem Ordner wechselt deshalb auch das Jahr in P106 und in der Beschreibung.
Die Zuordnung steht in `schema.py` (`wahlspalten()`, `wahljahr()`).

Zwei Ausgabearten:

- **kein_treffer** → `CREATE` + `LAST`-Zeilen, die Person wird neu angelegt.
- **zugeordnet**   → `Qxxxx`-Zeilen, die das bestehende Item ergänzen. Aussagen,
  die das Item laut Peru-Auszug schon hat, werden weggelassen.

Labels entstehen **nur bei der Neuanlage**, deutsch (`Lde`) und englisch
(`Len`). Ein bestehendes Item bekommt keins: `Len` würde dort ein vorhandenes
englisches Label überschreiben, und ob es eins hat, führt der Auszug nicht mit.
Die beiden Labels unterscheiden sich in genau einem Wort — „(geb. Hahn)" wird
zu „(nee Hahn)"; der Name selbst ist keine Übersetzungssache.

QuickStatements V1: Tabulator-getrennt, Zeichenketten in Anführungszeichen,
Zeitwerte mit `/Genauigkeit` (11 = Tag, 9 = Jahr), Qualifikatoren hängen an
dieselbe Zeile.
"""

import re

from schema import (WAHLJAHR_STANDARD, quelle_key, wahljahr, wahlspalten)

SEX_QID = {'w': 'Q17', 'm': 'Q18'}

# Welche Spalte welche Wahl meint, steht in `schema.py` — je Ordner, weil
# nicht alle Ordner zur selben Wahl gehören. Ein Vermerk ist ein Vermerk:
# Haken und Kreuz stehen beide für Teilnahme, nur das **leere** Feld heißt
# „nicht teilgenommen". Was `tick()` nicht als Ja lesen konnte (Streichung,
# „—"), ist None und erzeugt keine Aussage — weder ja noch nein. Der
# Stimmschein-Vermerk „St." aus Ordner 6 steht als 2 in der Spalte und zählt
# hier ebenfalls nicht: er belegt, dass jemand anderswo wählen durfte, nicht
# dass er gewählt hat.
TEILGENOMMEN = 1


def _jahr_qualifikator(ordner):
    """Das Wahljahr als Zeitwert mit Jahresgenauigkeit."""
    return '+%04d-00-00T00:00:00Z/9' % wahljahr(ordner)


def _s(text):
    """Zeichenkette für QuickStatements: Anführungszeichen maskieren."""
    return '"%s"' % str(text or '').replace('\\', '\\\\').replace('"', '\\"')


def _datum(iso):
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', (iso or '').strip())
    if not m:
        return None
    return f'+{m.group(1)}-{m.group(2)}-{m.group(3)}T00:00:00Z/11'


def _zeile(*teile):
    return '\t'.join(str(t) for t in teile)


def beschreibung(e, jahre=None):
    """Wie im Muster-Item: „*06.03.1896; 1933 Wahlteilnehmer in Aschersleben".

    Das Jahr kommt aus dem Ordner: wer in Ordner 7 steht, war 1928
    Wahlteilnehmer und nicht 1933. Werden mehrere Registereinträge zu **einem**
    Item zusammengeführt, nennt `jahre` alle belegten Wahljahre — wer 1928 und
    1933 gewählt hat, ist beides, und eine Beschreibung, die nur das eine nennt,
    wäre die halbe Wahrheit."""
    d = (e['geburtsdatum'] or '')
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', d)
    stern = f'*{m.group(3)}.{m.group(2)}.{m.group(1)}; ' if m else ''
    j = sorted(set(jahre)) if jahre else [wahljahr(e['ordner'])]
    return f'{stern}{" und ".join(str(x) for x in j)} Wahlteilnehmer in Aschersleben'


# Der Klammerzusatz zum Geburtsnamen ist das Einzige, worin sich deutsches und
# englisches Label unterscheiden — der Name selbst ist keine Übersetzungssache.
GEB_ZUSATZ = {'de': 'geb.', 'en': 'nee'}


def label(e, sprache='de'):
    # Ein akademischer Titel steht in `titel` und gehört **nicht** ins Label —
    # er geht als P170 mit. Der Rückfall auf `vorname` gilt deshalb nur, wo
    # kein Titel abgetrennt wurde; sonst käme das „Dr." darüber zurück.
    vor = e['vorname_norm'] if e.get('titel') else (e['vorname_norm'] or e['vorname'])
    name = ' '.join(x for x in (vor, e['familienname']) if x)
    if e['geburtsname']:
        name += f" ({GEB_ZUSATZ[sprache]} {e['geburtsname']})"
    return name


def aussagen(e, cfg, ziel, vorhanden=frozenset()):
    """Die Aussagen der Quelle als (Property, Wert, *Qualifikatoren)-Tupel.
    `ziel` ist 'CREATE' für neue Items, sonst die Q-ID des bestehenden."""
    neu = ziel == 'CREATE'
    out = []

    if neu:
        out.append(('P2', 'Q7'))
        d = _datum(e['geburtsdatum'])
        if d:
            out.append(('P77', d))
        if cfg.get('qs_geschlecht') == 'ja' and SEX_QID.get(e['geschlecht']):
            out.append(('P154', SEX_QID[e['geschlecht']]))
        # Wie P154 nur bei der Neuanlage: der Peru-Auszug führt P170 nicht mit,
        # an einem bestehenden Item ließe sich ein Doppel nicht ausschließen.
        if e.get('titel') and cfg.get('qs_titel'):
            out.append(('P170', cfg['qs_titel']))

    # Ort und Adresse mit dem Jahr der Wahl als Datum-Qualifikator. Das Jahr
    # gehört zum Ordner: Ordner 7 belegt eine Adresse von 1928, nicht von 1933.
    jahr = _jahr_qualifikator(e['ordner'])
    if cfg.get('qs_ort') and cfg['qs_ort'] not in vorhanden:
        out.append(('P83', cfg['qs_ort'], 'P106', jahr))
    if e['adress_qid'] and e['adress_qid'] not in vorhanden:
        out.append(('P208', e['adress_qid'], 'P106', jahr))

    # Teilnahme an den drei Wahlen — je Spalte eine Aussage, aber nur, wo die
    # Akte einen Vermerk trägt. Die Bemerkung der Akte hängt als Notiz des
    # Originals an der **ersten** erzeugten Aussage; sie gilt dem Registereintrag,
    # nicht einer einzelnen Wahl, und dreimal derselbe Text wäre nur Rauschen.
    # Die Rolle bei der Wahl (P277) hängt dagegen an **jeder** Teilnahme: sie
    # sagt etwas über die einzelne Aussage, nicht über den Registereintrag.
    bem = (e['bemerkung'] or '').strip()
    # „(…)" sind Anmerkungen der Edition, nicht Text der Quelle.
    notiz = _s(bem) if bem and not bem.startswith('(') else None
    for spalte, schluessel in wahlspalten(e['ordner']):
        if e.get(spalte) != TEILGENOMMEN or not cfg.get(schluessel):
            continue
        zeile = ['P119', cfg[schluessel]]
        if cfg.get('qs_rolle'):
            zeile += ['P277', cfg['qs_rolle']]
        if notiz:
            zeile += ['P520', notiz]
        out.append(tuple(zeile))
        notiz = None

    # Die Primärquelle ist der Ordner, in dem der Eintrag steht — jeder hat sein
    # eigenes Item. Ist für einen Ordner keins hinterlegt, entsteht keine
    # Aussage; ein falscher Ordner wäre schlimmer als gar keine Angabe.
    quelle = cfg.get(quelle_key(e['ordner']))
    if quelle:
        if e['akte_nr']:
            out.append(('P51', quelle, 'P499', e['akte_nr']))
        else:
            out.append(('P51', quelle))

    if cfg.get('qs_projekt') and cfg['qs_projekt'] not in vorhanden:
        out.append(('P131', cfg['qs_projekt']))

    # P120 „Möglicherweise identisch mit" — die von Hand vorgemerkte Q-ID.
    # Der Regelfall ist ein neu angelegtes Item mit einem Verdacht daneben;
    # ein Selbstbezug wird übersprungen, falls das Ziel dieselbe Q-ID ist.
    if e.get('p120_qid') and e['p120_qid'] != ziel:
        out.append(('P120', e['p120_qid']))

    return out


def doppelte_neuanlagen(eintraege, doubletten):
    """Welche Einträge dieses Exports **denselben Menschen** neu anlegen würden.

    Zwei Registereinträge derselben Person, beide als „keine Person in
    FactGrid" entschieden, ergeben zwei `CREATE` — zwei Items für einen
    Menschen, die hinterher von Hand zusammengeführt werden müssten. Seit
    Ordner 6 und 7 ist das kein Randfall mehr: die beiden gehören zu anderen
    Wahlen, und wer 1928 wählen durfte, durfte es 1933 meistens auch.

    Verhindert wird hier nichts — der Export bleibt vollständig, aber er sagt
    es. Welche der beiden Zeilen das Item anlegt und welche später an das
    fertige Item gehängt wird, ist eine Entscheidung und keine Rechnung.

    `doubletten` ist {lfd_id: [(partner, score), …]}."""
    neue = {e['lfd_id'] for e in eintraege if e['status'] == 'kein_treffer'}
    out = {}
    for lfd in sorted(neue):
        partner = [(p, s) for p, s in doubletten.get(lfd, ()) if p in neue]
        if partner:
            out[lfd] = sorted(partner, key=lambda x: -x[1])
    return out


def _fuehrend(gruppe):
    """Welcher Registereintrag einer Doublettengruppe das Item anlegt.

    Es führt die **reichste Namensform**: ein Geburtsname schlägt alles, dann
    der ausgeschriebene Vorname vor der Abkürzung („Richard Sagebaum" vor
    „Rich. Sagebaum"), dann der längere Name („Paul Otto Müller" vor „Paul
    Müller"). Erst danach entscheidet der Ordner und zuletzt die laufende
    Nummer — die beiden nur, damit dieselbe Eingabe immer dieselbe Tabelle
    ergibt. Ordner 7 führt keine Geburtsnamen, deshalb gewinnt bei einem Paar
    6↔7 in aller Regel Ordner 6."""
    return min(gruppe, key=lambda e: (
        0 if e['geburtsname'] else 1,
        0 if '.' not in (e['vorname_norm'] or e['vorname'] or '') else 1,
        -len(label(e)),
        e['ordner'],
        e['lfd_id']))


def gruppen(eintraege, doubletten):
    """Die Neuanlagen dieses Exports, gruppiert nach Mensch.

    Zwei Registereinträge, die `doubletten` als denselben Menschen führt und
    die beide neu angelegt würden, gehören in **ein** Item. Die Beziehung wird
    transitiv geschlossen: Wilhelm Thiede steht in drei Ordnern, und wer A=B
    und B=C sagt, hat A=C schon gesagt.

    Rückgabe: Liste von Listen, jede nach `_fuehrend()` sortiert (der Anleger
    zuerst), die Gruppen in der Reihenfolge ihres ersten Vorkommens."""
    neue = {e['lfd_id']: e for e in eintraege if e['status'] == 'kein_treffer'}
    eltern = {}

    def wurzel(x):
        eltern.setdefault(x, x)
        while eltern[x] != x:
            eltern[x] = eltern[eltern[x]]
            x = eltern[x]
        return x

    for lfd in neue:
        for partner, _score in doubletten.get(lfd, ()):
            if partner in neue:
                a, b = wurzel(lfd), wurzel(partner)
                if a != b:
                    eltern[a] = b

    aus = {}
    for lfd in neue:
        aus.setdefault(wurzel(lfd), []).append(lfd)
    fertig = []
    for lfd, e in neue.items():                      # Reihenfolge des Exports
        w = wurzel(lfd)
        if w not in aus:
            continue
        mit = [neue[x] for x in aus.pop(w)]
        kopf = _fuehrend(mit)
        fertig.append([kopf] + sorted((m for m in mit if m is not kopf),
                                      key=lambda m: m['lfd_id']))
    return fertig


def bauen(eintraege, cfg, vorhandene_aussagen=None, doubletten=None,
          zusammenfuehren=False):
    """Vollständige QuickStatements-Tabelle als Liste von Zeilen.

    `zusammenfuehren` legt für eine Gruppe von Doubletten **ein** Item an
    statt eines je Registereintrag. Das ist ausdrücklich nicht der Regelfall:
    ohne den Schalter warnt der Export nur (`doppelte_neuanlagen()`), weil die
    Frage, welche Zeile das Item anlegt, eine Entscheidung ist und keine
    Rechnung. Mit dem Schalter ist sie beantwortet — nach `_fuehrend()`."""
    vorhandene_aussagen = vorhandene_aussagen or {}
    eintraege = [dict(e) for e in eintraege]
    doubletten = doubletten or {}
    anleger, folge = {}, set()
    if zusammenfuehren:
        for g in gruppen(eintraege, doubletten):
            anleger[g[0]['lfd_id']] = g
            folge.update(m['lfd_id'] for m in g[1:])
    # Gewarnt wird nur, wo nicht zusammengeführt wird — sonst warnte der Export
    # vor etwas, das er selbst gerade erledigt hat.
    warnung = {} if zusammenfuehren else doppelte_neuanlagen(eintraege, doubletten)
    zeilen = []
    neu = bestehend = vereint = 0
    ordner = {}

    for e in eintraege:
        if e['lfd_id'] in folge:        # steht schon beim Anleger seiner Gruppe
            continue
        if e['status'] == 'kein_treffer':
            gruppe = anleger.get(e['lfd_id'], [e])
            neu += 1
            vereint += len(gruppe) - 1
            # Die Warnung steht **vor** dem CREATE, damit sie beim Durchsehen
            # an der Zeile klebt, um die es geht. QuickStatements überliest
            # Zeilen mit `#`.
            for partner, score in warnung.get(e['lfd_id'], ()):
                zeilen.append(f"# ACHTUNG {e['lfd_id']} {label(e)}: derselbe "
                              f'Mensch steht als {partner} in diesem Export '
                              f'und würde ein zweites Item bekommen '
                              f'(Übereinstimmung {score})')
            if len(gruppe) > 1:
                zeilen.append(
                    f'# ZUSAMMENGEFÜHRT {label(e)}: '
                    + ', '.join(f"{m['lfd_id']} (Ordner {m['ordner']}, "
                                f'„{label(m)}“)' for m in gruppe)
                    + ' — ein Item für alle')
            zeilen.append('CREATE')
            ziel = 'LAST'
            zeilen.append(_zeile('LAST', 'Lde', _s(label(e))))
            if cfg.get('qs_label_en') == 'ja':
                zeilen.append(_zeile('LAST', 'Len', _s(label(e, 'en'))))
            # Aliase: der Geburtsname jedes beteiligten Eintrags und jede
            # abweichende Namensform der Akte. Wer nach „Marie Both" sucht,
            # soll „Maria Roth (geb. Haase)" finden.
            for alias in dict.fromkeys(
                    [m['geburtsname'] for m in gruppe if m['geburtsname']]
                    + [label(m) for m in gruppe[1:] if label(m) != label(e)]):
                zeilen.append(_zeile('LAST', 'Ade', _s(alias)))
            if cfg.get('qs_beschreibung') == 'ja':
                jahre = [wahljahr(m['ordner']) for m in gruppe]
                zeilen.append(_zeile('LAST', 'Dde', _s(beschreibung(e, jahre))))
            vorhanden = frozenset()
        elif e['status'] == 'zugeordnet' and e['ziel_qid']:
            gruppe = [e]
            bestehend += 1
            ziel = e['ziel_qid']
            vorhanden = vorhandene_aussagen.get(ziel, frozenset())
        else:
            continue

        # Die Aussagen aller Einträge der Gruppe an dasselbe Item. Nur der
        # Anleger gilt als „neu" — Mensch, Geburtsdatum und Geschlecht sagt
        # sonst jeder Folgeeintrag ein zweites Mal. Wortgleiche Aussagen fallen
        # weg, verschiedene bleiben: derselbe Ort mit anderem Jahr, die andere
        # Adresse, die andere Wahl und **jede** Fundstelle (P51/P499).
        gesehen = set()
        for m in gruppe:
            ordner[m['ordner']] = ordner.get(m['ordner'], 0) + 1
            m_ziel = 'CREATE' if (ziel == 'LAST' and m is gruppe[0]) else ziel
            for a in aussagen(m, cfg, m_ziel, vorhanden):
                if a in gesehen:
                    continue
                gesehen.add(a)
                zeilen.append(_zeile(ziel, *a))

    jahre = sorted({wahljahr(o) for o in ordner}) or [WAHLJAHR_STANDARD]
    kopf = [
        '# QuickStatements V1 — Wählerverzeichnis Aschersleben '
        + ' und '.join(str(j) for j in jahre),
        f'# {neu} neue Personen (CREATE), {bestehend} bestehende Items ergänzt',
    ]
    for o in sorted(ordner):
        wahlen = [cfg[k] for _, k in wahlspalten(o) if cfg.get(k)]
        kopf.append(f'# Ordner {o} ({wahljahr(o)}): {ordner[o]} Einträge, '
                    f"Primärquelle (P51) {cfg.get(quelle_key(o)) or '— keine'}"
                    f", Wahlen (P119) {', '.join(wahlen) or '— keine'}")
    if vereint:
        kopf.append(f'# {vereint} weitere Registereinträge sind in diese Items '
                    'eingegangen, statt eigene anzulegen — siehe die Zeilen '
                    '„ZUSAMMENGEFÜHRT". Es führt die reichste Namensform; die '
                    'anderen Schreibweisen stehen als Alias am Item, und jeder '
                    'Eintrag behält seine eigene Fundstelle (P51/P499).')
    if warnung:
        kopf.append(f'# ACHTUNG: {len(warnung)} dieser Einträge legen einen '
                    'Menschen an, der in diesem Export noch einmal vorkommt — '
                    'siehe die Zeilen „ACHTUNG" weiter unten.')
    return kopf + [''] + zeilen
