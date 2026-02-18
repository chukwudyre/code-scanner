from pathlib import Path

from code_scanner.db import Database
from code_scanner.models import Finding, RepoDescriptor


def test_db_run_and_findings(tmp_path: Path):
    db_path = tmp_path / "scanner.db"
    db = Database(db_path)
    db.init_schema()

    run_id = db.start_run(mode="full", total_repos=1)
    repo = RepoDescriptor(
        provider_name="local-test",
        provider_type="local",
        external_id="repo-1",
        full_name="local/repo-1",
        clone_url=None,
        default_branch=None,
        web_url=None,
        local_path=str(tmp_path),
    )
    repo_id = db.upsert_repo(repo)

    count = db.insert_findings(
        run_id,
        repo_id,
        commit_sha="abc123",
        findings=[
            Finding(
                file_path="main.py",
                line_number=10,
                signal_code="ML_TEST",
                category="test",
                severity="high",
                detector="unit",
                confidence=0.9,
                evidence="model.fit(X, y)",
            )
        ],
    )

    db.update_repo_scan_state(repo_id, "abc123", run_id)
    db.finish_run(
        run_id,
        status="SUCCESS",
        scanned_repos=1,
        skipped_repos=0,
        findings_count=count,
        error_count=0,
    )

    rows = db.query("SELECT COUNT(*) AS c FROM findings")
    assert int(rows[0]["c"]) == 1

    last_commit = db.get_last_commit_sha(repo_id)
    assert last_commit == "abc123"

    db.close()
