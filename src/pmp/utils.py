"""Utility helpers for PMP CLI."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional
from typing import Any, Dict
from pmp.errors import PMPError
from string import Template


class BraceTemplate(Template):
    """Template class that uses {{variable}} syntax instead of $variable."""

    pattern = r"""
        \{\{              # Match opening double braces
        \s*               # Optional whitespace
        (?P<named>[_a-z][_a-z0-9]*)  # Variable name (same pattern as Template)
        \s*               # Optional whitespace
        \}\}              # Match closing double braces
        """


def read_content(file_path: Optional[str], inline: Optional[str]) -> str:
    """Resolve prompt content from a file, inline text, or stdin."""
    if file_path and inline:
        raise PMPError("provide either --file or --content, not both")

    if file_path:
        path = Path(file_path).expanduser()
        if not path.exists():
            raise PMPError(f'file "{file_path}" does not exist')
        try:
            return path.read_text()
        except PermissionError as exc:
            raise PMPError(f'cannot read "{file_path}": permission denied') from exc

    if inline is not None:
        return inline

    if not sys.stdin.isatty():
        data = sys.stdin.read()
        if data.strip():
            return data

    raise PMPError("prompt content is required (--file, --content, or stdin)")


def parse_tags(tag_args: Optional[List[str]]) -> List[str]:
    """Parse comma-separated tag arguments into a list."""
    if not tag_args:
        return []
    tags: List[str] = []
    for chunk in tag_args:
        for tag in chunk.split(","):
            cleaned = tag.strip()
            if cleaned and cleaned not in tags:
                tags.append(cleaned)
    return tags


def expand_path(value: Optional[str]) -> Optional[str]:
    """Expand ~ and environment variables for filesystem paths."""
    if value is None:
        return None
    return os.path.expandvars(os.path.expanduser(value))


def render_template(template: str, vars: Dict[str, Any]) -> str:
    """Render a template with variables matching {{ variable_name }}"""
    return BraceTemplate(template).substitute(**vars)
