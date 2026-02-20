from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from easy_local_scanner.models import Finding


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: str | Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS scan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                repo_path TEXT NOT NULL,
                rules_path TEXT NOT NULL,
                files_scanned INTEGER NOT NULL DEFAULT 0,
                findings_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                line_number INTEGER NOT NULL,
                rule_code TEXT NOT NULL,
                severity TEXT NOT NULL,
                evidence TEXT,
                FOREIGN KEY(run_id) REFERENCES scan_runs(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_findings_run_id ON findings(run_id);
            CREATE INDEX IF NOT EXISTS idx_findings_rule_code ON findings(rule_code);
            """
        )
        self.conn.commit()

    def start_run(self, repo_path: str, rules_path: str) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO scan_runs (started_at, repo_path, rules_path, status)
            VALUES (?, ?, ?, 'RUNNING')
            """,
            (utc_now(), repo_path, rules_path),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def finish_run(
        self,
        run_id: int,
        *,
        files_scanned: int,
        findings_count: int,
        status: str,
        notes: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            UPDATE scan_runs
            SET finished_at = ?, files_scanned = ?, findings_count = ?, status = ?, notes = ?
            WHERE id = ?
            """,
            (utc_now(), files_scanned, findings_count, status, notes, int(run_id)),
        )
        self.conn.commit()

    def insert_findings(self, run_id: int, findings: list[Finding]) -> int:
        if not findings:
            return 0
        self.conn.executemany(
            """
            INSERT INTO findings (run_id, file_path, line_number, rule_code, severity, evidence)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    int(run_id),
                    item.file_path,
                    int(item.line_number),
                    item.rule_code,
                    item.severity,
                    item.evidence,
                )
                for item in findings
            ],
        )
        self.conn.commit()
        return len(findings)

    def latest_run_id(self) -> int | None:
        row = self.conn.execute("SELECT id FROM scan_runs ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return int(row["id"])

    def fetch_run(self, run_id: int):
        row = self.conn.execute("SELECT * FROM scan_runs WHERE id = ?", (int(run_id),)).fetchone()
        return dict(row) if row else None

    def fetch_rows(self, sql: str, params: tuple = ()) -> list[dict]:
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
