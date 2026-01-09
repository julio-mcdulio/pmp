from __future__ import annotations
from enum import Enum
from importlib import metadata
from typing import Type, Dict

from pmp.backends.storage import BUILTIN_STORAGE_BACKENDS
from pmp.backends.storage.base import PromptStorageBackend
from pmp.errors import ConfigError

class PluginTypes(Enum):
    STORAGE = "storage"
    EXECUTION = "execution"

_PLUGINS: Dict[str, Type[PromptStorageBackend]] = {}

def load_backend(name: str, backend_type: PluginTypes, options: Dict[str, object]) -> PromptStorageBackend:
    """Return an instantiated backend by name."""
    normalized_name = (name or "file").lower()
    # Get a matching builtin backend if it exists
    if backend_type == PluginTypes.STORAGE:
        backend_cls = BUILTIN_STORAGE_BACKENDS.get(normalized_name)
        if not backend_cls:
            # Get a matching plugin backend if it exists
            backend_cls = get_plugin(PluginTypes.STORAGE, normalized_name)
    elif backend_type == PluginTypes.EXECUTION:
        # Get a matching plugin backend if it exists
        # we don't plan to have any built-in execution backends for now
        backend_cls = get_plugin(PluginTypes.EXECUTION, normalized_name)
    if not backend_cls:
        raise ConfigError(f'unknown backend "{normalized_name}"')
    return backend_cls(**options)

def load_plugins() -> None:
    """Get a list of installed plugins."""
    # Load storage plugins
    for entry in metadata.entry_points(group="pmp.plugins.storage"):
        plugin_cls = entry.load()
        if not issubclass(plugin_cls, PromptStorageBackend):
            print(f'WARNING: plugin "{entry.name}" does not implement PromptBackend')
            continue
        if entry.name in _PLUGINS:
            print(f'WARNING: plugin "{entry.name}" already loaded, overwriting')
        _PLUGINS[f"{PluginTypes.STORAGE.value}.{entry.name}"] = plugin_cls

def get_plugin(plugin_type: PluginTypes, name: str) -> Type[PromptStorageBackend]:
    """Get a plugin by name."""
    if not _PLUGINS:
        load_plugins()
    plugin_name = f"{plugin_type.value}.{name}"
    if plugin_name not in _PLUGINS:
        raise ConfigError(f'unknown plugin "{plugin_name}"')
    return _PLUGINS[plugin_name]