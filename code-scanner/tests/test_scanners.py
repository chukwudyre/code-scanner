import json
from pathlib import Path

from code_scanner.models import ScanSettings, SignalRule
from code_scanner.scanners.engine import scan_repository


def test_scanner_detects_rules_and_ast(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "model.py").write_text(
        "import sklearn\n"
        "from transformers import AutoModel\n"
        "model.fit(X, y)\n"
        "pred = model.predict(X)\n",
        encoding="utf-8",
    )

    rules = [
        SignalRule(
            signal_code="ML_SKLEARN_USAGE",
            category="classical_ml",
            severity="medium",
            description="sklearn usage",
            pattern="\\bsklearn\\b",
            ignore_case=True,
        ),
        SignalRule(
            signal_code="ML_TRAINING_CALL",
            category="model_lifecycle",
            severity="high",
            description="fit call",
            pattern="\\.fit\\s*\\(",
            ignore_case=False,
        ),
    ]

    findings = scan_repository(
        repo,
        rules,
        ScanSettings(
            include_repo_patterns=(),
            exclude_repo_patterns=(),
            max_file_size_bytes=200_000,
            max_files_per_repo=1000,
        ),
    )

    codes = {item.signal_code for item in findings}
    assert "ML_SKLEARN_USAGE" in codes
    assert "ML_TRAINING_CALL" in codes
    assert "AST_SKLEARN_IMPORT" in codes
    assert "AST_TRAIN_CALL" in codes


def test_scanner_detects_js_ts_java_and_polyglot_signals(tmp_path: Path):
    repo = tmp_path / "polyglot-repo"
    repo.mkdir()

    (repo / "llm.ts").write_text(
        "import OpenAI from 'openai';\n"
        "const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });\n"
        "await client.chat.completions.create({ model: 'gpt-4.1-mini', messages: [] });\n",
        encoding="utf-8",
    )
    (repo / "Trainer.java").write_text(
        "import org.apache.spark.ml.Pipeline;\n"
        "class Trainer {\n"
        "  void run() { fit(); predict(); }\n"
        "}\n",
        encoding="utf-8",
    )
    (repo / "analysis.R").write_text(
        "library(caret)\n"
        "fit <- train(y ~ ., data = df, method = 'rf')\n",
        encoding="utf-8",
    )
    (repo / "model.sql").write_text(
        "SELECT * FROM ML.PREDICT(MODEL `project.dataset.m`, (SELECT 1 AS x));\n",
        encoding="utf-8",
    )
    (repo / "pipeline.scala").write_text(
        "import org.apache.spark.ml.Pipeline\n"
        "val model = pipeline.fit(df)\n",
        encoding="utf-8",
    )

    rules = [
        SignalRule(
            signal_code="ML_OPENAI_USAGE",
            category="llm",
            severity="high",
            description="openai usage",
            pattern="\\bopenai\\b",
            ignore_case=True,
        )
    ]

    findings = scan_repository(
        repo,
        rules,
        ScanSettings(
            include_repo_patterns=(),
            exclude_repo_patterns=(),
            max_file_size_bytes=200_000,
            max_files_per_repo=5000,
        ),
    )

    codes = {item.signal_code for item in findings}
    assert "JS_OPENAI_IMPORT" in codes
    assert "JS_OPENAI_API_CALL" in codes
    assert "JAVA_SPARK_ML_IMPORT" in codes
    assert "JAVA_TRAIN_CALL" in codes
    assert "R_ML_LIBRARY" in codes
    assert "SQL_ML_OPERATION" in codes
    assert "SCALA_SPARK_ML" in codes


def test_scanner_detects_notebook_ast_signals(tmp_path: Path):
    repo = tmp_path / "nb-repo"
    repo.mkdir()

    notebook_payload = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "cells": [
            {
                "cell_type": "code",
                "source": [
                    "import sklearn\n",
                    "from sklearn.linear_model import LinearRegression\n",
                    "model.fit(X, y)\n",
                    "pred = model.predict(X)\n",
                ],
                "metadata": {},
            }
        ],
        "metadata": {},
    }
    (repo / "analysis.ipynb").write_text(json.dumps(notebook_payload), encoding="utf-8")

    findings = scan_repository(
        repo,
        rules=[],
        scan_settings=ScanSettings(
            include_repo_patterns=(),
            exclude_repo_patterns=(),
            max_file_size_bytes=2_000_000,
            max_files_per_repo=5000,
        ),
    )

    codes = {item.signal_code for item in findings}
    assert "NB_AST_SKLEARN_IMPORT" in codes
    assert "NB_AST_TRAIN_CALL" in codes
    assert "NB_AST_INFER_CALL" in codes
