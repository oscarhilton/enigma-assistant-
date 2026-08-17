"""Audited remote egress gate — sole path for hosted-model transmission (SEC-02)."""

from personal_enigma.privacy.egress.assert_remote_safe import assert_remote_safe
from personal_enigma.privacy.egress.classification import (
    PrivateDerived,
    PrivateRaw,
    RemoteSafeContext,
)
from personal_enigma.privacy.egress.disclosure import (
    CONVERSATION_EGRESS_EXCLUDED,
    CONVERSATION_EGRESS_INCLUDED,
    EgressDisclosure,
    redact_transport_secrets,
    tool_names_from_wire,
)
from personal_enigma.privacy.egress.errors import EgressBlockedError
from personal_enigma.privacy.egress.gate import (
    AuditedEgressGate,
    EgressResult,
    build_audited_egress_gate,
    get_audited_egress_gate,
    set_audited_egress_gate,
)
from personal_enigma.privacy.egress.store import (
    AuditBackedDisclosureStore,
    DisclosureStore,
    InMemoryDisclosureStore,
)

__all__ = [
    "CONVERSATION_EGRESS_EXCLUDED",
    "CONVERSATION_EGRESS_INCLUDED",
    "AuditBackedDisclosureStore",
    "AuditedEgressGate",
    "DisclosureStore",
    "EgressBlockedError",
    "EgressDisclosure",
    "EgressResult",
    "InMemoryDisclosureStore",
    "PrivateDerived",
    "PrivateRaw",
    "RemoteSafeContext",
    "assert_remote_safe",
    "build_audited_egress_gate",
    "get_audited_egress_gate",
    "redact_transport_secrets",
    "set_audited_egress_gate",
    "tool_names_from_wire",
]
