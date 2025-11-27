 """SQLite backend implementation."""

 from __future__ import annotations

 import json
 import sqlite3
 from pathlib import Path
 from typing import Dict, List, Optional

 from ..errors import PromptAlreadyExists, PromptNotFound, VersionNotFound
 from ..models import PromptSummary, PromptVersion, utcnow_iso
 from .base import PromptBackend


 class SQLiteBackend(PromptBackend):
     """Stores prompts in a SQLite database."""

     def __init__(self, path: Optional[str] = None):
         if not path:
             raise ValueError("sqlite backend requires a path")
         self.db_path = Path(path).expanduser()
         self.db_path.parent.mkdir(parents=True, exist_ok=True)
         self.conn = sqlite3.connect(self.db_path)
         self.conn.execute("PRAGMA foreign_keys = ON")
         self._ensure_schema()

     # --------------------------------------------------------------- interface
     def add(self, name: str, content: str, metadata: Dict[str, object]) -> None:
         with self.conn:
             cursor = self.conn.execute("SELECT id FROM prompts WHERE name = ?", (name,))
             if cursor.fetchone():
                 raise PromptAlreadyExists(f'prompt "{name}" already exists')
             cursor = self.conn.execute("INSERT INTO prompts (name) VALUES (?)", (name,))
             prompt_id = cursor.lastrowid
             self._insert_version(prompt_id, name, 1, content, metadata)

     def get(self, name: str, version: Optional[int] = None) -> Dict[str, object]:
         prompt_id = self._prompt_id(name)
         if version is None:
             row = self.conn.execute(
                 """
                 SELECT version, content, metadata, created_at
                 FROM prompt_versions
                 WHERE prompt_id = ?
                 ORDER BY version DESC
                 LIMIT 1
                 """,
                 (prompt_id,),
             ).fetchone()
             if not row:
                 raise PromptNotFound(f'prompt "{name}" does not have any versions')
         else:
             row = self.conn.execute(
                 """
                 SELECT version, content, metadata, created_at
                 FROM prompt_versions
                 WHERE prompt_id = ? AND version = ?
                 """,
                 (prompt_id, version),
             ).fetchone()
             if not row:
                 raise VersionNotFound(f'prompt "{name}" version {version} not found')
         metadata = json.loads(row[2])
         return {
             "name": name,
             "version": row[0],
             "content": row[1],
             "metadata": metadata,
             "created_at": row[3],
         }

     def update(self, name: str, content: str, metadata: Dict[str, object]) -> None:
         prompt_id = self._prompt_id(name)
         current_version = self.conn.execute(
             "SELECT COALESCE(MAX(version), 0) FROM prompt_versions WHERE prompt_id = ?",
             (prompt_id,),
         ).fetchone()[0]
         next_version = current_version + 1
         self._insert_version(prompt_id, name, next_version, content, metadata)

     def delete(self, name: str, version: Optional[int] = None) -> None:
         prompt_id = self._prompt_id(name)
         if version is None:
             row = self.conn.execute(
                 "SELECT version FROM prompt_versions WHERE prompt_id = ? ORDER BY version DESC LIMIT 1",
                 (prompt_id,),
             ).fetchone()
             if not row:
                 raise PromptNotFound(f'prompt "{name}" does not contain any versions')
             version = row[0]
         with self.conn:
             result = self.conn.execute(
                 "DELETE FROM prompt_versions WHERE prompt_id = ? AND version = ?",
                 (prompt_id, version),
             )
             if result.rowcount == 0:
                 raise VersionNotFound(f'prompt "{name}" version {version} not found')
             remaining = self.conn.execute(
                 "SELECT COUNT(*) FROM prompt_versions WHERE prompt_id = ?",
                 (prompt_id,),
             ).fetchone()[0]
             if remaining == 0:
                 self.conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))

     def list(self, filters: Optional[Dict[str, object]] = None) -> List[Dict[str, object]]:
         filters = filters or {}
         query = """
             SELECT p.name,
                    v.version,
                    v.metadata,
                    v.created_at
             FROM prompts p
             JOIN prompt_versions v ON p.id = v.prompt_id
             INNER JOIN (
                 SELECT prompt_id, MAX(version) AS max_version
                 FROM prompt_versions
                 GROUP BY prompt_id
             ) latest ON latest.prompt_id = p.id AND latest.max_version = v.version
         """
         rows = self.conn.execute(query).fetchall()
         results: List[Dict[str, object]] = []
         for name, version, metadata_raw, created_at in rows:
             metadata = json.loads(metadata_raw)
             if not _matches_filters(metadata, filters):
                 continue
             summary = PromptSummary(
                 name=name,
                 latest_version=version,
                 updated_at=created_at,
                 metadata=metadata,
             )
             results.append(summary.to_dict())
         return results

     # ---------------------------------------------------------------- helpers
     def _ensure_schema(self) -> None:
         with self.conn:
             self.conn.execute(
                 """
                 CREATE TABLE IF NOT EXISTS prompts (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT NOT NULL UNIQUE
                 )
                 """
             )
             self.conn.execute(
                 """
                 CREATE TABLE IF NOT EXISTS prompt_versions (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     prompt_id INTEGER NOT NULL,
                     version INTEGER NOT NULL,
                     content TEXT NOT NULL,
                     metadata TEXT NOT NULL,
                     created_at TEXT NOT NULL,
                     FOREIGN KEY(prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
                     UNIQUE(prompt_id, version)
                 )
                 """
             )

     def _prompt_id(self, name: str) -> int:
         row = self.conn.execute("SELECT id FROM prompts WHERE name = ?", (name,)).fetchone()
         if not row:
             raise PromptNotFound(f'prompt "{name}" does not exist')
         return row[0]

     def _insert_version(self, prompt_id: int, name: str, version: int, content: str, metadata: Dict[str, object]) -> None:
         payload = PromptVersion(
             name=name,
             version=version,
             content=content,
             metadata=metadata,
             created_at=utcnow_iso(),
         )
         with self.conn:
             self.conn.execute(
                 """
                 INSERT INTO prompt_versions (prompt_id, version, content, metadata, created_at)
                 VALUES (?, ?, ?, ?, ?)
                 """,
                 (prompt_id, version, payload.content, json.dumps(payload.metadata), payload.created_at),
             )


 def _matches_filters(metadata: Dict[str, object], filters: Dict[str, object]) -> bool:
     tag = filters.get("tag")
     if tag:
         tags = metadata.get("tags") or []
         if tag not in tags:
             return False
     model = filters.get("model")
     if model and metadata.get("model") != model:
         return False
     return True

