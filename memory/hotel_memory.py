"""
Hotel Memory — Persistent Context with SQLite
───────────────────────────────────────────────
Same public API as the v2.0 ChromaDB version (save_briefing,
get_past_briefings, save_anomaly, get_recurring_anomalies, save_chat,
get_chat_history, get_stats) so app.py needs no changes here.

Why SQLite instead of ChromaDB for v3.0:
  - Briefings and chat history are always retrieved by *recency*, not
    semantic similarity — that's a plain "ORDER BY date DESC", not a
    vector search. Chroma was solving a problem this project doesn't have.
  - Removes chromadb + onnxruntime + the sentence-transformer embedding
    model from the dependency tree, which meaningfully lowers the app's
    RAM footprint (relevant on Streamlit Community Cloud's 1GB cap).
  - No more pysqlite3-binary override hack — that existed only because
    Chroma needed a newer SQLite than some environments ship with.

If you want semantic anomaly matching back as a portfolio feature later,
add chromadb as an optional extra and swap just the anomalies table for
a Chroma collection — briefings/chat can stay in SQLite either way.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from config import SQLITE_DB_PATH, HOTEL_ID


class HotelMemory:
    def __init__(self, db_path: str = SQLITE_DB_PATH):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_schema()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS briefings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, hotel_id TEXT, text TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT, description TEXT, severity TEXT,
                date TEXT, hotel_id TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT, content TEXT, timestamp TEXT, hotel_id TEXT
            )""")

    # ─── Briefings ───────────────────────────────────────────────────────
    def save_briefing(self, briefing_text: str, date: str = None):
        date = date or datetime.today().strftime("%Y-%m-%d")
        with self._conn() as c:
            c.execute(
                "INSERT INTO briefings (date, hotel_id, text) VALUES (?, ?, ?)",
                (date, HOTEL_ID, briefing_text),
            )

    def get_past_briefings(self, n: int = 7) -> list:
        """Most recent N briefings, newest first."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT text FROM briefings WHERE hotel_id = ? ORDER BY id DESC LIMIT ?",
                (HOTEL_ID, n),
            ).fetchall()
        return [r["text"] for r in rows]

    # ─── Anomalies ───────────────────────────────────────────────────────
    def save_anomaly(self, anomaly_type: str, description: str, severity: str):
        with self._conn() as c:
            c.execute(
                "INSERT INTO anomalies (type, description, severity, date, hotel_id) VALUES (?, ?, ?, ?, ?)",
                (anomaly_type, description, severity, datetime.today().strftime("%Y-%m-%d"), HOTEL_ID),
            )

    def get_recurring_anomalies(self, n: int = 10) -> list:
        """
        Most recent anomalies, newest first, each annotated with how many
        times that anomaly type has fired in the last 14 days — a cheap,
        deterministic stand-in for "semantic recurrence" that needs no
        embeddings at all.
        """
        with self._conn() as c:
            rows = c.execute(
                "SELECT type, description, severity, date FROM anomalies "
                "WHERE hotel_id = ? ORDER BY id DESC LIMIT ?",
                (HOTEL_ID, n),
            ).fetchall()
            counts = dict(c.execute(
                "SELECT type, COUNT(*) FROM anomalies WHERE hotel_id = ? "
                "AND date >= date('now', '-14 days') GROUP BY type",
                (HOTEL_ID,),
            ).fetchall())

        result = []
        for r in rows:
            meta = {
                "type": r["type"], "severity": r["severity"], "date": r["date"],
                "occurrences_last_14_days": counts.get(r["type"], 1),
            }
            result.append((r["description"], meta))
        return result

    # ─── Chat History ────────────────────────────────────────────────────
    def save_chat(self, role: str, message: str):
        with self._conn() as c:
            c.execute(
                "INSERT INTO chat (role, content, timestamp, hotel_id) VALUES (?, ?, ?, ?)",
                (role, message, datetime.now().isoformat(), HOTEL_ID),
            )

    def get_chat_history(self, n: int = 10) -> list:
        """Last N messages, oldest first (chronological, for context building)."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT role, content FROM chat WHERE hotel_id = ? ORDER BY id DESC LIMIT ?",
                (HOTEL_ID, n),
            ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    # ─── Stats ───────────────────────────────────────────────────────────
    def get_stats(self) -> dict:
        with self._conn() as c:
            briefings = c.execute("SELECT COUNT(*) FROM briefings WHERE hotel_id = ?", (HOTEL_ID,)).fetchone()[0]
            anomalies = c.execute("SELECT COUNT(*) FROM anomalies WHERE hotel_id = ?", (HOTEL_ID,)).fetchone()[0]
            chats = c.execute("SELECT COUNT(*) FROM chat WHERE hotel_id = ?", (HOTEL_ID,)).fetchone()[0]
        return {
            "total_briefings": briefings,
            "total_anomalies": anomalies,
            "total_chat_messages": chats,
        }
