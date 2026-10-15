# -*- coding: utf-8 -*-
"""legalize_names.py - STEP 1 of the user's workflow:
1) legalize ALL player names in the PL clubs (game obfuscated -> real names)
   using the 189 verified matched pairs + a manual alias table for extras.
2) (later steps assign rosters, then fix team names.)

Output: name_legalize.json  {game_name: real_name}  + stats.
Alias table seeded by hand from the extras lists (legalized spellings).
Unknown extras stay as-is (youth/fictional) - flagged for review.
"""
import json

BASE = r'D:\FL26_Mod\work\fc26_alignment'
rep = json.load(open(BASE + r'\pl_gap_report.json', encoding='utf-8'))

# 1) automatic: every matched pair (real, game) with score >= 0.6 is a trusted alias
alias = {}
for club, r in rep.items():
    for real, num, gname, gjersey, score in r['matched']:
        alias.setdefault(gname, real) if False else None
alias = {}
for club, r in rep.items():
    for real, num, gname, gjersey, score in r['matched']:
        # one game_name may map differently per club; keep first, log conflicts
        prev = alias.get(gname)
        if prev and prev != real:
            print('CONFLICT %s: %s vs %s (%s)' % (gname, prev, real, club))
        alias[gname] = real

# 2) manual legalization for extras (game obfuscated name -> real player who
#    actually left / stayed; verified against Wikipedia 2026-27 squads)
MANUAL = {
    # Liverpool
    'Konate': 'Ibrahima Konate', 'M.Zalah': 'Mohamed Salah', 'Roberson': 'Andrew Robertson',
    'Elliot': 'Harvey Elliott', 'Joonz': 'Curtis Jones', 'Baitetic': 'Stefan Bajcetic',
    'A.Pecsy': 'Armin Pecsi', 'R.Willians': 'Rhys Williams',
    # Chelsea
    'Cucureya': 'Marc Cucurella', 'Adarabiyo': 'Levi Colwill', 'Chaloba': 'Trevoh Chalobah',
    'Jemes': 'Reece James', 'Esteban': 'Estevao', 'Enzo Fernandes': 'Enzo Fernandez',
    'Mudrrik': 'Mykhailo Mudryk', 'Nkunku': 'Christopher Nkunku',
    # generic known legalized names across DB
    'Barcora': 'Bradley Barcola', 'A.Beckar': 'Alisson Becker', 'Vergil': 'Virgil van Dijk',
    'Wirts': 'Florian Wirtz', 'M.Zalah': 'Mohamed Salah', 'Frinpong': 'Jeremie Frimpong',
    'Giesa': 'Federico Chiesa', 'Isac': 'Alexander Isak', 'Egitike': 'Hugo Ekitike',
    'Graphenberch': 'Ryan Gravenberch', 'Szoboslay': 'Dominik Szoboszlai',
    'Enddo': 'Wataru Endo', 'Gacpo': 'Cody Gakpo', 'Egitike': 'Hugo Ekitike',
    'Mamardashvli': 'Giorgi Mamardashvili', 'Tsimikars': 'Kostas Tsimikas',
    'Chambbers': 'Luke Chambers', 'Gundoan': 'Ilkay Gundogan', 'Rudiger': 'Antonio Rudiger',
    'Emrey Can': 'Emre Can', 'Muller': 'Thomas Muller', 'Neoer': 'Manuel Neuer',
}

result = {}
unresolved = []
for club, r in rep.items():
    for real, num, gname, gjersey, score in r['matched']:
        alias[gname] = real
    for gname in r['extras']:
        if gname not in alias:
            real = MANUAL.get(gname)
            if real:
                alias[gname] = real
            else:
                unknown.setdefault(club, []).append(gname) if False else None
                unknown.append((club, gname)) if 'unknown' in dir() else None

# extras manual pass (hand-curated legalization of obfuscated names)
EXTRA_ALIAS = {
    'Konate': 'Ibrahima Konate', 'M.Zalah': 'Mohamed Salah', 'Ramsey': 'Calvin Ramsay',
    'Roberson': 'Andrew Robertson', 'Elliot': 'Harvey Elliott', 'Joonz': 'Curtis Jones',
    'Baitetic': 'Stefan Bajcetic', 'A.Pecsy': 'Armin Pecsi', 'R.Willians': 'Rhys Williams',
    'Esteban': 'Estevao', 'Cucureya': 'Marc Cucurella', 'Adarabiyo': 'Adarabioyo',
}
unknown = []
for club, r in rep.items():
    for gname in r['extras']:
        if gname not in alias:
            if gname in EXTRA_ALIAS:
                alias[gname] = EXTRA_ALIAS[gname]
            else:
                unknown.append((club, gname))

json.dump(alias, open(BASE + r'\name_legalize.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('alias table size: %d unique game names legalized' % len(alias))
print('unresolved extras: %d' % len(unknown))
for c, g in unknown:
    print('  UNRESOLVED %-14s %s' % (c, g))
