"""Build terminal report-back handoffs from Cursor run payloads (CLOUD-04)."""

from __future__ import annotations

from typing import Any

from personal_enigma.cursor_relay.create_contract import PENDING_BRANCH
from personal_enigma.cursor_relay.cursor_client import CursorApiError, CursorClient
from personal_enigma.cursor_relay.handoff import success_handoff_for_tool
from personal_enigma.cursor_relay.result_store import (
    TERMINAL_RUN_STATUSES,
    ResultStore,
    TerminalRunSnapshot,
)


def is_terminal_status(status: str | None) -> bool:
    return str(status or "").upper() in TERMINAL_RUN_STATUSES


def _git_entries(run: dict[str, Any]) -> list[dict[str, Any]]:
    git = run.get("git") or {}
    branches = git.get("branches") or []
    if isinstance(branches, list):
        return [b for b in branches if isinstance(b, dict)]
    return []


def _pr_number(url: str | None) -> int:
    if not url:
        return 0
    try:
        return int(str(url).rstrip("/").split("/")[-1])
    except ValueError:
        return 0


def extract_git_metadata(run: dict[str, Any]) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    branches: list[str] = []
    pr_urls: list[str] = []
    raw_entries: list[dict[str, Any]] = []
    for entry in _git_entries(run):
        raw_entries.append(entry)
        branch = entry.get("branch")
        if branch:
            branches.append(str(branch))
        pr_url = entry.get("prUrl")
        if pr_url:
            pr_urls.append(str(pr_url))
    return branches, pr_urls, raw_entries


def snapshot_from_get_run(
    *,
    agent_id: str,
    run_id: str,
    run: dict[str, Any],
    source: str = "get_run",
) -> TerminalRunSnapshot:
    status = str(run.get("status") or "UNKNOWN").upper()
    branches, pr_urls, raw_git = extract_git_metadata(run)
    stream_error = None
    if status == "ERROR":
        err = run.get("error")
        if isinstance(err, dict):
            code = str(err.get("code") or "run_error")
            message = str(err.get("message") or "Run failed")
            stream_error = {"code": code, "message": message}
    return TerminalRunSnapshot(
        agent_id=agent_id,
        run_id=run_id,
        run_status=status,
        final_result=run.get("result") if isinstance(run.get("result"), str) else None,
        duration_ms=run.get("durationMs") if isinstance(run.get("durationMs"), int) else None,
        git_branches=branches,
        pr_urls=pr_urls,
        result_source=source,
        stream_error=stream_error,
        raw_git=raw_git,
    )


def snapshot_from_stream_result(
    *,
    agent_id: str,
    run_id: str,
    payload: dict[str, Any],
    stream_error: dict[str, str] | None = None,
) -> TerminalRunSnapshot:
    status = str(payload.get("status") or "UNKNOWN").upper()
    git_wrapper = {"git": payload.get("git") or {}}
    branches, pr_urls, raw_git = extract_git_metadata(git_wrapper)
    text = payload.get("text")
    final_result = str(text) if isinstance(text, str) and text else None
    duration = payload.get("durationMs")
    duration_ms = duration if isinstance(duration, int) else None
    return TerminalRunSnapshot(
        agent_id=agent_id,
        run_id=run_id,
        run_status=status,
        final_result=final_result,
        duration_ms=duration_ms,
        git_branches=branches,
        pr_urls=pr_urls,
        result_source="stream",
        stream_error=stream_error,
        raw_git=raw_git,
    )


def build_result_handoff(
    *,
    snapshot: TerminalRunSnapshot | None,
    agent_id: str,
    run_id: str,
    ticket_ids: list[str],
    run_status: str,
    terminal: bool,
    pending: bool = False,
) -> dict[str, Any]:
    branches = snapshot.git_branches if snapshot else []
    pr_entries: list[dict[str, Any]] = []
    if snapshot:
        for entry in snapshot.raw_git:
            pr_url = entry.get("prUrl")
            if pr_url:
                pr_entries.append(
                    {
                        "number": _pr_number(str(pr_url)),
                        "base": "main",
                        "head": str(entry.get("branch") or ""),
                    }
                )

    actual_head = branches[0] if branches else None
    head = str(actual_head or PENDING_BRANCH)

    if terminal and snapshot is not None:
        summary = (
            f"Terminal run {run_id} status={snapshot.run_status}"
            + (f" ({snapshot.duration_ms}ms)" if snapshot.duration_ms is not None else "")
        )
        extra: dict[str, Any] = {
            "run_status": snapshot.run_status,
            "terminal": True,
            "duration_ms": snapshot.duration_ms,
            "final_result": snapshot.final_result,
            "git_branches": snapshot.git_branches,
            "pr_urls": snapshot.pr_urls,
            "result_source": snapshot.result_source,
        }
        if snapshot.stream_error:
            extra["stream_error"] = snapshot.stream_error
        evidence = [
            {
                "kind": "note",
                "summary": snapshot.final_result or summary,
                "ref": agent_id,
            }
        ]
        handoff = success_handoff_for_tool(
            tool="result",
            agent_id=agent_id,
            run_id=run_id,
            branch=head,
            ticket_ids=ticket_ids,
            summary=summary,
            action_kind="no_action",
            open_prs=pr_entries,
            extra_observed=extra,
        )
        handoff["evidence"] = evidence
        return handoff

    status_upper = str(run_status or "UNKNOWN").upper()
    summary = (
        f"Run {run_id} not terminal yet (status={status_upper})"
        if not pending
        else f"Run {run_id} terminal result pending (status={status_upper})"
    )
    extra_pending: dict[str, Any] = {
        "run_status": status_upper,
        "terminal": False,
        "duration_ms": None,
        "final_result": None,
        "git_branches": branches,
        "pr_urls": [],
        "result_source": None,
    }
    handoff = success_handoff_for_tool(
        tool="result",
        agent_id=agent_id,
        run_id=run_id,
        branch=head,
        ticket_ids=ticket_ids,
        summary=summary,
        action_kind="no_action",
        open_prs=pr_entries,
        extra_observed=extra_pending,
    )
    # Replace default evidence for non-terminal path.
    handoff["evidence"] = [{"kind": "note", "summary": summary, "ref": agent_id}]
    return handoff


def _merge_snapshots(
    *,
    agent_id: str,
    run_id: str,
    stream_snapshot: TerminalRunSnapshot,
    get_snapshot: TerminalRunSnapshot,
) -> TerminalRunSnapshot:
    return TerminalRunSnapshot(
        agent_id=agent_id,
        run_id=run_id,
        run_status=stream_snapshot.run_status or get_snapshot.run_status,
        final_result=stream_snapshot.final_result or get_snapshot.final_result,
        duration_ms=(
            stream_snapshot.duration_ms
            if stream_snapshot.duration_ms is not None
            else get_snapshot.duration_ms
        ),
        git_branches=stream_snapshot.git_branches or get_snapshot.git_branches,
        pr_urls=stream_snapshot.pr_urls or get_snapshot.pr_urls,
        result_source="stream",
        stream_error=stream_snapshot.stream_error or get_snapshot.stream_error,
        raw_git=stream_snapshot.raw_git or get_snapshot.raw_git,
    )


def resolve_terminal_snapshot(
    *,
    cursor: CursorClient,
    result_store: ResultStore,
    agent_id: str,
    run_id: str,
) -> tuple[TerminalRunSnapshot | None, str, bool]:
    """Resolve a terminal snapshot via cache, GET run, and optional SSE stream."""

    cached = result_store.get(agent_id, run_id)
    if cached is not None:
        cached = TerminalRunSnapshot.from_dict({**cached.to_dict(), "result_source": "cache"})
        return cached, cached.run_status, True

    run = cursor.get_run(agent_id, run_id)
    run_status = str(run.get("status") or "UNKNOWN").upper()
    if not is_terminal_status(run_status):
        return None, run_status, False

    get_snapshot = snapshot_from_get_run(agent_id=agent_id, run_id=run_id, run=run)
    stream_snapshot: TerminalRunSnapshot | None = None
    try:
        stream_outcome = cursor.stream_run(agent_id, run_id)
        stream_snapshot = snapshot_from_stream_result(
            agent_id=agent_id,
            run_id=run_id,
            payload={
                "status": stream_outcome.status,
                "text": stream_outcome.text,
                "durationMs": stream_outcome.duration_ms,
                "git": stream_outcome.git,
            },
            stream_error=stream_outcome.stream_error,
        )
    except CursorApiError as exc:
        if exc.code not in {"stream_expired", "stream_no_terminal"}:
            raise

    if stream_snapshot is not None:
        merged = _merge_snapshots(
            agent_id=agent_id,
            run_id=run_id,
            stream_snapshot=stream_snapshot,
            get_snapshot=get_snapshot,
        )
        result_store.put(merged)
        return merged, merged.run_status, True

    result_store.put(get_snapshot)
    return get_snapshot, get_snapshot.run_status, True
