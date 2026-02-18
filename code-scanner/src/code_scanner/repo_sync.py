from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from code_scanner.models import RepoDescriptor, SyncedRepo


class RepoSyncError(RuntimeError):
    pass


def sync_repo(repo: RepoDescriptor, cache_root: str | Path, use_token_for_clone: bool) -> SyncedRepo:
    if repo.local_path:
        local = Path(repo.local_path).resolve()
        if not local.exists():
            raise RepoSyncError(f"Local repo path does not exist: {local}")
        return SyncedRepo(repo_path=local, commit_sha=_read_head_sha(local))

    if not repo.clone_url:
        raise RepoSyncError(f"Repo {repo.full_name} has no clone URL")

    cache_root_path = Path(cache_root).resolve()
    cache_root_path.mkdir(parents=True, exist_ok=True)
    repo_dir = cache_root_path / _safe_repo_dirname(repo.provider_name, repo.full_name)

    clone_url = repo.clone_url
    tokenized_clone_url = clone_url
    if use_token_for_clone and repo.auth_token:
        tokenized_clone_url = _inject_token(clone_url, repo.auth_token, repo.clone_auth_user)

    if not repo_dir.exists():
        branch = repo.default_branch or "main"
        cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            branch,
            tokenized_clone_url,
            str(repo_dir),
        ]
        _run_git(cmd)
    else:
        _run_git(["git", "-C", str(repo_dir), "remote", "set-url", "origin", tokenized_clone_url])
        _run_git(["git", "-C", str(repo_dir), "fetch", "origin", "--prune", "--depth", "1"])

        branch = repo.default_branch
        if branch:
            checkout = subprocess.run(
                ["git", "-C", str(repo_dir), "checkout", branch],
                text=True,
                capture_output=True,
            )
            if checkout.returncode != 0:
                _run_git(["git", "-C", str(repo_dir), "checkout", "-B", branch, f"origin/{branch}"])
            _run_git(["git", "-C", str(repo_dir), "pull", "--ff-only", "origin", branch])
        else:
            _run_git(["git", "-C", str(repo_dir), "pull", "--ff-only"])

    return SyncedRepo(repo_path=repo_dir, commit_sha=_read_head_sha(repo_dir))


def _safe_repo_dirname(provider_name: str, full_name: str) -> str:
    safe = full_name.replace("/", "__").replace(" ", "_")
    return f"{provider_name}__{safe}"


def _run_git(cmd: list[str]) -> None:
    process = subprocess.run(cmd, text=True, capture_output=True)
    if process.returncode != 0:
        stderr = (process.stderr or "").strip()
        stdout = (process.stdout or "").strip()
        message = stderr or stdout or "unknown git error"
        raise RepoSyncError(f"Git command failed: {' '.join(cmd)}\n{message[:500]}")


def _read_head_sha(repo_path: Path) -> str | None:
    process = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
    )
    if process.returncode != 0:
        return None
    sha = (process.stdout or "").strip()
    return sha or None


def _inject_token(url: str, token: str, username: str | None) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        return url

    user = (username or "token").strip()
    safe_user = quote(user, safe="")
    safe_token = quote(token, safe="")

    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{safe_user}:{safe_token}@{host}{port}"

    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
