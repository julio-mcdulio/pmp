"""Output helpers for CLI formatting."""

from __future__ import annotations

import json
from typing import Any, List, Sequence, Dict
from enum import Enum
from dataclasses import dataclass
import yaml


class OutputFormatType(str, Enum):
    RAW = "raw"
    JSON = "json"
    YAML = "yaml"


def as_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def as_yaml(payload: Any) -> str:
    return yaml.safe_dump(payload, sort_keys=False).rstrip()


def render_table(rows: Sequence[Sequence[str]], headers: Sequence[str]) -> str:
    table = [headers, *rows]
    widths = [max(len(str(row[idx])) for row in table) for idx in range(len(headers))]
    lines: List[str] = []
    for idx, row in enumerate(table):
        rendered = "  ".join(
            str(cell).ljust(widths[col]) for col, cell in enumerate(row)
        )
        lines.append(rendered.rstrip())
        if idx == 0:
            lines.append("  ".join("-" * width for width in widths))
    return "\n".join(lines)


def print_get(record: Dict[str, Any], format_: OutputFormatType) -> None:
    if format_ == OutputFormatType.RAW:
        print(record["content"], end="" if record["content"].endswith("\n") else "\n")
    elif format_ == OutputFormatType.JSON:
        print(as_json(record))
    elif format_ == OutputFormatType.YAML:
        print(as_yaml(record))


def print_list(
    prompts: List[Dict[str, Any]], format_: OutputFormatType, is_long: bool
) -> None:
    if format_ == OutputFormatType.JSON:
        print(as_json(prompts))
        return
    if format_ == OutputFormatType.YAML:
        print(as_yaml(prompts))
        return
    if is_long:
        rows = []
        for item in prompts:
            metadata = item.get("metadata", {})
            tags = ",".join(metadata.get("tags", []))
            rows.append(
                [
                    item["name"],
                    str(item["latest_version"]),
                    tags,
                    metadata.get("model", "") or "",
                    item.get("updated_at", ""),
                ]
            )
        if rows:
            print(
                render_table(
                    rows, headers=["NAME", "VERSION", "TAGS", "MODEL", "UPDATED"]
                )
            )
        return
    for item in prompts:
        print(item["name"])
