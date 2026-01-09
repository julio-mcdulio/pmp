"""Application service coordinating CLI and backend."""

from __future__ import annotations

from typing import Dict, List, Optional

from pmp.backends.storage.base import PromptStorageBackend
from pmp.errors import PromptNotFound, VersionNotFound


class PromptService:
    def __init__(self, storage_backend: PromptStorageBackend):
        self.storage_backend = storage_backend

    def add_prompt(self, name: str, content: str, tags: List[str], model: Optional[str]) -> Dict[str, object]:
        metadata = _build_metadata(tags, model)
        self.storage_backend.add(name, content, metadata)
        return self.storage_backend.get(name)

    def update_prompt(self, name: str, content: str, tags: Optional[List[str]], model: Optional[str]) -> Dict[str, object]:
        latest = self.storage_backend.get(name)
        metadata = latest.get("metadata", {})
        merged = _build_metadata(tags if tags is not None else metadata.get("tags"), model or metadata.get("model"))
        self.storage_backend.edit(name, content, merged)
        return self.storage_backend.get(name)

    def get_prompt(self, name: str, version: Optional[int]=None) -> Dict[str, object]:
        return self.storage_backend.get(name, version)

    def delete_prompt(self, name: str, version: Optional[int], purge_all: bool) -> Dict[str, object]:
        if purge_all and version is None:
            deleted_versions: List[int] = []
            while True:
                try:
                    latest = self.storage_backend.get(name)
                except PromptNotFound:
                    break
                try:
                    self.storage_backend.delete(name, latest["version"])
                except VersionNotFound:
                    continue
                deleted_versions.append(latest["version"])
            if not deleted_versions:
                raise PromptNotFound(f'prompt "{name}" does not exist')
            return {"name": name, "deleted_versions": deleted_versions}
        target = self.storage_backend.get(name, version)
        try:
            self.storage_backend.delete(name, version)
        except VersionNotFound as exc:
            missing_version = version or target["version"]
            raise PromptNotFound(f'prompt "{name}" version {missing_version} does not exist') from exc
        return target

    def list_prompts(self, tag: Optional[str], model: Optional[str]) -> List[Dict[str, object]]:
        filters = {}
        if tag:
            filters["tag"] = tag
        if model:
            filters["model"] = model
        return self.storage_backend.list(filters)


def _build_metadata(tags: Optional[List[str]], model: Optional[str]) -> Dict[str, object]:
    metadata: Dict[str, object] = {}
    if tags:
        metadata["tags"] = tags
    if model:
        metadata["model"] = model
    return metadata

