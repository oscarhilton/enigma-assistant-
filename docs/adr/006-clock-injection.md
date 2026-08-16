# ADR-006: Clock injection for domain time

## Status

Accepted

## Context

Demo Mode advances a fictional timeline independently of wall-clock. Domain decisions that call `datetime.now()` / `date.today()` / `time.time()` bind evaluations to the developer’s machine date and break overdue, decay, and recency behaviour.

## Decision

- Domain logic that affects deadlines, commitments, overdue status, snoozing, memory decay, event recency, attention escalation, context retrieval, or notification timing **must** obtain “now” from an injected `Clock`.
- Provide at least `SystemClock` (Private Mode) and `SimulationClock` (Demo Mode) behind a shared protocol.
- Logging / telemetry may still use wall-clock.
- Owned by D02; Environment from D01 supplies the active clock.

## Consequences

- Searching the codebase for naked `datetime.now()` in domain packages is a D02 acceptance check.
- Scenario replay becomes deterministic for time-dependent behaviour.
