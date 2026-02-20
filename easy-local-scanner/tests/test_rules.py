from pathlib import Path
import unittest

from easy_local_scanner.rules import load_rules


class RulesTests(unittest.TestCase):
    def test_load_default_rules(self):
        root = Path(__file__).resolve().parents[1]
        rules = load_rules(root / "configs" / "rules.json")
        self.assertGreater(len(rules), 0)
        self.assertTrue(any(rule.code == "SKLEARN_USAGE" for rule in rules))


if __name__ == "__main__":
    unittest.main()
