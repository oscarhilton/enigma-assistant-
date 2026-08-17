"""Ensure remote provider HTTP is only reachable through the egress gate module."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

SCAN_ROOTS = (
    REPO_ROOT / "apps" / "api" / "src",
    REPO_ROOT / "apps" / "worker" / "src",
    REPO_ROOT / "packages" / "evaluation" / "src",
    REPO_ROOT / "packages" / "reasoning" / "src",
)

EGRESS_GATE_DIR = REPO_ROOT / "packages" / "privacy" / "src" / "personal_enigma" / "privacy" / "egress"

FORBIDDEN_PATTERNS = (
    re.compile(r"request\.urlopen\s*\("),
    re.compile(r"/chat/completions"),
)

ALLOWLIST_FILES = {
    EGRESS_GATE_DIR / "providers" / "openai.py",
    EGRESS_GATE_DIR / "providers" / "fireworks.py",
    REPO_ROOT
    / "packages"
    / "reasoning"
    / "src"
    / "personal_enigma"
    / "reasoning"
    / "fireworks_transport.py",
}


def _iter_py_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [path for path in root.rglob("*.py") if path.is_file()]


def test_no_direct_chat_completions_outside_gate_providers() -> None:
    violations: list[str] = []
    for root in SCAN_ROOTS:
        for path in _iter_py_files(root):
            if path in ALLOWLIST_FILES:
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(text):
                    violations.append(f"{path.relative_to(REPO_ROOT)}: {pattern.pattern}")
    assert violations == [], "Direct provider HTTP found outside egress gate:\n" + "\n".join(
        violations
    )


def test_demo_orchestrator_has_no_direct_provider_http() -> None:
    path = (
        REPO_ROOT
        / "apps"
        / "api"
        / "src"
        / "personal_enigma"
        / "api"
        / "demo_orchestrator.py"
    )
    text = path.read_text(encoding="utf-8")
    assert "urlopen" not in text
    assert "chat/completions" not in text
    assert "FireworksChatTransport" not in text
    assert "OpenAIChatTransport" not in text
