"""AEAD encryption and key wrapping for the Private vault."""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_SIZE = 32
NONCE_SIZE = 12
WRAP_MAGIC = b"ENMK"
WRAP_VERSION = 1
BLOB_MAGIC = b"ENBL"
BLOB_VERSION = 1


class CryptoError(Exception):
    """Raised when encryption or decryption fails."""


@dataclass(frozen=True, slots=True)
class WrappedKeyBundle:
    """Master-key-wrapped data, blob, and audit keys persisted on disk."""

    data_key: bytes
    blob_key: bytes
    audit_key: bytes


def generate_key() -> bytes:
    """Return a fresh 256-bit key."""
    return os.urandom(KEY_SIZE)


def encrypt_aead(key: bytes, plaintext: bytes, *, associated_data: bytes = b"") -> bytes:
    """Encrypt ``plaintext`` with AES-256-GCM; returns nonce || ciphertext || tag."""
    if len(key) != KEY_SIZE:
        raise CryptoError("AES-GCM key must be 32 bytes")
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, associated_data)
    return nonce + ciphertext


def decrypt_aead(key: bytes, envelope: bytes, *, associated_data: bytes = b"") -> bytes:
    """Decrypt an AES-256-GCM envelope produced by :func:`encrypt_aead`."""
    if len(key) != KEY_SIZE:
        raise CryptoError("AES-GCM key must be 32 bytes")
    if len(envelope) < NONCE_SIZE + 16:
        raise CryptoError("Ciphertext envelope too short")
    nonce = envelope[:NONCE_SIZE]
    ciphertext = envelope[NONCE_SIZE:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, associated_data)
    except Exception as exc:
        raise CryptoError("AEAD decryption failed") from exc


def wrap_key_bundle(master_key: bytes, bundle: WrappedKeyBundle) -> bytes:
    """Wrap the three data keys with the master key for on-disk storage."""
    payload = struct.pack(
        ">III",
        len(bundle.data_key),
        len(bundle.blob_key),
        len(bundle.audit_key),
    )
    payload += bundle.data_key + bundle.blob_key + bundle.audit_key
    body = encrypt_aead(master_key, payload, associated_data=WRAP_MAGIC)
    return WRAP_MAGIC + bytes([WRAP_VERSION]) + body


def unwrap_key_bundle(master_key: bytes, blob: bytes) -> WrappedKeyBundle:
    """Recover wrapped data keys using the master key."""
    if len(blob) < len(WRAP_MAGIC) + 1:
        raise CryptoError("Wrapped key blob too short")
    if blob[: len(WRAP_MAGIC)] != WRAP_MAGIC:
        raise CryptoError("Invalid wrapped key magic")
    if blob[len(WRAP_MAGIC)] != WRAP_VERSION:
        raise CryptoError("Unsupported wrapped key version")
    payload = decrypt_aead(master_key, blob[len(WRAP_MAGIC) + 1 :], associated_data=WRAP_MAGIC)
    if len(payload) < 12:
        raise CryptoError("Wrapped key payload too short")
    data_len, blob_len, audit_len = struct.unpack(">III", payload[:12])
    keys_blob = payload[12:]
    expected = data_len + blob_len + audit_len
    if len(keys_blob) != expected:
        raise CryptoError("Wrapped key payload length mismatch")
    offset = 0
    data_key = keys_blob[offset : offset + data_len]
    offset += data_len
    blob_key = keys_blob[offset : offset + blob_len]
    offset += blob_len
    audit_key = keys_blob[offset : offset + audit_len]
    if len({len(data_key), len(blob_key), len(audit_key)}) != 1 or len(data_key) != KEY_SIZE:
        raise CryptoError("Wrapped keys must each be 32 bytes")
    return WrappedKeyBundle(data_key=data_key, blob_key=blob_key, audit_key=audit_key)


def encrypt_blob(key: bytes, plaintext: bytes) -> bytes:
    """Encrypt raw source bytes for ``blobs/`` storage."""
    body = encrypt_aead(key, plaintext, associated_data=BLOB_MAGIC)
    return BLOB_MAGIC + bytes([BLOB_VERSION]) + body


def decrypt_blob(key: bytes, envelope: bytes) -> bytes:
    """Decrypt a blob envelope from ``blobs/``."""
    if len(envelope) < len(BLOB_MAGIC) + 1:
        raise CryptoError("Blob envelope too short")
    if envelope[: len(BLOB_MAGIC)] != BLOB_MAGIC:
        raise CryptoError("Invalid blob magic")
    if envelope[len(BLOB_MAGIC)] != BLOB_VERSION:
        raise CryptoError("Unsupported blob version")
    return decrypt_aead(key, envelope[len(BLOB_MAGIC) + 1 :], associated_data=BLOB_MAGIC)
