"""Life Scripts — multi-turn episodes of Alex's life as the product test.

Frozen rules (C12):

1. Scripts speak like Alex, never like Enigma internals.
2. Assertions observe public effects + structured boundaries.
3. Model-specific behaviour is replaceable; world truth is not.
4. Not falling back is not the same as understanding.

If Enigma passes the life, the internals are allowed to change.
"""

from personal_enigma.evaluation.life_scripts.runner import (
    EpisodeReport,
    format_episode_transcript,
    format_turn_failure,
    resolve_script_path,
    run_life_script,
)
from personal_enigma.evaluation.life_scripts.schema import (
    LifeScript,
    LifeScriptError,
    load_life_script,
)

__all__ = [
    "EpisodeReport",
    "LifeScript",
    "LifeScriptError",
    "format_episode_transcript",
    "format_turn_failure",
    "load_life_script",
    "resolve_script_path",
    "run_life_script",
]
