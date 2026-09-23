"""Django Storage backend for private Vercel Blob objects.

Selected via DOCUMENT_STORAGE_BACKEND=vercel_blob (local filesystem otherwise).
The stored `name` is the blob URL (opaque identifier); there is deliberately
NO public URL — downloads always go through the permission-checked Django
download endpoints, which stream bytes fetched server-side with the token.

No model changes are needed: FileField works through this Storage API.
"""
from __future__ import annotations

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class BlobStorage(Storage):
    def _client(self):
        from django.conf import settings

        from .blobstore import VercelBlobClient

        return VercelBlobClient(
            base_url=settings.BLOB_API_BASE_URL,
            token=settings.BLOB_READ_WRITE_TOKEN,
            api_version=getattr(settings, "BLOB_API_VERSION", "10"),
        )

    def _save(self, name, content):
        data = content.read()
        result = self._client().put(
            name,
            data,
            content_type=getattr(content, "content_type", None),
            private=True,
        )
        return result.url

    def get_available_name(self, name, max_length=None):
        # Deterministic names (Blob pathname); app-level SHA-256 dedupe
        # prevents accidental overwrites of distinct files.
        return name

    def _open(self, name, mode="rb"):
        return ContentFile(self._client().download(name), name=name.split("/")[-1])

    def exists(self, name):
        return self._client().exists(name)

    def delete(self, name):
        self._client().delete(name)

    def url(self, name):
        raise ValueError("Vercel Blob storage is private and exposes no public URL.")
