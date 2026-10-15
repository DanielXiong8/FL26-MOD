# player_blob Protobuf Schema

## File: player_blob payload (per-row, ~75-135 bytes)

### Outer Message

| Field | Wire | Description |
|-------|------|-------------|
| f1 | varint | player_id (matches PK) |
| f2 | varint | unknown (observed: 1) |
| f4 | varint | position code (6=?) |
| f5 | varint | team_id |
| f8 | varint | jersey number |
| f9 | message | **Player Details** (nested) |
| f10 | varint | unknown (observed: 60) |
| f11 | message | **Appearance IDs** (nested) |

### f9: Player Details (nested message)

| Field | Wire | Description |
|-------|------|-------------|
| f1 | string | **Player Name** (e.g., "Christopher Bailey") |
| f2 | varint | Birth year (e.g., 2008) |
| f3 | varint | Height (e.g., 191) |
| f4 | varint | **balance** |
| f5 | varint | **reaction** |
| f6 | varint | **acceleration** |
| f7 | varint | **velocity** |
| f8 | varint | **stamina** |
| f9 | varint | **agility** |
| f10 | varint | **shotpower** |
| f11 | varint | **standingtackle** |
| f12 | varint | **slidingtackle** |
| f13 | varint | **ballcontrol** |
| f14 | varint | **dribble** |
| f15 | varint | **shortpass** |
| f16 | varint | **highpass** |
| f17 | varint | **shot** |
| f18 | varint | **volley** |
| f19 | varint | **mental_defensivepositioning** |
| f20 | varint | **mental_vision** |
| f21 | varint | Overall rating |
| f22 | varint | Foot (1=left? 2=right?) |
| f25 | bytes | unknown (1 byte) |
| f27 | varint | unknown (observed: 202) |

### f11: Appearance IDs (nested message)

| Field | Wire | Description |
|-------|------|-------------|
| f7 | varint | appearance ID 1 |
| f8 | varint | appearance ID 2 |
| f10 | varint | appearance ID 3 |
| f11 | varint | appearance ID 4 |
| f14 | varint | appearance ID 5 |
| f15 | varint | appearance ID 6 |
| f16 | varint | appearance ID 7 |
| f17 | varint | appearance ID 8 |
| f18 | varint | appearance ID 9 |
| f19 | varint | appearance ID 10 |
| f21 | varint | appearance ID 11 |

## archive_blob Protobuf Schema (save-level metadata)

| Field | Wire | Description |
|-------|------|-------------|
| f1 | message | Competition data (fixtures, standings) |
| f2 | message | **UserPlayer metadata** |
| f4 | varint | unknown (observed: 52) |
| f5 | message | Trophy/cup progress |
| f6 | message[] | Team season data (repeated) |
| f7 | message | Career year (f1=2026) |
| f8 | message | Season state (f22=user team_id) |
| f9 | string | empty |

### f2: UserPlayer Metadata

| Field | Wire | Description |
|-------|------|-------------|
| f2 | varint | Kit number (13) |
| f3 | string | **Kit name** ("BAILEY") |
| f4 | varint | Appearance ID (240) |
| f5 | varint | Position (2) |
