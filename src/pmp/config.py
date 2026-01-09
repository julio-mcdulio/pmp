"""Configuration helpers for PMP."""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback
    import tomli as tomllib  # type: ignore

from pmp.errors import ConfigError
from pmp.utils import expand_path, parse_value


DEFAULT_FILE_BACKEND_PATH = "~/.local/share/pmp/prompts"
DEFAULT_SQLITE_BACKEND_PATH = "~/.local/share/pmp/pmp.db"

DEFAULT_BACKEND_OPTIONS: Dict[str, Dict[str, Any]] = {
    "file": {"path": DEFAULT_FILE_BACKEND_PATH},
    "sqlite": {"path": DEFAULT_SQLITE_BACKEND_PATH},
}

@dataclass
class BackendSettings:
    """Resolved backend configuration."""

    name: str
    options: Dict[str, Any]


class ConfigManager:
    """Loads, stores, and mutates the PMP configuration file."""

    def __init__(self, config_path: Optional[str] = None):
        env_path = os.environ.get("PMP_CONFIG_FILE")
        raw_path = (
            config_path or env_path or (Path.home() / ".config" / "pmp" / "config.toml")
        )
        self.path = Path(raw_path).expanduser()
        self._data = self._load()

    @property
    def data(self) -> Dict[str, Any]:
        return copy.deepcopy(self._data)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = dumps(self._data)
        self.path.write_text(text, encoding="utf-8")

    def set_value(self, dotted_key: str, value: Any) -> None:
        key_parts = _normalize_key_path(dotted_key.split("."))
        _set_nested(self._data, key_parts, value)

    def get_value(self, dotted_key: str, default: Any = None) -> Any:
        key_parts = _normalize_key_path(dotted_key.split("."))
        return _get_nested(self._data, key_parts, default)

    def resolve_backend(
        self, backend_override: Optional[str], profile_override: Optional[str]
    ) -> BackendSettings:
        env_profile, env_backend, env_backend_opts = _read_env_overrides()

        backend_name = (
            (backend_override or env_backend)
            or self._data.get("backend")
            or "file"
        )

        options: Dict[str, Any] = {}
        options.update(DEFAULT_BACKEND_OPTIONS.get(backend_name, {}))
        options.update(_ensure_dict(self._data.get("backends", {}).get(backend_name)))
        if backend_name in env_backend_opts:
            options.update(env_backend_opts[backend_name])

        return BackendSettings(
            name=backend_name, options=_expand_backend_options(backend_name, options)
        )

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        with self.path.open("rb") as handle:
            try:
                return tomllib.load(handle)
            except (
                tomllib.TOMLDecodeError
            ) as exc:  # pragma: no cover - invalid file is rare
                raise ConfigError(f"invalid config: {exc}") from exc


def _ensure_dict(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not value:
        return {}
    return copy.deepcopy(value)


def _expand_backend_options(name: str, options: Dict[str, Any]) -> Dict[str, Any]:
    expanded = {}
    for key, value in options.items():
        if key in {"path", "database"}:
            expanded[key] = expand_path(value)
        else:
            expanded[key] = value
    if name == "sqlite" and "database" in expanded and "path" not in expanded:
        expanded["path"] = expanded["database"]
    return expanded


def _read_env_overrides() -> (
    Tuple[Optional[str], Optional[str], Dict[str, Dict[str, Any]]]
):
    backend = os.environ.get("PMP_BACKEND")
    backend_opts: Dict[str, Dict[str, Any]] = {}
    prefix = "PMP_BACKEND_"
    for env_key, raw_value in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        remainder = env_key[len(prefix) :]
        parts = remainder.split("_")
        if len(parts) < 2:
            continue
        backend_name = parts[0].lower()
        option_key = "_".join(parts[1:]).lower()
        backend_opts.setdefault(backend_name, {})[option_key.replace("_", "-")] = (
            parse_value(raw_value)
        )
    return None, backend.lower() if backend else None, backend_opts


def _normalize_key_path(parts: List[str]) -> List[str]:
    if parts[0] == "backend" and len(parts) > 1:
        return ["backends", *parts[1:]]
    return parts


def _set_nested(target: Dict[str, Any], parts: List[str], value: Any) -> None:
    scope = target
    for part in parts[:-1]:
        scope = scope.setdefault(part, {})
        if not isinstance(scope, dict):
            raise ConfigError(
                f'cannot assign "{ ".".join(parts) }" inside non-table key'
            )
    scope[parts[-1]] = value


def _get_nested(source: Dict[str, Any], parts: List[str], default: Any) -> Any:
    scope = source
    for part in parts:
        if not isinstance(scope, dict) or part not in scope:
            return default
        scope = scope[part]
    return scope


# ------------------------------------------------------------------ TOML write
def dumps(data: Dict[str, Any]) -> str:
    """Serialize the configuration into TOML (sufficient for PMP needs)."""
    lines: List[str] = []
    scalars, tables = _split_table(data)
    for key, value in scalars:
        lines.append(f"{key} = {format_toml_value(value)}")
    for key, value in tables:
        if lines and lines[-1] != "":
            lines.append("")
        lines.extend(_dump_table(key, value))
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _split_table(
    table: Dict[str, Any],
) -> Tuple[List[Tuple[str, Any]], List[Tuple[str, Dict[str, Any]]]]:
    scalars: List[Tuple[str, Any]] = []
    group: List[Tuple[str, Dict[str, Any]]] = []
    for key, value in table.items():
        if isinstance(value, dict):
            group.append((key, value))
        else:
            scalars.append((key, value))
    return scalars, group


def _dump_table(prefix: str, table: Dict[str, Any]) -> List[str]:
    lines = [f"[{prefix}]"]
    scalars, tables = _split_table(table)
    for key, value in scalars:
        lines.append(f"{key} = {format_toml_value(value)}")
    for key, value in tables:
        lines.append("")
        lines.extend(_dump_table(f"{prefix}.{key}", value))
    return lines


def format_toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        rendered = ", ".join(format_toml_value(item) for item in value)
        return f"[{rendered}]"
    if value is None:
        return '""'
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'
