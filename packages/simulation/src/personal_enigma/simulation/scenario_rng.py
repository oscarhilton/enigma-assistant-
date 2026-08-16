"""Seeded RNG primitives for deterministic scenario generation (D3).

Canonical scenarios must never call unseeded randomness. Prefer:

```python
rng = scenario_rng("alex-v1")
```

or ``package.rng()`` after loading a validated package.
"""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from personal_enigma.simulation.scenario import ScenarioPackage


def normalize_scenario_seed(seed: str | int | bytes) -> str | int | bytes:
    """Return a stable seed value suitable for ``random.Random``."""
    if isinstance(seed, (int, bytes)):
        return seed
    text = seed.strip()
    if not text:
        raise ValueError("scenario seed must be non-empty")
    return text


def scenario_rng(seed: str | int | bytes) -> Random:
    """Build a deterministic ``Random`` from an explicit scenario seed.

    Matches the Phase 2 contract ``rng = Random(\"alex-v1\")`` while keeping a
    single entry point for adapters and corpus generators. Callers must pass a
    seed — there is no default, to avoid silently coupling unrelated scenarios.
    """
    return Random(normalize_scenario_seed(seed))


def rng_for_package(package: ScenarioPackage) -> Random:
    """Return the RNG for a loaded package (manifest ``seed`` or scenario id)."""
    return scenario_rng(package.effective_seed)
