# Code Scanner

`code-scanner` is a deterministic, local-first repository scanner for model governance.

It supports:
- GitHub org repos
- Bitbucket Cloud workspaces
- Bitbucket Server/Data Center projects
- Local git repos

It stores scan history and findings in a local SQLite database.

## What it does

1. Discovers repos from configured providers.
2. Syncs repos locally (or scans local paths directly).
3. Runs deterministic detectors:
- `ripgrep` pattern rules (high recall)
- Python AST analysis (structured signals)
- JS/TS structured import/call analysis
- Java structured import/call analysis
- Polyglot pattern analysis for R, SQL, and Scala
4. Writes findings to local SQLite.
5. Generates CSV/JSON governance reports.

## Quick start

```bash
cd /Users/chukwudire/Documents/New\ project/code-scanner
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Initialize DB:

```bash
code-scanner init --db-path data/code_scanner.db
```

Run local scan (using default local provider in example config):

```bash
code-scanner scan --config configs/config.example.json --mode full
```

Generate reports:

```bash
code-scanner report --db-path data/code_scanner.db --output-dir outputs/report-1
```

## Run Playbooks

### 1) Scan current local repo (single repo)

Config:
- Use `configs/config.example.json` as-is (`root_dir: "."`, `recursive: false`)

Run:

```bash
code-scanner init --db-path data/code_scanner.db
code-scanner scan --config configs/config.example.json --mode full
code-scanner report --db-path data/code_scanner.db --output-dir outputs/report-local-single
```

### 2) Scan many local repos under one parent folder

Use `configs/local-multi.example.json` and set `root_dir` to the parent path that contains repo folders.

Run:

```bash
code-scanner scan --config configs/local-multi.example.json --mode full
code-scanner report --db-path data/code_scanner.db --output-dir outputs/report-local-multi
```

### 3) Scan one public GitHub repo (single target)

Use `configs/github-single-public.example.json` and set:
- `org` to the repo owner
- CLI `--repo-regex` to `^owner/repo$`

Example for `https://github.com/chukwudyre/code-scanner`:

```bash
code-scanner scan \
  --config configs/github-single-public.example.json \
  --mode full \
  --repo-regex '^chukwudyre/code-scanner$' \
  --limit 1

code-scanner report --db-path data/code_scanner.db --output-dir outputs/report-github-single
```

### 4) Incremental scans (after baseline full scan)

```bash
code-scanner scan --config configs/config.example.json --mode incremental
```

### 5) Restricted environments (no app launcher / no pip install)

Run the module directly with approved Python:

```bash
PYTHONPATH=src python -m code_scanner.cli init --db-path data/code_scanner.db
PYTHONPATH=src python -m code_scanner.cli scan --config configs/config.example.json --mode full
PYTHONPATH=src python -m code_scanner.cli report --db-path data/code_scanner.db --output-dir outputs/report-1
```

## Config

The default config is `configs/config.example.json`.

### Local provider (works immediately)

```json
{
  "type": "local",
  "name": "local-workspace",
  "root_dir": ".",
  "recursive": false
}
```

### GitHub provider

```json
{
  "type": "github",
  "name": "github-enterprise",
  "base_url": "https://api.github.com",
  "org": "your-org",
  "token_env": "GITHUB_TOKEN",
  "use_token_for_clone": true
}
```

### Bitbucket Cloud provider

```json
{
  "type": "bitbucket_cloud",
  "name": "bitbucket-cloud",
  "workspace": "your-workspace",
  "token_env": "BITBUCKET_TOKEN",
  "use_token_for_clone": true
}
```

### Bitbucket Server provider

```json
{
  "type": "bitbucket_server",
  "name": "bitbucket-server",
  "base_url": "https://bitbucket.company.com",
  "project_key": "RISK",
  "token_env": "BITBUCKET_TOKEN",
  "use_token_for_clone": true
}
```

## Incremental scans

After an initial full scan, run incremental mode:

```bash
code-scanner scan --config configs/config.example.json --mode incremental
```

Incremental mode skips repos when commit SHA has not changed.

## Outputs

The scanner writes data to SQLite (`data/code_scanner.db`) and reports include:
- `run_summary.json`
- `findings_by_repo.csv`
- `findings_by_signal.csv`
- `top_findings.csv`

## Language coverage (v1.1)

- Structured scanners:
  - Python (`.py`) AST
  - Jupyter notebooks (`.ipynb`) code-cell AST
  - JavaScript/TypeScript (`.js/.jsx/.ts/.tsx/.mjs/.cjs`)
  - Java/Kotlin/Scala (`.java/.kt/.scala`) structured heuristics
- Pattern-based detectors:
  - R (`.r`)
  - SQL (`.sql`)
  - Scala (`.scala`)
  - Plus any language matched by `configs/default_rules.json` through `ripgrep`

## Notes

- `ripgrep` is used when installed; otherwise scanner falls back to Python regex scanning.
- For private repos, authenticated clone requires `use_token_for_clone=true` and working token permissions.
- This is deterministic scanning; no LLM is required.
- For notebook-heavy repos, keep `scan.max_file_size_bytes` high (for example `15000000`) so `.ipynb` files are not skipped.
- If you hit TLS certificate errors on macOS Python, install/refresh trust roots and optionally set:
  - `SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())")`
  - or `CODE_SCANNER_CA_BUNDLE=/path/to/company-ca-bundle.pem`
