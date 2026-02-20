from __future__ import annotations

import json
from pathlib import Path

from easy_local_scanner.models import Rule


class RulesError(ValueError):
    pass


def load_rules(path: str | Path) -> list[Rule]:
    rules_path = Path(path)
    if not rules_path.exists():
        raise RulesError(f"Rules file not found: {rules_path}")

    raw = json.loads(rules_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise RulesError("Rules file must contain a non-empty JSON list")

    rules: list[Rule] = []
    for item in raw:
        if not isinstance(item, dict):
            raise RulesError("Each rule must be an object")
        for key in ("code", "description", "severity", "pattern"):
            if key not in item:
                raise RulesError(f"Rule missing key: {key}")
        rules.append(
            Rule(
                code=str(item["code"]),
                description=str(item["description"]),
                severity=str(item["severity"]).lower(),
                pattern=str(item["pattern"]),
                ignore_case=bool(item.get("ignore_case", False)),
            )
        )

    return rules
