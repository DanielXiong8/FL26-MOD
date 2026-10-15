# -*- coding: utf-8 -*-
# make_manifest.py - build the PL update manifest: missing players (to inject,
# with FC26-approx OVR) + matched players (OVR update) + departures (flag).
import json

BASE = r'D:\FL26_Mod\work\fc26_alignment'
rep = json.load(open(BASE + r'\pl_gap_report.json', encoding='utf-8'))

# FC26-approx OVR for missing players (public ratings knowledge; defaults for fringe)
OVR = {
 'Vitezslav Jaros': 70, 'Harvey Davies': 58, 'Virgil van Dijk': 90, 'Jeremy Jacquet': 74,
 'Kostas Tsimikas': 76, 'Ronald Araujo': 85, 'Luke Chambers': 62, 'James McConnell': 62,
 'Victor Munoz': 76, 'Bradley Barcola': 84, 'Lewis Koumas': 64, 'Jayden Danns': 63,
 'Mike Penders': 65, 'Teddy Sharman-Lowe': 58, 'Marco Palestra': 72, 'Valentin Barco': 76,
 'Maxence Lacroix': 80, 'Geovany Quenda': 77, 'Estêvão': 86,
 'David Raya': 87, 'Tommy Setford': 60, 'Gabriel Magalhães': 84, 'Ezri Konsa': 79, 'Christos Tzolis': 76,
 'Finlay Herrick': 52, 'Morato': 74, 'Adama Boiro': 68, 'Joël Veltman': 75, 'Airidas Golambeckis': 60,
 'Ezra Mayers': 60, 'Edson Álvarez': 79, 'Arne Engels': 74, 'Joël Piroe': 75, 'Manor Solomon': 77,
 'Divine Mukasa': 68, 'Maxwel Cornet': 73,
 'Pascal Struijk': 73, 'Hadjam': 68, 'Chema Andrés': 66,
 'Kim Ji-Soo': 64, 'Benjamin Fredrick': 60, 'Kevin Schade': 79, 'Mamadou Sangaré': 74,
 'Axel Disasi': 78, 'Takehiro Tomiyasu': 76, 'Honest Ahanor': 65, 'Anan Khalaili': 68,
 'Óscar Mingueza': 76, 'Ben Chilwell': 75, 'Quinten Timber': 78, 'Sebastian Williams': 60,
 'Ismaïla Sarr': 79, 'Dwight McNeil': 76, 'Zavier Gozo': 62, 'Darío Osorio': 72,
 'Zion Suzuki': 77, 'James Wright': 50, 'Taylor Harwood-Bellis': 75, 'Alejandro Garnacho': 79,
 'Ainsley Maitland-Niles': 73, 'Michael Keane': 73, 'Kiernan Dewsbury-Hall': 77, 'Hayden Hackney': 73,
 'Tyrique George': 70, 'Brennan Johnson': 78,
 'Julián Araujo': 72, 'Max Aarons': 71, 'António Silva': 78, 'Lewis Cook': 72, 'Alex Tóth': 66,
 'Daniel Jebbison': 64, 'Álvaro Rodríguez': 70,
 'John Victor': 72, 'Steven Benda': 68, 'Ousmane Diomande': 76, 'Daniel Muñoz': 80,
 'Ibrahim Sangaré': 78, 'Xaver Schlager': 77, 'Arnaud Kalimuendo': 74, 'Liam Delap': 76,
 'Dan Bentley': 65, 'Ethan Pinnock': 74, 'Stephen Mfuni': 62, 'Aurèle Amenda': 70,
 'Caleb Yirenkyi': 64, 'Gustavo Hamer': 76, 'Haji Wright': 70, 'Taiwo Awoniyi': 74,
 'Loum Tchaouna': 72, 'Yann Gboho': 72, 'Sidiki Cherif': 60,
 'Alex Borto': 55, 'David Affengruber': 72, 'César Palacios': 68, 'Hugo Larsson': 74,
 'Shea Charles': 68, 'Manuel Ángel': 62, 'Gonzalo García': 70,
}
POS_TO_TEMPLATE = {'GK': 'GK', 'DF': 'DF', 'MF': 'MF', 'FW': 'FW', '?': 'MF'}

manifest = {'inject': [], 'ovr_update': [], 'departures': []}
for club, r in rep.items():
    for name, num, pos in r['missing']:
        manifest['inject'].append({
            'club': club, 'team_id': r['tid'], 'name': name,
            'jersey': int(num) if str(num).isdigit() and int(num) > 0 else 0,
            'pos': pos, 'ovr': OVR.get(name, 70)})
    for real, num, gname, gjersey, score in r['matched']:
        manifest['ovr_update'].append({
            'club': club, 'team_id': r['tid'], 'game_name': gname,
            'real_name': real, 'ovr_real': OVR.get(real, None)})
    for gname in r['extras']:
        manifest['departures'].append({'club': club, 'team_id': r['tid'], 'game_name': gname})

json.dump(manifest, open(BASE + r'\pl_update_manifest.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('INJECT: %d players | OVR_UPDATE: %d | DEPARTURES(verify): %d' % (
    len(manifest['inject']), len(manifest['ovr_update']), len(manifest['departures'])))
print()
print('Sample inject entries:')
for e in manifest['inject'][:12]:
    print('  %-14s %-24s #%-3s %-3s OVR %d' % (e['club'], e['name'], e['jersey'], e['pos'], e['ovr']))
no_ovr = [e for e in manifest['inject'] if e['name'] not in OVR]
print('\ninject without hand OVR (default 70): %d' % len(no_ovr))
