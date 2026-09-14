from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import AuthenticatedUser, require_admin, require_employee
from app.models import (
    BlockedSlot,
    ScheduleBreak,
    ScheduleException,
    User,
    WorkSchedule,
)
from app.schemas import (
    AvailabilityResponse,
    AvailabilitySlot,
    BlockedSlotCreate,
    BlockedSlotOut,
    ScheduleBreakCreate,
    ScheduleBreakOut,
    ScheduleExceptionCreate,
    ScheduleExceptionOut,
    WorkScheduleCreate,
    WorkScheduleOut,
)
from app.services.availability import AvailabilityError, AvailabilityService
from app.services.scheduling import (
    SchedulingError,
    ensure_exception_compatibility,
    resolve_schedule_scope,
)


router = APIRouter(tags=["scheduling"])


def _domain_error(error: AvailabilityError | SchedulingError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    )


def _not_found(entity: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "SCHEDULE_RESOURCE_NOT_FOUND", "message": f"{entity} not found"},
    )


def _flush_or_conflict(session: Session) -> None:
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SCHEDULE_CONFLICT",
                "message": "The schedule change conflicts with existing data",
            },
        ) from None


@router.get("/availability", response_model=AvailabilityResponse)
def get_availability(
    branch_id: UUID,
    employee_id: UUID,
    service_id: UUID,
    local_date: Annotated[date, Query(alias="date")],
    _user: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AvailabilityResponse:
    try:
        result = AvailabilityService(
            session,
            slot_interval_minutes=settings.availability_slot_interval_minutes,
        ).calculate(branch_id, employee_id, service_id, local_date)
    except AvailabilityError as error:
        raise _domain_error(error) from None
    return AvailabilityResponse(
        date=result.local_date,
        timezone=result.timezone_name,
        service_duration_minutes=result.service_duration_minutes,
        slot_interval_minutes=result.slot_interval_minutes,
        slots=[AvailabilitySlot(start=item.start, end=item.end) for item in result.slots],
    )


@router.post(
    "/admin/work-schedules",
    response_model=WorkScheduleOut,
    status_code=status.HTTP_201_CREATED,
)
def create_work_schedule(
    payload: WorkScheduleCreate,
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> WorkSchedule:
    try:
        scope = resolve_schedule_scope(session, payload.employee_id, payload.branch_id)
    except SchedulingError as error:
        raise _domain_error(error) from None
    item = WorkSchedule(
        **payload.model_dump(), organization_id=scope.organization_id
    )
    session.add(item)
    _flush_or_conflict(session)
    session.refresh(item)
    return item


@router.put("/admin/work-schedules/{schedule_id}", response_model=WorkScheduleOut)
def update_work_schedule(
    schedule_id: UUID,
    payload: WorkScheduleCreate,
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> WorkSchedule:
    item = session.get(WorkSchedule, schedule_id)
    if item is None:
        raise _not_found("Work schedule")
    try:
        scope = resolve_schedule_scope(session, payload.employee_id, payload.branch_id)
    except SchedulingError as error:
        raise _domain_error(error) from None
    for name, value in payload.model_dump().items():
        setattr(item, name, value)
    item.organization_id = scope.organization_id
    _flush_or_conflict(session)
    session.refresh(item)
    return item


@router.post(
    "/admin/schedule-breaks",
    response_model=ScheduleBreakOut,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule_break(
    payload: ScheduleBreakCreate,
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> ScheduleBreak:
    try:
        scope = resolve_schedule_scope(session, payload.employee_id, payload.branch_id)
    except SchedulingError as error:
        raise _domain_error(error) from None
    item = ScheduleBreak(
        **payload.model_dump(), organization_id=scope.organization_id
    )
    session.add(item)
    _flush_or_conflict(session)
    session.refresh(item)
    return item


@router.put("/admin/schedule-breaks/{break_id}", response_model=ScheduleBreakOut)
def update_schedule_break(
    break_id: UUID,
    payload: ScheduleBreakCreate,
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> ScheduleBreak:
    item = session.get(ScheduleBreak, break_id)
    if item is None:
        raise _not_found("Schedule break")
    try:
        scope = resolve_schedule_scope(session, payload.employee_id, payload.branch_id)
    except SchedulingError as error:
        raise _domain_error(error) from None
    for name, value in payload.model_dump().items():
        setattr(item, name, value)
    item.organization_id = scope.organization_id
    _flush_or_conflict(session)
    session.refresh(item)
    return item


@router.post(
    "/admin/schedule-exceptions",
    response_model=ScheduleExceptionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule_exception(
    payload: ScheduleExceptionCreate,
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> ScheduleException:
    try:
        scope = resolve_schedule_scope(session, payload.employee_id, payload.branch_id)
        ensure_exception_compatibility(
            session,
            payload.employee_id,
            payload.branch_id,
            payload.local_date,
            payload.is_day_off,
            payload.is_active,
        )
    except SchedulingError as error:
        raise _domain_error(error) from None
    item = ScheduleException(
        **payload.model_dump(), organization_id=scope.organization_id
    )
    session.add(item)
    _flush_or_conflict(session)
    session.refresh(item)
    return item


@router.put(
    "/admin/schedule-exceptions/{exception_id}", response_model=ScheduleExceptionOut
)
def update_schedule_exception(
    exception_id: UUID,
    payload: ScheduleExceptionCreate,
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> ScheduleException:
    item = session.get(ScheduleException, exception_id)
    if item is None:
        raise _not_found("Schedule exception")
    try:
        scope = resolve_schedule_scope(session, payload.employee_id, payload.branch_id)
        ensure_exception_compatibility(
            session,
            payload.employee_id,
            payload.branch_id,
            payload.local_date,
            payload.is_day_off,
            payload.is_active,
            excluding_id=item.id,
        )
    except SchedulingError as error:
        raise _domain_error(error) from None
    for name, value in payload.model_dump().items():
        setattr(item, name, value)
    item.organization_id = scope.organization_id
    _flush_or_conflict(session)
    session.refresh(item)
    return item


def _create_blocked_slot(
    payload: BlockedSlotCreate,
    actor: User,
    session: Session,
    own_only: bool,
) -> BlockedSlot:
    try:
        scope = resolve_schedule_scope(session, payload.employee_id, payload.branch_id)
    except SchedulingError as error:
        raise _domain_error(error) from None
    if own_only and scope.employee.user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "EMPLOYEE_BLOCK_SCOPE_FORBIDDEN",
                "message": "Employees may only manage their own blocked slots",
            },
        )
    item = BlockedSlot(
        **payload.model_dump(),
        organization_id=scope.organization_id,
        created_by_user_id=actor.id,
    )
    session.add(item)
    _flush_or_conflict(session)
    session.refresh(item)
    return item


def _update_blocked_slot(
    block_id: UUID,
    payload: BlockedSlotCreate,
    actor: User,
    session: Session,
    own_only: bool,
) -> BlockedSlot:
    item = session.get(BlockedSlot, block_id)
    if item is None:
        raise _not_found("Blocked slot")
    try:
        scope = resolve_schedule_scope(session, payload.employee_id, payload.branch_id)
    except SchedulingError as error:
        raise _domain_error(error) from None
    if own_only and (item.employee_id != scope.employee.id or scope.employee.user_id != actor.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "EMPLOYEE_BLOCK_SCOPE_FORBIDDEN",
                "message": "Employees may only manage their own blocked slots",
            },
        )
    for name, value in payload.model_dump().items():
        setattr(item, name, value)
    item.organization_id = scope.organization_id
    _flush_or_conflict(session)
    session.refresh(item)
    return item


@router.post(
    "/admin/blocked-slots",
    response_model=BlockedSlotOut,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_blocked_slot(
    payload: BlockedSlotCreate,
    admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> BlockedSlot:
    return _create_blocked_slot(payload, admin, session, own_only=False)


@router.put("/admin/blocked-slots/{block_id}", response_model=BlockedSlotOut)
def update_admin_blocked_slot(
    block_id: UUID,
    payload: BlockedSlotCreate,
    admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> BlockedSlot:
    return _update_blocked_slot(block_id, payload, admin, session, own_only=False)


@router.post(
    "/employee/blocked-slots",
    response_model=BlockedSlotOut,
    status_code=status.HTTP_201_CREATED,
)
def create_own_blocked_slot(
    payload: BlockedSlotCreate,
    employee_user: Annotated[User, Depends(require_employee)],
    session: Annotated[Session, Depends(get_db)],
) -> BlockedSlot:
    return _create_blocked_slot(payload, employee_user, session, own_only=True)


@router.put("/employee/blocked-slots/{block_id}", response_model=BlockedSlotOut)
def update_own_blocked_slot(
    block_id: UUID,
    payload: BlockedSlotCreate,
    employee_user: Annotated[User, Depends(require_employee)],
    session: Annotated[Session, Depends(get_db)],
) -> BlockedSlot:
    return _update_blocked_slot(block_id, payload, employee_user, session, own_only=True)
