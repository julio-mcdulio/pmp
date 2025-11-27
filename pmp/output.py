 """Output helpers for CLI formatting."""

 from __future__ import annotations

 import json
from typing import Any, List, Sequence

 import yaml


 def as_json(payload: Any) -> str:
     return json.dumps(payload, indent=2, ensure_ascii=False)


 def as_yaml(payload: Any) -> str:
     return yaml.safe_dump(payload, sort_keys=False).rstrip()


 def render_table(rows: Sequence[Sequence[str]], headers: Sequence[str]) -> str:
     table = [headers, *rows]
     widths = [max(len(str(row[idx])) for row in table) for idx in range(len(headers))]
     lines: List[str] = []
     for idx, row in enumerate(table):
         rendered = "  ".join(str(cell).ljust(widths[col]) for col, cell in enumerate(row))
         lines.append(rendered.rstrip())
         if idx == 0:
             lines.append("  ".join("-" * width for width in widths))
     return "\n".join(lines)

