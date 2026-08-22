"""Memory decay — active private state → pseudonymous shadow (SEC-06).

DECAY reduces detail, precision, and linkability while retaining utility.
FORGET (see ``forget.py``) is terminal — recoverability → zero.
"""

from __future__ import annotations

import hashlib
from sqlite3 import Connection as SqlCipherConnection

from personal_enigma.api.storage.derived import get_derived_record, insert_derived_record
from personal_enigma.domain.retention import DerivedRecord, MemoryLayer

# Active → shadow field compression map (detail↓ precision↓ linkability↓).
_SHADOW_FIELD_MAP: dict[str, str] = {
    "due_at": "due_bucket",
    "exact_amount": "amount_band",
    "location": "coarse_region",
    "subject": "importance",
    "body_excerpt": "response_expected",
    "display_name": "entity_ref",
}


def compress_payload_to_shadow(payload: dict[str, object]) -> dict[str, object]:
    """Compress active-state payload into shadow enums/buckets."""
    shadow: dict[str, object] = {}
    for key, value in payload.items():
        shadow_key = _SHADOW_FIELD_MAP.get(key, key)
        if shadow_key != key and shadow_key in shadow:
            continue
        if key in ("due_at", "exact_time"):
            shadow[shadow_key] = _time_to_bucket(str(value))
        elif key in ("exact_amount",):
            shadow[shadow_key] = _amount_to_band(value)
        elif key in ("location",):
            shadow[shadow_key] = _location_to_coarse_region(value)
        elif key in ("subject", "body_excerpt", "display_name"):
            shadow[shadow_key] = "ABSTRACTED"
        else:
            shadow[shadow_key] = value
    shadow["_decayed"] = True
    return shadow


def decay_record(conn: SqlCipherConnection, record_id: str) -> DerivedRecord:
    """Compress an active derived record into pseudonymous shadow form."""
    record = get_derived_record(conn, record_id)
    if record is None:
        raise ValueError(f"Derived record not found: {record_id}")
    if record.memory_layer == MemoryLayer.SHADOW:
        return record

    decayed = record.model_copy(
        update={
            "memory_layer": MemoryLayer.SHADOW,
            "payload": compress_payload_to_shadow(record.payload),
        }
    )
    insert_derived_record(conn, decayed)
    return decayed


def _time_to_bucket(value: str) -> str:
    lowered = value.lower()
    if "today" in lowered or "0 day" in lowered:
        return "WITHIN_1_DAY"
    if "tomorrow" in lowered or "1 day" in lowered:
        return "WITHIN_2_DAYS"
    if "week" in lowered or "7 day" in lowered:
        return "WITHIN_1_WEEK"
    return "LATER"


def _amount_to_band(value: object) -> str:
    if isinstance(value, (int, float)):
        amount = float(value)
    else:
        try:
            amount = float(str(value))
        except (TypeError, ValueError):
            return "UNKNOWN_BAND"
    if amount < 100:
        return "UNDER_100"
    if amount < 1000:
        return "UNDER_1000"
    return "OVER_1000"

def _location_to_coarse_region(value: object) -> str:
    """Reduce precise locations to coarse region tokens (not street-level text)."""
    text = str(value).strip()
    if not text:
        return "UNKNOWN_REGION"
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if len(parts) >= 2:
        city = parts[-2] if len(parts) >= 3 else parts[-1]
        token = "".join(ch if ch.isalnum() else "_" for ch in city.upper())
        token = token.strip("_")[:32] or "UNKNOWN"
        return f"REGION_{token}"
    digest = hashlib.sha256(text.lower().encode("utf-8")).hexdigest()[:8].upper()
    return f"REGION_BUCKET_{digest}"

