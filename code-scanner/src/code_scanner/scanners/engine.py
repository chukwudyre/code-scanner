from __future__ import annotations

from pathlib import Path

from code_scanner.models import Finding, ScanSettings, SignalRule
from code_scanner.scanners.java_structured import run_java_structured_scan
from code_scanner.scanners.js_ts_structured import run_js_ts_structured_scan
from code_scanner.scanners.notebooks import run_notebook_scan
from code_scanner.scanners.polyglot_patterns import run_polyglot_pattern_scan
from code_scanner.scanners.python_ast import run_python_ast_scan
from code_scanner.scanners.rules import run_rules_scan


def scan_repository(repo_path: Path, rules: list[SignalRule], scan_settings: ScanSettings) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(
        run_rules_scan(
            repo_path,
            rules,
            max_file_size_bytes=scan_settings.max_file_size_bytes,
            max_files_per_repo=scan_settings.max_files_per_repo,
        )
    )
    findings.extend(
        run_python_ast_scan(
            repo_path,
            max_file_size_bytes=scan_settings.max_file_size_bytes,
            max_files_per_repo=scan_settings.max_files_per_repo,
        )
    )
    findings.extend(
        run_notebook_scan(
            repo_path,
            max_file_size_bytes=scan_settings.max_file_size_bytes,
            max_files_per_repo=scan_settings.max_files_per_repo,
        )
    )
    findings.extend(
        run_js_ts_structured_scan(
            repo_path,
            max_file_size_bytes=scan_settings.max_file_size_bytes,
            max_files_per_repo=scan_settings.max_files_per_repo,
        )
    )
    findings.extend(
        run_java_structured_scan(
            repo_path,
            max_file_size_bytes=scan_settings.max_file_size_bytes,
            max_files_per_repo=scan_settings.max_files_per_repo,
        )
    )
    findings.extend(
        run_polyglot_pattern_scan(
            repo_path,
            max_file_size_bytes=scan_settings.max_file_size_bytes,
            max_files_per_repo=scan_settings.max_files_per_repo,
        )
    )

    # Deduplicate exact duplicates from different scanners or repeated matches.
    deduped: dict[tuple, Finding] = {}
    for item in findings:
        key = (
            item.file_path,
            item.line_number,
            item.signal_code,
            item.detector,
            item.evidence,
        )
        deduped[key] = item

    return list(deduped.values())
