from pathlib import Path
import unittest

from easy_local_scanner.models import Rule
from easy_local_scanner.scanner import scan_local_repo


class ScannerTests(unittest.TestCase):
    def test_scan_detects_findings(self):
        root = Path(__file__).resolve().parent / "sample_repo"
        root.mkdir(exist_ok=True)
        (root / "model.py").write_text(
            "import sklearn\n"
            "model.fit(X, y)\n"
            "pred = model.predict(X)\n",
            encoding="utf-8",
        )

        rules = [
            Rule(
                code="SKLEARN_USAGE",
                description="sklearn usage",
                severity="medium",
                pattern=r"\bsklearn\b",
                ignore_case=True,
            ),
            Rule(
                code="TRAIN_CALL",
                description="train call",
                severity="high",
                pattern=r"\bfit\s*\(",
                ignore_case=True,
            ),
        ]

        files_scanned, findings = scan_local_repo(
            root,
            rules,
            max_file_size_bytes=200000,
            max_files=1000,
        )

        self.assertGreaterEqual(files_scanned, 1)
        codes = {item.rule_code for item in findings}
        self.assertIn("SKLEARN_USAGE", codes)
        self.assertIn("TRAIN_CALL", codes)


if __name__ == "__main__":
    unittest.main()
