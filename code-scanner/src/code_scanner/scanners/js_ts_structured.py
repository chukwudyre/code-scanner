from __future__ import annotations

import re
from pathlib import Path

from code_scanner.models import Finding


JS_TS_IMPORT_PATTERNS = [
    (re.compile(r"^\s*import\s+.*?\bfrom\s+['\"]openai['\"]", re.IGNORECASE), ("JS_OPENAI_IMPORT", "llm", "high")),
    (re.compile(r"^\s*import\s+.*?\bfrom\s+['\"]@?langchain", re.IGNORECASE), ("JS_LANGCHAIN_IMPORT", "llm", "medium")),
    (re.compile(r"^\s*import\s+.*?\bfrom\s+['\"]@tensorflow/tfjs['\"]", re.IGNORECASE), ("JS_TFJS_IMPORT", "deep_learning", "high")),
    (re.compile(r"^\s*import\s+.*?\bfrom\s+['\"]onnxruntime", re.IGNORECASE), ("JS_ONNX_IMPORT", "deep_learning", "medium")),
    (re.compile(r"^\s*const\s+\w+\s*=\s*require\(\s*['\"]openai['\"]\s*\)", re.IGNORECASE), ("JS_OPENAI_IMPORT", "llm", "high")),
]

JS_TS_CALL_PATTERNS = [
    (re.compile(r"\b(chat\.completions\.create|responses\.create|embeddings\.create)\s*\("), ("JS_OPENAI_API_CALL", "llm", "high")),
    (re.compile(r"\b(predict|infer|generate)\s*\("), ("JS_INFER_CALL", "model_lifecycle", "medium")),
    (re.compile(r"\b(train|fit)\s*\("), ("JS_TRAIN_CALL", "model_lifecycle", "high")),
]

JS_TS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}


def run_js_ts_structured_scan(
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
        if not file_path.is_file() or file_path.suffix.lower() not in JS_TS_EXTENSIONS:
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
        lines = text.splitlines()
        for idx, line in enumerate(lines, start=1):
            for pattern, signal in JS_TS_IMPORT_PATTERNS:
                if pattern.search(line):
                    findings.append(_to_finding(relative, idx, signal, line.strip()))

            for pattern, signal in JS_TS_CALL_PATTERNS:
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
        detector="js_ts_structured",
        confidence=0.9,
        evidence=evidence[:500],
    )
