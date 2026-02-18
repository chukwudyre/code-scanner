from __future__ import annotations

import os
from urllib.parse import urlencode

from code_scanner.http import get_json
from code_scanner.models import ProviderSettings, RepoDescriptor
from code_scanner.providers.base import RepoProvider


class GitHubProvider(RepoProvider):
    def __init__(self, settings: ProviderSettings):
        self.settings = settings
        if not settings.org:
            raise ValueError("GitHub provider requires 'org'")
        self.base_url = (settings.base_url or "https://api.github.com").rstrip("/")

    def list_repos(self) -> list[RepoDescriptor]:
        token = _token_from_env(self.settings.token_env)
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "code-scanner/0.1",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        repos: list[RepoDescriptor] = []
        per_page = 100
        owner = str(self.settings.org)
        owner_scope, page_data = _resolve_owner_scope(
            base_url=self.base_url,
            owner=owner,
            headers=headers,
            per_page=per_page,
        )

        page = 1
        while True:
            for item in page_data:
                descriptor = _to_repo_descriptor(
                    item=item,
                    provider_name=self.settings.name,
                    provider_type=self.settings.type,
                    auth_token=token,
                )
                if descriptor:
                    repos.append(descriptor)

            if len(page_data) < per_page:
                break

            page += 1
            query = urlencode({"per_page": per_page, "page": page, "type": "all"})
            url = f"{self.base_url}/{owner_scope}/{owner}/repos?{query}"
            response = get_json(url, headers=headers)
            page_data = response.data
            if not isinstance(page_data, list):
                raise RuntimeError("GitHub API returned invalid repos payload")

        return repos


def _resolve_owner_scope(
    *,
    base_url: str,
    owner: str,
    headers: dict[str, str],
    per_page: int,
) -> tuple[str, list[dict]]:
    query = urlencode({"per_page": per_page, "page": 1, "type": "all"})
    org_url = f"{base_url}/orgs/{owner}/repos?{query}"
    try:
        response = get_json(org_url, headers=headers)
    except RuntimeError as exc:
        # Personal user accounts return 404 on /orgs/{owner}/repos.
        if "HTTP 404" not in str(exc):
            raise
        user_url = f"{base_url}/users/{owner}/repos?{query}"
        response = get_json(user_url, headers=headers)
        if not isinstance(response.data, list):
            raise RuntimeError("GitHub API returned invalid repos payload")
        return "users", response.data

    if not isinstance(response.data, list):
        raise RuntimeError("GitHub API returned invalid repos payload")
    return "orgs", response.data


def _to_repo_descriptor(
    *,
    item: dict,
    provider_name: str,
    provider_type: str,
    auth_token: str | None,
) -> RepoDescriptor | None:
    repo_id = str(item.get("id") or "").strip()
    full_name = str(item.get("full_name") or "").strip()
    if not repo_id or not full_name:
        return None

    return RepoDescriptor(
        provider_name=provider_name,
        provider_type=provider_type,
        external_id=repo_id,
        full_name=full_name,
        clone_url=str(item.get("clone_url") or "") or None,
        default_branch=str(item.get("default_branch") or "main"),
        web_url=str(item.get("html_url") or "") or None,
        auth_token=auth_token,
        clone_auth_user="x-access-token",
    )


def _token_from_env(token_env: str | None) -> str | None:
    if not token_env:
        return None
    token = os.getenv(token_env)
    if token:
        return token.strip()
    return None
