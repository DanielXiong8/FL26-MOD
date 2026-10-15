# -*- coding: utf-8 -*-
"""make_plan.py v2 - full 20-club plan: RENAME / TRANSFER / INJECT / REMOVE.
All matches are CLUB-SCOPED (same obfuscated name at another club = another person).
Sources: 189 authoritative matched pairs + hand-verified same-club match-fixes
(CLUB_FIXES) + hand-verified transfers (TRANSFERS) + target-squad driven injects.
"""
import json

BASE = r'D:\FL26_Mod\work\fc26_alignment'
db = json.load(open(BASE + r'\db_survey.json', encoding='utf-8'))
rep = json.load(open(BASE + r'\pl_gap_report.json', encoding='utf-8'))
sq = json.load(open(BASE + r'\squad_pl_full.json', encoding='utf-8'))
OVR = json.load(open(BASE + r'\ovr_dict.json', encoding='utf-8'))

PL = {
 'Arsenal':20030,'Liverpool':20027,'Chelsea':20028,'Tottenham':20029,'Newcastle':20037,
 'ManCity':20026,'ManUnited':20031,'Bournemouth':20046,'AstonVilla':20039,'Brentford':20036,
 'Brighton':20035,'CrystalPalace':20038,'Everton':20041,'Fulham':20367,'Coventry':20324,
 'Ipswich':20398,'HullCity':20313,'NottinghamForest':20050,'Sunderland':20311,'WestHam':20032
}

# ---------- hand-verified same-club match fixes (obf -> real), club-scoped ----------
CLUB_FIXES = {
 'Tottenham': {'Simond':'Xavi Simons','Galagher':'Conor Gallagher','Madison':'James Maddison',
   'Bergval':'Lucas Bergvall','Odober':'Wilson Odobert','Richarlisson':'Richarlison',
   'Kutos':'Mohammed Kudus','Graey':'Archie Gray','Tell':'Mathys Tel'},
 'Newcastle': {'Pop':'Nick Pope','Scher':'Fabian Schär','Gillespee':'Mark Gillespie',
   'Livramanto':'Tino Livramento','Hail':'Lewis Hall','Bortman':'Sven Botman',
   'J.Ramsee':'Jacob Ramsey','Willok':'Joe Willock','Wisa':'Yoane Wissa',
   'Osela':'William Osula','Barns':'Harvey Barnes','Eranga':'Anthony Elanga',
   'Murfee':'Jacob Murphy'},
 'ManCity': {'Donaruma':'Gianluigi Donnarumma','Bettinelly':'Marcus Bettinelli',
   'Ruben':'Rúben Dias','Guehi':'Marc Guéhi','Gvardior':'Joško Gvardiol',
   'Akt-Nuri':'Rayan Aït-Nouri','Kovachic':'Mateo Kovačić','Cherky':'Rayan Cherki',
   'Fodan':'Phil Foden','Harland':'Erling Haaland','Semenllo':'Antoine Semenyo',
   'Douku':'Jérémy Doku'},
 'ManUnited': {'S.Lamens':'Senne Lammens','Herton':'Tom Heaton','Dorgu':'Patrick Dorgu',
   'Darot':'Diogo Dalot','de Liht':'Matthijs de Ligt','Tilemans':'Youri Tielemans',
   'B.Fernandez':'Bruno Fernandes','Mownt':'Mason Mount','Cunia':'Matheus Cunha',
   'Zirkse':'Joshua Zirkzee'},
 'Bournemouth': {'Petrovich':'Djordje Petrović','Hell':'James Hill','J.Solar':'Julio Soler',
   'L.Cork':'Lewis Cook','Toht':'Alex Tóth','Evanilsen':'Evanilson','Kruivert':'Justin Kluivert',
   'Adly':'Amine Adli','Kroupy':'Junior Kroupi','Rayen':'Rayan',
   'Milosavljevic':'Veljko Milosavljević'},
 'Brentford': {'Schader':'Kevin Schade'},
 'Everton': {'Kin':'Tom King','Keen':'Michael Keane'},
 'Fulham': {'Belge':'Sander Berge'},
 'Coventry': {'Eckles':'Josh Eccles'},
 'Ipswich': {'Parmer':'Alex Palmer','Buton':'David Button','Waltom':'Christian Walton',
   'Fulong':'Darnell Furlong','Dayvis':'Leif Davis','Kipe':'Cédric Kipré',
   'Graves':'Jacob Greaves',"O'Shia":"Dara O'Shea",'Matusina':'Azor Matusiwa',
   'Tyler':'Jack Taylor','Nunez':'Marcelino Núñez','Philogane':'Jaden Philogene',
   'Mcater':'Kasey McAteer','Mehmedi':'Anis Mehmeti','Clake':'Jack Clarke'},
 'HullCity': {'Phillipes':'Dillon Phillips','Coile':'Lewie Coyle','Gills':'Ryan Giles',
   'Haghes':'Charlie Hughes','Azayi':'Semi Ajayi','Eagan':'John Egan','McNail':'Paddy McNair',
   'Mateso':'Eliot Matazo','Gelhart':'Joe Gelhardt','Ó.Zanbrano':'Óscar Zambrano',
   'Crocks':'Matt Crooks','K.Dower':'Kieran Dowell','Sleater':'Regan Slater',
   'McBurny':'Oli McBurnie','M.Belloumy':'Mohamed Belloumi'},
 'NottinghamForest': {'Mcater':'James McAtee','Yayts':'Ryan Yates','Neitz':'Luca Netz'},
 'Sunderland': {'More':'Simon Moore','Roaf':'Robin Roefs','Arderete':'Omar Alderete',
   'Reinirdo':'Reinildo','Mukieler':'Nordi Mukiele','T.Humer':'Trai Hume',
   'Riggins':'Chris Rigg',"O'Niern":"Luke O'Nien",'Diara':'Habib Diarra',
   'Sadici':'Noah Sadiki','E.LeFey':'Enzo Le Fée','Abdullah':'Abdoullah Ba',
   'Talvi':'Chemsdine Talbi','Brobey':'Brian Brobbey','Anguro':'Nilson Angulo',
   'Mundy':'Romaine Mundle','Isidar':'Wilson Isidor','Ta Be':'Jocelin Ta Bi','Ballowd':'Daniel Ballard','Zhaka':'Granit Xhaka'},
 'Chelsea': {'Roggers':'Morgan Rogers'},
 'CrystalPalace': {'Sal':'Ismaïla Sarr'},
 'Barcelona': {'Valde':'Alejandro Balde'},
 'RealMadrid': {'Asancio':'Raul Asencio','Theballos':'Dani Ceballos'},
 'Sevilla': {'I.Romelo':'Isaac Romero','Calmona':'Jose Angel Carmona',
             'Suaso':'Gabriel Suazo'},
 'Levante': {'M.Ryen':'Mathew Ryan','Bruge':'Roger Brugue','O.Reid':'Oriol Rey',
             'Orasagasti':'Jon Ander Olasagasti','V.Garciaa':'Victor Garcia',
             'Romelo':'Ivan Romero','Etta Eiong':'Karl Etta Eyong'},
 'Malaga': {'Garirea':'Einar Galilea','Murilo':'Diego Murillo','Purga':'Carlos Puga',
            'Morino':'Izan Merino','Rolenso':'Dani Lorenzo','Dotol':'Carlos Dotor',
            'Joaquin':'Joaquin Munoz','Rarrubia':'David Larrubia','Haytam':'Haitam',
            'A.Pastol':'Alex Pastor'},
 'WestHam': {'Kirman':'Max Kilman'},
}

# ---------- hand-verified transfers (real, src_game, src_team_hint, dst, jersey, ovr) ----------
# ovr None => keep the source card's own rating (game value stays)
LIGA = {'Barcelona':20101,'RealMadrid':20102,'AtleticoMadrid':20103,'Valencia':20104,
 'Getafe':20105,'Sevilla':20106,'Espanyol':20107,'AthleticBilbao':20108,
 'RealSociedad':20109,'Alaves':20110,'Villarreal':20113,'Osasuna':20114,
 'RealBetis':20119,'CeltaVigo':20120,'RayoVallecano':20121,'Elche':20122,
 'Levante':20123,'Malaga':20301,'RacingSantander':20304,'Deportivo':20396}
CLUB_ID = {c: t for c, t in PL.items()}
CLUB_ALL = {**LIGA, **PL}
CLUB_ID.update({'Paris':20051,'Roma':20081,'Barcelona':20101,'Strasbourg':20061,
                'Frankfurt':20131,'MexicoCity':20595,'Southampton':20040,'Wolves':20033})
TRANSFERS = [
 ('Bradley Barcola',      'Barcora',      CLUB_ID['Paris'],      'Liverpool',        29, 84),
 ('Kostas Tsimikas',      'Tsimikars',    CLUB_ID['Roma'],       'Liverpool',        21, 76),
 ('Ronald Araujo',        'R.Alaojo',     CLUB_ID['Barcelona'],  'Liverpool',        33, 85),
 ('Alejandro Garnacho',   'Ganacho',      CLUB_ID['Chelsea'],    'AstonVilla',        0, 79),
 ('Ben Chilwell',         'Chilweel',     CLUB_ID['Strasbourg'], 'CrystalPalace',    33, 75),
 ('Arnaud Kalimuendo',    'Kalimendo',    CLUB_ID['Frankfurt'],  'NottinghamForest', 15, 74),
 ('Julián Araujo',        'Araujo',       CLUB_ID['MexicoCity'], 'Bournemouth',       2, 72),
 ('Andy Robertson',       'Roberson',     CLUB_ID['Liverpool'],  'Tottenham',         0, None),
 ('Jan Paul van Hecke',   'van Hercke',   CLUB_ID['Brighton'],   'Tottenham',         0, None),
 ('Marcos Senesi',        'Seresi',       CLUB_ID['Bournemouth'],'Tottenham',         0, None),
 ('Mykhaylo Mudryk',      'Mudrick',      CLUB_ID['Chelsea'],    'Tottenham',         0, None),
 ('Andrey Santos',        'Andrei',       CLUB_ID['Chelsea'],    'ManUnited',        17, None),
 ('Marcus Rashford',      'Roshford',     CLUB_ID['Barcelona'],  'ManUnited',         9, None),
 ('Maxence Lacroix',      'Lakroix',      CLUB_ID['CrystalPalace'],'Chelsea',         5, None),
 ('Taylor Harwood-Bellis','Harwod-Bellis',CLUB_ID['Southampton'],'AstonVilla',        4, None),
 ('Daniel Muñoz',         'Munioz',       CLUB_ID['CrystalPalace'],'NottinghamForest',27, None),
 ('Morato',               'Morado',       CLUB_ID['NottinghamForest'],'WestHam',       5, None),
 ('Joël Veltman',         'Vertman',      CLUB_ID['Brighton'],   'WestHam',          34, None),
 ('Kevin Danso',          'Danson',       CLUB_ID['Tottenham'],  'Sunderland',        4, None),
 ('Tim Iroegbunam',       'Iroegbrnam',   CLUB_ID['Everton'],    'HullCity',         42, None),
 ('Saša Lukić',           'Lurkic',       CLUB_ID['Fulham'],     'Ipswich',          23, None),
 ('Taiwo Awoniyi',        'Awniy',        CLUB_ID['NottinghamForest'],'Coventry',    14, None),
 ('Gustavo Hamer',        'Chamer',       None,                  'Coventry',         38, None),
 ('Dan Bentley',          'Bently',       CLUB_ID['Wolves'],     'Coventry',         25, None),
 ('Ezri Konsa',           'Konsah',       CLUB_ID['AstonVilla'], 'Arsenal',          15, None),
 ('Axel Disasi',          'Dizasi',       CLUB_ID['WestHam'],    'CrystalPalace',     5, None),
 ('Dwight McNeil',        'McNell',       CLUB_ID['Everton'],    'CrystalPalace',    11, None),
 ('Arne Engels',          'Engels',       20211,                 'WestHam',           7, None),
 ('Ousmane Diomande',     'Diaomande',    'NT',                  'NottinghamForest',  2, None),
 ('Joan Garcia',          'Garsia',       20101,                 'Barcelona',          1, None),
 ('Wojciech Szczesny',    'Szcsesny',     20101,                 'Barcelona',         13, None),
 ('Marc Cucurella',       'Cucureya',     20028,                 'RealMadrid',        17, None),
 ('Bernardo Silva',       'Bernaldo',     20026,                 'RealMadrid',        20, None),
 ('Gabriel Jesus',        'G.Jersus',     20030,                 'Barcelona',          9, None),
 ('Rodri',                'Rodriguez',    20026,                 'Barcelona',         16, None),
 ('Anthony Gordon',       'Gordin',       20037,                 'Barcelona',         17, None),
 ('Cristian Romero',      'Romeyro',      20029,                 'AtleticoMadrid',    21, None),
 ('Victor Munoz',         'V.Munoz',      20114,                 'Liverpool',         23, None),
 ('Enes Unal',            'E.Unar',       20046,                 'Getafe',            19, None),
 ('Fran Garcia',          'F.Garsia',     20102,                 'RealBetis',         11, None),
 ('Altay Bayindir',       'Bayindur',     20031,                 'CeltaVigo',          1, None),
 ('Nemanja Gudelj',       'Gudely',       20106,                 'Getafe',             8, None),
 ('Dani Ceballos',        'Theballos',    20102,                 'RealBetis',         25, None),
]

# ---------- extra OVR for new injects (merged over ovr_dict) ----------
OVR_EXTRA = {
 'Lukas Hornicek':72,'Lukáš Horníček':72,'Ewen Jaouen':55,'Aidan Harris':58,
 'Bazoumana Touré':75,'Gerónimo Rulli':80,'Iliman Ndiaye':78,'Allan':74,'Karl Darlow':70,
 'Tyler Fletcher':60,'Victor Lindelöf':74,'Christian Walton':70,'Issa Diop':72,
 'Abdoul Ouattara':70,'Florentino Luís':76,'Exequiel Palacios':74,'Abdul Fatawu':74,
 'Sindre Walle Egeli':66,'Zian Flemming':72,'Julio Enciso':73,'Emersonn':66,
 'Chuba Akpom':71,'Daizen Maeda':77,'Kjell Scherpen':70,'Jack Butland':73,
 'Konstantinos Tzolakis':72,'Brooke Norton-Cuffy':70,'Lucas Herrington':58,
 'Matt Targett':71,'Nobel Mendy':65,'Hidemasa Morita':74,'Jens Hjertø-Dahl':64,
 'Lucas Gourna-Douath':70,'Abdülkadir Ömür':68,'Christos Mouzakitis':66,
 'Sorba Thomas':72,'Elliot Stroud':64,'Ilyas Ansah':68,'Robinio Vaz':62,
 'Mohamed-Ali Cho':70,'Steven Benda':68,'Xaver Schlager':77,'Liam Delap':76,
 'Melker Ellborg':62,'Dayann Methalie':60,'Thomas Meunier':73,'Alan Browne':70,
 'Jules Ahoka':60,'Malick Fofana':76,'Juan Riquelme Angulo':62,'Mohamadou Kanté':68,
 'Keiber Lamadrid':66,'Harrison Reed':68,'Hugo Larsson':74,'Oscar Bobb':74,
 'Ben Wilson':66,'Stephen Mfuni':62,'Aurèle Amenda':70,'Caleb Yirenkyi':64,
 'Haji Wright':70,'Sidiki Cherif':60,'Illan Meslier':79,'Kjell':70,
 'Ethan Pinnock':73,
}
OVR.update(OVR_EXTRA)

# ---------- resolve pids ----------
def roster_of(tid):
    return db['teams'].get(str(tid), {}).get('roster', [])

def pids_by_name(tid):
    d = {}
    for p in roster_of(tid):
        d.setdefault(p['name'], []).append(p['pid'])
    return d

def find_team_of(gname):
    for tid, t in db['teams'].items():
        if t.get('national'):
            continue
        for p in t.get('roster', []):
            if p['name'] == gname:
                return int(tid)
    return None

RENAME = {}
# (a) 189 authoritative matched pairs (pid-scoped)
for club, r in rep.items():
    byname = pids_by_name(r['tid'])
    for real, num, gname, gjersey, score in r['matched']:
        pids = byname.get(gname, [])
        if len(pids) == 1:
            RENAME[pids[0]] = real
# (b) same-club match fixes
FIXED = set()  # (club, real) now keeps
for club, fixes in CLUB_FIXES.items():
    byname = pids_by_name(CLUB_ALL[club])
    roster = {p['pid']: p for p in roster_of(CLUB_ALL[club])}
    for gname, real in fixes.items():
        pids = byname.get(gname, [])
        if len(pids) == 1:
            RENAME[pids[0]] = real
            FIXED.add((club, real))
        elif len(pids) > 1:
            # same obf name twice in one club (data artifact): rename highest-OVR pid
            best = max(pids, key=lambda q: roster[q]['attrs'][1])
            RENAME[best] = real
            FIXED.add((club, real))
            print('  FIX multi-pid pick by OVR: %s %s -> pid %d' % (club, gname, best))

# (c) transfers
TRANSFER = []
transfer_reals = set()
for real, src_game, src_hint, dst_club, jersey, ovr in TRANSFERS:
    if src_hint == 'NT':  # player exists only in a national team: rename + keep NT + add club
        src_team = None
        for tid2, t2 in db['teams'].items():
            if t2.get('national') and any(p['name'] == src_game for p in t2.get('roster', [])):
                src_team = int(tid2); break
    else:
        src_team = src_hint if src_hint else find_team_of(src_game)
    if src_team is None:
        print('  TRANSFER no source:', real, src_game)
        continue
    pids = pids_by_name(src_team).get(src_game, [])
    if len(pids) != 1:
        print('  TRANSFER src pid ambiguous(%d): %s @%s' % (len(pids), src_game, src_team))
        continue
    pid = pids[0]
    RENAME[pid] = real
    transfer_reals.add(real)
    TRANSFER.append({'pid': pid, 'src_team': src_team, 'src_name': src_game,
                     'dst_club': dst_club, 'new_team': CLUB_ALL[dst_club],
                     'jersey': jersey, 'ovr': ovr, 'real': real})

# (d) leaver renames (curated)
CURATED_LEAVERS = {
 'Liverpool': {'M.Zalah': 'Mohamed Salah', 'Konate': 'Ibrahima Konate'},
}
REMOVE = []
for club, names in CURATED_LEAVERS.items():
    for p in roster_of(PL[club]):
        if p['name'] in names:
            REMOVE.append({'team': PL[club], 'pid': p['pid'], 'name': p['name']})
            RENAME[p['pid']] = names[p['name']]

# ---------- INJECT: target-driven, all 20 clubs ----------
# Liverpool: full target lives in liverpool_gap.json (squad file only has _ref);
# real 2026-27 numbers from the club page (fetched 2026-10-02).
LIV_GAP = json.load(open(BASE + r'\liverpool_gap.json', encoding='utf-8'))
LIV_NUM = {'Jeremy Jacquet':5,'Kostas Tsimikas':21,'Ronald Araujo':33,'Luke Chambers':44,
           'James McConnell':53,'Victor Munoz':23,'Bradley Barcola':29,'Lewis Koumas':67,
           'Jayden Danns':76,'Vitezslav Jaros':56,'Harvey Davies':95}
LIV_POS = {'Giorgi Mamardashvili':'GK','Vitezslav Jaros':'GK','Harvey Davies':'GK',
           'Jeremy Jacquet':'DF','Kostas Tsimikas':'DF','Ronald Araujo':'DF',
           'Luke Chambers':'DF','James McConnell':'MF','Federico Chiesa':'FW',
           'Victor Munoz':'FW','Bradley Barcola':'FW','Lewis Koumas':'FW','Jayden Danns':'FW'}

EXCLUDE_INJECT = {('CrystalPalace', 'Evann Guessand')}  # matched at Villa; target conflict
INJECT = []
for club, tid in PL.items():
    if club == 'Liverpool':
        continue
    matched_reals = {m[0] for m in rep.get(club, {}).get('matched', [])}
    keeps = matched_reals | {real for c, real in FIXED if c == club}
    for pos in ('GK', 'DF', 'MF', 'FW'):
        for num, nm in sq.get(club, {}).get(pos, []) or []:
            if nm in keeps or nm in transfer_reals or (club, nm) in EXCLUDE_INJECT:
                continue
            jersey = int(num) if str(num).isdigit() and int(num) > 0 else 0
            INJECT.append({'club': club, 'team_id': tid, 'name': nm, 'jersey': jersey,
                           'pos': pos, 'ovr': OVR.get(nm, 70)})

# Liverpool injects = gap missing - transfers (matched stay via RENAME)
liv_matched = {m[0] for m in rep['Liverpool']['matched']}
for nm, pos in LIV_GAP['missing']:
    if nm in transfer_reals or nm in liv_matched:
        continue
    INJECT.append({'club': 'Liverpool', 'team_id': PL['Liverpool'], 'name': nm,
                   'jersey': LIV_NUM.get(nm, 0), 'pos': LIV_POS.get(nm, pos if pos != '?' else 'MF'),
                   'ovr': OVR.get(nm, 70)})

# ======================= LA LIGA (Spanish League A) =======================
sqes = json.load(open(BASE + r'\squad_laliga.json', encoding='utf-8'))
mt = json.load(open(BASE + r'\laliga_match1.json', encoding='utf-8'))
REJECT = {('RealMadrid','Bernardo Silva'),('Sevilla','Peque Fernandez'),
 ('RealBetis','Cucho Hernandez'),('Getafe','Andres Garcia'),
 ('Deportivo','Riki Rodriguez')}
for club, o in mt.items():
    for p in o['pairs']:
        if (club, p['real']) in REJECT:
            continue
        RENAME[p['pid']] = p['real']
        FIXED.add((club, p['real']))
# loaned-in players: keep at parent club (game has no loan state)
LOAN_SKIP = {
 'Valencia': {'Harvey Elliott','Kayne van Oevelen'},
 'Espanyol': {'Unai Nunez','Andoni Gorosabel','Quilindschy Hartman','Gabriel Moscardo',
              'Vanja Drkusic','Bryan Zaragoza'},
 'RealSociedad': {'Mamadou Sarr'},
 'RealBetis': {'Diego Conde'},
 'RayoVallecano': {'Adria Pedrosa','Emil Audero','Marash Kumbulla','Mujaid Sadick'},
 'Elche': {'Facundo Buonanotte','Thomas Lemar'},
 'Levante': {'Ifeanyi Ndukwe','Hugo Sotelo','Dani Requena','Petar Ratkov','Axel Tape',
             'Thiago Fernandez','Manu Sanchez'},
 'Malaga': {'Jens Cajuste','Jose Salinas','Adam Aznou'},
 'RacingSantander': {'Andre Almeida','Jeanuel Belocian','Matteo Prati','Yassir Zabiri'},
 'Deportivo': {'Marc Casado','Jose Maria Gimenez','Angelino'},
}
NAT_EX = {'Dominik Livakovic':'Croatia','Karim Adeyemi':'Germany','Roony Bardghji':'Sweden',
 'Denzel Dumfries':'Netherlands','Yan Diomande':'Ivory Coast','Endrick':'Brazil',
 'Lee Kang-in':'South Korea','Morten Hjulmand':'Denmark','Ademola Lookman':'Nigeria',
 'Jonathan David':'Canada','Kayne van Oevelen':'Netherlands','Mouctar Diakhaby':'Guinea',
 'Justin de Haas':'Netherlands','Aliou Dieng':'Mali','Ryunosuke Sato':'Japan',
 'Pablo Maffeo':'Argentina','Saba Sazonov':'Georgia','Abdel Abqar':'Morocco',
 'Johan Mojica':'Colombia','Nemanja Gudelj':'Serbia','Orel Mangala':'Belgium',
 'Jean Ives Valou':'Ivory Coast','Arouna Sangante':'Senegal','Gabriel Suazo':'Chile',
 'Lucien Agoume':'France','Giorgi Kochorashvili':'Georgia','Youssouf Fofana':'France',
 'Robbie Ure':'Scotland','Lucas Stassin':'Belgium','Felix Correia':'Portugal',
 'Clemens Riedel':'Germany','Alex Padilla':'Mexico','Johaneko Louis-Jean':'France',
 'Job Ochieng':'Kenya','Adrian Rodriguez':'Argentina','Gregoire Swiderski':'Canada',
 'Nicolas Valentini':'Argentina','Facundo Garces':'Argentina','Ville Koski':'Finland',
 'Carlos Protesoni':'Uruguay','Selu Diallo':'Guinea','Peter Gulacsi':'Hungary',
 'Alassane Diatta':'Senegal','Nathan Saliba':'Canada','Ilias Akhomach':'Morocco',
 'Nicolas Pepe':'Ivory Coast','Rockson Yeboah':'Ghana','Romain Del Castillo':'France',
 'Jonathan Dubasin':'Belgium','Valentin Gomez':'Argentina','Junior Firpo':'Dominican Republic',
 'Facundo Bernal':'Uruguay','Troy Parrott':'Ireland','Ionut Radu':'Romania',
 'Abdoulaye Faye':'Senegal','Sebastian Caceres':'Uruguay','Couhaib Driouech':'Morocco',
 'Jones El-Abdellaoui':'Morocco','Giorgi Tsitaishvili':'Georgia','Alejandro Iturbe':'Spain',
 'Roy Revivo':'Israel','Kevin Lomonaco':'Argentina','Matia Barzic':'Croatia',
 'Martim Neto':'Portugal','Ali Houary':'Morocco','Ezequiel Ponce':'Argentina',
 'Lucas Cepeda':'Chile','Abiel Osorio':'Argentina','Aissa Mandi':'Algeria',
 'Enzo Bardeli':'France','Yanis Musuayi':'Belgium','Simon Eriksson':'Sweden',
 'Pedro Felipe':'Brazil','Giorgi Guliashvili':'Georgia','Lorenzo Amatucci':'Italy',
 'Jonathan Asp Jensen':'Denmark','Bright Ede':'Poland',
 'Pierre-Emerick Aubameyang':'Gabon','Bil Nsongo':'Cameroon','Jeremy Toljan':'Germany'}
_nat_lc_names = set()
for club, tid in LIGA.items():
    keeps = {real for c, real in FIXED if c == club}
    for num, nm, pos in sqes.get(club, []):
        if nm in keeps or nm in transfer_reals or nm in LOAN_SKIP.get(club, set()):
            continue
        jersey = int(num) if isinstance(num, int) and num > 0 else 0
        INJECT.append({'club': club, 'team_id': tid, 'name': nm, 'jersey': jersey,
                       'pos': pos, 'ovr': 70,
                       'nat': NAT_EX.get(nm, 'Spain')})
# Konate: removed from Liverpool (leaver) -> attach to Real Madrid as free agent
ATTACH = [{'pid': 111411, 'team': 20102, 'jersey': 16, 'ovr': None}]
INJECT = [e for e in INJECT if not (e['club'] == 'RealMadrid' and e['name'] == 'Ibrahima Konate')]
INJECT = [e for e in INJECT if not (e['club'] == 'Barcelona' and e['name'] == 'Alejandro Balde')]
INJECT = [e for e in INJECT if not (e['club'] == 'RealBetis' and e['name'] == 'Dani Ceballos')]

# ======================= BULK LEAGUES (DE/IT/FR) =======================
extra = json.load(open(BASE + r'\merged_extra.json', encoding='utf-8'))
extra6 = json.load(open(BASE + r'\merged_extra6.json', encoding='utf-8'))
for pid, real in extra6['RENAME'].items():
    RENAME[int(pid)] = real
TRANSFER.extend(extra6['TRANSFER'])
INJECT.extend(extra6['INJECT'])
extra8 = json.load(open(BASE + r'\merged_extra8.json', encoding='utf-8'))
for pid, real in extra8['RENAME'].items():
    RENAME[int(pid)] = real
TRANSFER.extend(extra8['TRANSFER'])
INJECT.extend(extra8['INJECT'])
extra7 = json.load(open(BASE + r'\merged_extra7.json', encoding='utf-8'))
for pid, real in extra7['RENAME'].items():
    RENAME[int(pid)] = real
TRANSFER.extend(extra7['TRANSFER'])
INJECT.extend(extra7['INJECT'])
extra9 = json.load(open(BASE + r'\merged_extra9.json', encoding='utf-8'))
for pid, real in extra9['RENAME'].items():
    RENAME[int(pid)] = real
TRANSFER.extend(extra9['TRANSFER'])
INJECT.extend(extra9['INJECT'])
extra10 = json.load(open(BASE + r'\merged_extra10.json', encoding='utf-8'))
for pid, real in extra10['RENAME'].items():
    RENAME[int(pid)] = real
TRANSFER.extend(extra10['TRANSFER'])
INJECT.extend(extra10['INJECT'])
extra11 = json.load(open(BASE + r'\merged_extra11.json', encoding='utf-8'))
for pid, real in extra11['RENAME'].items():
    RENAME[int(pid)] = real
TRANSFER.extend(extra11['TRANSFER'])
INJECT.extend(extra11['INJECT'])
extra12 = json.load(open(BASE + r'\merged_extra12.json', encoding='utf-8'))
for pid, real in extra12['RENAME'].items():
    RENAME[int(pid)] = real
TRANSFER.extend(extra12['TRANSFER'])
INJECT.extend(extra12['INJECT'])
for pid, real in extra['RENAME'].items():
    RENAME[int(pid)] = real
TRANSFER.extend(extra['TRANSFER'])
INJECT.extend(extra['INJECT'])

# ======================= ROSTER CAP 33 REBALANCE =======================
# Device-proven hard limit: >33 members = dead squad (AFH). Keep target squad
# (keeps + transfers-in + injects), fill remaining slots with strongest extras,
# REMOVE the rest; drop weakest injects first if the target itself overflows.
CAP = 33
transferred_out = {(t['src_team'], t['pid']) for t in TRANSFER}
team_final, team_current = {}, {}
for tid_s, t in db['teams'].items():
    team_current[int(tid_s)] = {p['pid']: p for p in t['roster']}
    team_final[int(tid_s)] = set()
for tid_s, t in db['teams'].items():
    for p in t['roster']:
        if p['pid'] in RENAME and (int(tid_s), p['pid']) not in transferred_out:
            team_final[int(tid_s)].add(p['pid'])
for t in TRANSFER:
    team_final[t['new_team']].add(t['pid'])
    team_final[t['src_team']].discard(t['pid'])
for a in ATTACH:
    team_final[a['team']].add(a['pid'])

inject_by_team = {}
for e in INJECT:
    inject_by_team.setdefault(e['team_id'], []).append(e)

drop_inject_ids = set()
new_remove = list(REMOVE)
for tid, final in team_final.items():
    cur = team_current.get(tid, {})
    if not final and tid not in inject_by_team:
        continue  # untouched team
    finals = {p for p in final if p in cur or p == 111411 or
              any(t['pid'] == p and t['new_team'] == tid for t in TRANSFER)}
    n_inj = len(inject_by_team.get(tid, []))
    extras = [p for p, info in cur.items()
              if p not in finals and (tid, p) not in {(r['team'], r['pid']) for r in REMOVE}
              and (tid, p) not in transferred_out]
    extras.sort(key=lambda p: -cur[p]['attrs'][1])
    room = CAP - len(finals)
    keep_inj = n_inj if n_inj <= room else room
    if keep_inj < n_inj:
        # drop weakest injects (ovr asc, then list order = shirt order)
        lst = inject_by_team[tid]
        order = sorted(range(len(lst)), key=lambda i: (lst[i]['ovr'], i))
        for i in order[keep_inj:]:
            drop_inject_ids.add(id(lst[i]))
    room -= keep_inj
    keep_ex = extras if len(extras) <= room else extras[:room]
    exset = set(keep_ex)
    for p in extras:
        if p not in exset:
            new_remove.append({'team': tid, 'pid': p, 'name': cur[p]['name']})
INJECT = [e for e in INJECT if id(e) not in drop_inject_ids]
REMOVE = new_remove
print('REBALANCE: injects kept %d / dropped %d | removals now %d' % (
    len(INJECT), len(drop_inject_ids), len(REMOVE)))

_years = {}
_yf = BASE + r'\inject_years.json'
import os as _os2
if _os2.path.exists(_yf):
    _years = json.load(open(_yf, encoding='utf-8'))
for _e in INJECT:
    _e['birth'] = _years.get(_e['name'])

plan = {'RENAME': RENAME, 'TRANSFER': TRANSFER, 'INJECT': INJECT, 'REMOVE': REMOVE,
        'ATTACH': ATTACH}
json.dump(plan, open(BASE + r'\pl_plan.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

from collections import Counter
print('RENAME   : %d pids' % len(RENAME))
print('TRANSFER : %d' % len(TRANSFER))
for t in TRANSFER:
    print('    %-22s <- %-14s @%s -> %-18s #%s ovr=%s' % (
        t['real'], t['src_name'], t['src_team'], t['dst_club'], t['jersey'], t['ovr']))
print('INJECT   : %d' % len(INJECT))
print('  by club:', dict(Counter(e['club'] for e in INJECT)))
print('REMOVE   : %d' % len(REMOVE))
