"""Corpus sanitiser — Demo-safe rewrite + reject pipeline (ADR-007).

Pipeline: strip generation metadata → secret scan → unexpected-entity scan →
identity/domain rewrite → URL + in-body email rewrite → name rewrite →
zero-tolerance post-scan. Rejected conversations never enter derived indexes
used for public Demo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from personal_enigma.simulation.corpus.models import CorpusConversation, CorpusMessage

SANITISER_VERSION = "2"

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

# Conservative densylist for unexpected real-world entities (fixture + gate).
# Prefer rejection over heroic generalisation when density is high.
_REAL_ENTITY_DENYLIST = frozenset(
    {
        "barack obama",
        "elon musk",
        "taylor swift",
        "jeff bezos",
        "oprah winfrey",
        "angela merkel",
        "volodymyr zelenskyy",
        "google",
        "microsoft",
        "amazon",
        "facebook",
        "instagram",
        "netflix",
        "tesla",
        "spacex",
        "openai",
        "chatgpt",
        "nvidia",
        "walmart",
        "jpmorgan",
        "goldman sachs",
    }
)
# "apple" is matched only as a company token (not fruit / names).
_REAL_ENTITY_COMPANY_TOKENS = frozenset({"apple inc", "apple.com", "wwdc"})

# Reject when this many distinct denylist hits appear in one conversation.
_REAL_ENTITY_DENSITY_THRESHOLD = 3

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_EMAIL_ADDR_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
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


class ImportBoundaryError(ValueError):
    """Zero-tolerance import-boundary gate failure (hard fail, not a soft metric)."""


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
    # Only preserve explicitly known protagonist aliases — never a bare "alex@"
    # prefix match (could be a real-world domain in upstream corpora).
    protagonist = False
    if self_email and email_key == self_email.lower():
        protagonist = True
    elif email_key in preserve_emails or email_key in _PRESERVE_EMAILS:
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


def _scan_unexpected_real_entities(text: str) -> list[str]:
    """Return distinct denylist hits (word-boundary; conservative densylist)."""
    lower = text.lower()
    hits: list[str] = []
    for name in sorted(_REAL_ENTITY_DENYLIST, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", lower):
            hits.append(name)
    for name in sorted(_REAL_ENTITY_COMPANY_TOKENS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", lower):
            hits.append(name)
    # De-dupe while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for hit in hits:
        if hit not in seen:
            seen.add(hit)
            unique.append(hit)
    return unique


def is_reserved_demo_domain(domain: str) -> bool:
    """True for RFC 2606 / .example reserved hosts used by Demo Mode."""
    host = domain.strip().lower().rstrip(".")
    if not host:
        return False
    if host in {"example.com", "example.org", "example.net", "localhost"}:
        return True
    return host.endswith(".example") or host.endswith(".test") or host.endswith(".invalid")


def _url_host(url: str) -> str:
    after_scheme = url.split("://", 1)[-1]
    host_port = after_scheme.split("/", 1)[0]
    host = host_port.split("@")[-1]  # drop userinfo
    host = host.split(":", 1)[0]  # drop port
    return host.strip().lower().rstrip(".")


def find_import_boundary_violations(text: str) -> list[str]:
    """Zero-tolerance scan: real domains, live URLs, secrets, dense real entities."""
    violations: list[str] = []
    for match in _EMAIL_ADDR_RE.finditer(text):
        addr = match.group(0)
        domain = addr.rsplit("@", 1)[-1].lower()
        if not is_reserved_demo_domain(domain):
            violations.append(f"real_domain:{domain}")
    for match in _URL_RE.finditer(text):
        host = _url_host(match.group(0))
        if host and not is_reserved_demo_domain(host):
            violations.append(f"live_url:{host}")
    for label in _scan_secrets(text):
        violations.append(f"secret:{label}")
    entity_hits = _scan_unexpected_real_entities(text)
    if len(entity_hits) >= _REAL_ENTITY_DENSITY_THRESHOLD:
        violations.append(
            "unexpected_real_entity:" + ",".join(entity_hits[:8])
        )
    # De-dupe preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for item in violations:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def assert_import_boundary_clean(conversation: CorpusConversation) -> None:
    """Hard gate: raise if any import-boundary violation remains in output."""
    blobs: list[str] = []
    for msg in conversation.messages:
        blobs.extend(
            [
                msg.subject,
                msg.body_text,
                msg.sender_email,
                msg.sender_name,
                *msg.recipient_emails,
                *msg.recipient_names,
            ]
        )
    violations = find_import_boundary_violations("\n".join(blobs))
    if violations:
        raise ImportBoundaryError(
            f"import boundary violated for {conversation.id!r}: "
            + ", ".join(violations)
        )


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


def _rewrite_emails_in_text(
    text: str,
    *,
    identities: dict[str, IdentityMapping],
    rewrite_seed: str,
    preserve_emails: frozenset[str],
    self_email: str | None,
) -> str:
    """Rewrite every in-body address onto a reserved .example mapping."""

    def _sub(match: re.Match[str]) -> str:
        addr = match.group(0)
        key = addr.strip().lower()
        if key in identities:
            return identities[key].email
        mapping = _identity_for(
            source_email=addr,
            source_name=addr,
            rewrite_seed=rewrite_seed,
            preserve_emails=preserve_emails,
            self_email=self_email,
        )
        identities[key] = mapping
        return mapping.email

    return _EMAIL_ADDR_RE.sub(_sub, text)


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
    reject_real_entities: bool = True,
    preserve_emails: set[str] | frozenset[str] | None = None,
    self_email: str | None = None,
) -> CorpusConversation:
    """Sanitise a conversation; raises ValueError if rejected.

    Prefer :func:`sanitise_conversation_detailed` when rejection diagnostics matter.
    """
    result = sanitise_conversation_detailed(
        conversation,
        rewrite_domains=rewrite_domains,
        rewrite_seed=rewrite_seed,
        reject_secrets=reject_secrets,
        reject_real_entities=reject_real_entities,
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
    reject_real_entities: bool = True,
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

    # Pre-rewrite rejection gates (secrets + dense real entities).
    for msg in conversation.messages:
        blob = "\n".join(
            [msg.subject, msg.body_text, msg.sender_email, *msg.recipient_emails]
        )
        if reject_secrets:
            hits = _scan_secrets(blob)
            if hits:
                diagnostics.rejected = True
                diagnostics.reasons.extend(f"secret:{h}" for h in hits)
                return SanitiseResult(conversation=None, diagnostics=diagnostics)
        if reject_real_entities:
            entities = _scan_unexpected_real_entities(blob)
            if len(entities) >= _REAL_ENTITY_DENSITY_THRESHOLD:
                diagnostics.rejected = True
                diagnostics.reasons.append(
                    "unexpected_real_entity:" + ",".join(entities[:8])
                )
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
        body = msg.body_text
        subject = msg.subject
        if rewrite_domains:
            body = _rewrite_urls(body, company_index=company_index)
            subject = _rewrite_urls(subject, company_index=company_index)
            body = _rewrite_emails_in_text(
                body,
                identities=diagnostics.identities,
                rewrite_seed=rewrite_seed,
                preserve_emails=preserve,
                self_email=self_email,
            )
            subject = _rewrite_emails_in_text(
                subject,
                identities=diagnostics.identities,
                rewrite_seed=rewrite_seed,
                preserve_emails=preserve,
                self_email=self_email,
            )
            body = _rewrite_names_in_body(body, diagnostics.identities)
            subject = _rewrite_names_in_body(subject, diagnostics.identities)
        else:
            # Still rewrite URLs so live hosts never survive even when
            # identity rewrite is disabled for a developer experiment.
            body = _rewrite_urls(body, company_index=company_index)
            subject = _rewrite_urls(subject, company_index=company_index)

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

    cleaned = CorpusConversation(id=conversation.id, messages=messages)

    # Zero-tolerance post-scan: if rewrite missed anything, reject (do not ship).
    if rewrite_domains:
        try:
            assert_import_boundary_clean(cleaned)
        except ImportBoundaryError as exc:
            diagnostics.rejected = True
            diagnostics.reasons.append(f"post_scan:{exc}")
            return SanitiseResult(conversation=None, diagnostics=diagnostics)

    return SanitiseResult(conversation=cleaned, diagnostics=diagnostics)
