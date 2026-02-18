from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from code_scanner.db import Database


def generate_reports(
    *,
    db_path: str,
    output_dir: str,
    run_id: int | None = None,
) -> dict:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    db = Database(db_path)
    db.init_schema()

    target_run = run_id or _latest_run_id(db)
    if target_run is None:
        db.close()
        raise RuntimeError("No scan runs found. Execute a scan first.")

    run_rows = db.query("SELECT * FROM scan_runs WHERE id = ?", (int(target_run),))
    if not run_rows:
        db.close()
        raise RuntimeError(f"Run {target_run} not found")

    run_row = dict(run_rows[0])

    by_repo = [
        dict(row)
        for row in db.query(
            """
            SELECT
                r.full_name AS repo,
                COUNT(*) AS finding_count,
                SUM(CASE WHEN f.severity = 'high' THEN 1 ELSE 0 END) AS high_count,
                SUM(CASE WHEN f.severity = 'medium' THEN 1 ELSE 0 END) AS medium_count,
                SUM(CASE WHEN f.severity = 'low' THEN 1 ELSE 0 END) AS low_count
            FROM findings f
            JOIN repos r ON r.id = f.repo_id
            WHERE f.run_id = ?
            GROUP BY r.full_name
            ORDER BY finding_count DESC, repo ASC
            """,
            (int(target_run),),
        )
    ]

    by_signal = [
        dict(row)
        for row in db.query(
            """
            SELECT
                signal_code,
                category,
                severity,
                COUNT(*) AS finding_count
            FROM findings
            WHERE run_id = ?
            GROUP BY signal_code, category, severity
            ORDER BY finding_count DESC, signal_code ASC
            """,
            (int(target_run),),
        )
    ]

    top_findings = [
        dict(row)
        for row in db.query(
            """
            SELECT
                r.full_name AS repo,
                f.file_path,
                f.line_number,
                f.signal_code,
                f.category,
                f.severity,
                f.detector,
                f.confidence,
                f.evidence
            FROM findings f
            JOIN repos r ON r.id = f.repo_id
            WHERE f.run_id = ?
            ORDER BY
                CASE f.severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                r.full_name ASC,
                f.file_path ASC,
                f.line_number ASC
            LIMIT 2000
            """,
            (int(target_run),),
        )
    ]

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(Path(db_path).resolve()),
        "run": run_row,
        "counts": {
            "repos_with_findings": len(by_repo),
            "signals_triggered": len(by_signal),
            "top_findings_rows": len(top_findings),
        },
        "files": {},
    }

    run_json = out_dir / "run_summary.json"
    repo_csv = out_dir / "findings_by_repo.csv"
    signal_csv = out_dir / "findings_by_signal.csv"
    top_csv = out_dir / "top_findings.csv"

    _write_json(run_json, summary)
    _write_csv(repo_csv, by_repo)
    _write_csv(signal_csv, by_signal)
    _write_csv(top_csv, top_findings)

    summary["files"] = {
        "run_summary": str(run_json.resolve()),
        "findings_by_repo": str(repo_csv.resolve()),
        "findings_by_signal": str(signal_csv.resolve()),
        "top_findings": str(top_csv.resolve()),
    }

    _write_json(run_json, summary)
    db.close()
    return summary


def _latest_run_id(db: Database) -> int | None:
    rows = db.query("SELECT id FROM scan_runs ORDER BY id DESC LIMIT 1")
    if not rows:
        return None
    return int(rows[0]["id"])


def _write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            handle.write("")
            return

        fieldnames: list[str] = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)

        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
