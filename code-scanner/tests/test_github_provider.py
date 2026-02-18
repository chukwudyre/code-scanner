from code_scanner.http import HttpResponse
from code_scanner.models import ProviderSettings
from code_scanner.providers.github import GitHubProvider


def test_github_provider_org_scope(monkeypatch):
    calls: list[str] = []

    def fake_get_json(url, headers=None, timeout=30):
        calls.append(url)
        assert "/orgs/psf/repos" in url
        data = [
            {
                "id": 1,
                "full_name": "psf/requests",
                "clone_url": "https://github.com/psf/requests.git",
                "default_branch": "main",
                "html_url": "https://github.com/psf/requests",
            }
        ]
        return HttpResponse(status=200, headers={}, data=data)

    monkeypatch.setattr("code_scanner.providers.github.get_json", fake_get_json)

    provider = GitHubProvider(
        ProviderSettings(type="github", name="gh", org="psf")
    )
    repos = provider.list_repos()

    assert len(repos) == 1
    assert repos[0].full_name == "psf/requests"
    assert any("/orgs/psf/repos" in url for url in calls)


def test_github_provider_user_scope_fallback(monkeypatch):
    calls: list[str] = []

    def fake_get_json(url, headers=None, timeout=30):
        calls.append(url)
        if "/orgs/chukwudyre/repos" in url:
            raise RuntimeError("HTTP 404 for https://api.github.com/orgs/chukwudyre/repos")
        if "/users/chukwudyre/repos" in url:
            data = [
                {
                    "id": 2,
                    "full_name": "chukwudyre/Penn-CIS545-Project",
                    "clone_url": "https://github.com/chukwudyre/Penn-CIS545-Project.git",
                    "default_branch": "main",
                    "html_url": "https://github.com/chukwudyre/Penn-CIS545-Project",
                }
            ]
            return HttpResponse(status=200, headers={}, data=data)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("code_scanner.providers.github.get_json", fake_get_json)

    provider = GitHubProvider(
        ProviderSettings(type="github", name="gh", org="chukwudyre")
    )
    repos = provider.list_repos()

    assert len(repos) == 1
    assert repos[0].full_name == "chukwudyre/Penn-CIS545-Project"
    assert any("/orgs/chukwudyre/repos" in url for url in calls)
    assert any("/users/chukwudyre/repos" in url for url in calls)
