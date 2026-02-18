from __future__ import annotations

import re
from pathlib import Path

from code_scanner.models import Finding


JAVA_IMPORT_PATTERNS = [
    (re.compile(r"^\s*import\s+ai\.onnxruntime\..*;"), ("JAVA_ONNX_IMPORT", "deep_learning", "medium")),
    (re.compile(r"^\s*import\s+org\.deeplearning4j\..*;"), ("JAVA_DL4J_IMPORT", "deep_learning", "high")),
    (re.compile(r"^\s*import\s+org\.apache\.spark\.ml\..*;"), ("JAVA_SPARK_ML_IMPORT", "classical_ml", "medium")),
    (re.compile(r"^\s*import\s+smile\..*;"), ("JAVA_SMILE_IMPORT", "classical_ml", "medium")),
    (re.compile(r"^\s*import\s+com\.openai\..*;"), ("JAVA_OPENAI_IMPORT", "llm", "high")),
]

JAVA_CALL_PATTERNS = [
    (re.compile(r"\b(fit|train|trainModel)\s*\("), ("JAVA_TRAIN_CALL", "model_lifecycle", "high")),
    (re.compile(r"\b(predict|infer|classify|score)\s*\("), ("JAVA_INFER_CALL", "model_lifecycle", "medium")),
    (re.compile(r"\b(save|load)\s*\("), ("JAVA_MODEL_IO_CALL", "model_lifecycle", "medium")),
]

JAVA_EXTENSIONS = {".java", ".kt", ".scala"}


def run_java_structured_scan(
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
        if not file_path.is_file() or file_path.suffix.lower() not in JAVA_EXTENSIONS:
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
        for idx, line in enumerate(text.splitlines(), start=1):
            for pattern, signal in JAVA_IMPORT_PATTERNS:
                if pattern.search(line):
                    findings.append(_to_finding(relative, idx, signal, line.strip()))

            for pattern, signal in JAVA_CALL_PATTERNS:
                if pattern.search(line):
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
        detector="java_structured",
        confidence=0.88,
        evidence=evidence[:500],
    )
