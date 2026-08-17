"""Privacy classification, remote allowlist, and invariant gate."""

from personal_enigma.privacy.allowlist import (
    PERSON_PSEUDONYM_PREFIX,
    REMOTE_METADATA_KEYS,
    REMOTE_PAYLOAD_ALLOWLIST_DOC,
    REMOTE_PAYLOAD_TOP_LEVEL_KEYS,
)
from personal_enigma.privacy.inspector import InspectionResult, inspect_transformed_context
from personal_enigma.privacy.invariants import (
    PrivacyInvariantError,
    assert_no_private_person_fields,
    assert_notes_not_wholesale_remote_safe,
    assert_remote_payload_allowlisted,
    assert_remote_payload_safe,
    assert_transformed_corpus_safe,
    payload_as_dict,
    secrets_from_person,
)
from personal_enigma.privacy.levels import PrivacyLevel, default_level_for_source
from personal_enigma.privacy.notes_policy import (
    NotesRemotePolicyException,
    notes_default_privacy_level,
    wholesale_note_body_remote_safe,
)
from personal_enigma.privacy.remote import RemoteInferenceConfig, may_send_remotely
from personal_enigma.privacy.safe_logging import (
    content_hash,
    debug_raw_logging_enabled,
    format_safe_log_event,
    redact_string,
    safe_log_fields,
)
from personal_enigma.privacy.egress import (
    AuditedEgressGate,
    EgressBlockedError,
    EgressDisclosure,
    PrivateDerived,
    PrivateRaw,
    RemoteSafeContext,
    assert_remote_safe,
    build_audited_egress_gate,
    get_audited_egress_gate,
    set_audited_egress_gate,
)

__all__ = [
    "PERSON_PSEUDONYM_PREFIX",
    "NotesRemotePolicyException",
    "PrivacyInvariantError",
    "PrivacyLevel",
    "REMOTE_METADATA_KEYS",
    "REMOTE_PAYLOAD_ALLOWLIST_DOC",
    "REMOTE_PAYLOAD_TOP_LEVEL_KEYS",
    "AuditedEgressGate",
    "EgressBlockedError",
    "EgressDisclosure",
    "InspectionResult",
    "PrivateDerived",
    "PrivateRaw",
    "RemoteInferenceConfig",
    "RemoteSafeContext",
    "content_hash",
    "debug_raw_logging_enabled",
    "format_safe_log_event",
    "may_send_remotely",
    "redact_string",
    "safe_log_fields",
    "assert_no_private_person_fields",
    "assert_notes_not_wholesale_remote_safe",
    "assert_remote_payload_allowlisted",
    "assert_remote_payload_safe",
    "assert_remote_safe",
    "assert_transformed_corpus_safe",
    "build_audited_egress_gate",
    "default_level_for_source",
    "get_audited_egress_gate",
    "inspect_transformed_context",
    "may_send_remotely",
    "notes_default_privacy_level",
    "payload_as_dict",
    "secrets_from_person",
    "set_audited_egress_gate",
    "wholesale_note_body_remote_safe",
]
