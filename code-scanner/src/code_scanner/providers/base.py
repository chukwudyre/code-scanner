from __future__ import annotations

from abc import ABC, abstractmethod

from code_scanner.models import RepoDescriptor


class RepoProvider(ABC):
    @abstractmethod
    def list_repos(self) -> list[RepoDescriptor]:
        raise NotImplementedError
