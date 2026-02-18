from __future__ import annotations

import re
from pathlib import Path

from code_scanner.models import Finding


R_PATTERNS = [
    (re.compile(r"\blibrary\((caret|randomForest|xgboost|glmnet|tidymodels)\)"), ("R_ML_LIBRARY", "classical_ml", "medium")),
    (re.compile(r"\b(train|predict)\s*\("), ("R_TRAIN_OR_INFER", "model_lifecycle", "medium")),
]

SQL_PATTERNS = [
    (re.compile(r"\b(CREATE\s+MODEL|ML\.TRAINING_INFO|ML\.PREDICT|PREDICT\()\b", re.IGNORECASE), ("SQL_ML_OPERATION", "analytics_ml", "medium")),
]

SCALA_PATTERNS = [
    (re.compile(r"\b(org\.apache\.spark\.ml|spark\.ml)\b"), ("SCALA_SPARK_ML", "classical_ml", "medium")),
    (re.compile(r"\b(fit|transform|predict)\s*\("), ("SCALA_MODEL_CALL", "model_lifecycle", "medium")),
]

EXTENSION_PATTERN_MAP = {
    ".r": R_PATTERNS,
    ".R": R_PATTERNS,
    ".sql": SQL_PATTERNS,
    ".scala": SCALA_PATTERNS,
}


def run_polyglot_pattern_scan(
    repo_path: Path,
    *,
    max_file_size_bytes: int,
    max_files_per_repo: int,
) -> list[Finding]:
    findings: list[Finding] = []
    scanned = 0

    for file_path in repo_path.rglob("*"):
        if scanned >= max_files_per_repo:
            break
        if not file_path.is_file() or file_path.suffix not in EXTENSION_PATTERN_MAP:
            continue
        if "/.git/" in file_path.as_posix():
            continue

        scanned += 1

        try:
            if file_path.stat().st_size > max_file_size_bytes:
                continue
            text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        relative = str(file_path.relative_to(repo_path))
        patterns = EXTENSION_PATTERN_MAP[file_path.suffix]
        for idx, line in enumerate(text.splitlines(), start=1):
            for regex, signal in patterns:
                if regex.search(line):
                    findings.append(_to_finding(relative, idx, signal, line.strip()))

    return findings


def _to_finding(
    file_path: str,
    line_number: int,
    signal: tuple[str, str, str],
    evidence: str,
) -> Finding:
    code, category, severity = signal
    return Finding(
        file_path=file_path,
        line_number=line_number,
        signal_code=code,
        category=category,
        severity=severity,
        detector="polyglot_patterns",
        confidence=0.82,
        evidence=evidence[:500],
    )
