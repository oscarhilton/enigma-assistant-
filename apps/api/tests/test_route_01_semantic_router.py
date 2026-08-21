"""ROUTE-01 — cheap semantic router is primary; regex is a degraded-mode oracle.

Shadow success is labelled expected routes + Life Script outcomes, not regex
agreement. Production routing lives in the small LLM (RemoteSemanticBootstrap /
FixtureSemanticBootstrap as test oracle). Do not add English phrase families.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from personal_enigma.api.context_compilation import (
    RequestConstraints,
    RequestInterpretation,
    interpret_request,
    tools_for_interpretation,
)
from personal_enigma.api.conversation_context import ConversationContext
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession
from personal_enigma.api.intent_router import resolve_intent
from personal_enigma.api.semantic_bootstrap import (
    DEFAULT_FIREWORKS_ROUTER_MODEL,
    FixtureSemanticBootstrap,
    RemoteSemanticBootstrap,
    RouteCandidate,
    SemanticInterpretation,
    build_bootstrap_payload,
    build_bootstrap_remote_context,
    build_bootstrap_transformed_context,
    compile_with_bootstrap,
    default_reasoning_model,
    default_router_model,
    interpret_with_router,
    merge_request_interpretation,
    regex_fallback_is_honest,
    selected_route,
    set_semantic_bootstrap,
    utterance_for_router,
)
from personal_enigma.api.turn_kernel import run_private_turn
from personal_enigma.privacy.egress.errors import EgressBlockedError

JAN19 = "cp-2026-01-19T10:00"
_FIXTURE = FixtureSemanticBootstrap()

# Labelled expected routes — Life Script / multilingual paraphrases.
# Regex disagreement is recorded, never the pass criterion.
_LABELLED_CASES: tuple[tuple[str, str], ...] = (
    ("What's on this week?", "agenda"),
    ("Whats on this week?", "agenda"),
    ("anything coming up?", "agenda"),
    ("qué hay esta semana?", "agenda"),
    ("Was steht diese Woche an?", "agenda"),
    ("Qu'est-ce qu'il y a cette semaine?", "agenda"),
    ("Cosa c'è in programma questa settimana?", "agenda"),
    ("What should I do next?", "attention"),
    ("qué debería hacer ahora?", "attention"),
    ("Why is the sky blue?", "general_knowledge"),
    ("por qué el cielo es azul?", "general_knowledge"),
)


class _EmptyCalendarAdapter:
    def list_events(self) -> list[Any]:
        return []


class _DownGate:
    remote_config = type("Cfg", (), {"enabled": True})()
    disclosure_store = None

    def submit(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("provider down")


class _JsonGate:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.remote_config = type("Cfg", (), {"enabled": True})()
        self.disclosure_store = None

    def submit(self, *args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        return type(
            "Egress",
            (),
            {
                "sent": True,
                "response": type("Resp", (), {"text": json.dumps(self.payload)})(),
            },
        )()


def _tool_session() -> DemoToolSession:
    state = project_checkpoint(JAN19).state
    return DemoToolSession(
        state=state,
        context=ConversationContext(),
        checkpoint_id=JAN19,
        prior_state=None,
        at=state.simulated_time,
        conversation=[],
        synthetic_services=SyntheticDemoServices(),
    )


@pytest.fixture
def restore_bootstrap() -> Any:
    set_semantic_bootstrap(None)
    yield
    set_semantic_bootstrap(None)


def test_router_model_is_independent_of_reasoning_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FIREWORKS_ROUTER_MODEL", raising=False)
    monkeypatch.delenv("ENIGMA_ROUTER_MODEL", raising=False)
    monkeypatch.setenv("FIREWORKS_MODEL", "accounts/fireworks/models/gpt-oss-120b")
    assert default_router_model() == DEFAULT_FIREWORKS_ROUTER_MODEL
    assert default_router_model() != default_reasoning_model()
    remote = RemoteSemanticBootstrap()
    assert remote._model == DEFAULT_FIREWORKS_ROUTER_MODEL


def test_router_model_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "FIREWORKS_ROUTER_MODEL",
        "accounts/fireworks/models/qwen2p5-7b-instruct",
    )
    assert default_router_model() == "accounts/fireworks/models/qwen2p5-7b-instruct"
    assert RemoteSemanticBootstrap()._model == "accounts/fireworks/models/qwen2p5-7b-instruct"


def test_ranked_routes_and_abstain_on_fixture() -> None:
    coming = _FIXTURE.interpret("anything coming up?", None)
    assert coming is not None
    assert coming.abstain is False
    assert coming.routes[0] == RouteCandidate("agenda", 0.91)
    chosen = selected_route(coming)
    assert chosen is not None
    assert chosen.area == "agenda"

    abstain = SemanticInterpretation(abstain=True, fallback_reason="unsupported")
    assert selected_route(abstain) is None


def test_scripted_small_llm_returns_ranked_routes() -> None:
    gate = _JsonGate(
        {
            "routes": [
                {"area": "agenda", "confidence": 0.93},
                {"area": "attention", "confidence": 0.41},
            ],
            "evidence_domain": "PRIVATE_WORLD",
            "speech_act": "QUERY",
            "authority": "READ",
            "abstain": False,
            "confidence": 0.93,
        }
    )
    remote = RemoteSemanticBootstrap(gate=gate, model=DEFAULT_FIREWORKS_ROUTER_MODEL)
    parsed = remote.interpret("qué hay esta semana?", None)
    assert parsed is not None
    assert parsed.model_id == DEFAULT_FIREWORKS_ROUTER_MODEL
    assert parsed.latency_ms is not None
    assert parsed.abstain is False
    assert [row.area for row in parsed.routes] == ["agenda", "attention"]
    assert parsed.routes[0].confidence == 0.93


def test_confidence_never_grants_authority() -> None:
    session = _tool_session()
    det = interpret_request("anything coming up?", session)
    rogue = SemanticInterpretation(
        evidence_domain="PRIVATE_WORLD",
        authority="APPROVE",
        routes=(
            RouteCandidate("agenda", 0.99),
            RouteCandidate("assist", 0.98),
        ),
        candidate_families=("agenda", "assist"),
        confidence=0.99,
    )
    merged = merge_request_interpretation("anything coming up?", det, rogue, None)
    assert merged.evidence_domain == "PRIVATE_WORLD"
    assert merged.authority == "READ"
    assert "assist.approve" not in tools_for_interpretation(merged)


def test_ranked_routes_minimise_tool_surface() -> None:
    session = _tool_session()
    compiled = compile_with_bootstrap("anything coming up?", session, _FIXTURE)
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.authority == "READ"
    assert compiled.tool_names == ["agenda.get"]
    assert "assist.approve" not in compiled.tool_names
    assert "next_action.reject" not in compiled.tool_names


def test_shadow_labelled_routes_not_regex_agreement() -> None:
    """Semantic must match labelled expected area. Regex mismatch is informative."""
    session = _tool_session()
    disagreements: list[str] = []
    for utterance, expected in _LABELLED_CASES:
        semantic = _FIXTURE.interpret(utterance, None)
        assert semantic is not None, utterance
        chosen = selected_route(semantic)
        assert chosen is not None, f"semantic abstained on labelled {utterance!r}"
        assert chosen.area == expected, f"{utterance!r}: {chosen.area} != {expected}"
        regex_kind = resolve_intent(utterance).kind.value
        if regex_kind not in {expected, "unknown"} and expected not in regex_kind:
            disagreements.append(f"{utterance!r}: regex={regex_kind} labelled={expected}")
    # Disagreement is not failure — it proves regex is not ground truth.
    del session
    assert isinstance(disagreements, list)


def test_life_script_week_and_next_work_outcomes() -> None:
    session = _tool_session()
    week = compile_with_bootstrap("Whats on this week?", session, _FIXTURE)
    assert week.evidence_domain == "PRIVATE_WORLD"
    assert "agenda.get" in week.tool_names
    assert week.authority != "APPROVE"

    next_work = compile_with_bootstrap("What should I do next?", session, _FIXTURE)
    assert next_work.evidence_domain == "PRIVATE_WORLD"
    assert (
        "attention.get_current" in next_work.tool_names
        or "next_action.get" in next_work.tool_names
    )
    assert "assist.approve" not in next_work.tool_names


def test_multilingual_paraphrases_route_via_small_llm_not_regex() -> None:
    session = _tool_session()
    spanish = "qué hay esta semana?"
    assert resolve_intent(spanish).kind.value == "unknown"
    compiled = compile_with_bootstrap(spanish, session, _FIXTURE)
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert "agenda.get" in compiled.tool_names

    german = "Was steht diese Woche an?"
    compiled_de = compile_with_bootstrap(german, session, _FIXTURE)
    assert compiled_de.evidence_domain == "PRIVATE_WORLD"
    assert "agenda.get" in compiled_de.tool_names


def test_provider_down_non_english_abstains_instead_of_english_regex() -> None:
    remote = RemoteSemanticBootstrap(gate=_DownGate(), model=DEFAULT_FIREWORKS_ROUTER_MODEL)
    parsed = remote.interpret("¿Qué hay esta semana?", None)
    assert parsed is not None
    assert parsed.abstain is True
    assert parsed.fallback_reason is not None
    assert "provider_down" in parsed.fallback_reason
    assert parsed.model_id == DEFAULT_FIREWORKS_ROUTER_MODEL

    session = _tool_session()
    merged = merge_request_interpretation(
        "¿Qué hay esta semana?",
        interpret_request("¿Qué hay esta semana?", session),
        parsed,
        None,
    )
    assert merged.evidence_domain == "CONVERSATION_ONLY"
    assert merged.capability_families == ()
    assert merged.authority == "NONE"


def test_provider_down_english_regex_may_cover_honestly() -> None:
    remote = RemoteSemanticBootstrap(gate=_DownGate())
    parsed = remote.interpret("What's on today?", None)
    assert parsed is not None
    assert parsed.abstain is False
    assert parsed.fallback_reason == "provider_down"
    assert regex_fallback_is_honest("What's on today?") is True

    session = _tool_session()
    decision = interpret_with_router("What's on today?", session, bootstrap=None)
    assert decision.interpretation.evidence_domain == "PRIVATE_WORLD"
    assert "agenda" in decision.interpretation.capability_families


def test_routing_trace_fields_on_compile() -> None:
    session = _tool_session()
    decision = interpret_with_router("anything coming up?", session, _FIXTURE)
    trace = decision.trace
    assert trace["candidates"]
    assert trace["selected"] == "agenda"
    assert trace["selected_confidence"] == 0.91
    assert trace["abstain"] is False
    assert trace["primary"] == "semantic"
    assert "fallback_reason" in trace


def test_private_kernel_uses_semantic_router(
    restore_bootstrap: None,
) -> None:
    set_semantic_bootstrap(_FIXTURE)
    conversation: list[dict[str, Any]] = []
    result = run_private_turn(
        text="anything coming up?",
        at="2026-08-18T10:00:00Z",
        adapter=_EmptyCalendarAdapter(),
        conversation=conversation,
        context=ConversationContext(),
    )
    executed = result.llm_trace["executed_tool_request"]
    assert executed and executed[0]["name"] == "briefing.read"
    routing = result.llm_trace.get("routing")
    assert routing is not None
    assert routing["selected"] == "agenda"
    assert routing["primary"] == "semantic"
    assert routing["candidates"]


def test_private_kernel_outage_non_english_abstains(
    restore_bootstrap: None,
) -> None:
    set_semantic_bootstrap(RemoteSemanticBootstrap(gate=_DownGate()))
    conversation: list[dict[str, Any]] = []
    result = run_private_turn(
        text="¿Qué hay esta semana?",
        at="2026-08-18T10:00:00Z",
        adapter=_EmptyCalendarAdapter(),
        conversation=conversation,
        context=ConversationContext(),
    )
    assert result.llm_trace["executed_tool_request"] == []
    routing = result.llm_trace.get("routing")
    assert routing is not None
    assert routing["abstain"] is True
    assert routing["fallback_reason"]
    assert "unsupported" in str(routing["fallback_reason"])


def test_force_regex_router_skips_semantic(
    monkeypatch: pytest.MonkeyPatch,
    restore_bootstrap: None,
) -> None:
    monkeypatch.setenv("ENIGMA_FORCE_REGEX_ROUTER", "1")
    from personal_enigma.api.semantic_bootstrap import get_semantic_bootstrap

    set_semantic_bootstrap(None)
    assert get_semantic_bootstrap() is None
    session = _tool_session()
    decision = interpret_with_router("What's on today?", session, bootstrap=None)
    assert decision.trace["primary"] in {"regex_degraded", "abstain"}
    assert decision.interpretation.evidence_domain == "PRIVATE_WORLD"


def test_route_minimised_keeps_source_tools_when_source_constraint() -> None:
    interp = RequestInterpretation(
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
        profile="PRIVATE_QUERY",
        speech_act="QUESTION",
        constraints=RequestConstraints(source="email"),
        capability_families=("agenda",),
        request_kind="important_from_source",
        frame_inherited=False,
        route_minimised=True,
    )
    tools = tools_for_interpretation(interp)
    assert "source.recent" in tools
    assert "source.quote" in tools
    assert "attention.get_current" in tools


def test_provider_down_trace_reports_regex_degraded_primary() -> None:
    session = _tool_session()
    remote = RemoteSemanticBootstrap(gate=_DownGate())
    decision = interpret_with_router("What's on today?", session, bootstrap=remote)
    assert decision.trace["primary"] == "regex_degraded"
    assert decision.trace["fallback_reason"] == "provider_down"
    assert decision.interpretation.evidence_domain == "PRIVATE_WORLD"


def test_contraction_possessive_folds_but_identity_does_not() -> None:
    assert utterance_for_router("What's on today?") == "what's on today?"
    assert utterance_for_router("It's raining") == "it's raining"
    assert utterance_for_router("Sarah's birthday is tomorrow") == (
        "Sarah's birthday is tomorrow"
    )


def test_router_prompt_is_sanitised_payload_not_original_utterance() -> None:
    payload = build_bootstrap_payload("What's on today?", None)
    assert payload["utterance"] == "what's on today?"
    assert "What's" not in json.dumps(payload)

    ctx = build_bootstrap_remote_context(
        "What's on today?",
        None,
        model=DEFAULT_FIREWORKS_ROUTER_MODEL,
    )
    assert ctx.prompt == json.dumps(payload, default=str)
    assert "What's" not in ctx.prompt
    assert "What's" not in json.dumps(ctx.wire_body)


def test_identity_possessive_stays_blocked_and_never_submits() -> None:
    identity = "Sarah's birthday is tomorrow"
    with pytest.raises(EgressBlockedError):
        build_bootstrap_transformed_context(identity, None)

    gate = _JsonGate(
        {
            "routes": [{"area": "agenda", "confidence": 0.9}],
            "evidence_domain": "PRIVATE_WORLD",
            "abstain": False,
            "confidence": 0.9,
        }
    )
    submitted: list[Any] = []
    original_submit = gate.submit

    def _capture(*args: Any, **kwargs: Any) -> Any:
        submitted.append((args, kwargs))
        return original_submit(*args, **kwargs)

    gate.submit = _capture  # type: ignore[method-assign]
    parsed = RemoteSemanticBootstrap(
        gate=gate, model=DEFAULT_FIREWORKS_ROUTER_MODEL
    ).interpret(identity, None)
    assert submitted == []
    assert parsed is not None
    assert parsed.fallback_reason is not None
    assert "provider_down" in parsed.fallback_reason
