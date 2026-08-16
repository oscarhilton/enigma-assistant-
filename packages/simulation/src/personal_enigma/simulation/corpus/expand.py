"""Deterministic mini-corpus expansion for CI-scale acceptance (no HF download)."""

from __future__ import annotations

from collections.abc import Sequence
from hashlib import sha256

from personal_enigma.simulation.corpus.models import CorpusConversation, CorpusMessage


def expand_conversations(
    conversations: Sequence[CorpusConversation],
    *,
    target_count: int,
    seed: str = "mini-expand-v1",
) -> list[CorpusConversation]:
    """Repeat/mutate fixture conversations until ``target_count`` unique threads.

    Used so PR CI can exercise 100-conversation deterministic replay without
    downloading FinePersonas (~115k). Each expanded conversation keeps thread
    integrity; only ids / lightly varied subjects change.
    """
    if target_count <= 0:
        return []
    if not conversations:
        raise ValueError("cannot expand an empty conversation pool")

    base = list(conversations)
    out: list[CorpusConversation] = []
    index = 0
    while len(out) < target_count:
        template = base[index % len(base)]
        replica = index // len(base)
        index += 1
        digest = sha256(f"{seed}:{template.id}:{replica}".encode()).hexdigest()[:10]
        new_id = f"{template.id}-x{replica:04d}-{digest}"
        messages: list[CorpusMessage] = []
        for msg in template.messages:
            subject = msg.subject
            if replica > 0:
                subject = f"{msg.subject} [{replica}]"
            messages.append(
                msg.model_copy(
                    update={
                        "conversation_id": new_id,
                        "subject": subject,
                        "body_text": (
                            msg.body_text
                            if replica == 0
                            else f"{msg.body_text}\n\n(ref {digest})"
                        ),
                    }
                )
            )
        out.append(CorpusConversation(id=new_id, messages=messages))
    return out
