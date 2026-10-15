# SQLite Schema — static.db
File: C:\FL26_Mod\saves\working\Static\static.db
Size: 32,768 bytes

## Tables (4)

### archive_blob
```sql
CREATE TABLE archive_blob (
    id      INTEGER PRIMARY KEY CHECK (id = 1),
    payload BLOB NOT NULL
)
```
Rows: **1**

| # | Column | Type | PK | NotNull | Default |
|---|--------|------|----|---------|---------|
| 0 | id | INTEGER | 1 | 0 | None |
| 1 | payload | BLOB | 0 | 1 | None |

Sample data (first 3 rows, blobs as hex prefix):

Row 0:
  id: 1
  payload: BLOB[2467B] = 0a054368696e610a07417573747269610a07456e676c616e640a074972656c616e640a0844525f434f4e474f0a064379707275730a0753656e6567616c0a0747...

### match_blob
```sql
CREATE TABLE match_blob (
    data_scope    INTEGER NOT NULL,
    competition_id INTEGER NOT NULL,
    match_id      INTEGER NOT NULL,
    payload       BLOB NOT NULL,
    PRIMARY KEY (data_scope, competition_id, match_id)
)
```
Rows: **0**

| # | Column | Type | PK | NotNull | Default |
|---|--------|------|----|---------|---------|
| 0 | data_scope | INTEGER | 1 | 1 | None |
| 1 | competition_id | INTEGER | 2 | 1 | None |
| 2 | match_id | INTEGER | 3 | 1 | None |
| 3 | payload | BLOB | 0 | 1 | None |

### player_blob
```sql
CREATE TABLE player_blob (
    data_scope INTEGER NOT NULL,
    player_id  INTEGER NOT NULL,
    payload    BLOB NOT NULL,
    PRIMARY KEY (data_scope, player_id)
)
```
Rows: **0**

| # | Column | Type | PK | NotNull | Default |
|---|--------|------|----|---------|---------|
| 0 | data_scope | INTEGER | 1 | 1 | None |
| 1 | player_id | INTEGER | 2 | 1 | None |
| 2 | payload | BLOB | 0 | 1 | None |

### team_blob
```sql
CREATE TABLE team_blob (
    data_scope INTEGER NOT NULL,
    team_id    INTEGER NOT NULL,
    payload    BLOB NOT NULL,
    PRIMARY KEY (data_scope, team_id)
)
```
Rows: **0**

| # | Column | Type | PK | NotNull | Default |
|---|--------|------|----|---------|---------|
| 0 | data_scope | INTEGER | 1 | 1 | None |
| 1 | team_id | INTEGER | 2 | 1 | None |
| 2 | payload | BLOB | 0 | 1 | None |


## Indexes (3)

- `sqlite_autoindex_match_blob_1` on `match_blob`: None
- `sqlite_autoindex_player_blob_1` on `player_blob`: None
- `sqlite_autoindex_team_blob_1` on `team_blob`: None