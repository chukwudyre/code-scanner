from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from shutil import which

from code_scanner.models import Finding, SignalRule


def run_rules_scan(
    repo_path: Path,
    rules: list[SignalRule],
    *,
    max_file_size_bytes: int,
    max_files_per_repo: int,
) -> list[Finding]:
    if which("rg"):
        return _run_with_ripgrep(repo_path, rules)
    return _run_with_python(repo_path, rules, max_file_size_bytes, max_files_per_repo)


def _run_with_ripgrep(repo_path: Path, rules: list[SignalRule]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        cmd = ["rg", "--json", "--line-number", "--color", "never", "-e", rule.pattern, "."]
        if rule.ignore_case:
            cmd.insert(1, "-i")

        process = subprocess.run(cmd, cwd=repo_path, text=True, capture_output=True)
        if process.returncode not in {0, 1}:
            continue

        for line in process.stdout.splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("type") != "match":
                continue

            data = payload.get("data", {})
            path = data.get("path", {}).get("text")
            line_number = data.get("line_number")
            evidence = data.get("lines", {}).get("text", "").strip()
            if not path:
                continue

            findings.append(
                Finding(
                    file_path=str(path),
                    line_number=int(line_number) if isinstance(line_number, int) else None,
                    signal_code=rule.signal_code,
                    category=rule.category,
                    severity=rule.severity,
                    detector="rules_rg",
                    confidence=0.85,
                    evidence=evidence[:500],
                )
            )

    return findings


def _run_with_python(
    repo_path: Path,
    rules: list[SignalRule],
    max_file_size_bytes: int,
    max_files_per_repo: int,
) -> list[Finding]:
    compiled = [
        (
            rule,
            re.compile(rule.pattern, flags=re.IGNORECASE if rule.ignore_case else 0),
        )
        for rule in rules
    ]

    findings: list[Finding] = []
    scanned_files = 0

    for path in _iter_files(repo_path):
        if scanned_files >= max_files_per_repo:
            break
        scanned_files += 1

        if path.stat().st_size > max_file_size_bytes:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError:
            continue

        relative = str(path.relative_to(repo_path))
        for line_index, line in enumerate(text.splitlines(), start=1):
            for rule, pattern in compiled:
                if pattern.search(line):
                    findings.append(
                        Finding(
                            file_path=relative,
                            line_number=line_index,
                            signal_code=rule.signal_code,
                            category=rule.category,
                            severity=rule.severity,
                            detector="rules_py",
                            confidence=0.75,
                            evidence=line.strip()[:500],
                        )
                    )

    return findings


def _iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if "/.git/" in path.as_posix():
            continue
        yield path
