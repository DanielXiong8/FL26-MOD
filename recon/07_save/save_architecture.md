# Save Architecture — FL26 Player Career Mode

## Storage Location

```
/data/user/0/com.football.soccer.league.mod/files/Archives/
├── Common/
│   └── PlayerCareerThumbnail.db    (32KB) — career save thumbnail
├── PlayerCareer/
│   └── PlayerCareerYYYYMMDDhhmmss.db (4.3MB) — main career save
├── Friendly/
│   └── friendly.db                 (413KB) — friendly match data
├── Static/
│   └── static.db                   (32KB) — empty template
├── Club/ National/ CustomLeague/ ChampionsLeague/ ML/ SimpleClub/  (empty dirs)
```

## Access Method

MIUI strips `android:debuggable` at install time → `run-as` blocked.
Solution: **SaveExportActivity + SaveImportActivity** (Java-level, registered via AXML injection).

- Export: copies `/data/data/.../Archives/` → `/sdcard/Android/data/.../files/save_export/Archives/`
- Import: copies `/sdcard/Android/data/.../files/save_import/Archives/` → `/data/data/.../Archives/`

## Database Structure (PlayerCareer DB)

| Table | Rows | PK | Description |
|-------|------|----|-------------|
| `archive_blob` | 1 | id=1 | Career metadata (fixtures, standings, UserPlayer info) |
| `player_blob` | 37,616 | (data_scope, player_id) | All players in career (protobuf payload) |
| `team_blob` | 1,507 | (data_scope, team_id) | Team rosters + metadata |
| `match_blob` | 1,107 | (data_scope, competition_id, match_id) | Match results |

## UserPlayer Identification

- UserPlayer is stored as `player_id=1` in `player_blob` (wizard replaces original player)
- UserPlayer metadata (kit name, kit number, appearance, position) in `archive_blob` f2
- User's team_id in `archive_blob` f8.f22
- 17 attributes in `player_blob` f9.f4-f20
- Appearance IDs in `player_blob` f11

## Six-Dimension Card Stats

The game UI shows aggregated card stats (SPD/SHO/PAS/DRI/DEF/PHY), not raw attributes.
Formula: `PlayerIngameRatingRules` (IL2CPP) — weighted aggregation of 17 attributes with ~1.2 multiplier, capped at 100.

### Observed Mapping (player_id=1, pos=6):

| Card | Attributes (81-97) | Result | Likely Contributors |
|------|-------------------|--------|-------------------|
| SPD | 98 | | acceleration(83), velocity(84), reaction(82) |
| SHO | 88 | | shot(94), shotpower(87), volley(95) |
| PAS | 84 | | shortpass(92), highpass(93), mental_vision(97) |
| DRI | 89 | | dribble(91), ballcontrol(90), agility(86) |
| DEF | 75 | | standingtackle(88), slidingtackle(89), mental_defensivepositioning(96) |
| PHY | 88 | | balance(81), stamina(85), strength? |

Note: exact formula needs further reverse engineering of PlayerIngameRatingRules.
