"""P02b–e — constitutional slices against Demo truth the pilot shell must reflect."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.api.demo_assist import (
    AssistPlan,
    SyntheticDemoServices,
    execute_and_verify,
    overlay_session_world,
)
from personal_enigma.api.demo_attestation import apply_user_attestation
from personal_enigma.api.relational_bootstrap import (
    RelationalBootstrapInputs,
    compile_relational_bootstrap,
    continuation_forbidden_phrases,
    participates_in_register,
)
from personal_enigma.attention.projection import AttentionState, build_presentation_plan

MONDAY_CHECKPOINT = "cp-2026-01-19T10:00"
MAYA_BIRTHDAY_ID = "item-context_maya_birthday"
GOOSE_CONVENTION = (
    "When the user honks, answer with short goose energy. No meta commentary."
)


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.setenv("LLM_DISABLED", "1")
    monkeypatch.delenv("ENIGMA_PRIVATE_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("ENIGMA_DEMO_STORAGE_ROOT", raising=False)
    return TestClient(create_app())


def test_p02b_monday_projection_keeps_maya_birthday_in_context_not_needs_you(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    assert client.post("/worlds/switch", json={"world": "alex_lab"}).status_code == 200
    assert client.post(f"/demo/timeline/checkpoint/{MONDAY_CHECKPOINT}").status_code == 200

    attention = client.get("/demo/attention/state").json()
    needs_ids = {row["id"] for row in attention["needs_you"]}
    context_titles = {row["title"] for row in attention["context"]}
    assert MAYA_BIRTHDAY_ID not in needs_ids
    assert attention["presentation"]["chat_opening_count"] == 0
    assert "Book Saturday brunch" not in " ".join(context_titles).lower()


def test_p02c_honk_honk_bootstrap_participates_without_meta_inference() -> None:
    block = compile_relational_bootstrap(
        RelationalBootstrapInputs(
            shared_conventions=(GOOSE_CONVENTION,),
            ephemeral_register="goose",
            exemplars=("honk", "honk honk"),
        )
    )
    assert block is not None
    ok = "honk honk — got it."
    assert participates_in_register(ok, "goose") or "honk" in ok.casefold()
    assert continuation_forbidden_phrases(ok) == ()
    assert continuation_forbidden_phrases("Sounds like you're feeling playful!") != ()


def test_p02d_verification_failure_is_not_claimed_success() -> None:
    plan = AssistPlan(
        proposal_id="assist-notify-team",
        title="Send the team note",
        description="Synthetic demo note",
        action_label="Approve",
        source_item_id="item-notify-team",
        action_kind="synthetic_note",
    )
    ok, message = execute_and_verify(plan, SyntheticDemoServices(fail_writes=True))
    assert ok is False
    assert "couldn't verify" in message.casefold()
    assert "done —" not in message.casefold()


def test_p02e_attestation_cancel_removes_item_from_live_attention_overlay() -> None:
    state = AttentionState.model_validate(
        {
            "simulated_time": "2026-01-19T10:00:00+00:00",
            "checkpoint_id": MONDAY_CHECKPOINT,
            "needs_you": [],
            "context": [
                {
                    "id": MAYA_BIRTHDAY_ID,
                    "title": "Sort something for Maya's birthday",
                    "explanation": "Open loop",
                    "policy_decision": "context",
                    "bucket": "context",
                    "rank": 1,
                    "composite_score": 0.5,
                    "actionability_now": 0.5,
                    "reasons": [],
                    "evidence_ids": ["mail-maya-birthday"],
                }
            ],
            "next_actions": [],
            "can_wait_summary": None,
            "presentation": build_presentation_plan(0).model_dump(mode="json"),
        }
    )
    completed: set[str] = set()
    advances = {}
    apply_user_attestation(
        attestations=[],
        completed_item_ids=completed,
        advances=advances,
        target_id=MAYA_BIRTHDAY_ID,
        state="CANCELLED",
        at="2026-01-19T10:05:00+00:00",
        utterance="Forget that.",
    )
    overlaid = overlay_session_world(state, completed, advances)
    assert all(row.id != MAYA_BIRTHDAY_ID for row in (*overlaid.needs_you, *overlaid.context))
