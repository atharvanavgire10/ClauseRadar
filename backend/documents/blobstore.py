"""Vercel Blob transport — first-party, stdlib-only, private by default.

We deliberately do NOT use the community `vercel_blob` package: it hardcodes
public access on upload, which is unacceptable for private contract documents.
This client speaks the Blob HTTP API directly (Bearer token, never logged)
and always requests private access unless explicitly told otherwise.

All network failures surface as BlobError (token/redacted) so callers can
mark documents FAILED with a clear message instead of crashing.
"""
from __future__ import annotations

import json
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


class BlobError(Exception):
    """Blob operation failed. Never contains the auth token."""


@dataclass
class BlobResult:
    url: str
    pathname: str


def _redacted(message: str, token: str) -> str:
    return message.replace(token, "[redacted]") if token else message


class VercelBlobClient:
    """Minimal private Blob client. `base_url` is injectable for tests."""

    def __init__(self, *, base_url: str, token: str, api_version: str = "10", timeout: int = 30):
        if not token:
            raise BlobError("BLOB_READ_WRITE_TOKEN is not configured.")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.api_version = api_version
        self.timeout = timeout

    def _headers(self, extra: dict | None = None) -> dict:
        headers = {
            "authorization": f"Bearer {self.token}",
            "x-api-version": self.api_version,
        }
        if extra:
            headers.update(extra)
        return headers

    def _request(self, method: str, url: str, *, headers: dict, data: bytes | None = None,
                 content_type: str | None = None) -> tuple[int, bytes]:
        request_headers = dict(headers)
        if content_type:
            request_headers["content-type"] = content_type
        req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:500] if hasattr(exc, "read") else ""
            raise BlobError(f"Blob API error (status {exc.code}): {body}") from exc
        except Exception as exc:
            raise BlobError(f"Blob request failed: {_redacted(str(exc), self.token)}") from exc

    def put(self, pathname: str, data: bytes, *, content_type: str | None = None,
            private: bool = True) -> BlobResult:
        """Upload bytes; returns the blob URL. Uploads are deterministic
        (no random suffix) with overwrite allowed so names stay stable."""
        if not pathname or pathname.startswith("/"):
            raise BlobError("Blob pathname must be a non-empty relative path.")
        url = f"{self.base_url}/?pathname={urllib.parse.quote(pathname)}"
        headers = self._headers({
            "x-content-type": content_type or mimetypes.guess_type(pathname)[0] or "application/octet-stream",
            "access": "private" if private else "public",
            "x-allow-overwrite": "1",
        })
        status, body = self._request("PUT", url, headers=headers, data=data)
        if status != 200:
            raise BlobError(f"Blob upload failed (status {status}).")
        try:
            payload = json.loads(body.decode("utf-8"))
            return BlobResult(url=payload["url"], pathname=payload.get("pathname", pathname))
        except (ValueError, KeyError) as exc:
            raise BlobError("Blob upload returned an unreadable response.") from exc

    def download(self, url: str) -> bytes:
        """Authenticated server-side fetch (private blobs need the token)."""
        status, body = self._request("GET", url, headers=self._headers())
        if status != 200:
            raise BlobError(f"Blob download failed (status {status}).")
        return body

    def exists(self, url: str) -> bool:
        """Metadata probe; 404 means absent, other errors raise."""
        check_url = f"{self.base_url}/?url={urllib.parse.quote(url, safe='')}"
        try:
            status, _ = self._request("GET", check_url, headers=self._headers())
        except BlobError as exc:
            if "(status 404)" in str(exc):
                return False
            raise
        return status == 200

    def delete(self, urls: list[str] | str) -> None:
        if isinstance(urls, str):
            urls = [urls]
        if not urls:
            return
        status, _ = self._request(
            "POST",
            f"{self.base_url}/delete",
            headers=self._headers(),
            data=json.dumps({"urls": urls}).encode(),
            content_type="application/json",
        )
        if status != 200:
            raise BlobError(f"Blob delete failed (status {status}).")
