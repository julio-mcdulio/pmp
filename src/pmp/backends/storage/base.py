"""Abstract backend definition."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from importlib.util import find_spec


class PromptStorageBackend(ABC):
    """Interface all backends must implement."""

    @abstractmethod
    def add(self, name: str, content: str, metadata: Dict[str, object]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, name: str, version: Optional[int] = None) -> Dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def update(self, name: str, content: str, metadata: Dict[str, object]) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, name: str, version: Optional[int] = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def list(
        self, filters: Optional[Dict[str, object]] = None
    ) -> List[Dict[str, object]]:
        raise NotImplementedError


if find_spec("pluggy"):
    import pluggy

    hookspec = pluggy.HookspecMarker("pmp.backends")
    hookimpl = pluggy.HookimplMarker("pmp.backends")

    class PromptStorageBackendPlugin(ABC):
        """Plugin interface for prompt storage backends."""

        @hookspec
        def add(self, name: str, content: str, metadata: Dict[str, object]) -> None:
            """Add a new prompt."""

        @hookspec
        def get(self, name: str, version: Optional[int] = None) -> Dict[str, object]:
            """Get a prompt."""

        @hookspec
        def update(self, name: str, content: str, metadata: Dict[str, object]) -> None:
            """Update a prompt."""

        @hookspec
        def delete(self, name: str, version: Optional[int] = None) -> None:
            """Delete a prompt."""

        @hookspec
        def list(
            self, filters: Optional[Dict[str, object]] = None
        ) -> List[Dict[str, object]]:
            """List prompts."""
