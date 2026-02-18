from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from code_scanner.config import ConfigError, load_config
from code_scanner.db import Database
from code_scanner.pipeline import run_scan
from code_scanner.reporting import generate_reports


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-scanner",
        description="Deterministic local-first code scanner for model governance",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize local SQLite schema")
    init_parser.add_argument("--db-path", default="data/code_scanner.db")

    scan_parser = subparsers.add_parser("scan", help="Run repository scan")
    scan_parser.add_argument("--config", default="configs/config.example.json")
    scan_parser.add_argument("--mode", choices=["full", "incremental"], default="full")
    scan_parser.add_argument("--limit", type=int, default=None)
    scan_parser.add_argument("--repo-regex", default=None)

    report_parser = subparsers.add_parser("report", help="Generate report files from DB")
    report_parser.add_argument("--db-path", default="data/code_scanner.db")
    report_parser.add_argument(
        "--output-dir",
        default=f"outputs/report-{utc_stamp()}",
    )
    report_parser.add_argument("--run-id", type=int, default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        db = Database(args.db_path)
        db.init_schema()
        db.close()
        print(json.dumps({"db_path": str(Path(args.db_path).resolve()), "status": "initialized"}, indent=2))
        return 0

    if args.command == "scan":
        try:
            config = load_config(args.config)
        except ConfigError as exc:
            parser.error(str(exc))
            return 2

        summary = run_scan(
            config,
            mode=args.mode,
            limit=args.limit,
            repo_regex=args.repo_regex,
        )
        print(json.dumps(summary.to_dict(), indent=2, ensure_ascii=True))
        return 0

    if args.command == "report":
        summary = generate_reports(
            db_path=args.db_path,
            output_dir=args.output_dir,
            run_id=args.run_id,
        )
        print(json.dumps(summary, indent=2, ensure_ascii=True))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
