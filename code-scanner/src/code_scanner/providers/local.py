from __future__ import annotations

from pathlib import Path

from code_scanner.models import ProviderSettings, RepoDescriptor
from code_scanner.providers.base import RepoProvider


class LocalProvider(RepoProvider):
    def __init__(self, settings: ProviderSettings):
        self.settings = settings
        if not settings.root_dir:
            raise ValueError("Local provider requires 'root_dir'")

    def list_repos(self) -> list[RepoDescriptor]:
        root = Path(self.settings.root_dir).resolve()
        if not root.exists():
            raise RuntimeError(f"Local provider root_dir does not exist: {root}")

        repo_paths = _find_git_repos(root, recursive=self.settings.recursive)
        repos: list[RepoDescriptor] = []
        for path in repo_paths:
            relative_name = str(path.relative_to(root)) if path != root else path.name
            external_id = relative_name or path.name
            full_name = f"local/{external_id}"
            repos.append(
                RepoDescriptor(
                    provider_name=self.settings.name,
                    provider_type=self.settings.type,
                    external_id=external_id,
                    full_name=full_name,
                    clone_url=None,
                    default_branch=None,
                    web_url=None,
                    local_path=str(path),
                )
            )

        return repos


def _find_git_repos(root: Path, recursive: bool) -> list[Path]:
    repos: list[Path] = []

    if (root / ".git").exists():
        return [root]

    if not recursive:
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / ".git").exists():
                repos.append(child)
        if repos:
            return repos
        if any(path.is_file() for path in root.iterdir()):
            return [root]
        return []

    for git_dir in sorted(root.rglob(".git")):
        if git_dir.is_dir():
            repos.append(git_dir.parent)

    deduped = []
    seen: set[Path] = set()
    for repo in repos:
        resolved = repo.resolve()
        if resolved not in seen:
            deduped.append(resolved)
            seen.add(resolved)
    if deduped:
        return deduped

    # Fallback: scan root as a single repository-like target even if it is not a git repo.
    if any(path.is_file() for path in root.iterdir()):
        return [root]
    return []
