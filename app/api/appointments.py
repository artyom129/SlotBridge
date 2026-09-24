from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import AuthenticatedUser, require_client, require_roles
from app.models import Appointment, AppointmentStatus, User, UserRole
from app.schemas import (
    AppointmentAuditOut,
    AppointmentCancelRequest,
    AppointmentCreateRequest,
    AppointmentDetailOut,
    AppointmentListResponse,
    AppointmentOut,
    AppointmentRescheduleRequest,
    AppointmentResourceOut,
    AppointmentStatusHistoryOut,
    AppointmentStatusRequest,
)
from app.services.booking import BookingError, BookingService


router = APIRouter(prefix="/appointments", tags=["appointments"])
require_booking_operator = require_roles(UserRole.EMPLOYEE, UserRole.ADMIN)


def _http_error(error: BookingError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _appointment_out(appointment: Appointment) -> AppointmentOut:
    timezone_name = appointment.branch.timezone or appointment.organization.timezone
    zone = ZoneInfo(timezone_name)
    starts_at = _as_utc(appointment.starts_at)
    ends_at = _as_utc(appointment.ends_at)
    cancelled_at = (
        _as_utc(appointment.cancelled_at)
        if appointment.cancelled_at is not None
        else None
    )
    return AppointmentOut(
        id=appointment.id,
        organization_id=appointment.organization_id,
        client_user_id=appointment.client_user_id,
        branch=AppointmentResourceOut(
            id=appointment.branch_id, name=appointment.branch.name
        ),
        employee=AppointmentResourceOut(
            id=appointment.employee_id, name=appointment.employee.display_name
        ),
        service=AppointmentResourceOut(
            id=appointment.service_id, name=appointment.service.name
        ),
        starts_at=starts_at,
        ends_at=ends_at,
        timezone=timezone_name,
        local_starts_at=starts_at.astimezone(zone),
        local_ends_at=ends_at.astimezone(zone),
        status=appointment.status,
        client_note=appointment.client_note,
        cancellation_reason=appointment.cancellation_reason,
        cancelled_at=cancelled_at,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
        review_id=appointment.review.id if appointment.review is not None else None,
    )


def _appointment_detail(appointment: Appointment) -> AppointmentDetailOut:
    base = _appointment_out(appointment).model_dump()
    return AppointmentDetailOut(
        **base,
        status_history=[
            AppointmentStatusHistoryOut.model_validate(item)
            for item in appointment.status_history
        ],
        audit_events=[
            AppointmentAuditOut.model_validate(item)
            for item in appointment.audit_events
        ],
    )


@router.post(
    "",
    response_model=AppointmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Book an available slot for the authenticated client",
)
def create_appointment(
    payload: AppointmentCreateRequest,
    response: Response,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=255,
            description="Client-scoped persistent retry key",
        ),
    ],
    client: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AppointmentOut:
    try:
        result = BookingService(
            session,
            slot_interval_minutes=settings.availability_slot_interval_minutes,
        ).create(
            client,
            branch_id=payload.branch_id,
            employee_id=payload.employee_id,
            service_id=payload.service_id,
            starts_at=payload.starts_at,
            client_note=payload.client_note,
            idempotency_key=idempotency_key,
        )
    except BookingError as error:
        raise _http_error(error) from None
    if result.replayed:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotency-Replayed"] = "true"
    return _appointment_out(result.appointment)


@router.get(
    "/me",
    response_model=AppointmentListResponse,
    summary="List only the authenticated client's appointments",
)
def list_my_appointments(
    client: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    view: Annotated[
        Literal["all", "upcoming", "past", "cancelled"],
        Query(description="Temporal/status shortcut"),
    ] = "all",
    appointment_status: Annotated[
        AppointmentStatus | None, Query(alias="status")
    ] = None,
) -> AppointmentListResponse:
    try:
        appointments = BookingService(
            session,
            slot_interval_minutes=settings.availability_slot_interval_minutes,
        ).list_my(
            client,
            view=view,
            appointment_status=appointment_status,
        )
    except BookingError as error:
        raise _http_error(error) from None
    return AppointmentListResponse(
        items=[_appointment_out(item) for item in appointments]
    )


@router.get(
    "/{appointment_id}",
    response_model=AppointmentDetailOut,
    summary="Get an appointment with lifecycle and audit history",
)
def get_appointment(
    appointment_id: UUID,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AppointmentDetailOut:
    try:
        appointment = BookingService(
            session,
            slot_interval_minutes=settings.availability_slot_interval_minutes,
        ).get_authorized(appointment_id, actor)
    except BookingError as error:
        raise _http_error(error) from None
    return _appointment_detail(appointment)


@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentOut,
    summary="Cancel an authorized appointment without deleting it",
)
def cancel_appointment(
    appointment_id: UUID,
    payload: AppointmentCancelRequest,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AppointmentOut:
    try:
        appointment = BookingService(
            session,
            slot_interval_minutes=settings.availability_slot_interval_minutes,
        ).cancel(appointment_id, actor, payload.reason)
    except BookingError as error:
        raise _http_error(error) from None
    return _appointment_out(appointment)

@router.post(
    "/{appointment_id}/reschedule",
    response_model=AppointmentOut,
    summary="Atomically move an authorized appointment to an available slot",
)
def reschedule_appointment(
    appointment_id: UUID,
    payload: AppointmentRescheduleRequest,
    actor: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AppointmentOut:
    try:
        appointment = BookingService(
            session,
            slot_interval_minutes=settings.availability_slot_interval_minutes,
        ).reschedule(
            appointment_id,
            actor,
            payload.starts_at,
            payload.reason,
        )
    except BookingError as error:
        raise _http_error(error) from None
    return _appointment_out(appointment)


@router.post(
    "/{appointment_id}/status",
    response_model=AppointmentOut,
    summary="Apply a validated employee/admin lifecycle transition",
)
def change_appointment_status(
    appointment_id: UUID,
    payload: AppointmentStatusRequest,
    actor: Annotated[User, Depends(require_booking_operator)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AppointmentOut:
    try:
        appointment = BookingService(
            session,
            slot_interval_minutes=settings.availability_slot_interval_minutes,
        ).change_status(
            appointment_id,
            actor,
            payload.status,
            payload.reason,
        )
    except BookingError as error:
        raise _http_error(error) from None
    return _appointment_out(appointment)
