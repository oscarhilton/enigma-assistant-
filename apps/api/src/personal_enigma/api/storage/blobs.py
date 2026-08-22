"""Encrypted raw source blob store (PRIVATE_RAW)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from personal_enigma.api.storage.crypto import CryptoError, decrypt_blob, encrypt_blob


class BlobStoreError(Exception):
    """Raised when blob persistence fails."""


class BlobStore:
    """AEAD-encrypted files under ``blobs/`` — raw bodies never in SQL."""

    def __init__(self, root: Path, *, blob_key: bytes) -> None:
        self._root = root
        self._blob_key = blob_key
        self._root.mkdir(parents=True, exist_ok=True)

    def put(self, plaintext: bytes) -> str:
        """Encrypt and persist ``plaintext``; return opaque ``blob_ref``."""
        blob_ref = uuid4().hex
        path = self._path(blob_ref)
        path.write_bytes(encrypt_blob(self._blob_key, plaintext))
        return blob_ref

    def get(self, blob_ref: str) -> bytes:
        """Decrypt blob contents for ``blob_ref``."""
        path = self._path(blob_ref)
        if not path.exists():
            raise BlobStoreError(f"Blob not found: {blob_ref}")
        try:
            return decrypt_blob(self._blob_key, path.read_bytes())
        except CryptoError as exc:
            raise BlobStoreError(f"Failed to decrypt blob {blob_ref}") from exc

    def delete(self, blob_ref: str) -> None:
        """Remove blob file if present."""
        path = self._path(blob_ref)
        if path.exists():
            path.unlink()

    @staticmethod
    def content_hash(plaintext: bytes) -> str:
        """Return a stable SHA-256 hex digest for dedupe / integrity."""
        return hashlib.sha256(plaintext).hexdigest()

    def _path(self, blob_ref: str) -> Path:
        return self._root / f"{blob_ref}.bin"
