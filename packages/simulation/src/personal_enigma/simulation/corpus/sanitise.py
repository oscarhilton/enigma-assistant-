"""Corpus sanitiser — Demo-safe rewrite + reject pipeline (ADR-007).

Pipeline: strip generation metadata → identity/domain rewrite → URL rewrite →
secret scan → body name rewrite. Rejected conversations never enter derived
indexes used for public Demo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from personal_enigma.simulation.corpus.models import CorpusConversation, CorpusMessage

SANITISER_VERSION = "1"

# Fields that must never reach SyntheticMailSource / Enigma.
GENERATION_METADATA_KEYS = frozenset(
    {
        "prompt",
        "generation_prompt",
        "persona",
        "persona_metadata",
        "reasoning",
        "model_reasoning",
        "pipeline_metadata",
        "generated_context",
        "system_prompt",
    }
)

_FIRST_NAMES = (
    "Nina",
    "Jordan",
    "Sam",
    "Casey",
    "Riley",
    "Morgan",
    "Avery",
    "Quinn",
    "Taylor",
    "Jamie",
    "Drew",
    "Reese",
    "Cameron",
    "Hayden",
    "Parker",
    "Rowan",
)
_LAST_NAMES = (
    "Brooks",
    "Lee",
    "Rivera",
    "Ng",
    "Patel",
    "Nguyen",
    "Garcia",
    "Okeke",
    "Singh",
    "Cohen",
    "Walsh",
    "Diaz",
    "Kim",
    "Berg",
    "Sato",
    "Ali",
)

# Keep the demo protagonist address stable when present as a recipient/sender.
_PRESERVE_EMAILS = frozenset(
    {
        "alex@morgan.example",
        "alex.morgan@northwind.example",
        "alex.morgan@example.com",
    }
)

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("github_pat", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("generic_api_key", re.compile(r"(?i)\b(?:api[_-]?key|secret[_-]?key)\s*[:=]\s*\S+")),
    ("password_assignment", re.compile(r"(?i)\bpassword\s*[:=]\s*\S+")),
    ("otp_code", re.compile(r"(?i)\b(?:otp|one[- ]time(?: password)?)\s*[:=]?\s*\d{6}\b")),
    (
        "auth_url",
        re.compile(
            r"(?i)https?://\S*[?&](?:token|access_token|auth|api_key|key|password)=[^\s&]+"
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class IdentityMapping:
    """Scenario-local cast entry — simulation data, not Enigma memory."""

    person_id: str
    display_name: str
    email: str
    source_email: str
    source_name: str


@dataclass
class SanitiseDiagnostics:
    rejected: bool = False
    reasons: list[str] = field(default_factory=list)
    identities: dict[str, IdentityMapping] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SanitiseResult:
    conversation: CorpusConversation | None
    diagnostics: SanitiseDiagnostics


def strip_generation_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy without generation-pipeline keys."""
    return {k: v for k, v in raw.items() if k not in GENERATION_METADATA_KEYS}


def sanitise_raw_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Sanitise an untyped corpus row (e.g. FinePersonas JSON) before modelling."""
    cleaned = strip_generation_metadata(raw)
    emails = cleaned.get("emails")
    if isinstance(emails, list):
        cleaned["emails"] = [
            strip_generation_metadata(item) if isinstance(item, dict) else item
            for item in emails
        ]
    messages = cleaned.get("messages")
    if isinstance(messages, list):
        cleaned["messages"] = [
            strip_generation_metadata(item) if isinstance(item, dict) else item
            for item in messages
        ]
    return cleaned


def _stable_int(value: str) -> int:
    digest = sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def _identity_for(
    *,
    source_email: str,
    source_name: str,
    rewrite_seed: str,
    preserve_emails: frozenset[str],
    self_email: str | None,
) -> IdentityMapping:
    email_key = source_email.strip().lower()
    protagonist = False
    if self_email and email_key == self_email.lower():
        protagonist = True
    elif email_key in preserve_emails or email_key in _PRESERVE_EMAILS:
        protagonist = True
    elif email_key.startswith("alex@") or email_key.startswith("alex.morgan@"):
        protagonist = True
    if protagonist:
        return IdentityMapping(
            person_id="demo-protagonist",
            display_name=source_name or "Alex Morgan",
            email=(self_email or email_key),
            source_email=source_email,
            source_name=source_name,
        )
    idx = _stable_int(f"{rewrite_seed}:{email_key}")
    person_num = idx % 10_000
    company_num = (idx // 10_000) % 1_000
    first = _FIRST_NAMES[idx % len(_FIRST_NAMES)]
    last = _LAST_NAMES[(idx // len(_FIRST_NAMES)) % len(_LAST_NAMES)]
    return IdentityMapping(
        person_id=f"background-person-{person_num:04d}",
        display_name=f"{first} {last}",
        email=f"person-{person_num:04d}@company-{company_num:03d}.example",
        source_email=source_email,
        source_name=source_name,
    )


def _scan_secrets(text: str) -> list[str]:
    hits: list[str] = []
    for label, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            hits.append(label)
    return hits


def _rewrite_urls(text: str, *, company_index: int) -> str:
    portal = f"https://portal.company-{company_index:03d}.example"

    def _sub(match: re.Match[str]) -> str:
        url = match.group(0)
        # Preserve path-ish suffix when present; never keep live host.
        path = ""
        after_scheme = url.split("://", 1)[-1]
        slash = after_scheme.find("/")
        if slash >= 0:
            path = after_scheme[slash:]
            path = re.sub(r"[?#].*$", "", path)
        return f"{portal}{path or '/resource'}"

    return _URL_RE.sub(_sub, text)


def _rewrite_names_in_body(body: str, identities: dict[str, IdentityMapping]) -> str:
    """Replace source display names with rewritten cast names (longest first)."""
    replacements: list[tuple[str, str]] = []
    for mapping in identities.values():
        if mapping.source_name and mapping.source_name != mapping.display_name:
            replacements.append((mapping.source_name, mapping.display_name))
        # Also rewrite bare first names when unambiguous enough (>= 4 chars).
        src_first = mapping.source_name.split()[0] if mapping.source_name else ""
        dst_first = mapping.display_name.split()[0] if mapping.display_name else ""
        if len(src_first) >= 4 and dst_first and src_first != dst_first:
            replacements.append((src_first, dst_first))
    replacements.sort(key=lambda pair: len(pair[0]), reverse=True)
    out = body
    for old, new in replacements:
        out = re.sub(re.escape(old), new, out, flags=re.IGNORECASE)
    return out


def sanitise_conversation(
    conversation: CorpusConversation,
    *,
    rewrite_domains: bool = True,
    rewrite_seed: str = "demo-safe-v1",
    reject_secrets: bool = True,
    preserve_emails: set[str] | frozenset[str] | None = None,
    self_email: str | None = None,
) -> CorpusConversation:
    """Sanitise a conversation; raises ValueError if rejected for secrets.

    Prefer :func:`sanitise_conversation_detailed` when rejection diagnostics matter.
    """
    result = sanitise_conversation_detailed(
        conversation,
        rewrite_domains=rewrite_domains,
        rewrite_seed=rewrite_seed,
        reject_secrets=reject_secrets,
        preserve_emails=preserve_emails,
        self_email=self_email,
    )
    if result.conversation is None:
        reasons = ", ".join(result.diagnostics.reasons) or "rejected"
        raise ValueError(f"conversation {conversation.id!r} rejected: {reasons}")
    return result.conversation


def sanitise_conversation_detailed(
    conversation: CorpusConversation,
    *,
    rewrite_domains: bool = True,
    rewrite_seed: str = "demo-safe-v1",
    reject_secrets: bool = True,
    preserve_emails: set[str] | frozenset[str] | None = None,
    self_email: str | None = None,
) -> SanitiseResult:
    """Full sanitiser with accept/reject diagnostics."""
    diagnostics = SanitiseDiagnostics()
    if not conversation.messages:
        diagnostics.rejected = True
        diagnostics.reasons.append("empty_conversation")
        return SanitiseResult(conversation=None, diagnostics=diagnostics)

    # Only protagonist aliases are preserved; other reserved addresses are rewritten.
    preserve = frozenset({*(e.lower() for e in (preserve_emails or set())), *_PRESERVE_EMAILS})

    for msg in conversation.messages:
        key = msg.sender_email.strip().lower()
        if key not in diagnostics.identities:
            diagnostics.identities[key] = _identity_for(
                source_email=msg.sender_email,
                source_name=msg.sender_name,
                rewrite_seed=rewrite_seed,
                preserve_emails=preserve,
                self_email=self_email,
            )
        for i, email in enumerate(msg.recipient_emails):
            name = msg.recipient_names[i] if i < len(msg.recipient_names) else ""
            rkey = email.strip().lower()
            if rkey not in diagnostics.identities:
                diagnostics.identities[rkey] = _identity_for(
                    source_email=email,
                    source_name=name or email,
                    rewrite_seed=rewrite_seed,
                    preserve_emails=preserve,
                    self_email=self_email,
                )

    if reject_secrets:
        for msg in conversation.messages:
            blob = "\n".join(
                [msg.subject, msg.body_text, msg.sender_email, *msg.recipient_emails]
            )
            hits = _scan_secrets(blob)
            if hits:
                diagnostics.rejected = True
                diagnostics.reasons.extend(f"secret:{h}" for h in hits)
                return SanitiseResult(conversation=None, diagnostics=diagnostics)

    messages: list[CorpusMessage] = []
    for msg in conversation.messages:
        sender = diagnostics.identities[msg.sender_email.strip().lower()]
        recipient_emails: list[str] = []
        recipient_names: list[str] = []
        for i, addr in enumerate(msg.recipient_emails):
            mapped = diagnostics.identities[addr.strip().lower()]
            recipient_emails.append(mapped.email if rewrite_domains else addr)
            if i < len(msg.recipient_names):
                recipient_names.append(
                    mapped.display_name if rewrite_domains else msg.recipient_names[i]
                )
            elif rewrite_domains:
                recipient_names.append(mapped.display_name)
            else:
                recipient_names.append(addr)

        company_index = _stable_int(sender.email) % 1_000
        body = _rewrite_urls(msg.body_text, company_index=company_index)
        subject = _rewrite_urls(msg.subject, company_index=company_index)
        if rewrite_domains:
            body = _rewrite_names_in_body(body, diagnostics.identities)
            subject = _rewrite_names_in_body(subject, diagnostics.identities)

        messages.append(
            msg.model_copy(
                update={
                    "sender_name": sender.display_name if rewrite_domains else msg.sender_name,
                    "sender_email": sender.email if rewrite_domains else msg.sender_email,
                    "recipient_names": recipient_names,
                    "recipient_emails": recipient_emails,
                    "subject": subject,
                    "body_text": body,
                }
            )
        )

    return SanitiseResult(
        conversation=CorpusConversation(id=conversation.id, messages=messages),
        diagnostics=diagnostics,
    )
