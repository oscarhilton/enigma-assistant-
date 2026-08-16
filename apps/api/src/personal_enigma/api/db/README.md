# Private persistence (M00a)

Local SQLite database for sync cursors, ingested canonical records, and obligations.

## Location

Default file (when `ENIGMA_DATABASE_URL` is unset):

```text
$XDG_DATA_HOME/personal-enigma/private.db
# or ~/.local/share/personal-enigma/private.db
```

Override with a **sqlite** URL only:

```bash
export ENIGMA_DATABASE_URL="sqlite:////absolute/path/to/private.db"
```

Non-sqlite and host-qualified URLs are rejected. The DB is never bound to a network port.

## Migrations

Alembic scripts live in `migrations/`. Prefer the Python helpers:

```python
from personal_enigma.api.db.migrate import downgrade_base, upgrade_head

upgrade_head("sqlite:////tmp/enigma-private.db")
downgrade_base("sqlite:////tmp/enigma-private.db")
```

Or from a shell (after `uv sync`), with the URL set:

```bash
cd apps/api/src/personal_enigma/api/db
uv run alembic -c alembic.ini upgrade head
```

(`migrate.alembic_config` always overrides `sqlalchemy.url` and `script_location`.)

## Privacy

- Do not dump private tables to remote APIs.
- Do not store Notes bodies here for remote sync (Notes stay local / HIGH).
- Worker jobs open the same on-disk file via `personal_enigma.worker.storage`.
