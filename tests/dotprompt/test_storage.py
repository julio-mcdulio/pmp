"""Tests for DotPrompt backend storage plugin add and get methods."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pytest

from pmp.errors import PromptAlreadyExists, PromptNotFound, VersionNotFound
from pmp.plugins.storage.dotprompt.storage import DotPromptBackendStoragePlugin


@pytest.mark.dotprompt
def test_storage_add_and_get_basic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test basic add and get functionality."""

    # Set up config to use tmp_path
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    # Create plugin instance
    plugin = DotPromptBackendStoragePlugin()

    # Test add with simple content
    name = "test_prompt"
    content = "Hello, {{name}}!"
    metadata: Dict[str, object] = {"tags": ["greeting"], "model": "gpt-4"}

    plugin.add(name, content, metadata)

    # Verify file was created
    prompt_file = storage_dir / f"{name}.prompt"
    assert prompt_file.exists(), "Prompt file should be created"

    # Test get
    result = plugin.get(name)

    assert result["name"] == name
    assert result["version"] == 1
    assert "Hello, {{name}}!" in result["content"]
    assert "tags" in result["metadata"]
    assert result["metadata"]["tags"] == ["greeting"]
    assert result["metadata"]["model"] == "gpt-4"
    assert "created_at" in result


@pytest.mark.dotprompt
def test_storage_add_with_frontmatter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test add with content that already has frontmatter."""

    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    # Add with existing frontmatter
    name = "prompt_with_frontmatter"
    content = """---
model: gpt-3.5
description: A test prompt
---
Hello, {{user}}!"""
    metadata: Dict[str, object] = {"tags": ["test"]}

    plugin.add(name, content, metadata)

    # Get and verify
    result = plugin.get(name)

    # Should merge metadata
    assert result["metadata"]["model"] == "gpt-3.5"
    assert result["metadata"]["description"] == "A test prompt"
    assert result["metadata"]["tags"] == ["test"]
    assert "Hello, {{user}}!" in result["content"]


@pytest.mark.dotprompt
def test_storage_add_duplicate_raises_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that adding a duplicate prompt raises PromptAlreadyExists."""

    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    name = "duplicate_test"
    content = "Test content"
    metadata: Dict[str, object] = {}

    # Add first time - should succeed
    plugin.add(name, content, metadata)

    # Add second time - should raise error
    with pytest.raises(
        PromptAlreadyExists, match='prompt "duplicate_test" already exists'
    ):
        plugin.add(name, content, metadata)


@pytest.mark.dotprompt
def test_storage_get_nonexistent_raises_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that getting a nonexistent prompt raises PromptNotFound."""

    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    # Try to get nonexistent prompt
    with pytest.raises(PromptNotFound, match='prompt "nonexistent" not found'):
        plugin.get("nonexistent")


@pytest.mark.dotprompt
def test_storage_add_get_with_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test add and get with various metadata fields."""

    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    name = "metadata_test"
    content = "Template with {{variable}}"
    metadata: Dict[str, object] = {
        "tags": ["test", "example"],
        "model": "gpt-4",
        "temperature": 0.7,
        "custom_field": "custom_value",
    }

    plugin.add(name, content, metadata)

    result = plugin.get(name)

    # Verify all metadata is preserved
    assert result["metadata"]["tags"] == ["test", "example"]
    assert result["metadata"]["model"] == "gpt-4"
    assert result["metadata"]["temperature"] == 0.7
    assert result["metadata"]["custom_field"] == "custom_value"
    assert result["content"] is not None
    assert "Template with {{variable}}" in result["content"]


@pytest.mark.dotprompt
def test_storage_add_get_with_directory_structure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test add and get with prompts in subdirectories."""

    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    # Test with directory structure
    name = "subdir/prompt"
    content = "Nested prompt content"
    metadata: Dict[str, object] = {"category": "nested"}

    plugin.add(name, content, metadata)

    # Verify file was created in subdirectory
    prompt_file = storage_dir / "subdir" / "prompt.prompt"
    assert prompt_file.exists(), "Prompt file should be created in subdirectory"

    # Test get
    result = plugin.get(name)
    assert result["name"] == name
    assert "Nested prompt content" in result["content"]
    assert result["metadata"]["category"] == "nested"


@pytest.mark.dotprompt
def test_storage_get_returns_full_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that get returns the full file content including frontmatter."""

    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    name = "full_content_test"
    content = "Simple template"
    metadata: Dict[str, object] = {"model": "gpt-4"}

    plugin.add(name, content, metadata)

    result = plugin.get(name)

    # Content should include frontmatter and body
    assert "---" in result["content"], "Content should include frontmatter delimiters"
    assert (
        "model:" in result["content"]
    ), "Content should include metadata in frontmatter"
    assert (
        "Simple template" in result["content"]
    ), "Content should include template body"


@pytest.mark.dotprompt
def test_storage_add_merges_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that add properly merges existing frontmatter with provided metadata."""

    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    name = "merge_test"
    # Content with existing frontmatter
    content = """---
model: gpt-3.5
temperature: 0.5
---
Template body"""
    # Additional metadata to merge
    metadata: Dict[str, object] = {"temperature": 0.8, "tags": ["new"]}

    plugin.add(name, content, metadata)

    result = plugin.get(name)

    # Provided metadata should override existing
    assert result["metadata"]["temperature"] == 0.8
    # Existing metadata should be preserved if not overridden
    assert result["metadata"]["model"] == "gpt-3.5"
    # New metadata should be added
    assert result["metadata"]["tags"] == ["new"]
    # Template body should be preserved
    assert "Template body" in result["content"]


@pytest.mark.dotprompt
def test_storage_version_immutability_edge_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that versions are immutable - re-adding old content creates a new version.

    This tests the edge case where:
    - Version 1 has content A (hash A)
    - Version 2 has content B (hash B)
    - Adding content A again should create version 3, not return version 1
    """
    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    name = "immutable_test"
    content_v1 = "Version 1 content"
    metadata: Dict[str, object] = {}

    # Add version 1
    plugin.add(name, content_v1, metadata)
    result_v1 = plugin.get(name)
    assert result_v1["version"] == 1
    hash_v1 = result_v1["content"]

    # Update to version 2 with different content
    content_v2 = "Version 2 content"
    plugin.edit(name, content_v2, metadata)
    result_v2 = plugin.get(name)
    assert result_v2["version"] == 2
    assert result_v2["version"] != result_v1["version"]

    # Now add the same content as version 1 again
    # This should create version 3, NOT return version 1
    plugin.edit(name, content_v1, metadata)
    result_v3 = plugin.get(name)
    assert (
        result_v3["version"] == 3
    ), "Should create new version 3, not return version 1"
    assert result_v3["version"] != result_v1["version"]
    assert result_v3["version"] != result_v2["version"]
    # Content should match v1, but version number should be 3
    assert "Version 1 content" in result_v3["content"]


@pytest.mark.dotprompt
def test_storage_update_creates_new_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that update creates a new version when content changes."""
    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    name = "version_test"
    content_v1 = "Initial content"
    metadata: Dict[str, object] = {"model": "gpt-4"}

    # Add version 1
    plugin.add(name, content_v1, metadata)
    result_v1 = plugin.get(name)
    assert result_v1["version"] == 1
    assert "Initial content" in result_v1["content"]

    # Update to version 2
    content_v2 = "Updated content"
    plugin.edit(name, content_v2, metadata)
    result_v2 = plugin.get(name)
    assert result_v2["version"] == 2
    assert "Updated content" in result_v2["content"]
    assert result_v2["version"] > result_v1["version"]

    # Update to version 3
    content_v3 = "Third version content"
    plugin.edit(name, content_v3, metadata)
    result_v3 = plugin.get(name)
    assert result_v3["version"] == 3
    assert "Third version content" in result_v3["content"]


@pytest.mark.dotprompt
def test_storage_update_same_content_no_new_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that update doesn't create a new version when content is unchanged."""
    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    name = "no_change_test"
    content = "Same content"
    metadata: Dict[str, object] = {"model": "gpt-4"}

    # Add version 1
    plugin.add(name, content, metadata)
    result_v1 = plugin.get(name)
    version_1 = result_v1["version"]
    assert version_1 == 1

    # Update with same content - should not create new version
    plugin.edit(name, content, metadata)
    result_v2 = plugin.get(name)
    assert (
        result_v2["version"] == version_1
    ), "Should not create new version for same content"
    assert "Same content" in result_v2["content"]


@pytest.mark.dotprompt
def test_storage_get_specific_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that getting a specific version returns the correct content."""
    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    name = "version_specific_test"
    content_v1 = "First version"
    metadata: Dict[str, object] = {}

    # Add version 1
    plugin.add(name, content_v1, metadata)

    # Update to version 2
    content_v2 = "Second version"
    plugin.edit(name, content_v2, metadata)

    # Update to version 3
    content_v3 = "Third version"
    plugin.edit(name, content_v3, metadata)

    # Get specific versions
    result_v1 = plugin.get(name, version=1)
    assert result_v1["version"] == 1
    assert "First version" in result_v1["content"]

    result_v2 = plugin.get(name, version=2)
    assert result_v2["version"] == 2
    assert "Second version" in result_v2["content"]

    result_v3 = plugin.get(name, version=3)
    assert result_v3["version"] == 3
    assert "Third version" in result_v3["content"]

    # Get latest (no version specified)
    result_latest = plugin.get(name)
    assert result_latest["version"] == 3
    assert "Third version" in result_latest["content"]


@pytest.mark.dotprompt
def test_storage_get_nonexistent_version_raises_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that getting a nonexistent version raises VersionNotFound."""
    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    name = "version_error_test"
    content = "Test content"
    metadata: Dict[str, object] = {}

    # Add version 1
    plugin.add(name, content, metadata)

    # Try to get nonexistent version
    with pytest.raises(
        VersionNotFound, match='prompt "version_error_test" version 999 not found'
    ):
        plugin.get(name, version=999)


@pytest.mark.dotprompt
def test_storage_version_metadata_persistence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that version metadata (created_at) is properly stored and retrieved."""
    # Set up config
    config_path = tmp_path / "config.toml"
    storage_dir = tmp_path / "prompts"
    config_path.write_text(
        f"""
backend = "file"
[backends.file]
path = "{storage_dir}"
"""
    )
    monkeypatch.setenv("PMP_CONFIG_FILE", str(config_path))

    plugin = DotPromptBackendStoragePlugin()

    name = "metadata_persistence_test"
    content_v1 = "Version 1"
    metadata: Dict[str, object] = {}

    # Add version 1
    plugin.add(name, content_v1, metadata)
    result_v1 = plugin.get(name, version=1)
    created_at_v1 = result_v1["created_at"]
    assert created_at_v1 is not None
    assert isinstance(created_at_v1, str)

    # Update to version 2
    content_v2 = "Version 2"
    plugin.edit(name, content_v2, metadata)
    result_v2 = plugin.get(name, version=2)
    created_at_v2 = result_v2["created_at"]
    assert created_at_v2 is not None
    assert isinstance(created_at_v2, str)

    # Version 1's created_at should still be accessible
    result_v1_again = plugin.get(name, version=1)
    assert result_v1_again["created_at"] == created_at_v1
