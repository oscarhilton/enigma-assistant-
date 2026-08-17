"""Worker retention GC job (SEC-06)."""

from __future__ import annotations

from personal_enigma.api.storage.vault import PrivateVault


def run_retention_gc(*, root: str | None = None) -> dict[str, object]:
    """Sweep expired raw blobs and resolved obligations."""
    from pathlib import Path

    vault_root = Path(root) if root is not None else None
    with PrivateVault.open(root=vault_root) as vault:
        result = vault.run_gc()
    return {
        "expired_source_ids": list(result.expired_source_ids),
        "forget_count": len(result.forget_results),
        "resolved_obligations_expired": result.resolved_obligations_expired,
    }
