"""Attention engine interfaces."""

from personal_enigma.attention.kinds import AttentionKind
from personal_enigma.attention.protocol import AttentionEngine, AttentionItem

__all__ = ["AttentionEngine", "AttentionItem", "AttentionKind"]
