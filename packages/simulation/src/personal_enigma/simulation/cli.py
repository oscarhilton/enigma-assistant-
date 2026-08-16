"""CLI: ``enigma corpus …`` (argparse under packages/simulation).

Never downloads FinePersonas 115k in CI — network fetch requires ``--force-network``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from personal_enigma.simulation.corpus.adapters.finepersonas import (
    DEFAULT_HF_DATASET,
    fetch_huggingface,
    materialise_local_fixture,
)
from personal_enigma.simulation.corpus.cache import CorpusCache, DerivedCorpusCache
from personal_enigma.simulation.corpus.pipeline import (
    build_demo_safe_corpus,
    collect_conversations,
)
from personal_enigma.simulation.corpus.registry import default_registry
from personal_enigma.simulation.corpus.safety import (
    PublicDemoCorpusError,
    assert_public_demo_allowed,
)
from personal_enigma.simulation.corpus.sanitise import (
    SANITISER_VERSION,
    sanitise_conversation_detailed,
)
from personal_enigma.simulation.corpus.selectors import select_conversations


async def _collect(corpus_id: str) -> list:
    registry = default_registry()
    adapter = registry.adapter_for(corpus_id)
    return await collect_conversations(adapter)


def cmd_list(_args: argparse.Namespace) -> int:
    registry = default_registry()
    for corpus_id in registry.list_ids():
        manifest = registry.get(corpus_id)
        print(
            f"{corpus_id}\t{manifest.provenance.value}\tadapter={manifest.format_adapter}"
        )
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    """Materialise corpus into local cache; HF download only with --force-network."""
    registry = default_registry()
    manifest = registry.get(args.corpus_id)
    revision = args.revision or manifest.source.revision or "unspecified"
    cache = CorpusCache(root=Path(args.cache_root) if args.cache_root else None)
    target = cache.ensure_revision_dir(args.corpus_id, revision)

    if args.force_network:
        dataset = (
            args.dataset
            or manifest.source.dataset
            or DEFAULT_HF_DATASET
        )
        print(
            f"fetching Hugging Face dataset {dataset!r} revision={revision!r} → {target}",
            file=sys.stderr,
        )
        fetch_huggingface(
            dataset=dataset,
            revision=revision,
            target_root=target,
            max_conversations=args.max_conversations,
        )
        print(f"ok: wrote {target / 'conversations.jsonl'}")
        return 0

    # Local path: copy fixture / existing tree into cache (CI-safe).
    source = Path(args.from_path) if args.from_path else None
    if source is None:
        # Default: registry root for known corpora (e.g. finepersonas-mini).
        try:
            adapter = registry.adapter_for(args.corpus_id)
            source = getattr(adapter, "root", None)
        except KeyError:
            source = None
    if source is None or not Path(source).exists():
        print(
            "fetch: no local source. Pass --from-path PATH, or use "
            "--force-network for Hugging Face (never in CI).\n"
            f"Expected cache layout: {target}",
            file=sys.stderr,
        )
        return 2

    materialise_local_fixture(source_root=Path(source), target_root=target)
    print(f"ok: materialised {source} → {target}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    registry = default_registry()
    adapter = registry.adapter_for(args.corpus_id)

    async def _run() -> None:
        meta = await adapter.inspect()
        print(meta.model_dump_json(indent=2))

    asyncio.run(_run())
    return 0


def cmd_sanitise(args: argparse.Namespace) -> int:
    conversations = asyncio.run(_collect(args.corpus_id))
    accepted = 0
    rejected = 0
    for conv in conversations:
        result = sanitise_conversation_detailed(conv, rewrite_seed=args.seed)
        if result.conversation is None:
            rejected += 1
            if args.include_rejected:
                print(
                    json.dumps(
                        {"id": conv.id, "rejected": True, "reasons": result.diagnostics.reasons}
                    )
                )
            continue
        accepted += 1
        print(result.conversation.model_dump_json())
    print(
        f"# sanitiser={SANITISER_VERSION} accepted={accepted} rejected={rejected}",
        file=sys.stderr,
    )
    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    conversations = asyncio.run(_collect(args.corpus_id))
    selected = select_conversations(conversations, seed=args.seed, count=args.count)
    for conv in selected:
        print(conv.model_dump_json())
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    registry = default_registry()
    manifest = registry.get(args.corpus_id)
    if args.public_demo:
        try:
            assert_public_demo_allowed(manifest)
        except PublicDemoCorpusError as exc:
            print(f"verify failed: {exc}", file=sys.stderr)
            return 1
    print(f"ok: {manifest.id} provenance={manifest.provenance.value}")
    return 0


def _parse_cli_datetime(value: str) -> datetime:
    """Parse ISO datetime; naive values are treated as UTC, aware values converted."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def cmd_build(args: argparse.Namespace) -> int:
    registry = default_registry()
    manifest = registry.get(args.corpus_id)
    if args.public_demo:
        assert_public_demo_allowed(manifest)

    conversations = asyncio.run(_collect(args.corpus_id))
    window_start = _parse_cli_datetime(args.window_start)
    window_end = _parse_cli_datetime(args.window_end)
    derived = DerivedCorpusCache(
        root=Path(args.derived_root) if args.derived_root else None
    )
    result = build_demo_safe_corpus(
        conversations,
        manifest=manifest,
        seed=args.seed,
        count=args.count,
        window_start=window_start,
        window_end=window_end,
        derived=derived,
        profile=args.profile,
        expand_to=args.expand_to,
        require_synthetic=args.public_demo,
    )
    print(
        json.dumps(
            {
                **result.manifest,
                "derived_dir": str(result.derived_dir),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="enigma")
    sub = parser.add_subparsers(dest="group", required=True)

    corpus = sub.add_parser("corpus", help="Demo Mode background corpus tools")
    corpus_sub = corpus.add_subparsers(dest="command", required=True)

    p_list = corpus_sub.add_parser("list", help="List registered corpora")
    p_list.set_defaults(func=cmd_list)

    p_fetch = corpus_sub.add_parser(
        "fetch",
        help="Materialise corpus into local cache (HF only with --force-network)",
    )
    p_fetch.add_argument("corpus_id")
    p_fetch.add_argument("--revision", default=None)
    p_fetch.add_argument("--from-path", default=None, help="Local fixture/cache to copy")
    p_fetch.add_argument("--cache-root", default=None)
    p_fetch.add_argument("--dataset", default=None, help="HF dataset id override")
    p_fetch.add_argument(
        "--max-conversations",
        type=int,
        default=None,
        help="Cap HF rows when using --force-network",
    )
    p_fetch.add_argument(
        "--force-network",
        action="store_true",
        help="Allow Hugging Face download (never enable in PR CI)",
    )
    p_fetch.set_defaults(func=cmd_fetch)

    p_inspect = corpus_sub.add_parser("inspect", help="Inspect corpus metadata")
    p_inspect.add_argument("corpus_id")
    p_inspect.set_defaults(func=cmd_inspect)

    p_sanitise = corpus_sub.add_parser("sanitise", help="Sanitise conversations (stdout JSONL)")
    p_sanitise.add_argument("corpus_id")
    p_sanitise.add_argument("--seed", default="demo-safe-v1")
    p_sanitise.add_argument(
        "--include-rejected",
        action="store_true",
        help="Emit rejected rows with reasons",
    )
    p_sanitise.set_defaults(func=cmd_sanitise)

    p_sample = corpus_sub.add_parser("sample", help="Seeded conversation sample")
    p_sample.add_argument("corpus_id")
    p_sample.add_argument("--count", type=int, default=2)
    p_sample.add_argument("--seed", default="test")
    p_sample.set_defaults(func=cmd_sample)

    p_verify = corpus_sub.add_parser("verify", help="Verify provenance / public-demo gate")
    p_verify.add_argument("corpus_id")
    p_verify.add_argument("--public-demo", action="store_true")
    p_verify.set_defaults(func=cmd_verify)

    p_build = corpus_sub.add_parser(
        "build",
        help="Build demo-safe derived index (select + sanitise + timeline + cache)",
    )
    p_build.add_argument("corpus_id")
    p_build.add_argument("--seed", default="alex-v1-email-background-v1")
    p_build.add_argument("--count", type=int, default=100)
    p_build.add_argument(
        "--expand-to",
        type=int,
        default=None,
        help="Deterministically expand mini fixture before selection (CI scale)",
    )
    p_build.add_argument("--profile", default="demo-safe-v1")
    p_build.add_argument("--derived-root", default=None)
    p_build.add_argument("--window-start", default="2026-01-01")
    p_build.add_argument("--window-end", default="2026-06-30")
    p_build.add_argument("--public-demo", action="store_true")
    p_build.set_defaults(func=cmd_build)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
