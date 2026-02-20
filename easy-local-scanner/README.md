# Easy Local Scanner

A simple, local-only scanner designed for learning.

This project intentionally avoids provider/API complexity (GitHub, Bitbucket, Sourcegraph).
You point it at a local folder, it scans files with regex rules, stores findings in SQLite,
and writes a report.

## Why this project exists

`code-scanner` is production-style and more complex. This project is easier to read and extend.

Use this to learn the core flow first:
1. `init` database
2. `scan` local repo/folder
3. `report` outputs

Later, you can add provider adapters (GitHub/Bitbucket/Sourcegraph) on top of this.

## Project structure

- `src/easy_local_scanner/cli.py`: CLI commands
- `src/easy_local_scanner/scanner.py`: file scanning logic
- `src/easy_local_scanner/rules.py`: rules loader
- `src/easy_local_scanner/db.py`: SQLite schema and writes
- `src/easy_local_scanner/report.py`: CSV/JSON reports
- `configs/rules.json`: default rule set

## Quick start (no install required)

```bash
cd /Users/chukwudire/Documents/New\ project/easy-local-scanner

# 1) Initialize DB
PYTHONPATH=src python -m easy_local_scanner.cli init --db-path data/easy_scanner.db

# 2) Scan this project folder itself (example)
PYTHONPATH=src python -m easy_local_scanner.cli scan \
  --repo-path . \
  --rules configs/rules.json \
  --db-path data/easy_scanner.db

# 3) Generate report files
PYTHONPATH=src python -m easy_local_scanner.cli report \
  --db-path data/easy_scanner.db \
  --output-dir outputs/report-1
```

## Windows PowerShell variant

```powershell
cd "C:\path\to\easy-local-scanner"
python -m easy_local_scanner.cli init --db-path data/easy_scanner.db
python -m easy_local_scanner.cli scan --repo-path . --rules configs/rules.json --db-path data/easy_scanner.db
python -m easy_local_scanner.cli report --db-path data/easy_scanner.db --output-dir outputs/report-1
```

If Python must come from a shared path:

```powershell
& "Z:\shared\Python311\python.exe" -m easy_local_scanner.cli init --db-path data/easy_scanner.db
& "Z:\shared\Python311\python.exe" -m easy_local_scanner.cli scan --repo-path . --rules configs/rules.json --db-path data/easy_scanner.db
& "Z:\shared\Python311\python.exe" -m easy_local_scanner.cli report --db-path data/easy_scanner.db --output-dir outputs/report-1
```

## Common scan options

- `--repo-path`: local folder to scan (required)
- `--rules`: rule file (default `configs/rules.json`)
- `--max-file-size-bytes`: skip very large files
- `--max-files`: cap scan size
- `--include-exts`: file extensions to scan (comma-separated)
- `--exclude-dirs`: directory names to skip (comma-separated)

## Output files

- `summary.json`
- `findings_by_rule.csv`
- `findings_by_file.csv`
- `findings.csv`

## Extend this project later

Easy extension points:

1. Add a new provider module that returns local repo paths from GitHub/Bitbucket APIs.
2. Add AST scanners (Python/JS/Java) for higher signal quality.
3. Add risk scoring and owner mapping tables.
4. Add CI workflow for tests.

## Run tests

```bash
cd /Users/chukwudire/Documents/New\ project/easy-local-scanner
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v
```
