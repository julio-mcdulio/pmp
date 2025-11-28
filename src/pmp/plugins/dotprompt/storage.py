from importlib.util import find_spec
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Check if dotprompt is enabled in the configuration
if find_spec("pluggy"):
    import yaml

    from pmp.backends.base import PromptBackendStoragePlugin, hookimpl
    from pmp.config import ConfigManager, DEFAULT_FILE_BACKEND_PATH
    from pmp.errors import PromptAlreadyExists, PromptNotFound, VersionNotFound
    from pmp.models import utcnow_iso

    from dotpromptz.parse import extract_frontmatter_and_body, parse_document
    from dotpromptz.stores import DirStoreSync, DirStoreOptions
    from dotpromptz.stores._io import calculate_version
    from dotpromptz.typing import PromptData

    from pmp.plugins.dotprompt.versioning import DotpromptVersion

    class DotPromptBackendStoragePlugin(PromptBackendStoragePlugin):
        """DotPrompt backend storage plugin."""

        def __init__(self) -> None:
            """Initialize the DotPrompt backend storage plugin."""
            self.storage_dir = None
            try:
                config = ConfigManager()
                backend_settings = config.resolve_backend(None, None)
                # For dotprompt backend, use the path option
                path = backend_settings.options.get("path")
                if path:
                    self.storage_dir = Path(path).expanduser()
            except Exception:
                # Fallback to default file backend path
                self.storage_dir = Path(DEFAULT_FILE_BACKEND_PATH).expanduser()

            self.dir_store = DirStoreSync(DirStoreOptions(directory=self.storage_dir))

        @hookimpl
        def add(self, name: str, content: str, metadata: Dict[str, object]) -> None:
            """Add a new prompt as a dotprompt file."""
            version_manager = DotpromptVersion(name, self.storage_dir)

            # Check if prompt already exists
            try:
                self.dir_store.load(name, None)
                raise PromptAlreadyExists(f'prompt "{name}" already exists')
            except FileNotFoundError:
                # Prompt doesn't exist, which is what we want
                pass
            except PromptAlreadyExists:
                # Re-raise if it's already a PromptAlreadyExists
                raise
            except Exception:
                # Other errors are fine, we'll proceed with creating the prompt
                pass

            # Parse the content to see if it already has frontmatter
            frontmatter, body = extract_frontmatter_and_body(content)

            # Prepare metadata for frontmatter
            frontmatter_metadata: Dict[str, object] = {}

            # If content already has frontmatter, parse it and merge
            if frontmatter:
                try:
                    existing_metadata = yaml.safe_load(frontmatter) or {}
                    frontmatter_metadata.update(existing_metadata)
                except Exception:
                    # If parsing fails, start fresh
                    pass

            # Merge the provided metadata into frontmatter
            frontmatter_metadata.update(metadata)

            # Add name to frontmatter if not present
            if "name" not in frontmatter_metadata:
                frontmatter_metadata["name"] = name

            # Create the full file content with frontmatter and body
            if body:
                # Content had frontmatter, use the body
                template_body = body.strip()
            else:
                # Content is just the template body
                template_body = content.strip()

            # Generate YAML frontmatter
            frontmatter_yaml = yaml.dump(
                frontmatter_metadata,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            ).strip()

            # Combine frontmatter and body
            full_content = f"---\n{frontmatter_yaml}\n---\n{template_body}\n"

            content_hash = calculate_version(full_content)

            # Save using DirStoreSync
            prompt_data = PromptData(name=name, source=full_content)
            self.dir_store.save(prompt_data)

            # Create version 1 using version manager
            version_manager.add_version(content_hash, full_content)

        @hookimpl
        def get(self, name: str, version: Optional[int] = None) -> Dict[str, object]:
            """Get a prompt from a dotprompt file."""
            version_manager = DotpromptVersion(name, self.storage_dir)

            # If a specific version is requested, load from versioned file
            prompt_data = None
            if version is not None:
                # Find the hash for this version
                version_hash = version_manager.get_hash_by_version(version)
                if version_hash is None:
                    raise VersionNotFound(
                        f'prompt "{name}" version {version} not found'
                    )

                # Load content from versioned file
                full_content = version_manager.load_versioned_content(version)
                if full_content is None:
                    raise VersionNotFound(
                        f'prompt "{name}" version {version} not found'
                    )

                prompt_version = version
            else:
                # Load current version
                try:
                    prompt_data = self.dir_store.load(name, None)
                except FileNotFoundError:
                    raise PromptNotFound(f'prompt "{name}" not found')
                except Exception as e:
                    raise PromptNotFound(f'prompt "{name}" not found: {e}')

                # The prompt_data.source contains the full file content (frontmatter + body)
                full_content = prompt_data.source

                # Get the latest version number (not by hash, since versions are immutable)
                prompt_version = version_manager.get_latest_version()
                if prompt_version is None:
                    # No versions in metadata - this shouldn't happen, but default to 1
                    prompt_version = 1

            # Parse the document to extract metadata
            frontmatter, body = extract_frontmatter_and_body(full_content)

            # Extract metadata from frontmatter
            metadata_dict: Dict[str, Any] = {}
            if frontmatter:
                try:
                    existing_metadata = yaml.safe_load(frontmatter) or {}
                    metadata_dict.update(existing_metadata)
                except Exception:
                    # If parsing fails, start fresh
                    pass

            # Get created_at from version metadata or file modification time
            created_at = utcnow_iso()
            try:
                # Try to get created_at from version metadata
                created_at_from_meta = version_manager.get_version_created_at(
                    prompt_version
                )
                if created_at_from_meta:
                    created_at = created_at_from_meta
                else:
                    # Fallback to file modification time
                    if version is not None:
                        # Use versioned file
                        versioned_path = version_manager.get_versioned_file_path(
                            version
                        )
                        if versioned_path.exists():
                            mtime = os.path.getmtime(versioned_path)
                            from datetime import datetime, timezone

                            created_at = datetime.fromtimestamp(
                                mtime, tz=timezone.utc
                            ).isoformat(timespec="seconds")
                    else:
                        # Use current prompt file (prompt_data should already be loaded)
                        if prompt_data is not None:
                            try:
                                dir_name = os.path.dirname(name)
                                base_name = os.path.basename(name)
                                variant = prompt_data.variant
                                file_name = (
                                    f"{base_name}.{variant}.prompt"
                                    if variant
                                    else f"{base_name}.prompt"
                                )
                                file_path = (
                                    self.storage_dir / dir_name / file_name
                                    if dir_name
                                    else self.storage_dir / file_name
                                )
                                if file_path.exists():
                                    mtime = os.path.getmtime(file_path)
                                    from datetime import datetime, timezone

                                    created_at = datetime.fromtimestamp(
                                        mtime, tz=timezone.utc
                                    ).isoformat(timespec="seconds")
                            except Exception:
                                pass
            except Exception:
                pass

            return {
                "name": name,
                "version": prompt_version,
                "content": full_content,
                "metadata": metadata_dict,
                "created_at": created_at,
            }

        @hookimpl
        def update(self, name: str, content: str, metadata: Dict[str, object]) -> None:
            """Update a prompt - creates a new version if content hash changes."""

            # Check if prompt exists
            try:
                self.dir_store.load(name, None)
            except FileNotFoundError:
                raise PromptNotFound(f'prompt "{name}" does not exist')

            # Parse the content to see if it already has frontmatter
            frontmatter, body = extract_frontmatter_and_body(content)

            # Prepare metadata for frontmatter
            frontmatter_metadata: Dict[str, object] = {}

            # Load existing prompt to merge with existing frontmatter
            try:
                existing_prompt = self.dir_store.load(name, None)
                existing_parsed = parse_document(existing_prompt.source)
                if existing_parsed.raw:
                    frontmatter_metadata.update(existing_parsed.raw)
            except Exception:
                pass

            # If content already has frontmatter, parse it and merge
            if frontmatter:
                try:
                    content_metadata = yaml.safe_load(frontmatter) or {}
                    frontmatter_metadata.update(content_metadata)
                except Exception:
                    pass

            # Merge the provided metadata into frontmatter
            frontmatter_metadata.update(metadata)

            # Add name to frontmatter if not present
            if "name" not in frontmatter_metadata:
                frontmatter_metadata["name"] = name

            # Create the full file content with frontmatter and body
            if body:
                template_body = body.strip()
            else:
                template_body = content.strip()

            # Generate YAML frontmatter
            frontmatter_yaml = yaml.dump(
                frontmatter_metadata,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            ).strip()

            # Combine frontmatter and body
            full_content = f"---\n{frontmatter_yaml}\n---\n{template_body}\n"

            # Calculate content hash
            content_hash = calculate_version(full_content)

            # Check if this hash already exists and add version if needed
            version_manager = DotpromptVersion(name, self.storage_dir)
            version_manager.add_version(content_hash, full_content)

            # Update the current prompt file
            prompt_data = PromptData(name=name, source=full_content)
            self.dir_store.save(prompt_data)

        @hookimpl
        def delete(self, name: str, version: Optional[int] = None) -> None:
            """Delete a prompt."""
            pass

        @hookimpl
        def list(
            self, filters: Optional[Dict[str, object]] = None
        ) -> List[Dict[str, object]]:
            """List prompts."""
            pass
