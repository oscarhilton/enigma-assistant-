"""Demo storage checkpoint helpers (D5)."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class Checkpoint:
    """A named snapshot of demo storage state under the demo root only."""

    name: str
    path: Path
    created_at: datetime
    meta: dict[str, Any]


def ensure_demo_layout(root: Path) -> None:
    """Create standard demo storage directories under ``root``."""
    for name in ("state", "vectors", "config", "checkpoints"):
        (root / name).mkdir(parents=True, exist_ok=True)
    db = root / "enigma.db"
    if not db.exists():
        db.write_bytes(b"")


def write_engine_state(root: Path, state: dict[str, Any]) -> Path:
    ensure_demo_layout(root)
    path = root / "state" / "engine.json"
    path.write_text(json.dumps(state, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return path


def read_engine_state(root: Path) -> dict[str, Any]:
    path = root / "state" / "engine.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_checkpoint(
    root: Path,
    name: str,
    *,
    created_at: datetime | None = None,
    meta: dict[str, Any] | None = None,
) -> Checkpoint:
    """Copy mutable demo state into ``checkpoints/<name>/`` under the demo root."""
    ensure_demo_layout(root)
    dest = root / "checkpoints" / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for item in ("enigma.db", "state", "vectors", "config"):
        src = root / item
        if not src.exists():
            continue
        target = dest / item
        if src.is_dir():
            shutil.copytree(src, target)
        else:
            shutil.copy2(src, target)
    stamp = created_at if created_at is not None else datetime.now(tz=UTC)
    info = {"name": name, "created_at": stamp.isoformat(), "meta": meta or {}}
    (dest / "checkpoint.json").write_text(
        json.dumps(info, indent=2, default=str),
        encoding="utf-8",
    )
    return Checkpoint(name=name, path=dest, created_at=stamp, meta=meta or {})


def reset_demo_storage(root: Path) -> None:
    """Clear demo storage contents under ``root`` only (never touches Private)."""
    if root.exists():
        for child in list(root.iterdir()):
            # Symlinks must not be followed into foreign trees via rmtree.
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink(missing_ok=True)
    ensure_demo_layout(root)


def bootstrap_demo_storage(
    root: Path,
    *,
    scenario: str,
    now: datetime,
) -> Path:
    """Ensure empty demo layout and write a fresh engine checkpoint."""
    ensure_demo_layout(root)
    return write_engine_state(
        root,
        {
            "scenario": scenario,
            "now": now.isoformat(),
            "emitted_ids": [],
            "pending_ids": [],
            "bootstrapped": True,
        },
    )
