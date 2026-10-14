"""
DeskBuddy - Task and Reminder Manager
Lightweight SQLite-based storage for reminders and tasks.
"""

import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

DB_PATH = Path.home() / ".deskbuddy" / "tasks.db"

class TaskManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    due_at TEXT,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    reminded INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def add_task(
        self,
        title: str,
        description: str = "",
        due_at: Optional[str] = None,
        priority: str = "medium"
    ) -> int:
        """
        Adds a new task.
        due_at format expected: 'YYYY-MM-DD HH:MM:SS' or ISO format.
        """
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (title, description, due_at, priority, status, reminded, created_at)
                VALUES (?, ?, ?, ?, 'pending', 0, ?)
            """, (title, description, due_at, priority, created_at))
            conn.commit()
            return cursor.lastrowid

    def list_tasks(self, status: Optional[str] = "pending") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY due_at ASC, id DESC",
                    (status,)
                )
            else:
                cursor.execute("SELECT * FROM tasks ORDER BY id DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def complete_task(self, task_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_due_reminders(self, current_time: Optional[datetime.datetime] = None) -> List[Dict[str, Any]]:
        """
        Returns all pending tasks whose due_at is <= current_time and reminded == 0.
        """
        now_dt = current_time or datetime.datetime.now()
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks
                WHERE status = 'pending'
                  AND reminded = 0
                  AND due_at IS NOT NULL
                  AND due_at != ''
                  AND due_at <= ?
                ORDER BY due_at ASC
            """, (now_str,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def mark_reminded(self, task_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET reminded = 1 WHERE id = ?", (task_id,))
            conn.commit()
