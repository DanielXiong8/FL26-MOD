# -*- coding: utf-8 -*-
"""appearance_state.py — the ONE appearance/player state definition.

Builds and validates the state object consumed by Previewer / Injection / Save editor.
Maps user-facing options to the device-verified PA byte semantics (Phase 13B).
"""
ATTR_NAMES = ['balance', 'reaction', 'acceleration', 'velocity', 'stamina', 'agility',
              'shotpower', 'standingtackle', 'slidingtackle', 'ballcontrol', 'dribble',
              'shortpass', 'highpass', 'shot', 'volley',
              'mental_defensivepositioning', 'mental_vision']

# device-proven position attr templates (Phase 13B: uniform 81-97 classified GK;
# Ma Jiantao range(81,98) field-rated FW-slot-compatible; originals from CHN roster)
POS_TEMPLATES = {
    'GK': [72, 66, 53, 43, 43, 33, 50, 13, 13, 68, 17, 67, 67, 14, 16, 68, 68],   # Yang J. GK profile
    'FW': list(range(81, 98)),                                                   # device-proven field player
    'MF': [78, 80, 82, 79, 84, 80, 74, 62, 60, 85, 83, 86, 84, 72, 70, 74, 82],
    'DF': [70, 74, 78, 82, 80, 72, 60, 88, 85, 66, 62, 70, 72, 55, 58, 88, 80],
}


def build_state(cfg):
    """cfg = user web input; returns appearance_state dict + PA byte overrides."""
    ref = int(cfg.get('reference_pid') or 0)
    s = {
        'version': 'appearance-state-v1',
        # origin = ZERO-CLONE: no bytes copied from any existing player record.
        # Player record is built from scratch; face identity comes only from the
        # photo bake (b1=14 texture slot) + user's explicit appearance choices.
        'mode': 'origin' if ref == 0 else 'reference_clone',
        'reference_pid': ref if ref != 0 else None,
        'explicit': {
            'skin_tone': int(cfg.get('skin_tone', 6)),
            'face_texture_id': int(cfg.get('face_texture_id', 14)),
            'hair_index': None, 'hair_enabled': True,
            'hair_color_id': int(cfg.get('hair_color_id', 2)),
            'eyebrow_index': int(cfg.get('eyebrow_index', 1)),
            'beard_enabled': bool(cfg.get('beard_enabled', True)),
            'beard_style_id': int(cfg.get('beard_style_id', 1)),
            'b14': int(cfg.get('b14', 18)),
            'face_shape_id': 'FOLLOW_REFERENCE' if ref != 0 else 'ORIGIN_DEFAULT',
        },
        'eyes': 'Coming in V2',
        'photo_layers': {'face_texture_png': cfg.get('face_texture_png'),
                         'eye_region_mode': 'game_default_iris'},
        'player_identity': {
            'name': cfg.get('name', 'New Player'),
            'position': cfg.get('position', 'FW'),
            'preferred_foot': 'NOT_EXPOSED_V1',
            'nationality_nat': int(cfg.get('nat', 24)),
            'team_id': int(cfg.get('team_id', 10059)),
            'jersey_number': int(cfg.get('jersey', 30)),
            'attrs_17': list(cfg.get('attrs', POS_TEMPLATES.get(cfg.get('position', 'FW'), POS_TEMPLATES['FW']))),
        },
    }
    return s


def pa_overrides(state):
    """explicit.* -> PA byte overrides applied on top of the reference clone.
    PA layout (device-verified Phase 13B):
      b0 skin, b1 face tex, b3 hair idx, b4 hair flag, b5 hair color,
      b6 beard style(1-22), b7 beard flag, b8 eyebrow(1-7), b14 face shape."""
    ex = state['explicit']
    o = {}
    o[0] = ex['skin_tone']
    o[1] = ex['face_texture_id']
    o[5] = ex['hair_color_id']
    if ex['beard_enabled']:
        o[6] = max(1, min(22, ex['beard_style_id']))
        o[7] = 0
    else:
        o[6] = 255
        o[7] = 127
    o[8] = max(1, min(7, ex['eyebrow_index']))
    # b3/b14 stay cloned from reference (FOLLOW_REFERENCE in V1)
    return o


def validate(state, roster_count, cap=33):
    errs = []
    ident = state['player_identity']
    if not ident['name'] or len(ident['name']) > 32:
        errs.append('name: 1-32 chars required')
    j = ident['jersey_number']
    if not (1 <= j <= 99):
        errs.append('jersey: must be 1-99')
    if len(ident['attrs_17']) != 17:
        errs.append('attrs: need exactly 17 values')
    else:
        for i, v in enumerate(ident['attrs_17']):
            if not (1 <= v <= 127):
                errs.append('attrs[%d]=%d out of range 1-127' % (i, v))
    if roster_count >= cap:
        errs.append('This team has reached the supported roster limit (%d/%d).' % (roster_count, cap))
    return errs
