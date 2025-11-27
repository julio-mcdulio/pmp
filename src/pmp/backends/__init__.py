"""Backend loading entrypoints."""

from __future__ import annotations

from importlib import metadata
from typing import Dict, Type

from pmp.backends.base import PromptBackend
from pmp.backends.file_backend import FileBackend
from pmp.backends.sqlite_backend import SQLiteBackend
from pmp.errors import ConfigError

BUILTIN_BACKENDS: Dict[str, Type[PromptBackend]] = {
    "file": FileBackend,
    "sqlite": SQLiteBackend,
}


def load_backend(name: str, options: Dict[str, object]) -> PromptBackend:
    """Return an instantiated backend by name."""
    normalized = (name or "file").lower()
    backend_cls = BUILTIN_BACKENDS.get(normalized)
    if not backend_cls:
        backend_cls = _load_from_entrypoint(normalized)
    if not backend_cls:
        raise ConfigError(f'unknown backend "{name}"')
    return backend_cls(**options)


def _load_from_entrypoint(name: str) -> Type[PromptBackend] | None:
    try:
        entries = metadata.entry_points(group="pmp.backends")
    except TypeError:  # pragma: no cover - Python <3.10
        entries = metadata.entry_points().get("pmp.backends", [])
    for entry in entries:
        if entry.name == name:
            backend_cls = entry.load()
            if not issubclass(backend_cls, PromptBackend):
                raise ConfigError(f'backend "{name}" does not implement PromptBackend')
            return backend_cls
    return None

