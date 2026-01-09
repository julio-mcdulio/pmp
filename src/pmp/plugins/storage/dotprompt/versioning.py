"""Versioning support for DotPrompt storage backend.

This module provides version tracking that maps integer versions to content hashes,
supporting both PMP's integer versioning system and dotprompt's content-based versioning.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional

from pmp.models import utcnow_iso


class DotpromptVersion:
    """Manages version tracking for dotprompt files.

    Maintains a mapping between integer versions and content hashes, storing
    version metadata in JSON files and versioned content in separate files.
    """

    def __init__(self, name: str, storage_dir: Path):
        """Initialize version manager for a prompt.

        Args:
            name: The prompt name (may include directory structure)
            storage_dir: The base storage directory
        """
        self.name = name
        self.storage_dir = storage_dir

    def get_version_metadata_path(self) -> Path:
        """Get the path to the version metadata file for a prompt."""
        # Store version metadata in a hidden file: .prompt_name.versions.json
        # Handle directory structure in name
        dir_name = os.path.dirname(self.name) if os.path.dirname(self.name) else ""
        base_name = os.path.basename(self.name)
        metadata_file = f".{base_name}.versions.json"
        if dir_name:
            return self.storage_dir / dir_name / metadata_file
        return self.storage_dir / metadata_file

    def load_version_metadata(self) -> Dict[str, object]:
        """Load version metadata for a prompt."""
        metadata_path = self.get_version_metadata_path()
        if not metadata_path.exists():
            return {"versions": []}
        try:
            with open(metadata_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"versions": []}

    def save_version_metadata(self, metadata: Dict[str, object]) -> None:
        """Save version metadata for a prompt."""
        metadata_path = self.get_version_metadata_path()
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    def get_version_by_hash(self, content_hash: str) -> Optional[int]:
        """Find the integer version for a given content hash."""
        version_metadata = self.load_version_metadata()
        versions = version_metadata.get("versions", [])
        for v in versions:
            if v.get("hash") == content_hash:
                return v.get("version")
        return None

    def get_hash_by_version(self, version: int) -> Optional[str]:
        """Find the content hash for a given integer version."""
        version_metadata = self.load_version_metadata()
        versions = version_metadata.get("versions", [])
        for v in versions:
            if v.get("version") == version:
                return v.get("hash")
        return None

    def get_versioned_file_path(self, version: int) -> Path:
        """Get the path to a versioned prompt file."""
        dir_name = os.path.dirname(self.name) if os.path.dirname(self.name) else ""
        base_name = os.path.basename(self.name)
        file_name = f"{base_name}.v{version}.prompt"
        if dir_name:
            return self.storage_dir / dir_name / file_name
        return self.storage_dir / file_name

    def save_versioned_content(self, version: int, content: str) -> None:
        """Save content to a versioned file."""
        versioned_path = self.get_versioned_file_path(version)
        versioned_path.parent.mkdir(parents=True, exist_ok=True)
        with open(versioned_path, "w", encoding="utf-8") as f:
            f.write(content)

    def load_versioned_content(self, version: int) -> Optional[str]:
        """Load content from a versioned file."""
        versioned_path = self.get_versioned_file_path(version)
        if not versioned_path.exists():
            return None
        try:
            with open(versioned_path, encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    def add_version(self, content_hash: str, content: str) -> int:
        """Add a new version for the prompt.

        Returns the latest version if its content hash matches the provided hash.
        Otherwise, creates a new version. Since PMP versions are immutable,
        we never return an older version even if it has the same content hash.

        Args:
            content_hash: The content hash for this version
            content: The full content to save

        Returns:
            The version number (latest if hash matches, or newly created)
        """
        version_metadata = self.load_version_metadata()
        versions = version_metadata.get("versions", [])

        # Get the latest version
        if versions:
            latest_version = max(v.get("version", 0) for v in versions)
            latest_hash = self.get_hash_by_version(latest_version)

            # If the latest version has the same hash, return it (no change)
            if latest_hash == content_hash:
                return latest_version

            # Content is different, create new version
            next_version = latest_version + 1
        else:
            # No existing versions, start with version 1
            next_version = 1

        # Add new version to metadata
        versions.append(
            {"version": next_version, "hash": content_hash, "created_at": utcnow_iso()}
        )
        version_metadata["versions"] = versions
        self.save_version_metadata(version_metadata)

        # Save versioned content
        self.save_versioned_content(next_version, content)

        return next_version

    def get_latest_version(self) -> Optional[int]:
        """Get the latest version number for the prompt."""
        version_metadata = self.load_version_metadata()
        versions = version_metadata.get("versions", [])
        if not versions:
            return None
        return max(v.get("version", 0) for v in versions)

    def get_version_created_at(self, version: int) -> Optional[str]:
        """Get the created_at timestamp for a specific version."""
        version_metadata = self.load_version_metadata()
        versions = version_metadata.get("versions", [])
        for v in versions:
            if v.get("version") == version:
                return v.get("created_at")
        return None
