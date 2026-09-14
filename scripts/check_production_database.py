from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.database import engine  # noqa: E402


EXPECTED_REVISION = "20260911_0003"
EXPECTED_CONSTRAINT = "ex_appointments_employee_time_active"


def main() -> None:
    settings = get_settings()
    if settings.slotbridge_environment != "production":
        raise SystemExit("This check requires SLOTBRIDGE_ENVIRONMENT=production")
    if engine.dialect.name != "postgresql" or engine.dialect.driver != "psycopg":
        raise SystemExit("Production must use PostgreSQL through psycopg")

    with engine.connect() as connection:
        using_ssl = bool(
            connection.scalar(
                text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")
            )
        )
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
        has_btree_gist = bool(
            connection.scalar(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'"
                    ")"
                )
            )
        )
        has_exclusion_constraint = bool(
            connection.scalar(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_constraint "
                    "WHERE conname = :constraint_name AND contype = 'x'"
                    ")"
                ),
                {"constraint_name": EXPECTED_CONSTRAINT},
            )
        )

    result = {
        "driver": engine.dialect.driver,
        "ssl": using_ssl,
        "migration_revision": revision,
        "btree_gist": has_btree_gist,
        "exclusion_constraint": has_exclusion_constraint,
    }
    print(json.dumps(result, sort_keys=True))

    if not using_ssl:
        raise SystemExit("The PostgreSQL connection is not encrypted")
    if revision != EXPECTED_REVISION:
        raise SystemExit(f"Expected Alembic revision {EXPECTED_REVISION}")
    if not has_btree_gist or not has_exclusion_constraint:
        raise SystemExit("PostgreSQL double-booking protection is incomplete")


if __name__ == "__main__":
    main()
