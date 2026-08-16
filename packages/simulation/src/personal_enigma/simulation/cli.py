"""CLI: ``enigma corpus …`` (argparse under packages/simulation).

Never downloads FinePersonas 115k in CI — fetch is a stub that refuses bulk HF pulls
unless explicitly pointed at a local cache path.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from personal_enigma.simulation.corpus.cache import CorpusCache
from personal_enigma.simulation.corpus.registry import default_registry
from personal_enigma.simulation.corpus.safety import (
    PublicDemoCorpusError,
    assert_public_demo_allowed,
)
from personal_enigma.simulation.corpus.sanitise import sanitise_conversation
from personal_enigma.simulation.corpus.selectors import select_conversations


async def _collect(corpus_id: str) -> list:
    registry = default_registry()
    adapter = registry.adapter_for(corpus_id)
    out = []
    async for conv in adapter.iterate_conversations():
        out.append(conv)
    return out


def cmd_list(_args: argparse.Namespace) -> int:
    registry = default_registry()
    for corpus_id in registry.list_ids():
        manifest = registry.get(corpus_id)
        print(f"{corpus_id}\t{manifest.provenance.value}\tadapter={manifest.format_adapter}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    """Stub: refuse silent Hugging Face bulk download; document cache layout."""
    cache = CorpusCache()
    revision = args.revision or "unspecified"
    target = cache.revision_dir(args.corpus_id, revision)
    print(
        "fetch stub: will not download FinePersonas (~115k) from Hugging Face in CI.\n"
        f"Place pinned revision data under: {target}\n"
        "Use finepersonas-mini fixture for PR tests.",
        file=sys.stderr,
    )
    if args.force_network:
        print("error: --force-network is reserved; not implemented in scaffold", file=sys.stderr)
        return 2
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
    for conv in conversations:
        cleaned = sanitise_conversation(conv)
        print(cleaned.model_dump_json())
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="enigma")
    sub = parser.add_subparsers(dest="group", required=True)

    corpus = sub.add_parser("corpus", help="Demo Mode background corpus tools")
    corpus_sub = corpus.add_subparsers(dest="command", required=True)

    p_list = corpus_sub.add_parser("list", help="List registered corpora")
    p_list.set_defaults(func=cmd_list)

    p_fetch = corpus_sub.add_parser("fetch", help="Fetch corpus into local cache (stub)")
    p_fetch.add_argument("corpus_id")
    p_fetch.add_argument("--revision", default=None)
    p_fetch.add_argument(
        "--force-network",
        action="store_true",
        help="Reserved; scaffold refuses HF bulk download",
    )
    p_fetch.set_defaults(func=cmd_fetch)

    p_inspect = corpus_sub.add_parser("inspect", help="Inspect corpus metadata")
    p_inspect.add_argument("corpus_id")
    p_inspect.set_defaults(func=cmd_inspect)

    p_sanitise = corpus_sub.add_parser("sanitise", help="Sanitise conversations (stdout JSONL)")
    p_sanitise.add_argument("corpus_id")
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
