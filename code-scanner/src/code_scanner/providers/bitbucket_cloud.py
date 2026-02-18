from __future__ import annotations

import os
from urllib.parse import urlencode

from code_scanner.http import get_json
from code_scanner.models import ProviderSettings, RepoDescriptor
from code_scanner.providers.base import RepoProvider


class BitbucketCloudProvider(RepoProvider):
    def __init__(self, settings: ProviderSettings):
        self.settings = settings
        if not settings.workspace:
            raise ValueError("Bitbucket cloud provider requires 'workspace'")
        self.base_url = (settings.base_url or "https://api.bitbucket.org/2.0").rstrip("/")

    def list_repos(self) -> list[RepoDescriptor]:
        token = _token_from_env(self.settings.token_env)
        headers = {
            "User-Agent": "code-scanner/0.1",
            "Accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        repos: list[RepoDescriptor] = []
        url = f"{self.base_url}/repositories/{self.settings.workspace}?{urlencode({'pagelen': 100})}"

        while url:
            response = get_json(url, headers=headers)
            data = response.data
            values = data.get("values", []) if isinstance(data, dict) else []

            for item in values:
                uuid = str(item.get("uuid") or "").strip()
                full_name = str(item.get("full_name") or "").strip()
                if not uuid or not full_name:
                    continue

                clone_url = None
                links = item.get("links", {})
                for candidate in links.get("clone", []) if isinstance(links, dict) else []:
                    if candidate.get("name") == "https":
                        clone_url = str(candidate.get("href"))
                        break

                web_url = None
                html_link = links.get("html") if isinstance(links, dict) else None
                if isinstance(html_link, dict):
                    web_url = str(html_link.get("href") or "") or None

                mainbranch = item.get("mainbranch")
                default_branch = None
                if isinstance(mainbranch, dict):
                    default_branch = str(mainbranch.get("name") or "") or None

                repos.append(
                    RepoDescriptor(
                        provider_name=self.settings.name,
                        provider_type=self.settings.type,
                        external_id=uuid,
                        full_name=full_name,
                        clone_url=clone_url,
                        default_branch=default_branch or "main",
                        web_url=web_url,
                        auth_token=token,
                        clone_auth_user="x-token-auth",
                    )
                )

            if not isinstance(data, dict):
                break
            next_url = data.get("next")
            url = str(next_url) if next_url else ""

        return repos


def _token_from_env(token_env: str | None) -> str | None:
    if not token_env:
        return None
    token = os.getenv(token_env)
    if token:
        return token.strip()
    return None
