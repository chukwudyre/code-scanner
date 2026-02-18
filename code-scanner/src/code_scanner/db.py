from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from code_scanner.models import Finding, RepoDescriptor


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        self.conn.close()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS scan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                total_repos INTEGER NOT NULL DEFAULT 0,
                scanned_repos INTEGER NOT NULL DEFAULT 0,
                skipped_repos INTEGER NOT NULL DEFAULT 0,
                findings_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS repos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT NOT NULL,
                provider_type TEXT NOT NULL,
                external_id TEXT NOT NULL,
                full_name TEXT NOT NULL,
                clone_url TEXT,
                default_branch TEXT,
                web_url TEXT,
                local_path TEXT,
                last_seen_at TEXT NOT NULL,
                UNIQUE(provider_name, external_id)
            );

            CREATE TABLE IF NOT EXISTS repo_scan_state (
                repo_id INTEGER PRIMARY KEY,
                last_commit_sha TEXT,
                last_run_id INTEGER,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(repo_id) REFERENCES repos(id) ON DELETE CASCADE,
                FOREIGN KEY(last_run_id) REFERENCES scan_runs(id)
            );

            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                repo_id INTEGER NOT NULL,
                commit_sha TEXT,
                file_path TEXT NOT NULL,
                line_number INTEGER,
                signal_code TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                detector TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES scan_runs(id) ON DELETE CASCADE,
                FOREIGN KEY(repo_id) REFERENCES repos(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_findings_run_id ON findings(run_id);
            CREATE INDEX IF NOT EXISTS idx_findings_repo_id ON findings(repo_id);
            CREATE INDEX IF NOT EXISTS idx_findings_signal_code ON findings(signal_code);
            CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
            """
        )
        self.conn.commit()

    def start_run(self, mode: str, total_repos: int) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO scan_runs (started_at, mode, status, total_repos)
            VALUES (?, ?, 'RUNNING', ?)
            """,
            (utc_now(), mode, int(total_repos)),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        scanned_repos: int,
        skipped_repos: int,
        findings_count: int,
        error_count: int,
        notes: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            UPDATE scan_runs
            SET finished_at = ?,
                status = ?,
                scanned_repos = ?,
                skipped_repos = ?,
                findings_count = ?,
                error_count = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                utc_now(),
                status,
                int(scanned_repos),
                int(skipped_repos),
                int(findings_count),
                int(error_count),
                notes,
                int(run_id),
            ),
        )
        self.conn.commit()

    def upsert_repo(self, repo: RepoDescriptor) -> int:
        now = utc_now()
        self.conn.execute(
            """
            INSERT INTO repos (
                provider_name,
                provider_type,
                external_id,
                full_name,
                clone_url,
                default_branch,
                web_url,
                local_path,
                last_seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider_name, external_id) DO UPDATE SET
                full_name = excluded.full_name,
                clone_url = excluded.clone_url,
                default_branch = excluded.default_branch,
                web_url = excluded.web_url,
                local_path = excluded.local_path,
                last_seen_at = excluded.last_seen_at
            """,
            (
                repo.provider_name,
                repo.provider_type,
                repo.external_id,
                repo.full_name,
                repo.clone_url,
                repo.default_branch,
                repo.web_url,
                repo.local_path,
                now,
            ),
        )

        row = self.conn.execute(
            """
            SELECT id FROM repos WHERE provider_name = ? AND external_id = ?
            """,
            (repo.provider_name, repo.external_id),
        ).fetchone()
        self.conn.commit()
        if row is None:
            raise RuntimeError("Failed to fetch repo id after upsert")
        return int(row["id"])

    def get_last_commit_sha(self, repo_id: int) -> str | None:
        row = self.conn.execute(
            "SELECT last_commit_sha FROM repo_scan_state WHERE repo_id = ?",
            (int(repo_id),),
        ).fetchone()
        if row is None:
            return None
        value = row["last_commit_sha"]
        return str(value) if value else None

    def update_repo_scan_state(self, repo_id: int, commit_sha: str | None, run_id: int) -> None:
        self.conn.execute(
            """
            INSERT INTO repo_scan_state (repo_id, last_commit_sha, last_run_id, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(repo_id) DO UPDATE SET
                last_commit_sha = excluded.last_commit_sha,
                last_run_id = excluded.last_run_id,
                updated_at = excluded.updated_at
            """,
            (int(repo_id), commit_sha, int(run_id), utc_now()),
        )
        self.conn.commit()

    def insert_findings(
        self,
        run_id: int,
        repo_id: int,
        commit_sha: str | None,
        findings: list[Finding],
    ) -> int:
        if not findings:
            return 0

        self.conn.executemany(
            """
            INSERT INTO findings (
                run_id,
                repo_id,
                commit_sha,
                file_path,
                line_number,
                signal_code,
                category,
                severity,
                detector,
                confidence,
                evidence,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    int(run_id),
                    int(repo_id),
                    commit_sha,
                    row.file_path,
                    row.line_number,
                    row.signal_code,
                    row.category,
                    row.severity,
                    row.detector,
                    float(row.confidence),
                    row.evidence,
                    utc_now(),
                )
                for row in findings
            ],
        )
        self.conn.commit()
        return len(findings)

    def query(self, sql: str, params: tuple | None = None) -> list[sqlite3.Row]:
        cursor = self.conn.execute(sql, params or ())
        return list(cursor.fetchall())
