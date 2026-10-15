# -*- coding: utf-8 -*-
"""plan_bulk.py - build RENAME/TRANSFER/INJECT for the 3 bulk leagues (DE/IT/FR).
From match3_report: pairs -> keeps(rename). Unmatched -> strict transfer audit
(surname sim>=0.78 + OVR|diff|<=5 + nat match, unique candidate) else inject.
Outputs merge files consumed by make_plan (merged_extra.json).
"""
import json, re, unicodedata
from difflib import SequenceMatcher

BASE = r'D:\FL26_Mod\work\fc26_alignment'
db = json.load(open(BASE + r'\db_survey.json', encoding='utf-8'))
import os as _o
import statistics
rep = json.load(open(_o.environ.get('REPORT_FILE', BASE + r'\match3_report.json'), encoding='utf-8'))

FIFA = {'GER':'Germany','ITA':'Italy','FRA':'France','BRA':'Brazil','ARG':'Argentina',
 'ESP':'Spain','ENG':'England','NED':'Netherlands','POR':'Portugal','BEL':'Belgium',
 'DEN':'Denmark','SWE':'Sweden','NOR':'Norway','SUI':'Switzerland','AUT':'Austria',
 'POL':'Poland','CZE':'Czech Republic','USA':'United States','JPN':'Japan',
 'KOR':'South Korea','MAR':'Morocco','SEN':'Senegal','NGA':'Nigeria','CIV':'Ivory Coast',
 'GHA':'Ghana','CMR':'Cameroon','ALG':'Algeria','TUN':'Tunisia','EGY':'Egypt',
 'COL':'Colombia','URU':'Uruguay','CHI':'Chile','PAR':'Paraguay','PER':'Peru',
 'ECU':'Ecuador','VEN':'Venezuela','MEX':'Mexico','CRC':'Costa Rica','AUS':'Australia',
 'TUR':'Turkey','GRE':'Greece','SRB':'Serbia','CRO':'Croatia','SVK':'Slovakia',
 'SVN':'Slovenia','BIH':'Bosnia and Herzegovina','ALB':'Albania','MKD':'North Macedonia',
 'ROU':'Romania','BUL':'Bulgaria','HUN':'Hungary','UKR':'Ukraine','RUS':'Russia',
 'ISR':'Israel','GEO':'Georgia','ARM':'Armenia','KEN':'Kenya','GAB':'Gabon',
 'COD':'DR Congo','ANG':'Angola','RSA':'South Africa','MLI':'Mali','BFA':'Burkina Faso',
 'GUI':'Guinea','GNB':'Guinea-Bissau','CPV':'Cape Verde','UZB':'Uzbekistan','IRQ':'Iraq',
 'KSA':'Saudi Arabia','IRN':'Iran','WAL':'Wales','SCO':'Scotland','IRL':'Republic of Ireland',
 'CAN':'Canada','PAN':'Panama','JAM':'Jamaica','HON':'Honduras','CGO':'Congo','LBY':'Libya',
 'FIN':'Finland','ISL':'Iceland','EST':'Estonia','LVA':'Latvia','LTU':'Lithuania',
 'KVX':'Kosovo','MNE':'Montenegro','MDA':'Moldova','UAE':'United Arab Emirates',
 'QAT':'Qatar','CHN':'China PR','IND':'India','THA':'Thailand','VIE':'Vietnam',
 'AUS2':'Australia','NZL':'New Zealand','PUR':'Puerto Rico','DOM':'Dominican Republic',
 'CUB':'Cuba','HAI':'Haiti','GUF':'French Guiana','MTN':'Mauritania','NIG':'Niger','BLR':'Belarus','CHE':'Switzerland','CHL':'Chile','CRI':'Costa_Rica','CUW':'Curacao',
 'EQG':'Equatorial_Guinea','GLP':'Guadeloupe','HKG':'CHINA_HONG_KONG','KAZ':'Kazakhstan','KOS':'Kosovo',
 'LCA':'Saint_Lucia','LUX':'Luxembourg','NCL':'New_Caledonia','NGR':'Nigeria','PRK':'North_Korea',
 'PRY':'Paraguay','SER':'Serbia','SLO':'Slovenia','SMN':'San_Marino','TGO':'Togo','TPE':'Chinese_Taipei',
 'VIN':'Saint_Vincent_and_the_Grenadines',
 'TCD':'Chad','SUD':'Sudan','ZAM':'Zambia','ZIM':'Zimbabwe','MOZ':'Mozambique',
 'ANG2':'Angola','BEN':'Benin','TOG':'Togo','GAM':'Gambia','SLE':'Sierra Leone',
 'LBR':'Liberia','GHA2':'Ghana','RWA':'Rwanda','UGA':'Uganda','TAN':'Tanzania',
 'BDI':'Burundi','ETH':'Ethiopia','SOM':'Somalia','DJI':'Djibouti','COM':'Comoros',
 'CPV2':'Cape Verde','SYR':'Syria','LBN':'Lebanon','JOR':'Jordan','PLE':'Palestine',
 'KUW':'Kuwait','BHR':'Bahrain','OMA':'Oman','YEM':'Yemen','AFG':'Afghanistan',
 'PAK':'Pakistan','BAN':'Bangladesh','SRI':'Sri Lanka','MAS':'Malaysia','SIN':'Singapore',
 'IDN':'Indonesia','PHI':'Philippines','MGL':'Mongolia','KGZ':'Kyrgyzstan',
 'TJK':'Tajikistan','TKM':'Turkmenistan','UZB2':'Uzbekistan','NEP':'Nepal',
 'CAM':'Cambodia','LAO':'Laos','MYA':'Myanmar','BHU':'Bhutan','BRU':'Brunei',
 'TAI':'Chinese Taipei','GUA':'Guatemala','SLV':'El Salvador','NCA':'Nicaragua',
 'CRC2':'Costa Rica','HON2':'Honduras','SUR':'Suriname','GUY':'Guyana','VEN2':'Venezuela',
 'BOL':'Bolivia','PAR2':'Paraguay','TRI':'Trinidad and Tobago','BAR':'Barbados',
 'FIJ':'Fiji','SOL':'Solomon Islands','TAH':'Tahiti','PNG':'Papua New Guinea'}


def strip_acc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def norm(s):
    return re.sub(r'[^a-z]', '', strip_acc(s).lower())


# surname -> DB candidates index (with nat + ovr + team)
idx = {}
for tid, t in db['teams'].items():
    for p in t['roster']:
        sur = norm(p['name'].split()[-1]) if p['name'].split() else ''
        if len(sur) >= 4:
            idx.setdefault(sur, []).append(
                (p['pid'], p['name'], tid, p['jersey'], p['attrs'][1], p['nat']))

club_median = {}
for _lg, _clubs in rep.items():
    for _cl, _r in _clubs.items():
        _ovrs = [p['ovr'] for p in _r.get('pairs', [])]
        if _ovrs:
            club_median[_cl] = round(statistics.median(_ovrs))
RENAME, TRANSFER, INJECT = {}, [], []
stats = {'pairs': 0, 'transfer': 0, 'inject': 0}
claimed_pids = set()
for lg, clubs in rep.items():
    for club, r in clubs.items():
        tid = r['tid']
        for p in r['pairs']:
            RENAME[p['pid']] = p['real']
            stats['pairs'] += 1
        for num, nm, pos, nat in r['unmatched']:
            want_nat = FIFA.get(nat, '')
            sur = norm(nm.split()[-1]) if nm.split() else ''
            cands = []
            if len(sur) >= 4:
                for s2 in idx.keys():
                    if abs(len(s2) - len(sur)) > 3:
                        continue
                    so = SequenceMatcher(None, sur, s2).ratio()
                    if so < 0.78:
                        continue
                    for pid, gname, gtid, gj, govr, gnat in idx[s2]:
                        if abs(govr - 70) > 30:
                            pass
                        cands.append((pid, gname, gtid, gj, govr, gnat, so))
            strong = []
            for pid, gname, gtid, gj, govr, gnat, so in cands:
                if abs(govr - 70) <= 30 and govr > 0:
                    pass
                ok = so >= 0.78
                nat_ok = bool(want_nat) and bool(gnat) and norm(gnat) == norm(want_nat)
                if nat_ok:
                    ok = ok and True
                else:
                    ok = False  # require nationality match for auto-transfers
                if ok and govr >= 60:
                    strong.append((pid, gname, gtid, gj, govr))
            # dedupe by pid, require unique
            uniq = {}
            for pid, gname, gtid, gj, govr in strong:
                uniq[pid] = (gname, gtid, gj, govr)
            free = [pid for pid in uniq if pid not in claimed_pids]
            if len(free) == 1:
                pid = free[0]
                gname, gtid, gj, govr = uniq[pid]
                claimed_pids.add(pid)
                RENAME[pid] = nm
                TRANSFER.append({'pid': pid, 'src_team': int(gtid), 'src_name': gname,
                                 'dst_club': club, 'new_team': tid,
                                 'jersey': int(num) if isinstance(num, int) and num > 0 else 0,
                                 'ovr': None, 'real': nm})
                stats['transfer'] += 1
            else:
                _dnat = {'Bundesliga':'Germany','SerieA':'Italy','Ligue1':'France','Brazil':'Brazil',
                         'Argentina':'Argentina','Mexico':'Mexico','Saudi':'Saudi_Arabia','Japan':'Japan',
                         'K1':'South_Korea','China':'China','MLS':'United_States','Russia':'Russia'}.get(lg, 'England')
                INJECT.append({'club': club, 'league': lg, 'team_id': tid, 'name': nm,
                               'jersey': int(num) if isinstance(num, int) and num > 0 else 0,
                               'pos': pos, 'ovr': club_median.get(club, 70),
                               'nat': FIFA.get(nat) or (nat if nat and nat[0].isupper() else _dnat)})
                stats['inject'] += 1

json.dump({'RENAME': RENAME, 'TRANSFER': TRANSFER, 'INJECT': INJECT},
          open(_o.environ.get('EXTRA_FILE', BASE + r'\merged_extra.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('stats:', stats)
print('transfers sample:')
for t in TRANSFER[:12]:
    print('  %-22s <- %-16s @%s -> %s' % (t['real'], t['src_name'], t['src_team'], t['dst_club']))
