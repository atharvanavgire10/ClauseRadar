"""Storage abstraction — local filesystem today, S3-compatible tomorrow."""
from __future__ import annotations

from django.core.files.storage import default_storage


class DocumentStorage:
    """Thin wrapper so views/services never touch the storage backend directly."""

    def save(self, name: str, content) -> str:
        return default_storage.save(name, content)

    def delete(self, name: str) -> None:
        if name and default_storage.exists(name):
            default_storage.delete(name)

    def exists(self, name: str) -> bool:
        return default_storage.exists(name)

    def path(self, name: str) -> str:
        return default_storage.path(name)


storage = DocumentStorage()
