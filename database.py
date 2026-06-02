import sqlite3
import os
from datetime import date

DB_PATH = os.environ.get("DB_PATH", "kino_bot.db")


class Database:
    def __init__(self):
        self.db_path = DB_PATH

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_conn()
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                joined_at TEXT DEFAULT (date('now'))
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                code TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                file_id TEXT NOT NULL,
                category TEXT DEFAULT 'movie',
                views INTEGER DEFAULT 0,
                added_at TEXT DEFAULT (date('now'))
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                visit_date TEXT DEFAULT (date('now'))
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Default settings
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_active', '1')")

        conn.commit()
        conn.close()

    # ── Users ──

    def add_user(self, user_id: int, username: str, first_name: str):
        conn = self.get_conn()
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        conn.commit()
        conn.close()

    def get_users(self, limit: int = 20):
        conn = self.get_conn()
        rows = conn.execute(
            "SELECT * FROM users ORDER BY rowid DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_user_ids(self):
        conn = self.get_conn()
        rows = conn.execute("SELECT user_id FROM users").fetchall()
        conn.close()
        return [r["user_id"] for r in rows]

    # ── Videos ──

    def add_video(self, code: str, title: str, file_id: str, category: str = "movie"):
        conn = self.get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO videos (code, title, file_id, category) VALUES (?, ?, ?, ?)",
            (code, title, file_id, category)
        )
        conn.commit()
        conn.close()

    def get_video(self, code: str):
        conn = self.get_conn()
        row = conn.execute("SELECT * FROM videos WHERE code = ?", (code,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_video(self, code: str):
        conn = self.get_conn()
        conn.execute("DELETE FROM videos WHERE code = ?", (code,))
        conn.commit()
        conn.close()

    def get_by_category(self, category: str):
        conn = self.get_conn()
        rows = conn.execute(
            "SELECT * FROM videos WHERE category = ? ORDER BY added_at DESC", (category,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_top_videos(self, limit: int = 10):
        conn = self.get_conn()
        rows = conn.execute(
            "SELECT * FROM videos ORDER BY views DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def increment_views(self, code: str):
        conn = self.get_conn()
        conn.execute("UPDATE videos SET views = views + 1 WHERE code = ?", (code,))
        conn.commit()
        conn.close()

    # ── Visits ──

    def add_visit(self, user_id: int):
        conn = self.get_conn()
        conn.execute("INSERT INTO visits (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()

    # ── Stats ──

    def get_stats(self):
        conn = self.get_conn()
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_videos = conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        total_views = conn.execute("SELECT SUM(views) FROM videos").fetchone()[0] or 0
        today = date.today().isoformat()
        today_visits = conn.execute(
            "SELECT COUNT(*) FROM visits WHERE visit_date = ?", (today,)
        ).fetchone()[0]
        conn.close()
        return {
            "total_users": total_users,
            "total_videos": total_videos,
            "total_views": total_views,
            "today_visits": today_visits,
        }

    # ── Settings ──

    def is_bot_active(self) -> bool:
        conn = self.get_conn()
        row = conn.execute("SELECT value FROM settings WHERE key = 'bot_active'").fetchone()
        conn.close()
        return row["value"] == "1" if row else True

    def toggle_bot(self) -> bool:
        current = self.is_bot_active()
        new_val = "0" if current else "1"
        conn = self.get_conn()
        conn.execute("UPDATE settings SET value = ? WHERE key = 'bot_active'", (new_val,))
        conn.commit()
        conn.close()
        return not current
