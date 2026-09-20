from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Branch, Employee, EmployeeService, OrganizationMembership, Service, User
from app.services.availability import AvailabilityService
from app.services.booking import BookingError


@dataclass(frozen=True)
class JourneyStep:
    service_id: UUID
    service_name: str
    employee_id: UUID
    employee_name: str
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class JourneyRoute:
    strategy: str
    steps: tuple[JourneyStep, ...]
    total_minutes: int
    wait_minutes: int
    employee_count: int


class JourneyPlanner:
    def __init__(self, session: Session, slot_interval_minutes: int = 15):
        self.session = session
        self.availability = AvailabilityService(session, slot_interval_minutes)

    def plan(
        self,
        client: User,
        *,
        branch_id: UUID,
        service_ids: list[UUID],
        local_date: date,
        after_time: time,
        before_time: time,
    ) -> tuple[str, list[JourneyRoute]]:
        if not 2 <= len(service_ids) <= 6:
            raise BookingError(
                "JOURNEY_SERVICE_COUNT_INVALID",
                "Choose between two and six services",
                422,
            )
        branch = self.session.get(Branch, branch_id)
        if branch is None:
            raise BookingError("BOOKING_SCOPE_NOT_FOUND", "Booking scope not found", 404)
        membership = self.session.get(
            OrganizationMembership,
            {"user_id": client.id, "organization_id": branch.organization_id},
        )
        if membership is None:
            raise BookingError("BOOKING_SCOPE_NOT_FOUND", "Booking scope not found", 404)
        if after_time >= before_time:
            raise BookingError(
                "JOURNEY_TIME_RANGE_INVALID",
                "The end time must be later than the start time",
                422,
            )

        zone = ZoneInfo(branch.timezone or branch.organization.timezone)
        lower = datetime.combine(local_date, after_time, zone)
        upper = datetime.combine(local_date, before_time, zone)
        now = datetime.now(timezone.utc)
        options: list[list[JourneyStep]] = []
        for service_id in service_ids:
            service = self.session.get(Service, service_id)
            if (
                service is None
                or service.organization_id != branch.organization_id
                or not service.is_active
            ):
                raise BookingError(
                    "JOURNEY_SERVICE_NOT_FOUND",
                    "A selected service is unavailable",
                    404,
                )
            employees = list(
                self.session.scalars(
                    select(Employee)
                    .join(
                        EmployeeService,
                        EmployeeService.employee_id == Employee.id,
                    )
                    .where(
                        Employee.organization_id == branch.organization_id,
                        Employee.branch_id == branch.id,
                        Employee.is_active.is_(True),
                        EmployeeService.service_id == service.id,
                    )
                    .order_by(Employee.display_name)
                )
            )
            service_options: list[JourneyStep] = []
            for employee in employees:
                availability = self.availability.calculate(
                    branch.id,
                    employee.id,
                    service.id,
                    local_date,
                )
                service_options.extend(
                    JourneyStep(
                        service.id,
                        service.name,
                        employee.id,
                        employee.display_name,
                        slot.start,
                        slot.end,
                    )
                    for slot in availability.slots
                    if slot.start >= lower
                    and slot.end <= upper
                    and slot.start.astimezone(timezone.utc) > now
                )
            service_options.sort(key=lambda item: (item.starts_at, item.employee_name))
            if not service_options:
                return branch.timezone or branch.organization.timezone, []
            options.append(service_options[:120])

        candidates: list[tuple[JourneyStep, ...]] = []

        def build(index: int, current: list[JourneyStep]) -> None:
            if len(candidates) >= 20_000:
                return
            if index == len(options):
                candidates.append(tuple(current))
                return
            earliest = current[-1].ends_at if current else lower
            for option in options[index]:
                if option.starts_at < earliest:
                    continue
                current.append(option)
                build(index + 1, current)
                current.pop()

        build(0, [])
        if not candidates:
            return branch.timezone or branch.organization.timezone, []

        def metrics(route: tuple[JourneyStep, ...]) -> tuple[int, int, int]:
            elapsed = int((route[-1].ends_at - route[0].starts_at).total_seconds() // 60)
            work = sum(
                int((step.ends_at - step.starts_at).total_seconds() // 60)
                for step in route
            )
            return elapsed, elapsed - work, len({step.employee_id for step in route})

        selectors = (
            (
                "FASTEST",
                lambda route: (
                    metrics(route)[0],
                    metrics(route)[1],
                    route[0].starts_at,
                    metrics(route)[2],
                ),
            ),
            (
                "EARLIEST",
                lambda route: (
                    route[0].starts_at,
                    metrics(route)[0],
                    metrics(route)[2],
                ),
            ),
            (
                "FEWEST_EMPLOYEES",
                lambda route: (
                    metrics(route)[2],
                    metrics(route)[0],
                    route[0].starts_at,
                ),
            ),
        )
        routes = []
        for strategy, key in selectors:
            steps = min(candidates, key=key)
            elapsed, waiting, employees = metrics(steps)
            routes.append(
                JourneyRoute(strategy, steps, elapsed, waiting, employees)
            )
        return branch.timezone or branch.organization.timezone, routes
