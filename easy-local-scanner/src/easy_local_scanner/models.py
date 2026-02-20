from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    code: str
    description: str
    severity: str
    pattern: str
    ignore_case: bool


@dataclass(frozen=True)
class Finding:
    file_path: str
    line_number: int
    rule_code: str
    severity: str
    evidence: str
