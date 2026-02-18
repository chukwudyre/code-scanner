from pathlib import Path

from code_scanner.config import load_config, load_rules


def test_example_config_and_rules_load():
    root = Path(__file__).resolve().parents[1]
    config = load_config(root / "configs" / "config.example.json")
    rules = load_rules(root / "configs" / "default_rules.json")

    assert config.providers
    assert rules
    assert any(rule.signal_code == "ML_SKLEARN_USAGE" for rule in rules)
