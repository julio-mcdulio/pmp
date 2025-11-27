"""Data models shared across the PMP codebase."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utcnow_iso() -> str:
    """Return an ISO 8601 timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class PromptVersion:
    """Represents a single prompt version."""

    name: str
    version: int
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the version to a dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class PromptSummary:
    """Summary info returned by backends when listing prompts."""

    name: str
    latest_version: int
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "latest_version": self.latest_version,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

