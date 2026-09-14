from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import check_database_connection, get_db


router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/live")
def liveness() -> dict[str, str]:
    return {"status": "ok", "service": "slotbridge"}


@router.get("/ready")
def readiness(session: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    try:
        check_database_connection(session)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from None
    return {"status": "ready", "database": "ok"}
