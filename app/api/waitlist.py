from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import require_client
from app.models import Branch, Employee, OrganizationMembership, Service, User, WaitlistEntry, WaitlistStatus
from app.schemas import WaitlistCreateRequest, WaitlistListResponse, WaitlistOut
from app.services.booking import BookingError, BookingService

router = APIRouter(prefix="/waitlist", tags=["waitlist"])

def _out(entry, session):
    service = session.get(Service, entry.service_id)
    employee = session.get(Employee, entry.matched_employee_id or entry.employee_id) if (entry.matched_employee_id or entry.employee_id) else None
    return {**WaitlistOut.model_validate(entry).model_dump(), "service_name": service.name if service else None, "employee_name": employee.display_name if employee else None}

@router.post("", response_model=WaitlistOut, status_code=status.HTTP_201_CREATED)
def create_waitlist(payload: WaitlistCreateRequest, client: Annotated[User, Depends(require_client)], session: Annotated[Session, Depends(get_db)]):
    branch, service = session.get(Branch, payload.branch_id), session.get(Service, payload.service_id)
    if branch is None or service is None or service.organization_id != branch.organization_id or session.get(OrganizationMembership, {"user_id": client.id, "organization_id": branch.organization_id}) is None:
        raise HTTPException(404, detail={"code": "WAITLIST_SCOPE_NOT_FOUND", "message": "Waitlist scope not found"})
    if payload.employee_id is not None:
        employee = session.get(Employee, payload.employee_id)
        if employee is None or employee.organization_id != branch.organization_id or employee.branch_id != branch.id:
            raise HTTPException(404, detail={"code": "WAITLIST_SCOPE_NOT_FOUND", "message": "Waitlist scope not found"})
    entry = WaitlistEntry(organization_id=branch.organization_id, client_user_id=client.id, **payload.model_dump(), status=WaitlistStatus.WAITING)
    session.add(entry); session.flush(); session.refresh(entry)
    return _out(entry, session)

@router.get("/me", response_model=WaitlistListResponse)
def list_waitlist(client: Annotated[User, Depends(require_client)], session: Annotated[Session, Depends(get_db)]):
    items = list(session.scalars(select(WaitlistEntry).where(WaitlistEntry.client_user_id == client.id).order_by(WaitlistEntry.created_at.desc())))
    return WaitlistListResponse(items=[_out(item, session) for item in items])

@router.post("/{entry_id}/accept", response_model=WaitlistOut)
def accept_waitlist(entry_id: UUID, idempotency_key: Annotated[str, Header(alias="Idempotency-Key")], client: Annotated[User, Depends(require_client)], session: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]):
    entry = session.scalar(select(WaitlistEntry).where(WaitlistEntry.id == entry_id, WaitlistEntry.client_user_id == client.id).with_for_update())
    if entry is None: raise HTTPException(404, detail={"code": "WAITLIST_NOT_FOUND", "message": "Waitlist entry not found"})
    if entry.status != WaitlistStatus.MATCHED or entry.matched_employee_id is None or entry.matched_starts_at is None:
        raise HTTPException(409, detail={"code": "WAITLIST_NOT_MATCHED", "message": "Waitlist entry has no active match"})
    try:
        BookingService(session, slot_interval_minutes=settings.availability_slot_interval_minutes).create(client, branch_id=entry.branch_id, employee_id=entry.matched_employee_id, service_id=entry.service_id, starts_at=entry.matched_starts_at, client_note="Waitlist match", idempotency_key=idempotency_key)
    except BookingError as error:
        raise HTTPException(error.status_code, detail={"code": error.code, "message": error.message}) from None
    entry.status = WaitlistStatus.ACCEPTED; session.flush(); session.refresh(entry)
    return _out(entry, session)
