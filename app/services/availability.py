from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    BlockedSlot,
    Branch,
    Employee,
    EmployeeService,
    OCCUPYING_APPOINTMENT_STATUSES,
    Organization,
    ScheduleBreak,
    ScheduleException,
    Service,
    WorkSchedule,
)
from app.services.intervals import Interval, generate_slots, merge_intervals, subtract_intervals


class AvailabilityError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class AvailabilitySlotValue:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class AvailabilityResult:
    local_date: date
    timezone_name: str
    service_duration_minutes: int
    slot_interval_minutes: int
    slots: list[AvailabilitySlotValue]


def _zone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise AvailabilityError(
            "INVALID_TIMEZONE_CONFIGURATION",
            "Branch or organization timezone is invalid",
            422,
        ) from None


def _local_datetime(local_date: date, local_time: time, zone: ZoneInfo) -> datetime:
    naive = datetime.combine(local_date, local_time)
    aware = naive.replace(tzinfo=zone, fold=0)
    round_trip = aware.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
    if round_trip != naive:
        raise AvailabilityError(
            "INVALID_LOCAL_SCHEDULE_TIME",
            "A schedule interval falls in a daylight-saving time gap",
            422,
        )
    return aware


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class AvailabilityService:
    def __init__(self, session: Session, slot_interval_minutes: int = 15):
        if slot_interval_minutes <= 0:
            raise ValueError("slot_interval_minutes must be positive")
        self.session = session
        self.slot_interval_minutes = slot_interval_minutes

    def calculate(
        self,
        branch_id: UUID,
        employee_id: UUID,
        service_id: UUID,
        local_date: date,
        exclude_appointment_id: UUID | None = None,
    ) -> AvailabilityResult:
        branch = self.session.get(Branch, branch_id)
        if branch is None:
            raise AvailabilityError("BRANCH_NOT_FOUND", "Branch not found", 404)
        organization = self.session.get(Organization, branch.organization_id)
        employee = self.session.get(Employee, employee_id)
        service = self.session.get(Service, service_id)

        if organization is None or employee is None or service is None:
            raise AvailabilityError("RESOURCE_NOT_FOUND", "Requested resource not found", 404)
        if employee.organization_id != organization.id or service.organization_id != organization.id:
            raise AvailabilityError("RESOURCE_NOT_FOUND", "Requested resource not found", 404)
        if employee.branch_id != branch.id:
            raise AvailabilityError("RESOURCE_NOT_FOUND", "Requested resource not found", 404)
        if not organization.is_active:
            raise AvailabilityError("ORGANIZATION_INACTIVE", "Organization is inactive", 409)
        if not branch.is_active:
            raise AvailabilityError("BRANCH_INACTIVE", "Branch is inactive", 409)
        if not employee.is_active:
            raise AvailabilityError("EMPLOYEE_INACTIVE", "Employee is inactive", 409)
        if not service.is_active:
            raise AvailabilityError("SERVICE_INACTIVE", "Service is inactive", 409)

        link = self.session.get(
            EmployeeService, {"employee_id": employee.id, "service_id": service.id}
        )
        if link is None or link.organization_id != organization.id:
            raise AvailabilityError(
                "EMPLOYEE_SERVICE_MISMATCH",
                "Employee does not provide the requested service",
                422,
            )

        timezone_name = branch.timezone or organization.timezone
        zone = _zone(timezone_name)
        weekday = local_date.weekday()
        work_windows = self._work_windows(employee.id, branch.id, local_date, weekday, zone)
        if not work_windows:
            return AvailabilityResult(
                local_date,
                timezone_name,
                link.duration_override_minutes or service.duration_minutes,
                self.slot_interval_minutes,
                [],
            )

        breaks = self._recurring_breaks(employee.id, branch.id, local_date, weekday, zone)
        blocks = self._blocked_intervals(employee.id, branch.id, local_date, zone)
        appointments = self._appointment_intervals(
            employee.id,
            branch.id,
            local_date,
            zone,
            exclude_appointment_id,
        )
        free_windows = subtract_intervals(work_windows, breaks + blocks + appointments)
        duration_minutes = link.duration_override_minutes or service.duration_minutes
        slots = generate_slots(
            work_windows,
            free_windows,
            timedelta(minutes=duration_minutes),
            timedelta(minutes=self.slot_interval_minutes),
        )
        return AvailabilityResult(
            local_date,
            timezone_name,
            duration_minutes,
            self.slot_interval_minutes,
            [
                AvailabilitySlotValue(
                    item.start.astimezone(zone), item.end.astimezone(zone)
                )
                for item in slots
            ],
        )

    def _work_windows(
        self,
        employee_id: UUID,
        branch_id: UUID,
        local_date: date,
        weekday: int,
        zone: ZoneInfo,
    ) -> list[Interval]:
        exception_statement = select(ScheduleException).where(
            ScheduleException.employee_id == employee_id,
            ScheduleException.branch_id == branch_id,
            ScheduleException.local_date == local_date,
            ScheduleException.is_active.is_(True),
        )
        exceptions = list(self.session.scalars(exception_statement))
        if exceptions:
            if any(item.is_day_off for item in exceptions):
                return []
            return merge_intervals(
                [
                    Interval(
                        _local_datetime(local_date, item.start_time, zone).astimezone(
                            timezone.utc
                        ),
                        _local_datetime(local_date, item.end_time, zone).astimezone(
                            timezone.utc
                        ),
                    )
                    for item in exceptions
                    if item.start_time is not None and item.end_time is not None
                ]
            )

        schedule_statement = select(WorkSchedule).where(
            WorkSchedule.employee_id == employee_id,
            WorkSchedule.branch_id == branch_id,
            WorkSchedule.day_of_week == weekday,
            WorkSchedule.is_active.is_(True),
        )
        return merge_intervals(
            [
                Interval(
                    _local_datetime(local_date, item.start_time, zone).astimezone(
                        timezone.utc
                    ),
                    _local_datetime(local_date, item.end_time, zone).astimezone(
                        timezone.utc
                    ),
                )
                for item in self.session.scalars(schedule_statement)
            ]
        )

    def _recurring_breaks(
        self,
        employee_id: UUID,
        branch_id: UUID,
        local_date: date,
        weekday: int,
        zone: ZoneInfo,
    ) -> list[Interval]:
        statement = select(ScheduleBreak).where(
            ScheduleBreak.employee_id == employee_id,
            ScheduleBreak.branch_id == branch_id,
            ScheduleBreak.day_of_week == weekday,
            ScheduleBreak.is_active.is_(True),
        )
        return merge_intervals(
            [
                Interval(
                    _local_datetime(local_date, item.start_time, zone).astimezone(
                        timezone.utc
                    ),
                    _local_datetime(local_date, item.end_time, zone).astimezone(
                        timezone.utc
                    ),
                )
                for item in self.session.scalars(statement)
            ]
        )

    def _blocked_intervals(
        self,
        employee_id: UUID,
        branch_id: UUID,
        local_date: date,
        zone: ZoneInfo,
    ) -> list[Interval]:
        local_start = _local_datetime(local_date, time.min, zone)
        local_end = _local_datetime(local_date + timedelta(days=1), time.min, zone)
        utc_start = local_start.astimezone(timezone.utc)
        utc_end = local_end.astimezone(timezone.utc)
        statement = select(BlockedSlot).where(
            BlockedSlot.employee_id == employee_id,
            BlockedSlot.branch_id == branch_id,
            BlockedSlot.starts_at < utc_end,
            BlockedSlot.ends_at > utc_start,
            BlockedSlot.is_active.is_(True),
        )
        return merge_intervals(
            [
                Interval(
                    _as_utc(item.starts_at),
                    _as_utc(item.ends_at),
                )
                for item in self.session.scalars(statement)
            ]
        )

    def _appointment_intervals(
        self,
        employee_id: UUID,
        branch_id: UUID,
        local_date: date,
        zone: ZoneInfo,
        exclude_appointment_id: UUID | None,
    ) -> list[Interval]:
        local_start = _local_datetime(local_date, time.min, zone)
        local_end = _local_datetime(local_date + timedelta(days=1), time.min, zone)
        utc_start = local_start.astimezone(timezone.utc)
        utc_end = local_end.astimezone(timezone.utc)
        statement = select(Appointment).where(
            Appointment.employee_id == employee_id,
            Appointment.branch_id == branch_id,
            Appointment.starts_at < utc_end,
            Appointment.ends_at > utc_start,
            Appointment.status.in_(OCCUPYING_APPOINTMENT_STATUSES),
        )
        if exclude_appointment_id is not None:
            statement = statement.where(Appointment.id != exclude_appointment_id)
        return merge_intervals(
            [
                Interval(_as_utc(item.starts_at), _as_utc(item.ends_at))
                for item in self.session.scalars(statement)
            ]
        )
