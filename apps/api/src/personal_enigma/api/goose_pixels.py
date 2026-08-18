"""C35 — Goose pixel licence: work presence, C34 expressiveness.

Local SURFACE projection. Never attach to the remote working set.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from personal_enigma.api.relational_bootstrap import RelationalBootstrapBlock

GooseMotion = Literal["absent", "idle", "walk", "return"]
GooseExpressiveness = Literal["restrained", "playful"]
AgentWorkPhase = Literal["in_flight", "waiting", "complete"]
VisibilityLayer = Literal["surface", "inspectable", "forensic"]

_PHASE_MOTION: dict[AgentWorkPhase, GooseMotion] = {
    "in_flight": "walk",
    "waiting": "idle",
    "complete": "return",
}


@dataclass(frozen=True, slots=True)
class AgentWorkSnapshot:
    """Real work already knowable on SURFACE — not a Goose dossier."""

    exists: bool
    phase: AgentWorkPhase | None = None
    semantic_token: str = ""
    inspect_target: str | None = None
    inspect_labels: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GoosePixelLicence:
    motion: GooseMotion
    expressiveness: GooseExpressiveness
    layer: Literal["surface"] = "surface"
    grants_authority: bool = False
    is_evidence: bool = False
    inspect_target: str | None = None
    inspect_labels: tuple[str, ...] = ()
    work_semantic_token: str = ""

    def as_wire(self) -> dict[str, Any]:
        return {
            "kind": "goose_pixel_licence",
            "layer": self.layer,
            "motion": self.motion,
            "expressiveness": self.expressiveness,
            "grants_authority": False,
            "is_evidence": False,
            "inspect_target": self.inspect_target,
            "inspect_labels": list(self.inspect_labels),
            "work_semantic_token": self.work_semantic_token,
        }


def motion_from_work(work: AgentWorkSnapshot | None) -> GooseMotion:
    if work is None or not work.exists or work.phase is None:
        return "absent"
    return _PHASE_MOTION[work.phase]


def expressiveness_from_bootstrap(
    block: RelationalBootstrapBlock | None,
) -> GooseExpressiveness:
    if block is not None and block.culture_palette_available:
        return "playful"
    return "restrained"


def license_goose_pixels(
    *,
    work: AgentWorkSnapshot | None,
    bootstrap: RelationalBootstrapBlock | None,
) -> GoosePixelLicence:
    motion = motion_from_work(work)
    if motion == "absent":
        return GoosePixelLicence(motion="absent", expressiveness="restrained")
    assert work is not None
    return GoosePixelLicence(
        motion=motion,
        expressiveness=expressiveness_from_bootstrap(bootstrap),
        inspect_target=work.inspect_target,
        inspect_labels=work.inspect_labels,
        work_semantic_token=work.semantic_token,
    )


def pixels_allowed_on(layer: VisibilityLayer, licence: GoosePixelLicence) -> bool:
    if layer != "surface":
        return False
    return licence.motion != "absent"


__all__ = [
    "AgentWorkPhase",
    "AgentWorkSnapshot",
    "GoosePixelLicence",
    "expressiveness_from_bootstrap",
    "license_goose_pixels",
    "motion_from_work",
    "pixels_allowed_on",
]
