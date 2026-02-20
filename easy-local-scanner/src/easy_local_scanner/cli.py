from __future__ import annotations

import argparse
import json
from pathlib import Path

from easy_local_scanner.db import Database
from easy_local_scanner.report import build_report
from easy_local_scanner.rules import load_rules
from easy_local_scanner.scanner import (
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_INCLUDE_EXTS,
    scan_local_repo,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="easy-scan",
        description="Simple local-only scanner (init -> scan -> report)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize local SQLite DB")
    init_parser.add_argument("--db-path", default="data/easy_scanner.db")

    scan_parser = subparsers.add_parser("scan", help="Scan a local folder/repo")
    scan_parser.add_argument("--repo-path", required=True, help="Path to local repo/folder")
    scan_parser.add_argument("--rules", default="configs/rules.json", help="Rules JSON path")
    scan_parser.add_argument("--db-path", default="data/easy_scanner.db")
    scan_parser.add_argument("--max-file-size-bytes", type=int, default=15_000_000)
    scan_parser.add_argument("--max-files", type=int, default=40_000)
    scan_parser.add_argument(
        "--include-exts",
        default=",".join(sorted(DEFAULT_INCLUDE_EXTS)),
        help="Comma-separated extensions to include, e.g. .py,.ipynb,.js",
    )
    scan_parser.add_argument(
        "--exclude-dirs",
        default=",".join(sorted(DEFAULT_EXCLUDE_DIRS)),
        help="Comma-separated directory names to skip",
    )

    report_parser = subparsers.add_parser("report", help="Generate CSV/JSON report from DB")
    report_parser.add_argument("--db-path", default="data/easy_scanner.db")
    report_parser.add_argument("--output-dir", default="outputs/report-1")
    report_parser.add_argument("--run-id", type=int, default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        db = Database(args.db_path)
        db.init_schema()
        db.close()
        print(json.dumps({"status": "initialized", "db_path": str(Path(args.db_path).resolve())}, indent=2))
        return 0

    if args.command == "scan":
        include = {item.strip().lower() for item in args.include_exts.split(",") if item.strip()}
        exclude = {item.strip() for item in args.exclude_dirs.split(",") if item.strip()}

        rules = load_rules(args.rules)
        db = Database(args.db_path)
        db.init_schema()

        run_id = db.start_run(repo_path=args.repo_path, rules_path=args.rules)
        files_scanned = 0
        findings_count = 0

        try:
            files_scanned, findings = scan_local_repo(
                args.repo_path,
                rules,
                max_file_size_bytes=int(args.max_file_size_bytes),
                max_files=int(args.max_files),
                include_exts=include,
                exclude_dirs=exclude,
            )
            findings_count = db.insert_findings(run_id, findings)
            db.finish_run(
                run_id,
                files_scanned=files_scanned,
                findings_count=findings_count,
                status="SUCCESS",
            )
        except Exception as exc:
            db.finish_run(
                run_id,
                files_scanned=files_scanned,
                findings_count=findings_count,
                status="FAILED",
                notes=str(exc),
            )
            db.close()
            raise

        db.close()
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "status": "SUCCESS",
                    "repo_path": str(Path(args.repo_path).resolve()),
                    "rules": str(Path(args.rules).resolve()),
                    "files_scanned": files_scanned,
                    "findings_count": findings_count,
                    "db_path": str(Path(args.db_path).resolve()),
                },
                indent=2,
            )
        )
        return 0

    if args.command == "report":
        payload = build_report(args.db_path, args.output_dir, args.run_id)
        print(json.dumps(payload, indent=2))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
