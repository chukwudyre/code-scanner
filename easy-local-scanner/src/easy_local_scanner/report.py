from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from easy_local_scanner.db import Database


def build_report(db_path: str, output_dir: str, run_id: int | None = None) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    db = Database(db_path)
    db.init_schema()

    target_run = run_id or db.latest_run_id()
    if target_run is None:
        db.close()
        raise RuntimeError("No scan runs found. Run a scan first.")

    run = db.fetch_run(target_run)
    if run is None:
        db.close()
        raise RuntimeError(f"Run not found: {target_run}")

    by_rule = db.fetch_rows(
        """
        SELECT rule_code, severity, COUNT(*) AS findings_count
        FROM findings
        WHERE run_id = ?
        GROUP BY rule_code, severity
        ORDER BY findings_count DESC, rule_code ASC
        """,
        (int(target_run),),
    )

    by_file = db.fetch_rows(
        """
        SELECT file_path, COUNT(*) AS findings_count
        FROM findings
        WHERE run_id = ?
        GROUP BY file_path
        ORDER BY findings_count DESC, file_path ASC
        """,
        (int(target_run),),
    )

    all_findings = db.fetch_rows(
        """
        SELECT file_path, line_number, rule_code, severity, evidence
        FROM findings
        WHERE run_id = ?
        ORDER BY severity DESC, file_path ASC, line_number ASC
        """,
        (int(target_run),),
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(Path(db_path).resolve()),
        "run": run,
        "counts": {
            "findings_total": len(all_findings),
            "rules_triggered": len(by_rule),
            "files_with_findings": len(by_file),
        },
        "files": {},
    }

    summary_json = out / "summary.json"
    by_rule_csv = out / "findings_by_rule.csv"
    by_file_csv = out / "findings_by_file.csv"
    findings_csv = out / "findings.csv"

    _write_json(summary_json, summary)
    _write_csv(by_rule_csv, by_rule)
    _write_csv(by_file_csv, by_file)
    _write_csv(findings_csv, all_findings)

    summary["files"] = {
        "summary": str(summary_json.resolve()),
        "findings_by_rule": str(by_rule_csv.resolve()),
        "findings_by_file": str(by_file_csv.resolve()),
        "findings": str(findings_csv.resolve()),
    }
    _write_json(summary_json, summary)

    db.close()
    return summary


def _write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            handle.write("")
            return

        fieldnames = []
        seen = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)

        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
