from __future__ import annotations

import os
from urllib.parse import urlencode

from code_scanner.http import get_json
from code_scanner.models import ProviderSettings, RepoDescriptor
from code_scanner.providers.base import RepoProvider


class BitbucketServerProvider(RepoProvider):
    def __init__(self, settings: ProviderSettings):
        self.settings = settings
        if not settings.project_key:
            raise ValueError("Bitbucket server provider requires 'project_key'")
        if not settings.base_url:
            raise ValueError("Bitbucket server provider requires 'base_url'")
        self.base_url = settings.base_url.rstrip("/")

    def list_repos(self) -> list[RepoDescriptor]:
        token = _token_from_env(self.settings.token_env)
        headers = {
            "User-Agent": "code-scanner/0.1",
            "Accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        repos: list[RepoDescriptor] = []
        start = 0
        limit = 100

        while True:
            query = urlencode({"start": start, "limit": limit})
            url = (
                f"{self.base_url}/rest/api/1.0/projects/"
                f"{self.settings.project_key}/repos?{query}"
            )
            response = get_json(url, headers=headers)
            data = response.data
            if not isinstance(data, dict):
                raise RuntimeError("Bitbucket server API returned invalid payload")

            values = data.get("values", [])
            for item in values:
                repo_id = str(item.get("id") or "").strip()
                slug = str(item.get("slug") or "").strip()
                project = item.get("project", {}) if isinstance(item, dict) else {}
                project_key = str(project.get("key") or self.settings.project_key)
                full_name = f"{project_key}/{slug}" if slug else ""
                if not repo_id or not full_name:
                    continue

                clone_url = None
                links = item.get("links", {}) if isinstance(item, dict) else {}
                clone_links = links.get("clone", []) if isinstance(links, dict) else []
                for candidate in clone_links:
                    href = str(candidate.get("href") or "")
                    name = str(candidate.get("name") or "")
                    if href.startswith("http") and (name.lower() in {"http", "https"}):
                        clone_url = href
                        break

                web_url = None
                self_links = links.get("self", []) if isinstance(links, dict) else []
                if isinstance(self_links, list) and self_links:
                    web_url = str(self_links[0].get("href") or "") or None

                default_branch = _read_default_branch(
                    base_url=self.base_url,
                    project_key=project_key,
                    slug=slug,
                    headers=headers,
                )

                repos.append(
                    RepoDescriptor(
                        provider_name=self.settings.name,
                        provider_type=self.settings.type,
                        external_id=repo_id,
                        full_name=full_name,
                        clone_url=clone_url,
                        default_branch=default_branch or "main",
                        web_url=web_url,
                        auth_token=token,
                        clone_auth_user="x-token-auth",
                    )
                )

            if bool(data.get("isLastPage", True)):
                break
            start = int(data.get("nextPageStart", start + limit))

        return repos


def _read_default_branch(
    *,
    base_url: str,
    project_key: str,
    slug: str,
    headers: dict[str, str],
) -> str | None:
    if not slug:
        return None

    url = (
        f"{base_url}/rest/api/1.0/projects/{project_key}/repos/{slug}/branches/default"
    )
    try:
        response = get_json(url, headers=headers)
    except RuntimeError:
        return None

    data = response.data
    if not isinstance(data, dict):
        return None
    return str(data.get("displayId") or "") or None


def _token_from_env(token_env: str | None) -> str | None:
    if not token_env:
        return None
    token = os.getenv(token_env)
    if token:
        return token.strip()
    return None
