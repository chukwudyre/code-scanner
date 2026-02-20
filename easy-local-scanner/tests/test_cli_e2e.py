from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest


class CLIE2ETests(unittest.TestCase):
    def test_init_scan_report_e2e(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = tmp_path / "repo"
            repo.mkdir()
            (repo / "script.py").write_text("import openai\\nmodel.fit(X, y)\\n", encoding="utf-8")

            db = tmp_path / "scanner.db"
            out = tmp_path / "report"
            rules = root / "configs" / "rules.json"

            env = os.environ.copy()
            env["PYTHONPATH"] = str(root / "src")

            init = subprocess.run(
                [sys.executable, "-m", "easy_local_scanner.cli", "init", "--db-path", str(db)],
                cwd=root,
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            self.assertIn("initialized", init.stdout)

            scan = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "easy_local_scanner.cli",
                    "scan",
                    "--repo-path",
                    str(repo),
                    "--rules",
                    str(rules),
                    "--db-path",
                    str(db),
                ],
                cwd=root,
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            payload = json.loads(scan.stdout)
            self.assertGreaterEqual(payload["findings_count"], 1)

            report = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "easy_local_scanner.cli",
                    "report",
                    "--db-path",
                    str(db),
                    "--output-dir",
                    str(out),
                ],
                cwd=root,
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            report_payload = json.loads(report.stdout)
            self.assertIn("files", report_payload)


if __name__ == "__main__":
    unittest.main()
