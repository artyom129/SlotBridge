"""Run an isolated SQLite-backed backend for the Flutter contract smoke test.

This is a local test utility only. Production and Docker continue to use
PostgreSQL and Alembic; the temporary schema mirrors the existing pytest setup.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = (ROOT / "data" / "stage5-mobile-e2e.db").resolve()
if ROOT not in DATABASE_PATH.parents:
    raise SystemExit("Refusing to create an E2E database outside the project")

os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{DATABASE_PATH.as_posix()}"
os.environ["SLOTBRIDGE_ENVIRONMENT"] = "test"
os.environ.setdefault("JWT_SECRET", "stage5-e2e-jwt-secret-with-at-least-32-characters")
os.environ.setdefault(
    "MINDBODY_WEBHOOK_SECRET", "stage5-e2e-webhook-secret-with-at-least-32-chars"
)
os.environ["SLOTBRIDGE_DB_PATH"] = str(ROOT / "data" / "stage5-legacy-e2e.db")
sys.path.insert(0, str(ROOT))

from app.database import engine  # noqa: E402
from app.models import Base  # noqa: E402
from scripts.seed_domain import seed  # noqa: E402


def main() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed()

    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8765, log_level="warning")


if __name__ == "__main__":
    main()
