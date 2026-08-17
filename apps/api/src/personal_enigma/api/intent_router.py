"""Deterministic natural-language intent resolution for Demo conversation.

Maps normalised utterances to typed intents via keyword/pattern families — no LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ConversationIntentKind(StrEnum):
    ATTENTION_QUERY = "attention_query"
    NEXT_ACTION_QUERY = "next_action_query"
    REJECT_NEXT_ACTION = "reject_next_action"
    ALTERNATE_TASK_QUERY = "alternate_task_query"
    DURATION_QUERY = "duration_query"
    TIME_FIT_QUERY = "time_fit_query"
    CHANGES_QUERY = "changes_query"
    WAITING_ON_QUERY = "waiting_on_query"
    CAN_WAIT_QUERY = "can_wait_query"
    AVAILABILITY_QUERY = "availability_query"
    WHY_QUERY = "why_query"
    HELP_QUERY = "help_query"
    GREETING = "greeting"
    ACKNOWLEDGMENT = "acknowledgment"
    UNSUPPORTED_WORLD_QUERY = "unsupported_world_query"
    CAPABILITIES_QUERY = "capabilities_query"
    UNKNOWN = "unknown"


class TimeExpression(StrEnum):
    TODAY = "today"
    LATER_TODAY = "later_today"
    THIS_AFTERNOON = "this_afternoon"
    THIS_EVENING = "this_evening"
    TOMORROW = "tomorrow"
    AFTER_TOMORROW = "after_tomorrow"
    THIS_WEEK = "this_week"
    NEXT_WEEK = "next_week"
    THIS_WEEKEND = "this_weekend"
    FRIDAY_NIGHT = "friday_night"
    SATURDAY = "saturday"


@dataclass(frozen=True)
class ConversationIntent:
    kind: ConversationIntentKind
    period: TimeExpression | None = None
    requested_count: int | None = None


_ATTENTION_PHRASES = frozenset(
    {
        "what needs me",
        "what needs my attention",
        "what's urgent",
        "whats urgent",
        "what is urgent",
        "what is important",
        "what's important",
        "whats important",
        "what should i focus on",
        "anything important",
        "do i need to deal with anything",
    }
)

_NEXT_ACTION_PHRASES = frozenset(
    {
        "what should i do next",
        "what should i do",
        "what should i do now",
        "what should i do right now",
        "what do i do now",
        "what to do now",
        "what's next",
        "whats next",
        "what do i need to do now",
        "what do i need to do",
        "give me something to do",
        "what should i tackle",
    }
)

_REJECT_NEXT_ACTION_PHRASES = frozenset(
    {
        "nah, i can't be bothered",
        "nah i can't be bothered",
        "can't be bothered",
        "cant be bothered",
    }
)

_ALTERNATE_TASK_PHRASES = frozenset(
    {
        "another task i can do",
        "another task",
    }
)

_DURATION_PHRASES = frozenset(
    {
        "how much time would it take",
        "how much time",
    }
)

_TIME_FIT_PHRASES = frozenset(
    {
        "do i have time",
        "double check",
    }
)

_CHANGED_PHRASES = frozenset(
    {
        "what changed",
        "what's changed",
        "what has changed",
    }
)

_WAITING_PHRASES = frozenset(
    {
        "what am i waiting on",
        "what am i waiting for",
    }
)

_CAN_WAIT_PHRASES = frozenset({"what can wait"})

_HELP_PHRASES = frozenset(
    {
        "can you help me do that",
        "can you help me with that",
        "could you help me do that",
        "could you help me with that",
        "help me do that",
        "help me do this",
        "help me with that",
        "can you do that",
        "could you do that",
    }
)

_GREETINGS = frozenset({"hey", "hi", "hello"})

_URGENT_RE = re.compile(r"\b(what'?s?|whats|what is)\s+urgent\b")
_IMPORTANT_RE = re.compile(r"\b(what'?s?|whats|what is)\s+important\b")
_ANYTHING_IMPORTANT_RE = re.compile(r"\banything\s+important\b")
_DEAL_WITH_ANYTHING_RE = re.compile(r"\bdo i need to deal with anything\b")
_FOCUS_ON_RE = re.compile(r"\bwhat should i focus on\b")

_NEXT_RE = re.compile(r"\bwhat'?s?\s+next\b")
_NEED_TO_DO_RE = re.compile(r"\bwhat do i need to do\b")
_DO_NOW_RE = re.compile(r"\bwhat (should i do|do i do|to do)(?: right)? now\b")
_CANT_BE_BOTHERED_RE = re.compile(r"\b(can't|cant) be bothered\b")
_ANOTHER_TASK_RE = re.compile(r"\banother task(?: i can do)?\b")
_HOW_MUCH_TIME_RE = re.compile(r"\bhow much time(?: would it take)?\b")
_DO_I_HAVE_TIME_RE = re.compile(r"\bdo i have time\b")
_DOUBLE_CHECK_RE = re.compile(r"\bdouble check\b")
_RECENT_EMAIL_RE = re.compile(
    r"\b(?:what'?s?|whats|what is)\s+(?:the\s+)?"
    r"(?:latest|recent)\s+from\s+(?:my\s+)?(?:email|emails|mail)\b"
)
_LATEST_EMAIL_RE = re.compile(
    r"\b(?:latest|recent)\s+(?:from\s+)?(?:my\s+)?(?:email|emails|mail)\b"
)
_SOMETHING_TO_DO_RE = re.compile(r"\bgive me something to do\b")
_SHOULD_TACKLE_RE = re.compile(r"\bwhat should i tackle\b")

_AM_I_FREE_RE = re.compile(r"\bam i free\b")
_AM_I_FEE_TYPO_RE = re.compile(r"\bam i fee\b")
_CAN_I_DO_RE = re.compile(
    r"\bcan i do\b.*\b(friday|saturday|sunday|weekend|night)\b"
)
_SATURDAY_LOOKING_RE = re.compile(r"\bwhat'?s?\s+saturday\s+looking like\b")
_LATER_RE = re.compile(r"\blater(?:\s+today)?\b")
_THIS_AFTERNOON_RE = re.compile(r"\bthis afternoon\b")
_THIS_EVENING_RE = re.compile(r"\bthis evening\b")
_TOMORROW_RE = re.compile(r"\btomorrow\b")
_THIS_WEEKEND_RE = re.compile(r"\bthis weekend\b")
_FRIDAY_NIGHT_RE = re.compile(r"\bfriday night\b")
_SATURDAY_RE = re.compile(r"\bsaturday\b")
_TODAY_AGENDA_RE = re.compile(
    r"\bwhat(?:'s|s| is| do i have)(?:\s+(?:on|for|in my calendar))?\s+today\b"
)
_TODAY_ON_RE = re.compile(r"\bwhat(?:'s|s| is)\s+on\s+today\b")
_TOP_N_COUNT_RE = re.compile(r"\btop\s+(\d+)\b")
_URGENT_TYPO_RE = re.compile(r"\b(what'?s?|whats|what is)\s+ugent\b")
_OH_NO_RE = re.compile(r"^oh no\.?\.?\.?$")
_WEATHER_RE = re.compile(r"\bweather\b")
_CAPABILITIES_RE = re.compile(
    r"\b(?:"
    r"(?:what|whats|what's)\s+(?:can|do)\s+you\s+(?:do|help)|"
    r"what\s+are\s+you\s+(?:able|capable)\s+(?:of|to\s+do)|"
    r"(?:am\s+i|are\s+you)\b.*\brestricted\b|"
    r"restricted\s+to\s+conversations?"
    r")\b"
)
_PRIORITIES_TODAY_RE = re.compile(
    r"\b(?:"
    r"(?:what|whats|what's)\s+(?:are\s+)?(?:the\s+)?(?:top\s+\d+\s+)?things?\s+to\s+(?:get\s+)?done(?:\s+today)?|"
    r"top\s+\d+\s+things?\s+to\s+(?:get\s+)?done(?:\s+today)?|"
    r"(?:priorities|priority)\s+(?:for\s+)?today|"
    r"things?\s+to\s+(?:get\s+)?done\s+today"
    r")\b"
)


def normalize_utterance(text: str) -> str:
    lowered = text.strip().lower()
    for mark in ("\u2019", "\u2018", "`"):
        lowered = lowered.replace(mark, "'")
    collapsed = " ".join(lowered.split())
    collapsed = collapsed.rstrip("?!.,")
    collapsed = collapsed.rstrip("/")
    return collapsed


def _repair_availability_typos(normalized: str) -> str:
    """One-edit typo repair for availability-shaped phrases only — not global rewrite."""
    if _AM_I_FEE_TYPO_RE.search(normalized):
        return _AM_I_FEE_TYPO_RE.sub("am i free", normalized)
    return normalized


def _repair_attention_typos(normalized: str) -> str:
    """One-edit typo repair for attention-shaped phrases only — not global rewrite."""
    if _URGENT_TYPO_RE.search(normalized):
        return _URGENT_TYPO_RE.sub(r"\1 urgent", normalized)
    return normalized


# C05d fence: exact discourse modifiers only — not new phrase families.
_PERIOD_FOLLOW_UPS: dict[str, TimeExpression] = {
    "this week": TimeExpression.THIS_WEEK,
    "tomorrow": TimeExpression.TOMORROW,
    "next week": TimeExpression.NEXT_WEEK,
}

_AFTER_THAT_FOLLOW_UPS = frozenset({"and after that", "after that"})

_PERIOD_COMPOSABLE_KINDS = frozenset(
    {
        ConversationIntentKind.ATTENTION_QUERY,
        ConversationIntentKind.AVAILABILITY_QUERY,
        ConversationIntentKind.NEXT_ACTION_QUERY,
    }
)


def _matches_today_agenda(normalized: str) -> bool:
    return bool(_TODAY_AGENDA_RE.search(normalized) or _TODAY_ON_RE.search(normalized))


def _matches_acknowledgment(normalized: str) -> bool:
    return bool(_OH_NO_RE.match(normalized))


def detect_period_follow_up(text: str) -> TimeExpression | None:
    """Fenced period follow-ups: 'this week?', 'tomorrow?', 'next week?'."""
    return _PERIOD_FOLLOW_UPS.get(normalize_utterance(text))


def is_after_that_follow_up(text: str) -> bool:
    return normalize_utterance(text) in _AFTER_THAT_FOLLOW_UPS


def extract_top_n_count(normalized: str) -> int | None:
    """Parse N from an already-matched top-N attention phrase — not a new family."""
    match = _TOP_N_COUNT_RE.search(normalized)
    if match is None:
        return None
    count = int(match.group(1))
    return count if count > 0 else None


def horizon_after(last: TimeExpression | None) -> TimeExpression:
    """Resolve 'and after that?' against the last horizon."""
    if last == TimeExpression.TOMORROW:
        return TimeExpression.AFTER_TOMORROW
    if last in {
        TimeExpression.THIS_WEEK,
        TimeExpression.THIS_WEEKEND,
        TimeExpression.FRIDAY_NIGHT,
        TimeExpression.SATURDAY,
        TimeExpression.AFTER_TOMORROW,
        TimeExpression.NEXT_WEEK,
    }:
        return TimeExpression.NEXT_WEEK
    return TimeExpression.THIS_WEEK


def _detect_availability_period(normalized: str) -> TimeExpression | None:
    if _matches_today_agenda(normalized):
        return TimeExpression.TODAY
    text = _repair_availability_typos(normalized)
    if _AM_I_FREE_RE.search(text) or _CAN_I_DO_RE.search(text):
        if _LATER_RE.search(text):
            return TimeExpression.LATER_TODAY
        if _THIS_AFTERNOON_RE.search(text):
            return TimeExpression.THIS_AFTERNOON
        if _THIS_EVENING_RE.search(text):
            return TimeExpression.THIS_EVENING
        if _TOMORROW_RE.search(text):
            return TimeExpression.TOMORROW
    if _THIS_WEEKEND_RE.search(text):
        return TimeExpression.THIS_WEEKEND
    if _FRIDAY_NIGHT_RE.search(text):
        return TimeExpression.FRIDAY_NIGHT
    if _SATURDAY_LOOKING_RE.search(text) or _SATURDAY_RE.search(text):
        return TimeExpression.SATURDAY
    if _AM_I_FREE_RE.search(text) or _CAN_I_DO_RE.search(text):
        return TimeExpression.THIS_WEEKEND
    return None


def _matches_availability(normalized: str) -> bool:
    return _detect_availability_period(normalized) is not None


def _matches_unsupported_world(normalized: str) -> bool:
    return bool(_WEATHER_RE.search(normalized))


def _matches_capabilities(normalized: str) -> bool:
    return bool(_CAPABILITIES_RE.search(normalized))


def _matches_attention(normalized: str) -> bool:
    text = _repair_attention_typos(normalized)
    if text in _ATTENTION_PHRASES:
        return True
    return bool(
        _URGENT_RE.search(text)
        or _IMPORTANT_RE.search(text)
        or _ANYTHING_IMPORTANT_RE.search(text)
        or _DEAL_WITH_ANYTHING_RE.search(text)
        or _FOCUS_ON_RE.search(text)
        or _PRIORITIES_TODAY_RE.search(text)
    )


def _attention_intent(normalized: str) -> ConversationIntent:
    count = extract_top_n_count(normalized) if _PRIORITIES_TODAY_RE.search(normalized) else None
    return ConversationIntent(
        kind=ConversationIntentKind.ATTENTION_QUERY,
        requested_count=count,
    )


def _matches_next_action(normalized: str) -> bool:
    if normalized in _NEXT_ACTION_PHRASES:
        return True
    return bool(
        _NEXT_RE.search(normalized)
        or _NEED_TO_DO_RE.search(normalized)
        or _DO_NOW_RE.search(normalized)
        or _SOMETHING_TO_DO_RE.search(normalized)
        or _SHOULD_TACKLE_RE.search(normalized)
    )


def _matches_reject_next_action(normalized: str) -> bool:
    if normalized in _REJECT_NEXT_ACTION_PHRASES:
        return True
    return bool(_CANT_BE_BOTHERED_RE.search(normalized))


def _matches_alternate_task(normalized: str) -> bool:
    if normalized in _ALTERNATE_TASK_PHRASES:
        return True
    return bool(_ANOTHER_TASK_RE.search(normalized))


def _matches_duration(normalized: str) -> bool:
    if normalized in _DURATION_PHRASES:
        return True
    return bool(_HOW_MUCH_TIME_RE.search(normalized))


def _matches_time_fit(normalized: str) -> bool:
    if normalized in _TIME_FIT_PHRASES:
        return True
    return bool(_DO_I_HAVE_TIME_RE.search(normalized) or _DOUBLE_CHECK_RE.search(normalized))


def _matches_recent_email(normalized: str) -> bool:
    return bool(_RECENT_EMAIL_RE.search(normalized) or _LATEST_EMAIL_RE.search(normalized))


def compose_follow_up_intent(
    text: str,
    last_intent: ConversationIntent | None = None,
) -> ConversationIntent:
    """Attach a fenced horizon follow-up to the last intent (C05d).

    Conversation may change the query (intent + horizon). It may not change the truth.
    Unattached follow-ups stay unknown — they are not a new availability family.
    """
    if is_after_that_follow_up(text):
        if last_intent is not None and last_intent.kind in _PERIOD_COMPOSABLE_KINDS:
            return ConversationIntent(
                kind=last_intent.kind,
                period=horizon_after(last_intent.period),
                requested_count=last_intent.requested_count,
            )
        return resolve_intent(text)

    period = detect_period_follow_up(text)
    if period is None:
        return resolve_intent(text)
    if last_intent is not None and last_intent.kind in _PERIOD_COMPOSABLE_KINDS:
        return ConversationIntent(
            kind=last_intent.kind,
            period=period,
            requested_count=last_intent.requested_count,
        )
    return resolve_intent(text)


def resolve_intent(text: str) -> ConversationIntent:
    normalized = normalize_utterance(text)

    if normalized in _GREETINGS:
        return ConversationIntent(kind=ConversationIntentKind.GREETING)

    if _matches_acknowledgment(normalized):
        return ConversationIntent(kind=ConversationIntentKind.ACKNOWLEDGMENT)

    if normalized in _HELP_PHRASES:
        return ConversationIntent(kind=ConversationIntentKind.HELP_QUERY)

    if _matches_recent_email(normalized):
        return ConversationIntent(kind=ConversationIntentKind.ATTENTION_QUERY)

    if _matches_reject_next_action(normalized):
        return ConversationIntent(kind=ConversationIntentKind.REJECT_NEXT_ACTION)

    if _matches_alternate_task(normalized):
        return ConversationIntent(kind=ConversationIntentKind.ALTERNATE_TASK_QUERY)

    if _matches_duration(normalized):
        return ConversationIntent(kind=ConversationIntentKind.DURATION_QUERY)

    if _matches_time_fit(normalized):
        return ConversationIntent(kind=ConversationIntentKind.TIME_FIT_QUERY)

    if _matches_availability(normalized):
        return ConversationIntent(
            kind=ConversationIntentKind.AVAILABILITY_QUERY,
            period=_detect_availability_period(normalized),
        )

    if normalized.startswith("why"):
        return ConversationIntent(kind=ConversationIntentKind.WHY_QUERY)

    if normalized in _CHANGED_PHRASES:
        return ConversationIntent(kind=ConversationIntentKind.CHANGES_QUERY)

    if normalized in _WAITING_PHRASES:
        return ConversationIntent(kind=ConversationIntentKind.WAITING_ON_QUERY)

    if normalized in _CAN_WAIT_PHRASES:
        return ConversationIntent(kind=ConversationIntentKind.CAN_WAIT_QUERY)

    if _matches_next_action(normalized):
        return ConversationIntent(kind=ConversationIntentKind.NEXT_ACTION_QUERY)

    if _matches_attention(normalized):
        return _attention_intent(normalized)

    if _matches_unsupported_world(normalized):
        return ConversationIntent(kind=ConversationIntentKind.UNSUPPORTED_WORLD_QUERY)

    if _matches_capabilities(normalized):
        return ConversationIntent(kind=ConversationIntentKind.CAPABILITIES_QUERY)

    return ConversationIntent(kind=ConversationIntentKind.UNKNOWN)


__all__ = [
    "ConversationIntent",
    "ConversationIntentKind",
    "TimeExpression",
    "compose_follow_up_intent",
    "detect_period_follow_up",
    "extract_top_n_count",
    "horizon_after",
    "is_after_that_follow_up",
    "normalize_utterance",
    "resolve_intent",
]
