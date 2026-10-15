# -*- coding: utf-8 -*-
"""registry.py — cumulative web-built player registry.

WHY: every BUILD starts from the pristine base gamedata, but the device Archives
persist rosters across installs. If build N+1 drops players from build N, the
Archives roster keeps DEAD pids -> China squad crashes (user-hit bug: jersey 30
duplicated, China team unopenable). Fix: registry = source of truth; EVERY build
injects ALL registry players cumulatively (pids/jerseys never reused), so the
device roster always references live pids and stays under cap.
"""
import json, os, threading

REG_PATH = os.path.join(os.path.dirname(__file__), 'player_registry.json')
_lock = threading.Lock()


def load():
    with _lock:
        if os.path.exists(REG_PATH):
            return json.load(open(REG_PATH, encoding='utf-8'))
        return {'players': []}


def save(reg):
    with _lock:
        json.dump(reg, open(REG_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def all_players():
    return load()['players']


def by_team(team_id):
    return [p for p in all_players() if p['team_id'] == int(team_id)]


def used_pids():
    return {p['pid'] for p in all_players()}


def jerseys_in_team(team_id):
    return {p['jersey'] for p in by_team(team_id)}


def next_pid(base_used):
    """Allocate pid continuing after max(gamedata, registry)."""
    reg = used_pids()
    pid = max([175923] + list(base_used) + list(reg)) + 1
    while pid in reg or pid in base_used:
        pid += 1
    return pid


def add(pid, name, team_id, jersey, apk_sha, slot_note='', attrs=None, nat=24, **extra):
    reg = load()
    reg['players'].append({'pid': pid, 'name': name, 'team_id': team_id,
                           'jersey': jersey, 'apk_sha256': apk_sha,
                           'slot_note': slot_note, 'created': time.strftime('%Y-%m-%d %H:%M'),
                           'attrs': list(attrs) if attrs else None, 'nat': nat, **extra})
    save(reg)


import time
