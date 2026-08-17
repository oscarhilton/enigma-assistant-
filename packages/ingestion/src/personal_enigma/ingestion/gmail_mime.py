"""Hostile MIME / HTML boundary for Gmail ingestion (SEC-04).

All email body content is treated as **untrusted** attacker input (SEC-03).
This module parses Gmail API ``payload`` trees — it never executes HTML or
follows URLs. Attachments are metadata-only (lazy-fetch boundary).
"""

from __future__ import annotations

import base64
import re
from collections.abc import Mapping
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

# Gmail API body size guard — truncate hostile oversized payloads locally.
_MAX_BODY_CHARS = 512_000

_STRIP_TAGS = re.compile(r"<[^>]+>")


class _VisibleTextExtractor(HTMLParser):
    """Collect visible text; skip script/style and display:none blocks."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if tag == "div":
            style = _attr_value(attrs, "style") or ""
            if "display:none" in style.replace(" ", "").lower():
                self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "div" and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._chunks.append(data)

    def visible_text(self) -> str:
        return " ".join(self._chunks)


def _attr_value(attrs: list[tuple[str, str | None]], name: str) -> str | None:
    for key, value in attrs:
        if key.lower() == name.lower():
            return value
    return None


def decode_gmail_body_data(data: str | None) -> str | None:
    """Decode Gmail API base64url ``body.data`` to UTF-8 text."""
    if not data:
        return None
    padded = data + "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    return raw.decode("utf-8", errors="replace")


def strip_html_to_text(html: str) -> str:
    """Best-effort visible text extraction — hostile HTML stays untrusted."""
    parser = _VisibleTextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return _STRIP_TAGS.sub(" ", html)
    visible = parser.visible_text()
    if visible.strip():
        return visible
    return _STRIP_TAGS.sub(" ", html)


@dataclass(frozen=True, slots=True)
class GmailAttachmentMetadata:
    """Attachment boundary metadata — body bytes are never fetched here."""

    filename: str | None
    mime_type: str | None
    attachment_id: str | None
    size: int | None
    content_id: str | None
    part_headers: dict[str, str]


@dataclass(frozen=True, slots=True)
class ParsedGmailBody:
    """Parsed hostile MIME tree from a Gmail API payload."""

    plain_text: str | None
    html_text: str | None
    body_text: str | None
    attachments: tuple[GmailAttachmentMetadata, ...] = ()
    mime_type: str | None = None
    untrusted: bool = True
    parse_warnings: tuple[str, ...] = ()
    truncated: bool = False


def _truncate(text: str | None) -> tuple[str | None, bool]:
    if text is None:
        return None, False
    if len(text) <= _MAX_BODY_CHARS:
        return text, False
    return text[:_MAX_BODY_CHARS], True


def _part_headers(part: Mapping[str, Any]) -> dict[str, str]:
    headers = part.get("headers") or []
    out: dict[str, str] = {}
    if isinstance(headers, list):
        for item in headers:
            if isinstance(item, dict):
                name = item.get("name")
                value = item.get("value")
                if isinstance(name, str) and isinstance(value, str):
                    out[name.lower()] = value
    return out


def _collect_parts(
    payload: Mapping[str, Any] | None,
    *,
    plain_parts: list[str],
    html_parts: list[str],
    attachments: list[GmailAttachmentMetadata],
    warnings: list[str],
) -> None:
    if not payload or not isinstance(payload, dict):
        return

    mime = payload.get("mimeType")
    body = payload.get("body") if isinstance(payload.get("body"), dict) else {}
    parts = payload.get("parts") or []

    if isinstance(mime, str) and mime.startswith("multipart/"):
        if isinstance(parts, list):
            for part in parts:
                if isinstance(part, dict):
                    _collect_parts(part, plain_parts=plain_parts, html_parts=html_parts,
                                   attachments=attachments, warnings=warnings)
        return

    filename = payload.get("filename")
    attachment_id = body.get("attachmentId") if isinstance(body, dict) else None
    if filename or attachment_id:
        attachments.append(
            GmailAttachmentMetadata(
                filename=str(filename) if filename else None,
                mime_type=str(mime) if isinstance(mime, str) else None,
                attachment_id=str(attachment_id) if attachment_id else None,
                size=(
                    int(body["size"])
                    if isinstance(body, dict) and body.get("size") is not None
                    else None
                ),
                content_id=_part_headers(payload).get("content-id"),
                part_headers=_part_headers(payload),
            )
        )
        return

    decoded = decode_gmail_body_data(body.get("data") if isinstance(body, dict) else None)
    if decoded is None:
        return

    if mime == "text/plain":
        plain_parts.append(decoded)
    elif mime == "text/html":
        html_parts.append(decoded)
    elif isinstance(mime, str) and mime.startswith("text/"):
        plain_parts.append(decoded)
    else:
        warnings.append(f"unhandled_part_mime:{mime}")


def parse_gmail_payload(payload: Mapping[str, Any] | None) -> ParsedGmailBody:
    """Parse a Gmail API message payload — all extracted text is untrusted."""
    plain_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[GmailAttachmentMetadata] = []
    warnings: list[str] = []

    _collect_parts(
        payload if isinstance(payload, dict) else None,
        plain_parts=plain_parts,
        html_parts=html_parts,
        attachments=attachments,
        warnings=warnings,
    )

    plain_text, plain_trunc = _truncate("\n\n".join(plain_parts) if plain_parts else None)
    html_text, html_trunc = _truncate("\n\n".join(html_parts) if html_parts else None)

    body_text: str | None
    body_trunc = False
    if plain_text:
        body_text = plain_text
    elif html_text:
        body_text, body_trunc = _truncate(strip_html_to_text(html_text))
    else:
        body_text = None

    truncated = plain_trunc or html_trunc or body_trunc

    if truncated:
        warnings.append("body_truncated")

    mime_type = None
    if isinstance(payload, dict) and payload.get("mimeType"):
        mime_type = str(payload.get("mimeType"))

    return ParsedGmailBody(
        plain_text=plain_text,
        html_text=html_text,
        body_text=body_text,
        attachments=tuple(attachments),
        mime_type=mime_type,
        untrusted=True,
        parse_warnings=tuple(warnings),
        truncated=truncated,
    )


__all__ = [
    "GmailAttachmentMetadata",
    "ParsedGmailBody",
    "decode_gmail_body_data",
    "parse_gmail_payload",
    "strip_html_to_text",
]
