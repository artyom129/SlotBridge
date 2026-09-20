from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Appointment,
    AppointmentAuditAction,
    AppointmentAuditLog,
    AppointmentStatus,
    AppointmentStatusHistory,
    Branch,
    Employee,
    OCCUPYING_APPOINTMENT_STATUSES,
    Organization,
    OrganizationMembership,
    User,
    UserRole,
)
from app.services.availability import AvailabilityError, AvailabilityService
from app.services.waitlist import match_released_slot


class BookingError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class AppointmentLifecycle:
    ALLOWED_TRANSITIONS: dict[AppointmentStatus, frozenset[AppointmentStatus]] = {
        AppointmentStatus.BOOKED: frozenset(
            {AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED}
        ),
        AppointmentStatus.CONFIRMED: frozenset(
            {
                AppointmentStatus.IN_PROGRESS,
                AppointmentStatus.CANCELLED,
                AppointmentStatus.NO_SHOW,
            }
        ),
        AppointmentStatus.IN_PROGRESS: frozenset({AppointmentStatus.COMPLETED}),
        AppointmentStatus.COMPLETED: frozenset(),
        AppointmentStatus.CANCELLED: frozenset(),
        AppointmentStatus.NO_SHOW: frozenset(),
    }

    @classmethod
    def ensure_transition(
        cls, old_status: AppointmentStatus, new_status: AppointmentStatus
    ) -> None:
        if new_status not in cls.ALLOWED_TRANSITIONS[old_status]:
            raise BookingError(
                "INVALID_APPOINTMENT_STATUS_TRANSITION",
                f"Appointment cannot transition from {old_status.value} to {new_status.value}",
                409,
            )


@dataclass(frozen=True)
class BookingCreateResult:
    appointment: Appointment
    replayed: bool


@dataclass(frozen=True)
class JourneyBookingResult:
    appointments: list[Appointment]
    replayed: bool


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _create_request_fingerprint(
    branch_id: UUID,
    employee_id: UUID,
    service_id: UUID,
    starts_at: datetime,
    client_note: str | None,
) -> str:
    canonical = json.dumps(
        {
            "branch_id": str(branch_id),
            "client_note": client_note,
            "employee_id": str(employee_id),
            "service_id": str(service_id),
            "starts_at": _as_utc(starts_at).isoformat(),
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(error.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None)


def _is_idempotency_violation(error: IntegrityError) -> bool:
    name = _constraint_name(error)
    if name == "uq_appointments_client_idempotency_key":
        return True
    message = str(error.orig).lower()
    return (
        "appointments.client_user_id" in message
        and "appointments.idempotency_key" in message
    )


def _is_overlap_violation(error: IntegrityError) -> bool:
    return (
        _constraint_name(error) == "ex_appointments_employee_time_active"
        or getattr(error.orig, "sqlstate", None) == "23P01"
    )


class BookingService:
    def __init__(
        self,
        session: Session,
        slot_interval_minutes: int = 15,
        now_provider: Callable[[], datetime] | None = None,
    ):
        self.session = session
        self.availability = AvailabilityService(session, slot_interval_minutes)
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def create(
        self,
        client: User,
        *,
        branch_id: UUID,
        employee_id: UUID,
        service_id: UUID,
        starts_at: datetime,
        client_note: str | None,
        idempotency_key: str,
    ) -> BookingCreateResult:
        if client.role is not UserRole.CLIENT:
            raise BookingError(
                "CLIENT_ROLE_REQUIRED", "Only clients can create appointments", 403
            )
        key = idempotency_key.strip()
        if not key:
            raise BookingError(
                "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key must not be blank", 422
            )
        start_utc = _as_utc(starts_at)
        request_fingerprint = _create_request_fingerprint(
            branch_id, employee_id, service_id, start_utc, client_note
        )
        actor_id = client.id
        self._lock_idempotency_key(actor_id, key)
        existing = self._appointment_by_idempotency(actor_id, key)
        if existing is not None:
            self._ensure_same_create_request(existing, request_fingerprint)
            return BookingCreateResult(existing, replayed=True)

        if start_utc <= self._now():
            raise BookingError(
                "BOOKING_IN_PAST", "Appointments cannot be booked in the past", 422
            )

        branch, organization = self._resolve_client_branch(client, branch_id)
        end_utc = self._validate_target_slot(
            branch,
            organization,
            employee_id,
            service_id,
            start_utc,
        )
        appointment_id = uuid4()
        appointment = Appointment(
            id=appointment_id,
            organization_id=organization.id,
            branch_id=branch.id,
            client_user_id=actor_id,
            employee_id=employee_id,
            service_id=service_id,
            starts_at=start_utc,
            ends_at=end_utc,
            status=AppointmentStatus.BOOKED,
            idempotency_key=key,
            idempotency_fingerprint=request_fingerprint,
            client_note=client_note,
        )
        history = AppointmentStatusHistory(
            id=uuid4(),
            appointment_id=appointment_id,
            organization_id=organization.id,
            old_status=None,
            new_status=AppointmentStatus.BOOKED,
            changed_by_user_id=actor_id,
            reason="Appointment created",
        )
        audit = AppointmentAuditLog(
            id=uuid4(),
            appointment_id=appointment_id,
            organization_id=organization.id,
            action=AppointmentAuditAction.CREATED,
            changed_by_user_id=actor_id,
            reason="Appointment created",
            new_starts_at=start_utc,
            new_ends_at=end_utc,
        )
        self.session.add_all([appointment, history, audit])
        try:
            self.session.flush()
        except IntegrityError as error:
            idempotency_violation = _is_idempotency_violation(error)
            overlap_violation = _is_overlap_violation(error)
            self.session.rollback()
            if idempotency_violation:
                existing = self._appointment_by_idempotency(actor_id, key)
                if existing is not None:
                    self._ensure_same_create_request(existing, request_fingerprint)
                    return BookingCreateResult(existing, replayed=True)
            if overlap_violation:
                raise self._slot_booked_error() from None
            raise BookingError(
                "BOOKING_CONFLICT",
                "The appointment could not be created because related data changed",
                409,
            ) from None
        return BookingCreateResult(appointment, replayed=False)

    def create_journey(
        self,
        client: User,
        *,
        branch_id: UUID,
        steps: list[tuple[UUID, UUID, datetime]],
        client_note: str | None,
        idempotency_key: str,
    ) -> JourneyBookingResult:
        if client.role is not UserRole.CLIENT:
            raise BookingError(
                "CLIENT_ROLE_REQUIRED", "Only clients can create appointments", 403
            )
        key = idempotency_key.strip()
        if not key:
            raise BookingError(
                "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key must not be blank", 422
            )
        if not 2 <= len(steps) <= 6:
            raise BookingError(
                "JOURNEY_SERVICE_COUNT_INVALID",
                "Choose between two and six services",
                422,
            )
        self._lock_idempotency_key(client.id, f"journey:{key}")
        step_keys = [
            f"journey:{sha256(key.encode()).hexdigest()}:{index}"
            for index in range(len(steps))
        ]
        fingerprints = [
            _create_request_fingerprint(
                branch_id,
                employee_id,
                service_id,
                _as_utc(starts_at),
                client_note,
            )
            for service_id, employee_id, starts_at in steps
        ]
        existing = [
            self._appointment_by_idempotency(client.id, step_key)
            for step_key in step_keys
        ]
        if any(existing):
            if not all(existing):
                raise BookingError(
                    "JOURNEY_IDEMPOTENCY_CONFLICT",
                    "The journey retry state is incomplete",
                    409,
                )
            appointments = [item for item in existing if item is not None]
            for appointment, fingerprint in zip(
                appointments, fingerprints, strict=True
            ):
                self._ensure_same_create_request(appointment, fingerprint)
            return JourneyBookingResult(appointments, replayed=True)

        branch, organization = self._resolve_client_branch(client, branch_id)
        prepared: list[tuple[UUID, UUID, datetime, datetime]] = []
        previous_end: datetime | None = None
        for service_id, employee_id, starts_at in steps:
            start_utc = _as_utc(starts_at)
            if start_utc <= self._now():
                raise BookingError(
                    "BOOKING_IN_PAST", "Appointments cannot be booked in the past", 422
                )
            if previous_end is not None and start_utc < previous_end:
                raise BookingError(
                    "JOURNEY_STEPS_OVERLAP",
                    "Journey steps must be ordered and non-overlapping",
                    422,
                )
            try:
                end_utc = self._validate_target_slot(
                    branch,
                    organization,
                    employee_id,
                    service_id,
                    start_utc,
                )
            except BookingError as error:
                if error.status_code == 409:
                    raise BookingError(
                        "JOURNEY_CONFLICT",
                        "One journey step is no longer available; recalculate the route",
                        409,
                    ) from None
                raise
            prepared.append((service_id, employee_id, start_utc, end_utc))
            previous_end = end_utc

        appointments: list[Appointment] = []
        for index, (service_id, employee_id, starts_at, ends_at) in enumerate(
            prepared
        ):
            appointment = Appointment(
                id=uuid4(),
                organization_id=organization.id,
                branch_id=branch.id,
                client_user_id=client.id,
                employee_id=employee_id,
                service_id=service_id,
                starts_at=starts_at,
                ends_at=ends_at,
                status=AppointmentStatus.BOOKED,
                idempotency_key=step_keys[index],
                idempotency_fingerprint=fingerprints[index],
                client_note=client_note,
            )
            self.session.add_all(
                [
                    appointment,
                    AppointmentStatusHistory(
                        appointment_id=appointment.id,
                        organization_id=organization.id,
                        old_status=None,
                        new_status=AppointmentStatus.BOOKED,
                        changed_by_user_id=client.id,
                        reason="Multi-service journey created",
                    ),
                    AppointmentAuditLog(
                        appointment_id=appointment.id,
                        organization_id=organization.id,
                        action=AppointmentAuditAction.CREATED,
                        changed_by_user_id=client.id,
                        reason="Multi-service journey created",
                        new_starts_at=starts_at,
                        new_ends_at=ends_at,
                    ),
                ]
            )
            appointments.append(appointment)
        try:
            self.session.flush()
        except IntegrityError as error:
            overlap = _is_overlap_violation(error)
            self.session.rollback()
            if overlap:
                raise BookingError(
                    "JOURNEY_CONFLICT",
                    "One journey step is no longer available; recalculate the route",
                    409,
                ) from None
            replayed = [
                self._appointment_by_idempotency(client.id, step_key)
                for step_key in step_keys
            ]
            if all(replayed):
                values = [item for item in replayed if item is not None]
                for appointment, fingerprint in zip(
                    values, fingerprints, strict=True
                ):
                    self._ensure_same_create_request(appointment, fingerprint)
                return JourneyBookingResult(values, replayed=True)
            raise BookingError(
                "JOURNEY_CONFLICT",
                "The journey could not be created because related data changed",
                409,
            ) from None
        return JourneyBookingResult(appointments, replayed=False)

    def list_my(
        self,
        client: User,
        *,
        view: Literal["all", "upcoming", "past", "cancelled"] = "all",
        appointment_status: AppointmentStatus | None = None,
    ) -> list[Appointment]:
        if client.role is not UserRole.CLIENT:
            raise BookingError(
                "CLIENT_ROLE_REQUIRED", "Only clients have a personal appointment list", 403
            )
        statement = self._with_resources(
            select(Appointment).where(Appointment.client_user_id == client.id)
        )
        now = self._now()
        if view == "upcoming":
            statement = statement.where(
                Appointment.starts_at >= now,
                Appointment.status != AppointmentStatus.CANCELLED,
            )
        elif view == "past":
            statement = statement.where(
                Appointment.ends_at <= now,
                Appointment.status != AppointmentStatus.CANCELLED,
            )
        elif view == "cancelled":
            statement = statement.where(
                Appointment.status == AppointmentStatus.CANCELLED
            )
        if appointment_status is not None:
            statement = statement.where(Appointment.status == appointment_status)
        statement = statement.order_by(Appointment.starts_at, Appointment.id).limit(100)
        return list(self.session.scalars(statement))

    def get_authorized(self, appointment_id: UUID, actor: User) -> Appointment:
        return self._load_authorized(appointment_id, actor, for_update=False)

    def cancel(
        self, appointment_id: UUID, actor: User, reason: str | None
    ) -> Appointment:
        appointment = self._load_authorized(appointment_id, actor, for_update=True)
        now = self._now()
        if actor.role is UserRole.CLIENT and _as_utc(appointment.starts_at) <= now:
            raise BookingError(
                "CANCELLATION_WINDOW_CLOSED",
                "Clients can only cancel future appointments",
                409,
            )
        old_status = appointment.status
        AppointmentLifecycle.ensure_transition(old_status, AppointmentStatus.CANCELLED)
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancelled_at = now
        appointment.cancellation_reason = reason
        self._record_status_change(
            appointment, actor.id, old_status, AppointmentStatus.CANCELLED, reason
        )
        self._record_audit(
            appointment,
            actor.id,
            AppointmentAuditAction.CANCELLED,
            reason,
            old_starts_at=_as_utc(appointment.starts_at),
            old_ends_at=_as_utc(appointment.ends_at),
        )
        self._flush_action("CANCELLATION_CONFLICT")
        match_released_slot(self.session, appointment, appointment.starts_at)
        return appointment

    def reschedule(
        self,
        appointment_id: UUID,
        actor: User,
        starts_at: datetime,
        reason: str | None,
    ) -> Appointment:
        appointment = self._load_authorized(appointment_id, actor, for_update=True)
        now = self._now()
        if appointment.status not in {
            AppointmentStatus.BOOKED,
            AppointmentStatus.CONFIRMED,
        }:
            raise BookingError(
                "APPOINTMENT_NOT_RESCHEDULABLE",
                "Only booked or confirmed appointments can be rescheduled",
                409,
            )
        if actor.role is UserRole.CLIENT and _as_utc(appointment.starts_at) <= now:
            raise BookingError(
                "RESCHEDULE_WINDOW_CLOSED",
                "Clients can only reschedule future appointments",
                409,
            )
        start_utc = _as_utc(starts_at)
        if start_utc <= now:
            raise BookingError(
                "BOOKING_IN_PAST", "Appointments cannot be moved into the past", 422
            )
        if start_utc == _as_utc(appointment.starts_at):
            raise BookingError(
                "APPOINTMENT_TIME_UNCHANGED", "The new start time is unchanged", 409
            )
        branch = self.session.get(Branch, appointment.branch_id)
        organization = self.session.get(Organization, appointment.organization_id)
        if branch is None or organization is None:
            raise BookingError(
                "APPOINTMENT_SCOPE_NOT_FOUND", "Appointment scope not found", 404
            )
        new_end = self._validate_target_slot(
            branch,
            organization,
            appointment.employee_id,
            appointment.service_id,
            start_utc,
            exclude_appointment_id=appointment.id,
        )
        old_start = _as_utc(appointment.starts_at)
        old_end = _as_utc(appointment.ends_at)
        appointment.starts_at = start_utc
        appointment.ends_at = new_end
        self._record_audit(
            appointment,
            actor.id,
            AppointmentAuditAction.RESCHEDULED,
            reason,
            old_starts_at=old_start,
            old_ends_at=old_end,
            new_starts_at=start_utc,
            new_ends_at=new_end,
        )
        try:
            self.session.flush()
        except IntegrityError as error:
            overlap_violation = _is_overlap_violation(error)
            self.session.rollback()
            if overlap_violation:
                raise self._slot_booked_error() from None
            raise BookingError(
                "RESCHEDULE_CONFLICT",
                "The appointment could not be rescheduled because related data changed",
                409,
            ) from None
        match_released_slot(self.session, appointment, old_start)
        return appointment

    def change_status(
        self,
        appointment_id: UUID,
        actor: User,
        new_status: AppointmentStatus,
        reason: str | None,
    ) -> Appointment:
        if actor.role not in {UserRole.EMPLOYEE, UserRole.ADMIN}:
            raise BookingError(
                "STATUS_MANAGEMENT_FORBIDDEN",
                "Only the assigned employee or an organization admin can change status",
                403,
            )
        if new_status is AppointmentStatus.CANCELLED:
            raise BookingError(
                "USE_CANCELLATION_ENDPOINT",
                "Cancellation must use the cancellation endpoint",
                422,
            )
        appointment = self._load_authorized(appointment_id, actor, for_update=True)
        old_status = appointment.status
        AppointmentLifecycle.ensure_transition(old_status, new_status)
        appointment.status = new_status
        self._record_status_change(
            appointment, actor.id, old_status, new_status, reason
        )
        self._record_audit(
            appointment,
            actor.id,
            AppointmentAuditAction.STATUS_CHANGED,
            reason,
        )
        self._flush_action("STATUS_CHANGE_CONFLICT")
        return appointment

    def _resolve_client_branch(
        self, client: User, branch_id: UUID
    ) -> tuple[Branch, Organization]:
        branch = self.session.get(Branch, branch_id)
        if branch is None:
            raise BookingError("BOOKING_SCOPE_NOT_FOUND", "Booking scope not found", 404)
        organization = self.session.get(Organization, branch.organization_id)
        membership = self.session.get(
            OrganizationMembership,
            {"user_id": client.id, "organization_id": branch.organization_id},
        )
        if organization is None or membership is None:
            raise BookingError("BOOKING_SCOPE_NOT_FOUND", "Booking scope not found", 404)
        return branch, organization

    def _validate_target_slot(
        self,
        branch: Branch,
        organization: Organization,
        employee_id: UUID,
        service_id: UUID,
        start_utc: datetime,
        exclude_appointment_id: UUID | None = None,
    ) -> datetime:
        timezone_name = branch.timezone or organization.timezone
        try:
            zone = ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError):
            raise BookingError(
                "INVALID_TIMEZONE_CONFIGURATION",
                "Branch or organization timezone is invalid",
                422,
            ) from None
        local_date = start_utc.astimezone(zone).date()
        try:
            availability = self.availability.calculate(
                branch.id,
                employee_id,
                service_id,
                local_date,
                exclude_appointment_id=exclude_appointment_id,
            )
        except AvailabilityError as error:
            raise BookingError(error.code, error.message, error.status_code) from None
        proposed_end = start_utc + timedelta(
            minutes=availability.service_duration_minutes
        )
        if self._has_overlap(
            employee_id,
            start_utc,
            proposed_end,
            exclude_appointment_id=exclude_appointment_id,
        ):
            raise self._slot_booked_error()
        for slot in availability.slots:
            if _as_utc(slot.start) == start_utc:
                return _as_utc(slot.end)
        raise BookingError(
            "SLOT_UNAVAILABLE",
            "The requested start is not an available service slot",
            409,
        )

    def _has_overlap(
        self,
        employee_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        *,
        exclude_appointment_id: UUID | None,
    ) -> bool:
        statement = select(Appointment.id).where(
            Appointment.employee_id == employee_id,
            Appointment.starts_at < ends_at,
            Appointment.ends_at > starts_at,
            Appointment.status.in_(OCCUPYING_APPOINTMENT_STATUSES),
        )
        if exclude_appointment_id is not None:
            statement = statement.where(Appointment.id != exclude_appointment_id)
        return self.session.scalar(statement.limit(1)) is not None

    def _appointment_by_idempotency(
        self, client_user_id: UUID, key: str
    ) -> Appointment | None:
        return self.session.scalar(
            self._with_resources(select(Appointment)).where(
                Appointment.client_user_id == client_user_id,
                Appointment.idempotency_key == key,
            )
        )

    def _lock_idempotency_key(self, client_user_id: UUID, key: str) -> None:
        if self.session.get_bind().dialect.name != "postgresql":
            return
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"slotbridge:booking:{client_user_id}:{key}"},
        )

    def _ensure_same_create_request(
        self,
        appointment: Appointment,
        request_fingerprint: str,
    ) -> None:
        if appointment.idempotency_fingerprint != request_fingerprint:
            raise BookingError(
                "IDEMPOTENCY_KEY_REUSED",
                "This Idempotency-Key was already used for a different request",
                409,
            )

    def _load_authorized(
        self, appointment_id: UUID, actor: User, *, for_update: bool
    ) -> Appointment:
        statement = self._with_resources(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        if for_update:
            statement = statement.with_for_update()
        appointment = self.session.scalar(statement)
        if appointment is None or not self._can_access(appointment, actor):
            raise BookingError("APPOINTMENT_NOT_FOUND", "Appointment not found", 404)
        return appointment

    def _can_access(self, appointment: Appointment, actor: User) -> bool:
        if actor.role is UserRole.CLIENT:
            return appointment.client_user_id == actor.id
        if actor.role is UserRole.EMPLOYEE:
            return (
                self.session.scalar(
                    select(Employee.id).where(
                        Employee.id == appointment.employee_id,
                        Employee.user_id == actor.id,
                        Employee.organization_id == appointment.organization_id,
                        Employee.branch_id == appointment.branch_id,
                        Employee.is_active.is_(True),
                    )
                )
                is not None
            )
        if actor.role is UserRole.ADMIN:
            return (
                self.session.get(
                    OrganizationMembership,
                    {
                        "user_id": actor.id,
                        "organization_id": appointment.organization_id,
                    },
                )
                is not None
            )
        return False

    @staticmethod
    def _with_resources(statement):
        return statement.options(
            selectinload(Appointment.organization),
            selectinload(Appointment.branch),
            selectinload(Appointment.employee),
            selectinload(Appointment.service),
            selectinload(Appointment.client),
        )

    def _record_status_change(
        self,
        appointment: Appointment,
        actor_id: UUID,
        old_status: AppointmentStatus,
        new_status: AppointmentStatus,
        reason: str | None,
    ) -> None:
        self.session.add(
            AppointmentStatusHistory(
                appointment_id=appointment.id,
                organization_id=appointment.organization_id,
                old_status=old_status,
                new_status=new_status,
                changed_by_user_id=actor_id,
                reason=reason,
            )
        )

    def _record_audit(
        self,
        appointment: Appointment,
        actor_id: UUID,
        action: AppointmentAuditAction,
        reason: str | None,
        *,
        old_starts_at: datetime | None = None,
        old_ends_at: datetime | None = None,
        new_starts_at: datetime | None = None,
        new_ends_at: datetime | None = None,
    ) -> None:
        self.session.add(
            AppointmentAuditLog(
                appointment_id=appointment.id,
                organization_id=appointment.organization_id,
                action=action,
                changed_by_user_id=actor_id,
                reason=reason,
                old_starts_at=old_starts_at,
                old_ends_at=old_ends_at,
                new_starts_at=new_starts_at,
                new_ends_at=new_ends_at,
            )
        )

    def _flush_action(self, code: str) -> None:
        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            raise BookingError(
                code,
                "The appointment could not be changed because related data changed",
                409,
            ) from None

    def _now(self) -> datetime:
        return _as_utc(self.now_provider())

    @staticmethod
    def _slot_booked_error() -> BookingError:
        return BookingError(
            "SLOT_ALREADY_BOOKED",
            "This time slot is no longer available.",
            409,
        )
