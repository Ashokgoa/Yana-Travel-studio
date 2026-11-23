"""File storage abstraction.

Application code works with *relative keys* such as ``hotels/abc123.jpg`` and
never with absolute filesystem paths. ``LocalFileStorage`` maps keys onto the
uploads directory; a cloud implementation (Azure Blob / S3) can implement the
same interface later without touching callers.
"""

import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath

from app.core.config import get_settings

STORAGE_FOLDERS = (
    "logo",
    "countries",
    "cities",
    "hotels",
    "restaurants",
    "sightseeing",
    "transportation",
    "generated",
)

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class StorageError(ValueError):
    """Raised for invalid keys, e.g. attempted path traversal."""


def safe_filename(original_name: str) -> str:
    """Return a collision-free, filesystem-safe name that keeps the extension."""
    suffix = PurePosixPath(original_name.replace("\\", "/")).suffix.lower()
    suffix = _SAFE_CHARS.sub("", suffix)[:10]
    return f"{uuid.uuid4().hex}{suffix}"


class FileStorage(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes) -> str: ...

    @abstractmethod
    def read(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...


class LocalFileStorage(FileStorage):
    def __init__(self, root: Path):
        self.root = root.resolve()

    def ensure_layout(self) -> None:
        for folder in STORAGE_FOLDERS:
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        normalized = key.replace("\\", "/")
        pure = PurePosixPath(normalized)
        if not normalized or pure.is_absolute() or ".." in pure.parts or ":" in normalized:
            raise StorageError(f"Invalid storage key: {key!r}")
        path = (self.root / pure).resolve()
        if not path.is_relative_to(self.root):
            raise StorageError(f"Invalid storage key: {key!r}")
        return path

    def save(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def delete(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()


def get_storage() -> LocalFileStorage:
    return LocalFileStorage(get_settings().uploads_dir)
