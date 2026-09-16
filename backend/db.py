"""Two separate SQLite databases, kept deliberately distinct:

1. `stats.db` — durable storage for quiz results (survives restarts).
2. an in-memory sandbox database that the SQL Assistant queries — this is
   whatever schema/data the user has loaded, reset on request.
"""

import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
STATS_DB_PATH = DATA_DIR / "stats.db"

DESTRUCTIVE_RE = re.compile(
    r"\b(drop|delete|update|insert|alter|truncate|attach|pragma|replace)\b", re.IGNORECASE
)

DEFAULT_SCHEMA_SQL = """
CREATE TABLE students (
  id INTEGER PRIMARY KEY, name TEXT, major TEXT, year INTEGER, gpa REAL
);
CREATE TABLE courses (
  id INTEGER PRIMARY KEY, title TEXT, credits INTEGER, department TEXT
);
CREATE TABLE enrollments (
  student_id INTEGER, course_id INTEGER, grade TEXT, semester TEXT
);
INSERT INTO students VALUES
 (1,'Asha Rao','Computer Science',3,3.8),
 (2,'Leo Fernandes','Electronics',2,3.1),
 (3,'Mira Kulkarni','Computer Science',4,3.9),
 (4,'Dev Shah','Mechanical',1,2.9),
 (5,'Priya Nair','Computer Science',2,3.6),
 (6,'Arjun Mehta','Electronics',3,3.3),
 (7,'Sana Iyer','Data Science',4,3.95),
 (8,'Kabir Joshi','Mechanical',2,3.0);
INSERT INTO courses VALUES
 (101,'Data Structures',4,'Computer Science'),
 (102,'Digital Circuits',3,'Electronics'),
 (103,'Thermodynamics',4,'Mechanical'),
 (104,'Machine Learning',4,'Data Science'),
 (105,'Databases',3,'Computer Science'),
 (106,'Signals and Systems',3,'Electronics');
INSERT INTO enrollments VALUES
 (1,101,'A','Sem1'), (1,105,'A-','Sem2'), (2,102,'B+','Sem1'),
 (3,101,'A','Sem1'), (3,104,'A','Sem2'), (4,103,'B','Sem1'),
 (5,105,'A-','Sem1'), (5,101,'B+','Sem2'), (6,102,'A-','Sem1'),
 (6,106,'B+','Sem2'), (7,104,'A','Sem1'), (8,103,'B-','Sem1'),
 (2,106,'A-','Sem2'), (4,103,'B+','Sem2'), (7,105,'A-','Sem2');
"""


# ---------------- Quiz stats (durable) ----------------

def _stats_conn():
    conn = sqlite3.connect(STATS_DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS quiz_stats (topic TEXT PRIMARY KEY, correct INTEGER, total INTEGER)"
    )
    return conn


def record_quiz_result(topic: str, correct: int, total: int) -> None:
    conn = _stats_conn()
    try:
        row = conn.execute("SELECT correct, total FROM quiz_stats WHERE topic = ?", (topic,)).fetchone()
        if row:
            conn.execute(
                "UPDATE quiz_stats SET correct = ?, total = ? WHERE topic = ?",
                (row[0] + correct, row[1] + total, topic),
            )
        else:
            conn.execute(
                "INSERT INTO quiz_stats (topic, correct, total) VALUES (?, ?, ?)",
                (topic, correct, total),
            )
        conn.commit()
    finally:
        conn.close()


def get_quiz_stats() -> List[Dict]:
    conn = _stats_conn()
    try:
        rows = conn.execute("SELECT topic, correct, total FROM quiz_stats").fetchall()
        return [{"topic": r[0], "correct": r[1], "total": r[2]} for r in rows]
    finally:
        conn.close()


# ---------------- SQL Assistant sandbox ----------------

class Sandbox:
    """Holds the single in-memory sandbox connection the SQL Assistant uses."""

    def __init__(self):
        self.conn = None
        self.load(DEFAULT_SCHEMA_SQL)

    def load(self, schema_sql: str) -> None:
        if self.conn:
            self.conn.close()
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.executescript(schema_sql)
        self.conn.commit()

    def reset(self) -> None:
        self.load(DEFAULT_SCHEMA_SQL)

    def schema_text(self) -> str:
        rows = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND sql IS NOT NULL"
        ).fetchall()
        return ";\n".join(r[0] for r in rows) + ";" if rows else ""

    def is_destructive(self, sql: str) -> bool:
        return bool(DESTRUCTIVE_RE.search(sql))

    def execute(self, sql: str) -> Tuple[List[str], List[list]]:
        cursor = self.conn.execute(sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = [list(row) for row in cursor.fetchall()]
        return columns, rows


sandbox = Sandbox()
