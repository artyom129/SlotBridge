from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.appointments import _appointment_out
from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import require_client
from app.models import User
from app.schemas import AppointmentOut, AppointmentResourceOut
from app.services.booking import BookingError, BookingService
from app.services.journeys import JourneyPlanner


router = APIRouter(prefix="/journeys", tags=["multi-service-journeys"])


class JourneyPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_id: UUID
    service_ids: list[UUID] = Field(min_length=2, max_length=6)
    date: date
    after_time: time = time(0, 0)
    before_time: time = time(23, 59)


class JourneyStepOut(BaseModel):
    service: AppointmentResourceOut
    employee: AppointmentResourceOut
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    local_starts_at: AwareDatetime
    local_ends_at: AwareDatetime


class JourneyRouteOut(BaseModel):
    strategy: str
    steps: list[JourneyStepOut]
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    total_minutes: int
    wait_minutes: int
    employee_count: int


class JourneyPlanOut(BaseModel):
    timezone: str
    routes: list[JourneyRouteOut]


class JourneyBookStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: UUID
    employee_id: UUID
    starts_at: AwareDatetime

    @field_validator("starts_at", mode="after")
    @classmethod
    def normalize_start(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


class JourneyBookRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_id: UUID
    steps: list[JourneyBookStepRequest] = Field(min_length=2, max_length=6)
    client_note: str | None = Field(default=None, max_length=1000)


class JourneyBookOut(BaseModel):
    appointments: list[AppointmentOut]


def _http_error(error: BookingError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    )


@router.post("/plan", response_model=JourneyPlanOut)
def plan_journey(
    payload: JourneyPlanRequest,
    client: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JourneyPlanOut:
    try:
        timezone_name, routes = JourneyPlanner(
            session, settings.availability_slot_interval_minutes
        ).plan(
            client,
            branch_id=payload.branch_id,
            service_ids=payload.service_ids,
            local_date=payload.date,
            after_time=payload.after_time,
            before_time=payload.before_time,
        )
    except BookingError as error:
        raise _http_error(error) from None
    zone = ZoneInfo(timezone_name)
    return JourneyPlanOut(
        timezone=timezone_name,
        routes=[
            JourneyRouteOut(
                strategy=route.strategy,
                steps=[
                    JourneyStepOut(
                        service=AppointmentResourceOut(
                            id=step.service_id, name=step.service_name
                        ),
                        employee=AppointmentResourceOut(
                            id=step.employee_id, name=step.employee_name
                        ),
                        starts_at=step.starts_at.astimezone(timezone.utc),
                        ends_at=step.ends_at.astimezone(timezone.utc),
                        local_starts_at=step.starts_at.astimezone(zone),
                        local_ends_at=step.ends_at.astimezone(zone),
                    )
                    for step in route.steps
                ],
                starts_at=route.steps[0].starts_at.astimezone(timezone.utc),
                ends_at=route.steps[-1].ends_at.astimezone(timezone.utc),
                total_minutes=route.total_minutes,
                wait_minutes=route.wait_minutes,
                employee_count=route.employee_count,
            )
            for route in routes
        ],
    )


@router.post(
    "/book",
    response_model=JourneyBookOut,
    status_code=status.HTTP_201_CREATED,
)
def book_journey(
    payload: JourneyBookRequest,
    response: Response,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ],
    client: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JourneyBookOut:
    try:
        result = BookingService(
            session, settings.availability_slot_interval_minutes
        ).create_journey(
            client,
            branch_id=payload.branch_id,
            steps=[
                (step.service_id, step.employee_id, step.starts_at)
                for step in payload.steps
            ],
            client_note=payload.client_note,
            idempotency_key=idempotency_key,
        )
    except BookingError as error:
        raise _http_error(error) from None
    if result.replayed:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotency-Replayed"] = "true"
    return JourneyBookOut(
        appointments=[_appointment_out(item) for item in result.appointments]
    )
