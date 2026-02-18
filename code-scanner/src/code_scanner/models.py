from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderSettings:
    type: str
    name: str
    base_url: str | None = None
    token_env: str | None = None
    org: str | None = None
    workspace: str | None = None
    project_key: str | None = None
    root_dir: str | None = None
    recursive: bool = False
    use_token_for_clone: bool = False


@dataclass(frozen=True)
class ScanSettings:
    include_repo_patterns: tuple[str, ...] = ()
    exclude_repo_patterns: tuple[str, ...] = ()
    max_file_size_bytes: int = 500_000
    max_files_per_repo: int = 40_000


@dataclass(frozen=True)
class AppConfig:
    db_path: str
    repo_cache_dir: str
    rules_path: str
    providers: tuple[ProviderSettings, ...]
    scan: ScanSettings


@dataclass(frozen=True)
class RepoDescriptor:
    provider_name: str
    provider_type: str
    external_id: str
    full_name: str
    clone_url: str | None
    default_branch: str | None
    web_url: str | None
    auth_token: str | None = None
    clone_auth_user: str | None = None
    local_path: str | None = None


@dataclass(frozen=True)
class SignalRule:
    signal_code: str
    category: str
    severity: str
    description: str
    pattern: str
    ignore_case: bool = False


@dataclass(frozen=True)
class Finding:
    file_path: str
    line_number: int | None
    signal_code: str
    category: str
    severity: str
    detector: str
    confidence: float
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SyncedRepo:
    repo_path: Path
    commit_sha: str | None


@dataclass(frozen=True)
class ScanSummary:
    run_id: int
    mode: str
    status: str
    total_repos: int
    scanned_repos: int
    skipped_repos: int
    findings_count: int
    error_count: int
    output_dir: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
