"""Filesystem backend implementation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from pmp.backends.base import PromptBackend
from pmp.errors import PMPError, PromptAlreadyExists, PromptNotFound, VersionNotFound
from pmp.models import PromptSummary, PromptVersion, utcnow_iso

SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


class FileBackend(PromptBackend):
    """Stores prompts as JSON documents on disk."""

    def __init__(self, path: str):
        self.root = Path(path).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    def add(self, name: str, content: str, metadata: Dict[str, object]) -> None:
        """Create a new prompt with version 1."""
        self._validate_name(name)
        prompt_file = self._prompt_file(name)
        if prompt_file.is_file():
            raise PromptAlreadyExists(f'prompt "{name}" already exists')
        version = PromptVersion(name=name, version=1, content=content, metadata=metadata, created_at=utcnow_iso())
        self._write(prompt_file, {"name": name, "versions": [version.to_dict()]})

    def get(self, name: str, version: Optional[int] = None) -> Dict[str, object]:
        """Return the requested version (latest by default)."""
        data = self._load(name)
        versions = data.get("versions", [])
        if not versions:
            raise PromptNotFound(f'prompt "{name}" does not have any versions')
        if version is None:
            return versions[-1]
        for entry in versions:
            if entry["version"] == version:
                return entry
        raise VersionNotFound(f'prompt "{name}" version {version} not found')

    def update(self, name: str, content: str, metadata: Dict[str, object]) -> None:
        """Append a new version for an existing prompt."""
        prompt_file = self._prompt_file(name)
        if not prompt_file.is_file():
            raise PromptNotFound(f'prompt "{name}" does not exist')
        data = self._read(prompt_file)
        versions = data.setdefault("versions", [])
        next_version = versions[-1]["version"] + 1 if versions else 1
        versions.append(
            PromptVersion(name=name, version=next_version, content=content, metadata=metadata, created_at=utcnow_iso()).to_dict()
        )
        self._write(prompt_file, data)

    def delete(self, name: str, version: Optional[int] = None) -> None:
        """Delete a specific version or the latest version."""
        prompt_file = self._prompt_file(name)
        if not prompt_file.is_file():
            raise PromptNotFound(f'prompt "{name}" does not exist')
        data = self._read(prompt_file)
        versions = data.get("versions", [])
        if not versions:
            if version is None:
                try:
                    prompt_file.unlink()
                except FileNotFoundError:
                    pass
                return
            raise VersionNotFound(f'prompt "{name}" version {version} not found')
        target_version = version or versions[-1]["version"]
        remaining = [entry for entry in versions if entry["version"] != target_version]
        if len(remaining) == len(versions):
            raise VersionNotFound(f'prompt "{name}" version {target_version} not found')
        if remaining:
            data["versions"] = remaining
            self._write(prompt_file, data)
        else:
            prompt_file.unlink()

    def list(self, filters: Optional[Dict[str, object]] = None) -> List[Dict[str, object]]:
        """Return summaries of prompts that match the supplied filters."""
        filters = filters or {}
        results: List[Dict[str, object]] = []
        for file in sorted(self.root.glob("*.json")):
            if not file.is_file():
                continue
            payload = self._read(file)
            versions = payload.get("versions", [])
            if not versions:
                continue
            latest = versions[-1]
            metadata = latest.get("metadata", {})
            if not _matches_filters(metadata, filters):
                continue
            summary = PromptSummary(
                name=payload["name"],
                latest_version=latest["version"],
                updated_at=latest.get("created_at", ""),
                metadata=metadata,
            )
            results.append(summary.to_dict())
        return results

    def _prompt_file(self, name: str) -> Path:
        """Return the on-disk path for a prompt."""
        return self.root / f"{name}.json"

    def _load(self, name: str) -> Dict[str, object]:
        """Load prompt metadata from disk."""
        prompt_file = self._prompt_file(name)
        if not prompt_file.is_file():
            raise PromptNotFound(f'prompt "{name}" does not exist')
        return self._read(prompt_file)

    def _read(self, file_path: Path) -> Dict[str, object]:
        """Deserialize JSON payloads."""
        return json.loads(file_path.read_text(encoding="utf-8"))

    def _write(self, file_path: Path, payload: Dict[str, object]) -> None:
        """Persist prompt data."""
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _validate_name(name: str) -> None:
        if not SAFE_NAME.match(name):
            raise PMPError('prompt names may only include alphanumerics, ".", "_", or "-"')


def _matches_filters(metadata: Dict[str, object], filters: Dict[str, object]) -> bool:
    tag = filters.get("tag")
    if tag:
        tags = metadata.get("tags") or []
        if tag not in tags:
            return False
    model = filters.get("model")
    if model and metadata.get("model") != model:
        return False
    return True

