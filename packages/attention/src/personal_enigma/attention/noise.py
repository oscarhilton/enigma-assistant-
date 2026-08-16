"""Pragmatic first-cut machine / newsletter / marketing heuristics.

Full MESSAGE_ORIGIN taxonomy is ticketed separately; these patterns catch the
wind-tunnel failures (PrizeVault, Design Weekly, RouteFox, BuildCloud, etc.).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from personal_enigma.domain import PrivateMessage

# Fictional brands aligned with D08d noise templates + live dump offenders.
_BRAND_TOKENS: frozenset[str] = frozenset(
    {
        "prizevault",
        "luckyclick",
        "offerriver",
        "designledger",
        "stackbrief",
        "productpulse",
        "design weekly",
        "cartnest",
        "shopharbor",
        "invoicebee",
        "buildcloud",
        "deployhive",
        "syncforge",
        "cloudboost",
        "growthkit",
        "promonest",
        "accountguard",
        "safekey",
        "loginshield",
        "parcelpost",
        "routefox",
        "boxtrail",
        "meetslot",
        "calconfirm",
        "slotkeeper",
    }
)

_MACHINE_LOCAL_PARTS: frozenset[str] = frozenset(
    {
        "noreply",
        "no-reply",
        "news",
        "newsletter",
        "receipts",
        "hello",
        "accounts",
        "shipments",
        "calendar",
        "wins",
        "marketing",
        "promo",
        "notifications",
        "notify",
        "updates",
        "digest",
    }
)

_SUBJECT_NOISE_TOKENS: tuple[str, ...] = (
    "receipt",
    "out for delivery",
    "% off",
    "security notice",
    "build #",
    "claim your",
    "unsubscribe",
    "weekly #",
    "confirmed:",
    "your package",
    "shipped",
    "tracking",
    "newsletter",
    "digest",
)


def _message_fields(
    message: PrivateMessage | Mapping[str, Any],
) -> tuple[str, str, str, str]:
    if isinstance(message, PrivateMessage):
        sender = (message.from_person.email if message.from_person else None) or ""
        subject = message.subject or ""
        body = message.body_text or message.snippet or ""
        from_name = (message.from_person.display_name if message.from_person else None) or ""
    else:
        sender = str(message.get("from") or message.get("from_email") or "")
        subject = str(message.get("subject") or "")
        body = str(message.get("body_text") or message.get("snippet") or "")
        from_name = str(message.get("from_name") or "")
    return sender, subject, body, from_name


def looks_like_machine_noise(message: PrivateMessage | Mapping[str, Any]) -> bool:
    """True for clear automation / marketing / junk shapes — never commitments."""
    sender, subject, body, from_name = _message_fields(message)
    sender_l = sender.lower()
    subject_l = subject.lower()
    blob = f"{subject_l}\n{body.lower()}\n{from_name.lower()}"

    local = sender_l.split("@", 1)[0] if "@" in sender_l else sender_l
    if local in _MACHINE_LOCAL_PARTS:
        return True
    if any(token in blob for token in _BRAND_TOKENS):
        return True
    if any(token in subject_l for token in _SUBJECT_NOISE_TOKENS):
        return True
    return False


def looks_like_newsletter(message: PrivateMessage | Mapping[str, Any]) -> bool:
    """Narrower newsletter/digest detector used by F-newsletter fixtures."""
    _, subject, body, from_name = _message_fields(message)
    blob = f"{subject}\n{body}\n{from_name}".lower()
    return any(
        token in blob
        for token in (
            "newsletter",
            "weekly digest",
            "unsubscribe",
            "design weekly",
            "this week in",
        )
    )


def looks_like_package_notification(message: PrivateMessage | Mapping[str, Any]) -> bool:
    """Delivery / shipping automation — not an INFERRED_COMMITMENT."""
    _, subject, body, _ = _message_fields(message)
    blob = f"{subject}\n{body}".lower()
    return any(
        token in blob
        for token in (
            "out for delivery",
            "your package",
            "shipped",
            "tracking number",
            "routefox",
            "parcelpost",
            "boxtrail",
        )
    )
