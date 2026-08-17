"""User-facing forget operation API stubs (SEC-06)."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from personal_enigma.api.storage.vault import PrivateVault, VaultError


class RetentionInventoryItem(BaseModel):
    record_type: str
    memory_layer: str
    purpose: str
    derived_from_count: int
    id: str


class RetentionInventoryResponse(BaseModel):
    derived_records: list[RetentionInventoryItem] = Field(default_factory=list)
    source_record_count: int


class RetentionProvenanceResponse(BaseModel):
    derived_id: str
    record_type: str
    memory_layer: str
    purpose: str
    retention_class: str
    expires_after_resolution: str | None
    derived_from: list[str]
    confidence: float


class ScopedForgetRequest(BaseModel):
    source_ids: list[str] = Field(min_length=1)


class ScopedForgetResponse(BaseModel):
    results: list[dict[str, object]]


def install_forget_routes(app: FastAPI) -> None:
    @app.get("/private/retention/inventory", response_model=RetentionInventoryResponse)
    def retention_inventory() -> RetentionInventoryResponse:
        """What do you remember about me? — scoped summary, not raw dump."""
        try:
            with PrivateVault.open() as vault:
                records = vault.list_derived_records()
                source_count = vault.count_source_records()
        except VaultError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        items = [
            RetentionInventoryItem(
                id=r.id,
                record_type=r.record_type.value,
                memory_layer=r.memory_layer.value,
                purpose=r.lineage.purpose.value,
                derived_from_count=len(r.lineage.derived_from),
            )
            for r in records
        ]
        return RetentionInventoryResponse(
            derived_records=items,
            source_record_count=source_count,
        )

    @app.get(
        "/private/retention/provenance/{derived_id}",
        response_model=RetentionProvenanceResponse,
    )
    def retention_provenance(derived_id: str) -> RetentionProvenanceResponse:
        """Why are you remembering that? — lineage and expiry, not content."""
        try:
            with PrivateVault.open() as vault:
                record = vault.get_derived_record(derived_id)
        except VaultError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if record is None:
            raise HTTPException(status_code=404, detail="Derived record not found")
        return RetentionProvenanceResponse(
            derived_id=record.id,
            record_type=record.record_type.value,
            memory_layer=record.memory_layer.value,
            purpose=record.lineage.purpose.value,
            retention_class=record.lineage.retention_class.value,
            expires_after_resolution=record.lineage.expires_after_resolution,
            derived_from=list(record.lineage.derived_from),
            confidence=record.confidence,
        )

    @app.post("/private/retention/forget", response_model=ScopedForgetResponse)
    def scoped_forget(body: ScopedForgetRequest) -> ScopedForgetResponse:
        """Forget everything about matching sources — graph operation with cascade."""
        try:
            with PrivateVault.open() as vault:
                results = vault.forget_sources(body.source_ids)
        except VaultError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return ScopedForgetResponse(
            results=[
                {
                    "source_id": r.source_id,
                    "deleted_derived_ids": list(r.deleted_derived_ids),
                    "surviving_derived_ids": list(r.surviving_derived_ids),
                    "audit_id": r.audit_id,
                }
                for r in results
            ]
        )
