from __future__ import annotations

import re
from pathlib import Path

from code_scanner.config import load_rules
from code_scanner.db import Database
from code_scanner.models import AppConfig, RepoDescriptor, ScanSummary
from code_scanner.providers import build_provider
from code_scanner.repo_sync import RepoSyncError, sync_repo
from code_scanner.scanners import scan_repository


def run_scan(
    config: AppConfig,
    *,
    mode: str,
    limit: int | None,
    repo_regex: str | None,
) -> ScanSummary:
    mode_normalized = mode.strip().lower()
    if mode_normalized not in {"full", "incremental"}:
        raise ValueError("mode must be one of: full, incremental")

    rules = load_rules(config.rules_path)
    all_repos = discover_repos(config)
    selected_repos = _filter_repos(
        all_repos,
        include_patterns=config.scan.include_repo_patterns,
        exclude_patterns=config.scan.exclude_repo_patterns,
        repo_regex=repo_regex,
    )

    if limit is not None and limit > 0:
        selected_repos = selected_repos[:limit]

    db = Database(config.db_path)
    db.init_schema()

    scanned_repos = 0
    skipped_repos = 0
    findings_count = 0
    error_count = 0

    run_id = db.start_run(mode=mode_normalized, total_repos=len(selected_repos))

    provider_settings = {item.name: item for item in config.providers}

    try:
        for repo in selected_repos:
            repo_id = db.upsert_repo(repo)

            try:
                settings = provider_settings[repo.provider_name]
                synced = sync_repo(
                    repo,
                    cache_root=config.repo_cache_dir,
                    use_token_for_clone=settings.use_token_for_clone,
                )
            except RepoSyncError:
                error_count += 1
                continue

            previous_sha = db.get_last_commit_sha(repo_id)
            if (
                mode_normalized == "incremental"
                and previous_sha
                and synced.commit_sha
                and previous_sha == synced.commit_sha
            ):
                skipped_repos += 1
                continue

            try:
                findings = scan_repository(synced.repo_path, rules, config.scan)
                inserted = db.insert_findings(run_id, repo_id, synced.commit_sha, findings)
                findings_count += inserted
                scanned_repos += 1
                db.update_repo_scan_state(repo_id, synced.commit_sha, run_id)
            except Exception:
                error_count += 1
                continue

        status = "SUCCESS" if error_count == 0 else "PARTIAL_SUCCESS"
        db.finish_run(
            run_id,
            status=status,
            scanned_repos=scanned_repos,
            skipped_repos=skipped_repos,
            findings_count=findings_count,
            error_count=error_count,
        )

        return ScanSummary(
            run_id=run_id,
            mode=mode_normalized,
            status=status,
            total_repos=len(selected_repos),
            scanned_repos=scanned_repos,
            skipped_repos=skipped_repos,
            findings_count=findings_count,
            error_count=error_count,
        )
    except Exception as exc:
        db.finish_run(
            run_id,
            status="FAILED",
            scanned_repos=scanned_repos,
            skipped_repos=skipped_repos,
            findings_count=findings_count,
            error_count=error_count + 1,
            notes=str(exc),
        )
        raise
    finally:
        db.close()


def discover_repos(config: AppConfig) -> list[RepoDescriptor]:
    repos: list[RepoDescriptor] = []
    for provider_settings in config.providers:
        provider = build_provider(provider_settings)
        repos.extend(provider.list_repos())
    repos.sort(key=lambda item: (item.provider_name, item.full_name))
    return repos


def _filter_repos(
    repos: list[RepoDescriptor],
    *,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
    repo_regex: str | None,
) -> list[RepoDescriptor]:
    include_compiled = [re.compile(pat) for pat in include_patterns if pat]
    exclude_compiled = [re.compile(pat) for pat in exclude_patterns if pat]
    one_off_regex = re.compile(repo_regex) if repo_regex else None

    filtered: list[RepoDescriptor] = []
    for repo in repos:
        text = repo.full_name

        if include_compiled and not any(p.search(text) for p in include_compiled):
            continue
        if exclude_compiled and any(p.search(text) for p in exclude_compiled):
            continue
        if one_off_regex and not one_off_regex.search(text):
            continue

        filtered.append(repo)

    return filtered
