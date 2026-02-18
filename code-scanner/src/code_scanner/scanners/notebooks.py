from __future__ import annotations

import ast
import json
from pathlib import Path

from code_scanner.models import Finding


IMPORT_SIGNAL_MAP = {
    "openai": ("NB_AST_OPENAI_IMPORT", "llm", "high"),
    "transformers": ("NB_AST_TRANSFORMERS_IMPORT", "llm", "high"),
    "langchain": ("NB_AST_LANGCHAIN_IMPORT", "llm", "medium"),
    "sklearn": ("NB_AST_SKLEARN_IMPORT", "classical_ml", "medium"),
    "tensorflow": ("NB_AST_TENSORFLOW_IMPORT", "deep_learning", "high"),
    "keras": ("NB_AST_KERAS_IMPORT", "deep_learning", "high"),
    "torch": ("NB_AST_TORCH_IMPORT", "deep_learning", "high"),
    "xgboost": ("NB_AST_XGBOOST_IMPORT", "classical_ml", "medium"),
    "lightgbm": ("NB_AST_LIGHTGBM_IMPORT", "classical_ml", "medium"),
    "catboost": ("NB_AST_CATBOOST_IMPORT", "classical_ml", "medium"),
    "statsmodels": ("NB_AST_STATSMODELS_IMPORT", "statistics", "medium"),
}

CALL_SIGNAL_MAP = {
    "fit": ("NB_AST_TRAIN_CALL", "model_lifecycle", "high"),
    "train": ("NB_AST_TRAIN_CALL", "model_lifecycle", "high"),
    "predict": ("NB_AST_INFER_CALL", "model_lifecycle", "medium"),
    "infer": ("NB_AST_INFER_CALL", "model_lifecycle", "medium"),
    "generate": ("NB_AST_INFER_CALL", "model_lifecycle", "medium"),
    "save": ("NB_AST_SAVE_CALL", "model_lifecycle", "medium"),
    "load": ("NB_AST_LOAD_CALL", "model_lifecycle", "medium"),
}


def run_notebook_scan(
    repo_path: Path,
    *,
    max_file_size_bytes: int,
    max_files_per_repo: int,
) -> list[Finding]:
    findings: list[Finding] = []
    scanned = 0

    for file_path in repo_path.rglob("*.ipynb"):
        if scanned >= max_files_per_repo:
            break
        scanned += 1

        if "/.git/" in file_path.as_posix():
            continue

        try:
            if file_path.stat().st_size > max_file_size_bytes:
                continue
            notebook = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue

        cells = notebook.get("cells", []) if isinstance(notebook, dict) else []
        if not isinstance(cells, list):
            continue

        rel_path = str(file_path.relative_to(repo_path))
        for cell_index, cell in enumerate(cells, start=1):
            if not isinstance(cell, dict):
                continue
            if str(cell.get("cell_type", "")).strip().lower() != "code":
                continue

            source_text = _read_cell_source(cell.get("source"))
            if not source_text.strip():
                continue

            try:
                tree = ast.parse(source_text)
            except SyntaxError:
                continue

            findings.extend(_scan_cell_ast(tree, rel_path, cell_index))

    return findings


def _read_cell_source(source: object) -> str:
    if isinstance(source, str):
        return source
    if isinstance(source, list):
        return "".join(str(item) for item in source)
    return ""


def _scan_cell_ast(tree: ast.AST, file_path: str, cell_index: int) -> list[Finding]:
    findings: list[Finding] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                base = alias.name.split(".")[0]
                signal = IMPORT_SIGNAL_MAP.get(base)
                if signal:
                    findings.append(
                        _to_finding(
                            file_path,
                            getattr(node, "lineno", 1),
                            signal,
                            f"cell {cell_index}: import {alias.name}",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            signal = IMPORT_SIGNAL_MAP.get(module)
            if signal:
                findings.append(
                    _to_finding(
                        file_path,
                        getattr(node, "lineno", 1),
                        signal,
                        f"cell {cell_index}: from {node.module} import ...",
                    )
                )
        elif isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if call_name:
                signal = CALL_SIGNAL_MAP.get(call_name)
                if signal:
                    findings.append(
                        _to_finding(
                            file_path,
                            getattr(node, "lineno", 1),
                            signal,
                            f"cell {cell_index}: call {call_name}(...)",
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
        detector="notebook_ast",
        confidence=0.93,
        evidence=evidence,
    )
