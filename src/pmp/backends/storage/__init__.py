from __future__ import annotations
from typing import Dict, Type
from pmp.backends.storage.base import PromptStorageBackend
from pmp.backends.storage.file_backend import FileBackend
from pmp.backends.storage.sqlite_backend import SQLiteBackend

BUILTIN_STORAGE_BACKENDS: Dict[str, Type[PromptStorageBackend]] = {
    "file": FileBackend,
    "sqlite": SQLiteBackend,
}