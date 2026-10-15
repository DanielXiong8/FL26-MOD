# -*- coding: utf-8 -*-
"""
sqlite_store.py — SQLite read/write for FL26 save databases.
Handles backup, WAL mode, and safe writes.
"""
import sqlite3, os, shutil, hashlib, datetime

class SaveDB:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    def backup(self, backup_dir):
        """Create a timestamped backup."""
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = os.path.basename(self.path)
        dst = os.path.join(backup_dir, f"{ts}_{name}")
        shutil.copy2(self.path, dst)
        sha = hashlib.sha256(open(dst, "rb").read()).hexdigest()
        return dst, sha

    def get_player(self, player_id, scope=0):
        """Get player_blob payload."""
        cur = self.conn.cursor()
        cur.execute("SELECT payload FROM player_blob WHERE data_scope=? AND player_id=?", (scope, player_id))
        row = cur.fetchone()
        return row[0] if row else None

    def set_player(self, player_id, payload, scope=0):
        """Write player_blob payload."""
        cur = self.conn.cursor()
        cur.execute("UPDATE player_blob SET payload=? WHERE data_scope=? AND player_id=?", (payload, scope, player_id))
        self.conn.commit()
        return cur.rowcount > 0

    def get_archive(self):
        """Get archive_blob payload."""
        cur = self.conn.cursor()
        cur.execute("SELECT payload FROM archive_blob WHERE id=1")
        row = cur.fetchone()
        return row[0] if row else None

    def set_archive(self, payload):
        """Write archive_blob payload."""
        cur = self.conn.cursor()
        cur.execute("UPDATE archive_blob SET payload=? WHERE id=1", (payload,))
        self.conn.commit()
        return cur.rowcount > 0

    def get_team(self, team_id, scope=0):
        """Get team_blob payload."""
        cur = self.conn.cursor()
        cur.execute("SELECT payload FROM team_blob WHERE data_scope=? AND team_id=?", (scope, team_id))
        row = cur.fetchone()
        return row[0] if row else None

    def list_players(self, limit=20, offset=0):
        cur = self.conn.cursor()
        cur.execute("SELECT player_id, LENGTH(payload) FROM player_blob ORDER BY player_id LIMIT ? OFFSET ?", (limit, offset))
        return cur.fetchall()

    def player_count(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM player_blob")
        return cur.fetchone()[0]
