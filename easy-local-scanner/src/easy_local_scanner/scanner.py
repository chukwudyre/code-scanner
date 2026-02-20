from __future__ import annotations

import json
import re
from pathlib import Path

from easy_local_scanner.models import Finding, Rule


DEFAULT_INCLUDE_EXTS = {
    ".py",
    ".ipynb",
    ".js",
    ".ts",
    ".java",
    ".sql",
    ".r",
    ".scala",
    ".md",
    ".txt",
}

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
}


def scan_local_repo(
    repo_path: str | Path,
    rules: list[Rule],
    *,
    max_file_size_bytes: int,
    max_files: int,
    include_exts: set[str] | None = None,
    exclude_dirs: set[str] | None = None,
) -> tuple[int, list[Finding]]:
    root = Path(repo_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"repo_path must be an existing directory: {root}")

    include = include_exts or DEFAULT_INCLUDE_EXTS
    exclude = exclude_dirs or DEFAULT_EXCLUDE_DIRS
    compiled = [
        (rule, re.compile(rule.pattern, re.IGNORECASE if rule.ignore_case else 0))
        for rule in rules
    ]

    files_scanned = 0
    findings: list[Finding] = []
    seen: set[tuple[str, int, str]] = set()

    for file_path in _iter_candidate_files(root, include, exclude):
        if files_scanned >= max_files:
            break
        files_scanned += 1

        try:
            if file_path.stat().st_size > max_file_size_bytes:
                continue
        except OSError:
            continue

        if file_path.suffix.lower() == ".ipynb":
            text, line_map = _load_notebook_as_text(file_path)
            if text is None:
                continue
            lines = text.splitlines()
            for line_index, line in enumerate(lines, start=1):
                for rule, pattern in compiled:
                    if pattern.search(line):
                        original_line = line_map.get(line_index, line_index)
                        key = (str(file_path.relative_to(root)), original_line, rule.code)
                        if key in seen:
                            continue
                        seen.add(key)
                        findings.append(
                            Finding(
                                file_path=str(file_path.relative_to(root)),
                                line_number=original_line,
                                rule_code=rule.code,
                                severity=rule.severity,
                                evidence=line.strip()[:300],
                            )
                        )
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        rel = str(file_path.relative_to(root))
        for line_index, line in enumerate(content.splitlines(), start=1):
            for rule, pattern in compiled:
                if not pattern.search(line):
                    continue
                key = (rel, line_index, rule.code)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    Finding(
                        file_path=rel,
                        line_number=line_index,
                        rule_code=rule.code,
                        severity=rule.severity,
                        evidence=line.strip()[:300],
                    )
                )

    return files_scanned, findings


def _iter_candidate_files(root: Path, include_exts: set[str], exclude_dirs: set[str]):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in exclude_dirs for part in path.parts):
            continue
        if path.suffix.lower() in include_exts:
            yield path


def _load_notebook_as_text(path: Path) -> tuple[str | None, dict[int, int]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return None, {}

    cells = payload.get("cells") if isinstance(payload, dict) else None
    if not isinstance(cells, list):
        return None, {}

    merged_lines: list[str] = []
    line_map: dict[int, int] = {}
    current_line = 0

    for cell in cells:
        if not isinstance(cell, dict):
            continue
        if str(cell.get("cell_type", "")).lower() != "code":
            continue

        source = cell.get("source")
        if isinstance(source, str):
            source_lines = source.splitlines()
        elif isinstance(source, list):
            source_lines = "".join(str(item) for item in source).splitlines()
        else:
            source_lines = []

        for local_line_num, line in enumerate(source_lines, start=1):
            current_line += 1
            merged_lines.append(line)
            line_map[current_line] = local_line_num

    return "\n".join(merged_lines), line_map
