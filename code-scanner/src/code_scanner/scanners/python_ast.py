from __future__ import annotations

import ast
from pathlib import Path

from code_scanner.models import Finding


IMPORT_SIGNAL_MAP = {
    "openai": ("AST_OPENAI_IMPORT", "llm", "high"),
    "transformers": ("AST_TRANSFORMERS_IMPORT", "llm", "high"),
    "langchain": ("AST_LANGCHAIN_IMPORT", "llm", "medium"),
    "sklearn": ("AST_SKLEARN_IMPORT", "classical_ml", "medium"),
    "tensorflow": ("AST_TENSORFLOW_IMPORT", "deep_learning", "high"),
    "keras": ("AST_KERAS_IMPORT", "deep_learning", "high"),
    "torch": ("AST_TORCH_IMPORT", "deep_learning", "high"),
    "xgboost": ("AST_XGBOOST_IMPORT", "classical_ml", "medium"),
    "lightgbm": ("AST_LIGHTGBM_IMPORT", "classical_ml", "medium"),
    "catboost": ("AST_CATBOOST_IMPORT", "classical_ml", "medium"),
    "mlflow": ("AST_MLFLOW_IMPORT", "mlops", "medium"),
}

CALL_SIGNAL_MAP = {
    "fit": ("AST_TRAIN_CALL", "model_lifecycle", "high"),
    "train": ("AST_TRAIN_CALL", "model_lifecycle", "high"),
    "predict": ("AST_INFER_CALL", "model_lifecycle", "medium"),
    "infer": ("AST_INFER_CALL", "model_lifecycle", "medium"),
    "generate": ("AST_INFER_CALL", "model_lifecycle", "medium"),
    "save": ("AST_SAVE_CALL", "model_lifecycle", "medium"),
    "save_model": ("AST_SAVE_CALL", "model_lifecycle", "medium"),
    "load": ("AST_LOAD_CALL", "model_lifecycle", "medium"),
}


def run_python_ast_scan(
    repo_path: Path,
    *,
    max_file_size_bytes: int,
    max_files_per_repo: int,
) -> list[Finding]:
    findings: list[Finding] = []
    scanned = 0

    for file_path in repo_path.rglob("*.py"):
        if scanned >= max_files_per_repo:
            break
        scanned += 1

        if "/.git/" in file_path.as_posix():
            continue

        try:
            if file_path.stat().st_size > max_file_size_bytes:
                continue
        except OSError:
            continue

        try:
            source = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        rel_path = str(file_path.relative_to(repo_path))
        findings.extend(_scan_tree(tree, rel_path))

    return findings


def _scan_tree(tree: ast.AST, rel_path: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                base = alias.name.split(".")[0]
                signal = IMPORT_SIGNAL_MAP.get(base)
                if signal:
                    findings.append(
                        _to_finding(rel_path, getattr(node, "lineno", None), signal, f"import {alias.name}")
                    )

        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            signal = IMPORT_SIGNAL_MAP.get(module)
            if signal:
                findings.append(
                    _to_finding(rel_path, getattr(node, "lineno", None), signal, f"from {node.module} import ...")
                )

        elif isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if call_name:
                signal = CALL_SIGNAL_MAP.get(call_name)
                if signal:
                    findings.append(
                        _to_finding(
                            rel_path,
                            getattr(node, "lineno", None),
                            signal,
                            f"call {call_name}(...)"
                        )
                    )

    return findings


def _call_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _to_finding(
    file_path: str,
    line_number: int | None,
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
        detector="python_ast",
        confidence=0.95,
        evidence=evidence,
    )
