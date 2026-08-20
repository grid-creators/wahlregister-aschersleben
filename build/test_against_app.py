"""E2E-Test gegen den laufenden Server (Port 8770). Kein Netz nötig.

    systemctl restart wahlregister
    python3 build/test_against_app.py
"""

import json
import re
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get('REGISTER_URL', 'http://127.0.0.1:8770')
fails = []


def check(name, cond, info=''):
    print(('  ok   ' if cond else '  FAIL ') + name + (f'  — {info}' if info and not cond else ''))
    if not cond:
        fails.append(name)


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read().decode())


def raw(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return r.status, r.read().decode('utf-8-sig')


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


# Dieser Test läuft gegen den produktiven Dienst und schreibt dabei echte
# Entscheidungen. Er darf nur zurücknehmen, was er selbst gesetzt hat — sonst
# löscht ein Testlauf Handarbeit. (Genau das ist am 7.8.2026 passiert: die
# Aufräumzeile setzte *alle* entschiedenen Einträge einer Straße auf offen.)

def stand_von(lfd):
    e = get('/api/eintrag/' + lfd)
    return {'status': e['status'], 'qid': e['entschieden_qid'],
            'quelle': e['entschieden_quelle'], 'notiz': e['notiz'] or '',
            'p120': e['p120_qid']}


def herstellen(lfd, stand):
    """Den gemerkten Stand zurückschreiben — auch „war offen"."""
    post('/api/entscheidung', {'lfd_id': lfd, 'status': stand['status'] or 'offen',
                               'qid': stand['qid'] or '',
                               'quelle': stand['quelle'] or 'vorschlag',
                               'notiz': stand['notiz'],
                               'bearbeiter': 'Testlauf, Stand wiederhergestellt'})
    post('/api/p120', {'lfd_id': lfd, 'qid': stand['p120'] or '',
                       'bearbeiter': 'Testlauf, Stand wiederhergestellt'})


def freiraeumen(strasse):
    """Eine ganze Straße merken und auf `offen` setzen; gibt den Stand davor
    zurück, damit `herstellen()` ihn am Ende wieder einsetzen kann.

    Die Sammelentscheidung fasst nur `d.status IS NULL` an — inzwischen ist das
    Register aber vollständig entschieden, und ohne offene Einträge könnte der
    Test sie gar nicht mehr prüfen. Er legt sie sich deshalb selbst zurecht.
    Gemerkt wird **jeder** Eintrag der Straße, nicht nur der entschiedene:
    sonst bliebe am Ende offen, was der Test selbst entschieden hat."""
    stand = {r['lfd_id']: stand_von(r['lfd_id']) for r in get(
        '/api/liste?status=&limit=500&strasse='
        + urllib.parse.quote(strasse))['results']}
    for lfd, s in stand.items():
        if s['status']:
            post('/api/entscheidung', {'lfd_id': lfd, 'status': 'offen',
                                       'bearbeiter': 'Testlauf, räumt frei'})
    return stand


print('Seite')
with urllib.request.urlopen(BASE + '/', timeout=20) as r:
    html = r.read().decode()
check('Startseite lädt', r.status == 200 and 'appbar' in html)
check('nur noch eine Seite (keine Alt-Navigation)',
      '/statistik' not in html and '/adressen' not in html)

print('Arbeitsliste')
d = get('/api/liste?status=&limit=5')
check('3399 Einträge aus beiden Ordnern', d['count'] == 3399, d['count'])
check('5 Zeilen', len(d['results']) == 5, len(d['results']))
erste = d['results'][0]
check('Eintrag trägt seine Kandidaten', isinstance(erste['kandidaten'], list))
check('Fortschritt enthält die Zählstände',
      {'gesamt', 'zugeordnet', 'kein_treffer'} <= set(d['fortschritt']))

print('Ordner')
# Geprüft wird die Mechanik, nicht die Zahl: der Bestand wächst, und jeder
# neue Ordner soll den Test nicht brechen, sondern durch ihn laufen.
o = get('/api/ordner')['results']
check('die Ordner werden aufsteigend geführt',
      [x['ordner'] for x in o] == sorted(x['ordner'] for x in o) and len(o) >= 2, o)
check('jeder Ordner nennt seine Quell-CSV', all(x['quelle_csv'] for x in o), o)
check('jeder Ordner hat eine eigene Primärquelle',
      len({x['qs_quelle'] for x in o}) == len(o), o)
check('kein Ordner ist leer', all(x['gesamt'] > 0 for x in o), o)

d3 = get('/api/liste?status=&ordner=3&limit=5')
check('Ordnerfilter greift',
      d3['count'] == next(x['gesamt'] for x in o if x['ordner'] == 3),
      d3['count'])
check('… und liefert nur diesen Ordner',
      all(r['ordner'] == 3 for r in d3['results']))
check('Einträge aus Ordner 3 tragen ihr Präfix',
      d3['results'][0]['lfd_id'].startswith('3-'), d3['results'][0]['lfd_id'])
check('… und das Blatt der Fotografie', bool(d3['results'][0]['bild']),
      d3['results'][0]['bild'])
check('Fortschritt weist die Ordner einzeln aus',
      [x['ordner'] for x in d3['fortschritt']['ordner']]
      == [x['ordner'] for x in o], d3['fortschritt'].get('ordner'))
check('… und die Summe stimmt',
      sum(x['gesamt'] for x in d3['fortschritt']['ordner'])
      == d3['fortschritt']['gesamt'], d3['fortschritt']['ordner'])

# Dieselbe Straße in zwei Ordnern meint verschiedene Häuser. „Liebenwerder
# Plan 20" steht in beiden und hängt an verschiedenen Adressitems — wer den
# Ordner aus dem Join nimmt, exportiert für einen der beiden das falsche Haus.
items = {}
for ordner in (2, 3):
    r = get(f'/api/liste?status=&ordner={ordner}&strasse='
            + urllib.parse.quote('Liebenwerder Plan') + '&limit=200')
    items[ordner] = {x['adress_qid'] for x in r['results'] if x['hausnr'] == '20'}
check('Liebenwerder Plan 20 gibt es in beiden Ordnern',
      all(items[o] for o in (2, 3)), items)
check('… mit je eigenem Adress-Item', not (items[2] & items[3]), items)

d = get('/api/strassen')
check('Straßen werden je Ordner geführt',
      {'ordner', 'strasse', 'n'} <= set(d['results'][0]), d['results'][0])
check('… und dieselbe Straße steht in beiden Ordnern',
      len([s for s in d['results'] if s['strasse'] == 'Liebenwerder Plan']) == 2,
      [s for s in d['results'] if s['strasse'] == 'Liebenwerder Plan'])

d = get('/api/liste?treffer=mit&status=&limit=1')
check('Filter „mit Vorschlag"', d['count'] > 0 and d['results'][0]['n_kandidaten'] > 0,
      d['count'])
ein_lfd = d['results'][0]['lfd_id']
ein_lfd_vorher = stand_von(ein_lfd)   # am Ende wieder herstellen
ein_qid = d['results'][0]['kandidaten'][0]['qid']

d = get('/api/liste?treffer=ohne&status=&limit=1')
check('Filter „ohne Vorschlag"',
      d['count'] > 0 and d['results'][0]['n_kandidaten'] == 0, d['count'])

d = get('/api/liste?q=Badt&status=')
check('Volltextsuche', d['count'] >= 1, d['count'])
d = get('/api/liste?strasse=Badstuben&status=')
check('Straßenfilter', all(r['strasse'] == 'Badstuben' for r in d['results']))

e = get('/api/eintrag/' + ein_lfd)
check('Einzelabruf', e['lfd_id'] == ein_lfd)
check('Kandidat hat die vier Teilscores',
      set(e['kandidaten'][0]['teilscores']) ==
      {'nachname', 'vorname', 'geburtsdatum', 'adresse'},
      e['kandidaten'][0]['teilscores'])

try:
    get('/api/eintrag/9999')
    nf = False
except urllib.error.HTTPError as exc:
    nf = exc.code == 404
check('404 für unbekannte Nummer', nf)

d = get('/api/neu-abgleichen/' + ein_lfd + '?min_score=30')
check('Einzelabgleich rechnet frisch', d['count'] >= 1, d)

print('Adressen')
d = get('/api/liste?status=&limit=200')
mit_adresse = [r for r in d['results'] if r['adress_qid']]
check('Adress-Items sind verknüpft', len(mit_adresse) > 50, len(mit_adresse))

print('Entscheiden')
r = post('/api/entscheidung', {'lfd_id': ein_lfd, 'qid': ein_qid,
                               'status': 'zugeordnet'})
check('Zuordnung quittiert', r['ok'] and r['fortschritt']['zugeordnet'] >= 1, r)
e = get('/api/eintrag/' + ein_lfd)
check('Zuordnung ist gespeichert',
      e['status'] == 'zugeordnet' and e['entschieden_qid'] == ein_qid, e['status'])

r = post('/api/entscheidung', {'lfd_id': ein_lfd, 'status': 'kein_treffer'})
check('„kein Treffer" überschreibt', r['status'] == 'kein_treffer')
e = get('/api/eintrag/' + ein_lfd)
check('… und ist gespeichert', e['status'] == 'kein_treffer' and not e['entschieden_qid'])

try:
    post('/api/entscheidung', {'lfd_id': ein_lfd, 'status': 'zugeordnet', 'qid': 'x'})
    code = 200
except urllib.error.HTTPError as exc:
    code = exc.code
check('ungültige Q-ID wird abgewiesen', code == 400, code)

print('Jede Entscheidung ist möglich')
d = get('/api/suche?q=Spanier&limit=5')
check('freie Suche findet Personen', len(d['results']) >= 3, d)
check('Suchtreffer trägt Q-ID und Label',
      {'qid', 'label', 'url'} <= set(d['results'][0]), d['results'][0])
check('zu kurze Suche wird abgefangen', get('/api/suche?q=a')['results'] == [])

p = get('/api/person/Q878132')
check('bekannte Q-ID wird aufgelöst',
      p['bekannt'] and p['label'] == 'Max Badt', p)
p = get('/api/person/Q99999999')
check('unbekannte Q-ID: zuordenbar, aber mit Warnung',
      p['bekannt'] is False and p['note'], p)
try:
    get('/api/person/keineqid')
    code = 200
except urllib.error.HTTPError as exc:
    code = exc.code
check('Unsinn als Q-ID → 400', code == 400, code)

# Ein Eintrag ohne jeden Vorschlag muss trotzdem entscheidbar sein. Nicht auf
# `status=offen` einschränken: das Register ist inzwischen vollständig
# entschieden, dann gäbe es keinen einzigen Kandidaten für diesen Test mehr.
# Stattdessen den Stand merken und danach wiederherstellen.
ohne = get('/api/liste?treffer=ohne&status=&limit=1')['results'][0]['lfd_id']
ohne_vorher = stand_von(ohne)
r = post('/api/entscheidung', {'lfd_id': ohne, 'status': 'zugeordnet',
                               'qid': 'Q878132', 'quelle': 'qid'})
check('Eintrag ohne Vorschlag ist per Q-ID zuordenbar', r['ok'], r)
e = get('/api/eintrag/' + ohne)
check('… Label wird nachgeschlagen', e['entschieden_label'] == 'Max Badt',
      e['entschieden_label'])
check('… Herkunft wird festgehalten', e['entschieden_quelle'] == 'qid',
      e['entschieden_quelle'])
herstellen(ohne, ohne_vorher)

# Wer in Hopfenmarkt schon vor dem Test entschieden war, ist es auch danach —
# `freiraeumen` merkt sich jeden Stand, ganz unten wird er wieder eingesetzt.
hopfen_vorher = freiraeumen('Hopfenmarkt')

vorher = get('/api/liste?limit=1')['fortschritt']['offen']
r = post('/api/sammelentscheidung',
         {'status': 'kein_treffer', 'filter': {'strasse': 'Hopfenmarkt'}})
check('Sammelentscheidung greift', r['geaendert'] >= 1, r)
check('… und senkt die Zahl der offenen Einträge',
      r['fortschritt']['offen'] == vorher - r['geaendert'],
      (vorher, r['fortschritt']['offen']))
r2 = post('/api/sammelentscheidung',
          {'status': 'kein_treffer', 'filter': {'strasse': 'Hopfenmarkt'}})
check('… überschreibt nichts Entschiedenes', r2['geaendert'] == 0, r2)
try:
    post('/api/sammelentscheidung', {'status': 'zugeordnet', 'filter': {}})
    code = 200
except urllib.error.HTTPError as exc:
    code = exc.code
check('Sammel-Zuordnung ist nicht möglich', code == 400, code)

print('Änderungsprotokoll')
vorher = get('/api/protokoll?limit=1')['gesamt']
post('/api/entscheidung', {'lfd_id': ein_lfd, 'status': 'zugeordnet',
                           'qid': ein_qid, 'bearbeiter': 'Testlauf'})
post('/api/entscheidung', {'lfd_id': ein_lfd, 'status': 'kein_treffer',
                           'bearbeiter': 'Testlauf'})
d = get('/api/protokoll?lfd_id=' + ein_lfd)
check('jede Änderung wird festgehalten',
      get('/api/protokoll?limit=1')['gesamt'] == vorher + 2,
      (vorher, get('/api/protokoll?limit=1')['gesamt']))
letzte = d['results'][0]
check('der Stand davor steht drin',
      letzte['alt_status'] == 'zugeordnet' and letzte['alt_qid'] == ein_qid, letzte)
check('der neue Stand steht drin', letzte['neu_status'] == 'kein_treffer', letzte)
check('Bearbeiter/in wird übernommen', letzte['bearbeiter'] == 'Testlauf', letzte)
check('Eintragsname ist aufgelöst', bool(letzte['name_voll']), letzte)

st, body = raw('/export/protokoll.csv')
check('Protokoll als CSV', st == 200 and ein_lfd in body and 'Testlauf' in body, st)

# Der Verlauf folgt dem Ordnerfilter wie die Liste. Geprüft wird über die
# Summe: jede Protokollzeile gehört zu genau einem Ordner, keine fällt weg.
alle = get('/api/protokoll?limit=1')
je_ordner = {x['ordner']: get('/api/protokoll?limit=1&ordner=%d' % x['ordner'])
             for x in o}
check('Verlauf lässt sich auf einen Ordner eingrenzen',
      all(d['ordner'] == o for o, d in je_ordner.items()), je_ordner)
check('… und die Ordner ergeben zusammen den ganzen Verlauf',
      sum(d['gesamt'] for d in je_ordner.values()) == alle['gesamt'],
      ({o: d['gesamt'] for o, d in je_ordner.items()}, alle['gesamt']))
d = get('/api/protokoll?limit=200&ordner=3')
check('… und liefert nur Zeilen dieses Ordners',
      all(r['ordner'] == 3 and r['lfd_id'].startswith('3-') for r in d['results']),
      [r['lfd_id'] for r in d['results'] if r['ordner'] != 3][:5])
check('Stapel sagen, wie viel von ihnen im Ordner liegt',
      all('n_ordner' in s and s['n_ordner'] <= s['n'] for s in d['stapel']),
      d['stapel'][:2])

zeilen = {x['ordner']: len(raw('/export/protokoll.csv?ordner=%d'
                               % x['ordner'])[1].splitlines()) for x in o}
check('Protokoll-CSV je Ordner',
      sum(zeilen.values()) - len(zeilen) == len(body.splitlines()) - 1,
      (zeilen, len(body.splitlines())))

# Sammelentscheidung: ein Stapel, der sich zurücknehmen lässt
engel_vorher = freiraeumen('Engelgasse')
s = post('/api/sammelentscheidung', {'status': 'kein_treffer', 'bearbeiter': 'Testlauf',
                                     'filter': {'strasse': 'Engelgasse'}})
check('Sammelentscheidung bekommt eine Stapelkennung', bool(s.get('stapel')), s)
d = get('/api/protokoll?stapel=' + s['stapel'])
check('jeder betroffene Eintrag steht im Protokoll',
      len(d['results']) == s['geaendert'], (len(d['results']), s['geaendert']))

# Ein Eintrag des Stapels wird von Hand geändert — der muss die Rücknahme
# überleben, sonst wäre Handarbeit durch einen Klick weg.
betroffen = [r['lfd_id'] for r in d['results']]
post('/api/entscheidung', {'lfd_id': betroffen[0], 'status': 'zugeordnet',
                           'qid': 'Q878132', 'quelle': 'qid', 'bearbeiter': 'Kollegin'})
r = post('/api/stapel-zuruecknehmen', {'stapel': s['stapel'], 'bearbeiter': 'Testlauf'})
check('Sammelentscheidung ist zurücknehmbar',
      r['zurueckgenommen'] == s['geaendert'] - 1, r)
check('… die Handarbeit bleibt unangetastet', r['uebersprungen'] == 1, r)
e = get('/api/eintrag/' + betroffen[0])
check('… und steht unverändert da',
      e['status'] == 'zugeordnet' and e['entschieden_qid'] == 'Q878132', e['status'])
e = get('/api/eintrag/' + betroffen[1])
check('… der Rest ist wieder offen', e['status'] is None, e['status'])
r2 = post('/api/stapel-zuruecknehmen', {'stapel': s['stapel']})
check('zweite Rücknahme ändert nichts mehr', r2['zurueckgenommen'] == 0, r2)
try:
    post('/api/stapel-zuruecknehmen', {'stapel': 'gibtsnicht'})
    code = 200
except urllib.error.HTTPError as exc:
    code = exc.code
check('unbekannter Stapel → 404', code == 404, code)

check('Rücknahmen sind selbst protokolliert',
      any(x['aktion'] == 'ruecknahme'
          for x in get('/api/protokoll?stapel=' + s['stapel'])['results']))
post('/api/entscheidung', {'lfd_id': betroffen[0], 'status': 'offen'})

# Sammelentscheidung im Ordnerfilter: sie darf nur den gewählten Ordner
# anfassen. „Salzkoth" gibt es nur in Ordner 3 — geprüft wird trotzdem, dass
# kein Eintrag aus Ordner 2 im Stapel landet.
salz_vorher = freiraeumen('Salzkoth')
s3 = post('/api/sammelentscheidung',
          {'status': 'kein_treffer', 'bearbeiter': 'Testlauf',
           'filter': {'ordner': '3', 'strasse': 'Salzkoth'}})
check('Sammelentscheidung mit Ordnerfilter greift', s3['geaendert'] >= 1, s3)
betroffen3 = [r['lfd_id'] for r in get('/api/protokoll?stapel=' + s3['stapel'])['results']]
check('… und fasst nur den gewählten Ordner an',
      all(x.startswith('3-') for x in betroffen3), betroffen3[:5])
leer = post('/api/sammelentscheidung',
            {'status': 'kein_treffer',
             'filter': {'ordner': '2', 'strasse': 'Salzkoth'}})
check('… eine Straße im falschen Ordner trifft nichts', leer['geaendert'] == 0, leer)
post('/api/stapel-zuruecknehmen', {'stapel': s3['stapel'], 'bearbeiter': 'Testlauf'})

print('P120 „Möglicherweise identisch mit"')
p120_lfd = ein_lfd
p120_vorher = stand_von(p120_lfd)
r = post('/api/p120', {'lfd_id': p120_lfd, 'qid': 'q878132',
                       'bearbeiter': 'Testlauf'})
check('Q-ID wird vorgemerkt', r['ok'] and r['p120_qid'] == 'Q878132', r)
check('… Label wird nachgeschlagen', r['p120_label'] == 'Max Badt', r['p120_label'])
e = get('/api/eintrag/' + p120_lfd)
check('… und steht am Eintrag', e['p120_qid'] == 'Q878132', e['p120_qid'])
check('… ohne die Entscheidung anzufassen', e['status'] == p120_vorher['status'],
      e['status'])
check('… und ist protokolliert',
      any(x['aktion'] == 'p120' and x['neu_qid'] == 'Q878132'
          for x in get('/api/protokoll?lfd_id=' + p120_lfd)['results']))

try:
    post('/api/p120', {'lfd_id': p120_lfd, 'qid': 'Unsinn'})
    code = 200
except urllib.error.HTTPError as exc:
    code = exc.code
check('unsinnige Q-ID → 400', code == 400, code)

try:
    post('/api/p120', {'lfd_id': '9999', 'qid': 'Q1'})
    code = 200
except urllib.error.HTTPError as exc:
    code = exc.code
check('unbekannter Eintrag → 404', code == 404, code)

r = post('/api/p120', {'lfd_id': p120_lfd, 'qid': 'Q999999999'})
check('Q-ID außerhalb des Auszugs wird angenommen',
      r['ok'] and r['bekannt'] is False, r)

# Selbstbezug: was fest zugeordnet ist, kann nicht zugleich „möglicherweise
# identisch" sein.
post('/api/entscheidung', {'lfd_id': p120_lfd, 'status': 'zugeordnet',
                           'qid': 'Q878132', 'quelle': 'qid'})
try:
    post('/api/p120', {'lfd_id': p120_lfd, 'qid': 'Q878132'})
    code = 200
except urllib.error.HTTPError as exc:
    code = exc.code
check('Selbstbezug → 400', code == 400, code)

# Export: P120 hängt am entschiedenen Eintrag. Gezählt, nicht gesucht: dieselbe
# Q-ID kann an einem anderen Eintrag von Hand vorgemerkt sein (Q1351615 hängt
# an 0001) — dann sagt „steht im Export" für sich genommen nichts.
def p120_zeilen(qid):
    return sum(1 for l in get('/api/quickstatements')['zeilen']
               if l.endswith('\tP120\t' + qid))


p120_zahl = p120_zeilen('Q1351615')
post('/api/p120', {'lfd_id': p120_lfd, 'qid': 'Q1351615'})
check('P120 steht im Export', p120_zeilen('Q1351615') == p120_zahl + 1, p120_zahl)

post('/api/p120', {'lfd_id': p120_lfd, 'qid': ''})
e = get('/api/eintrag/' + p120_lfd)
check('leere Q-ID löscht die Vormerkung', e['p120_qid'] is None, e['p120_qid'])
check('… und sie verschwindet aus dem Export',
      p120_zeilen('Q1351615') == p120_zahl, p120_zahl)

print('QuickStatements')
d = get('/api/quickstatements')
check('Export enthält Zeilen', d['anzahl'] > 4, d['anzahl'])
txt = '\n'.join(d['zeilen'])
check('CREATE für „kein Treffer"', 'CREATE' in txt)
check('P2 = Q7 gesetzt', '\tP2\tQ7' in txt)
check('Primärquelle gesetzt', '\tP51\t' in txt)
st, body = raw('/export/quickstatements.txt')
check('Download liefert dieselbe Tabelle', st == 200 and 'CREATE' in body)

# Der Export lässt sich auf einen Ordner eingrenzen, und jeder Ordner trägt
# seine eigene Primärquelle — sonst hinge Ordner 3 am Archivale von Ordner 2.
# Nicht über die Zeilenzahl geprüft: solange ein Ordner unentschieden ist,
# steuert er nichts bei, und der Teilexport ist so groß wie der ganze.
quellen = {x['ordner']: x['qs_quelle'] for x in get('/api/ordner')['results']}


def ordner_kopf(zeilen):
    """Die Kopfzeilen „# Ordner N: X Einträge" als {N: X}."""
    treffer = (re.match(r'# Ordner (\d+): (\d+) Einträge', z) for z in zeilen)
    return {int(m.group(1)): int(m.group(2)) for m in treffer if m}


ganz = ordner_kopf(d['zeilen'])
check('der Kopf weist die exportierten Ordner aus', bool(ganz), d['zeilen'][:6])
teile = {o: get('/api/quickstatements?ordner=%d' % o)['zeilen'] for o in quellen}
check('jeder Ordner-Export enthält nur seinen Ordner',
      all(set(ordner_kopf(z)) <= {o} for o, z in teile.items()),
      {o: ordner_kopf(z) for o, z in teile.items()})
check('die Ordner-Exporte ergeben zusammen den ganzen',
      {o: ordner_kopf(z).get(o, 0) for o, z in teile.items()}
      == {o: ganz.get(o, 0) for o in teile},
      ({o: ordner_kopf(z) for o, z in teile.items()}, ganz))
for o, zeilen in teile.items():
    fremd = [q for x, q in quellen.items() if x != o]
    check(f'Ordner {o} trägt nur seine eigene Primärquelle',
          all(z.split('\t')[2] == quellen[o] for z in zeilen if '\tP51\t' in z)
          and not any(q in '\n'.join(zeilen) for q in fremd),
          [z for z in zeilen if '\tP51\t' in z][:3])

st, body = raw('/export/entscheidungen.csv')
check('CSV-Export', st == 200 and ein_lfd in body)
check('… mit dem Ordner in der Kopfzeile', body.splitlines()[0].startswith('ordner,'),
      body.splitlines()[0])

print('Einstellungen')
d = get('/api/einstellungen')
check('Vorbelegung nach dem Muster-Item', d['qs_ort'] == 'Q80706', d)
check('Primärquelle je Ordner',
      d['qs_quelle_o2'] == 'Q2080842' and d['qs_quelle_o3'] == 'Q2084011', d)
try:
    post('/api/einstellungen', {'qs_ort': 'keine-qid'})
    code = 200
except urllib.error.HTTPError as exc:
    code = exc.code
check('unsinnige Q-ID wird abgewiesen', code == 400, code)

print('Offener Zugang von außen')
# Die App verlangt kein Recht: entscheiden und herunterladen geht ohne alles.
PUB = os.environ.get('REGISTER_PUBLIC_URL', 'http://185.162.251.195:8770')
try:
    with urllib.request.urlopen(PUB + '/api/liste?limit=1', timeout=10) as r:
        json.loads(r.read().decode())
    erreichbar = True
except Exception:
    erreichbar = False
if not erreichbar:
    print('  --   öffentliche Adresse nicht erreichbar, übersprungen')
else:
    def pub_post(pfad, payload):
        req = urllib.request.Request(
            PUB + pfad, data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode())

    eins_vorher = stand_von('0001')
    code, r = pub_post('/api/entscheidung',
                       {'lfd_id': '0001', 'status': 'kein_treffer'})
    check('Entscheiden von außen ist möglich', code == 200 and r['ok'], (code, r))
    code, r = pub_post('/api/sammelentscheidung',
                       {'status': 'kein_treffer', 'filter': {'strasse': 'Hopfenmarkt'}})
    check('Sammelentscheidung von außen ist möglich', code == 200, code)
    with urllib.request.urlopen(PUB + '/export/quickstatements.txt', timeout=20) as r:
        body = r.read().decode('utf-8-sig')
    check('QuickStatements von außen herunterladbar',
          r.status == 200 and 'CREATE' in body, r.status)
    with urllib.request.urlopen(PUB + '/export/entscheidungen.csv', timeout=20) as r:
        check('CSV von außen herunterladbar', r.status == 200)
    herstellen('0001', eins_vorher)

# Testentscheidungen zurücknehmen — aber nur die eigenen. Jeder angefasste
# Eintrag geht auf den Stand zurück, den er vor dem Lauf hatte. `ein_lfd` zuletzt
# und getrennt: es hat einen eigenen gemerkten Stand von vor allen Straßen-
# aktionen, und der ist der ältere.
for strasse in (hopfen_vorher, engel_vorher, salz_vorher):
    for lfd, stand in strasse.items():
        if lfd != ein_lfd:
            herstellen(lfd, stand)
herstellen(ein_lfd, ein_lfd_vorher)
print()
if fails:
    print(f'{len(fails)} Test(s) fehlgeschlagen: ' + ', '.join(fails))
    sys.exit(1)
print('alle Tests bestanden')
