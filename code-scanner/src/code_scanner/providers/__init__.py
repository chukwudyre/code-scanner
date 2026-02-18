from __future__ import annotations

from code_scanner.models import ProviderSettings
from code_scanner.providers.base import RepoProvider
from code_scanner.providers.bitbucket_cloud import BitbucketCloudProvider
from code_scanner.providers.bitbucket_server import BitbucketServerProvider
from code_scanner.providers.github import GitHubProvider
from code_scanner.providers.local import LocalProvider


def build_provider(settings: ProviderSettings) -> RepoProvider:
    provider_type = settings.type.strip().lower()
    if provider_type == "github":
        return GitHubProvider(settings)
    if provider_type == "bitbucket_cloud":
        return BitbucketCloudProvider(settings)
    if provider_type == "bitbucket_server":
        return BitbucketServerProvider(settings)
    if provider_type == "local":
        return LocalProvider(settings)
    raise ValueError(f"Unsupported provider type: {settings.type}")
