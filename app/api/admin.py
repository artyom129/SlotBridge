from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import Organization, User
from app.schemas import OrganizationCreate, OrganizationOut


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/organizations",
    response_model=OrganizationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    payload: OrganizationCreate,
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> Organization:
    if session.scalar(select(Organization).where(Organization.slug == payload.slug)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already exists")
    organization = Organization(
        name=payload.name.strip(),
        slug=payload.slug,
        timezone=payload.timezone,
        is_active=True,
    )
    session.add(organization)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Slug already exists"
        ) from None
    session.refresh(organization)
    return organization
