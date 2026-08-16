from personal_enigma.attention import AttentionItem, AttentionKind


def test_attention_kinds() -> None:
    assert AttentionKind.EXPLICIT_REMINDER == "explicit_reminder"
    assert AttentionKind.INFERRED_COMMITMENT == "inferred_commitment"
    assert AttentionKind.PENDING_REPLY == "pending_reply"


def test_attention_item_smoke() -> None:
    item = AttentionItem(
        title="Review proposal",
        body="Due Friday; already in Reminders.",
        kind=AttentionKind.EXPLICIT_REMINDER,
    )
    assert item.score == 0.0
    assert item.priority == 0
