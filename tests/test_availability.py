from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import event

from app.models import (
    BlockedSlot,
    Branch,
    Employee,
    EmployeeService,
    Organization,
    ScheduleBreak,
    ScheduleException,
    Service,
    User,
    UserRole,
    WorkSchedule,
)
from app.security import hash_password
from app.services.availability import AvailabilityError, AvailabilityService


MONDAY = date(2026, 9, 21)


@dataclass
class Domain:
    organization: Organization
    branch: Branch
    employee: Employee
    service: Service
    employee_user: User


def make_domain(
    session,
    *,
    timezone_name: str = "UTC",
    branch_timezone: str | None = None,
    duration: int = 60,
    assigned: bool = True,
    employee_active: bool = True,
    service_active: bool = True,
    branch_active: bool = True,
    organization_active: bool = True,
) -> Domain:
    marker = uuid4().hex
    organization = Organization(
        name=f"Organization {marker}",
        slug=f"org-{marker}",
        timezone=timezone_name,
        is_active=organization_active,
    )
    employee_user = User(
        email=f"employee-{marker}@example.com",
        password_hash=hash_password("Availability-Test-2026!"),
        first_name="Test",
        last_name="Employee",
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    session.add_all([organization, employee_user])
    session.flush()
    branch = Branch(
        organization_id=organization.id,
        name="Main Branch",
        address="Test address",
        timezone=branch_timezone,
        is_active=branch_active,
    )
    service = Service(
        organization_id=organization.id,
        name="Test Service",
        description="Availability test",
        duration_minutes=duration,
        price=Decimal("10.00"),
        is_active=service_active,
    )
    session.add_all([branch, service])
    session.flush()
    employee = Employee(
        user_id=employee_user.id,
        organization_id=organization.id,
        branch_id=branch.id,
        display_name="Test Employee",
        is_active=employee_active,
    )
    session.add(employee)
    session.flush()
    if assigned:
        session.add(
            EmployeeService(
                employee_id=employee.id,
                service_id=service.id,
                organization_id=organization.id,
            )
        )
        session.flush()
    return Domain(organization, branch, employee, service, employee_user)


def add_work(session, domain: Domain, start: time, end: time) -> None:
    session.add(
        WorkSchedule(
            employee_id=domain.employee.id,
            branch_id=domain.branch.id,
            organization_id=domain.organization.id,
            day_of_week=MONDAY.weekday(),
            start_time=start,
            end_time=end,
        )
    )
    session.flush()


def add_break(session, domain: Domain, start: time, end: time) -> None:
    session.add(
        ScheduleBreak(
            employee_id=domain.employee.id,
            branch_id=domain.branch.id,
            organization_id=domain.organization.id,
            day_of_week=MONDAY.weekday(),
            start_time=start,
            end_time=end,
        )
    )
    session.flush()


def add_block(session, domain: Domain, start: datetime, end: datetime) -> None:
    session.add(
        BlockedSlot(
            employee_id=domain.employee.id,
            branch_id=domain.branch.id,
            organization_id=domain.organization.id,
            starts_at=start.astimezone(timezone.utc),
            ends_at=end.astimezone(timezone.utc),
            reason="Test block",
            created_by_user_id=domain.employee_user.id,
        )
    )
    session.flush()


def calculate(session, domain: Domain):
    return AvailabilityService(session).calculate(
        domain.branch.id, domain.employee.id, domain.service.id, MONDAY
    )


def start_times(result) -> list[str]:
    return [item.start.strftime("%H:%M") for item in result.slots]


def test_normal_working_day_returns_exact_60_minute_slots(session):
    domain = make_domain(session, duration=60)
    add_work(session, domain, time(9), time(12))

    result = calculate(session, domain)

    assert start_times(result) == [
        "09:00", "09:15", "09:30", "09:45", "10:00",
        "10:15", "10:30", "10:45", "11:00",
    ]
    assert result.slots[-1].end.strftime("%H:%M") == "12:00"


def test_configurable_slot_interval_changes_the_start_grid(session):
    domain = make_domain(session, duration=60)
    add_work(session, domain, time(9), time(12))

    result = AvailabilityService(session, slot_interval_minutes=30).calculate(
        domain.branch.id, domain.employee.id, domain.service.id, MONDAY
    )

    assert start_times(result) == ["09:00", "09:30", "10:00", "10:30", "11:00"]
    assert result.slot_interval_minutes == 30


def test_weekday_without_work_schedule_is_unavailable(session):
    domain = make_domain(session)

    assert calculate(session, domain).slots == []


@pytest.mark.parametrize(
    ("duration", "count", "last_start"),
    [(30, 11, "11:30"), (60, 9, "11:00"), (90, 7, "10:30")],
)
def test_service_duration_controls_exact_slots(session, duration, count, last_start):
    domain = make_domain(session, duration=duration)
    add_work(session, domain, time(9), time(12))

    result = calculate(session, domain)

    assert len(result.slots) == count
    assert start_times(result)[0] == "09:00"
    assert start_times(result)[-1] == last_start
    assert result.service_duration_minutes == duration


def test_break_removes_every_slot_that_would_overlap_it(session):
    domain = make_domain(session)
    add_work(session, domain, time(9), time(13))
    add_break(session, domain, time(10), time(11))

    assert start_times(calculate(session, domain)) == [
        "09:00", "11:00", "11:15", "11:30", "11:45", "12:00"
    ]


def test_blocked_slot_removes_every_slot_that_would_overlap_it(session):
    domain = make_domain(session)
    add_work(session, domain, time(9), time(13))
    add_block(
        session,
        domain,
        datetime(2026, 9, 21, 10, tzinfo=timezone.utc),
        datetime(2026, 9, 21, 11, tzinfo=timezone.utc),
    )

    assert start_times(calculate(session, domain)) == [
        "09:00", "11:00", "11:15", "11:30", "11:45", "12:00"
    ]


def test_multiple_work_intervals_keep_separate_availability(session):
    domain = make_domain(session)
    add_work(session, domain, time(9), time(11))
    add_work(session, domain, time(13), time(15))

    assert start_times(calculate(session, domain)) == [
        "09:00", "09:15", "09:30", "09:45", "10:00",
        "13:00", "13:15", "13:30", "13:45", "14:00",
    ]


def test_day_off_exception_overrides_recurring_schedule(session):
    domain = make_domain(session)
    add_work(session, domain, time(9), time(18))
    session.add(
        ScheduleException(
            employee_id=domain.employee.id,
            branch_id=domain.branch.id,
            organization_id=domain.organization.id,
            local_date=MONDAY,
            is_day_off=True,
        )
    )
    session.flush()

    assert calculate(session, domain).slots == []


def test_replacement_exception_replaces_instead_of_extending_recurring_schedule(session):
    domain = make_domain(session)
    add_work(session, domain, time(9), time(18))
    session.add(
        ScheduleException(
            employee_id=domain.employee.id,
            branch_id=domain.branch.id,
            organization_id=domain.organization.id,
            local_date=MONDAY,
            is_day_off=False,
            start_time=time(12),
            end_time=time(16),
        )
    )
    session.flush()

    starts = start_times(calculate(session, domain))
    assert starts == [
        "12:00", "12:15", "12:30", "12:45", "13:00", "13:15", "13:30",
        "13:45", "14:00", "14:15", "14:30", "14:45", "15:00",
    ]


def test_overlapping_breaks_are_merged_before_subtraction(session):
    domain = make_domain(session)
    add_work(session, domain, time(9), time(13))
    add_break(session, domain, time(10), time(11))
    add_break(session, domain, time(10, 30), time(11, 30))

    assert start_times(calculate(session, domain)) == [
        "09:00", "11:30", "11:45", "12:00"
    ]


def test_overlapping_blocks_and_outside_work_are_merged_and_clipped(session):
    domain = make_domain(session)
    add_work(session, domain, time(9), time(13))
    zone = timezone.utc
    add_block(session, domain, datetime(2026, 9, 21, 8, tzinfo=zone), datetime(2026, 9, 21, 10, 30, tzinfo=zone))
    add_block(session, domain, datetime(2026, 9, 21, 10, tzinfo=zone), datetime(2026, 9, 21, 11, 30, tzinfo=zone))

    assert start_times(calculate(session, domain)) == ["11:30", "11:45", "12:00"]


def test_service_longer_than_every_free_interval_returns_no_slots(session):
    domain = make_domain(session, duration=90)
    add_work(session, domain, time(9), time(10))

    assert calculate(session, domain).slots == []


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"employee_active": False}, "EMPLOYEE_INACTIVE"),
        ({"service_active": False}, "SERVICE_INACTIVE"),
        ({"branch_active": False}, "BRANCH_INACTIVE"),
        ({"organization_active": False}, "ORGANIZATION_INACTIVE"),
        ({"assigned": False}, "EMPLOYEE_SERVICE_MISMATCH"),
    ],
)
def test_invalid_availability_scope_has_explicit_domain_error(session, overrides, code):
    domain = make_domain(session, **overrides)
    add_work(session, domain, time(9), time(12))

    with pytest.raises(AvailabilityError) as raised:
        calculate(session, domain)

    assert raised.value.code == code


def test_cross_tenant_request_is_hidden_as_not_found(session):
    domain = make_domain(session)
    other = make_domain(session)
    add_work(session, domain, time(9), time(12))

    with pytest.raises(AvailabilityError) as raised:
        AvailabilityService(session).calculate(
            domain.branch.id, domain.employee.id, other.service.id, MONDAY
        )

    assert raised.value.code == "RESOURCE_NOT_FOUND"
    assert raised.value.status_code == 404


@pytest.mark.parametrize(
    ("timezone_name", "expected_offset"),
    [("Asia/Almaty", "+0500"), ("America/New_York", "-0400")],
)
def test_effective_timezone_is_applied_to_returned_slots(
    session, timezone_name, expected_offset
):
    domain = make_domain(session, timezone_name="UTC", branch_timezone=timezone_name)
    add_work(session, domain, time(9), time(11))

    result = calculate(session, domain)

    assert result.timezone_name == timezone_name
    assert result.slots[0].start.strftime("%H:%M %z") == f"09:00 {expected_offset}"


def test_organization_timezone_is_used_without_branch_override(session):
    domain = make_domain(session, timezone_name="Asia/Almaty")
    add_work(session, domain, time(9), time(11))

    result = calculate(session, domain)

    assert result.timezone_name == "Asia/Almaty"
    assert result.slots[0].start.utcoffset().total_seconds() == 5 * 3600


def test_dst_transition_uses_absolute_service_duration(session):
    spring_forward = date(2026, 3, 8)
    domain = make_domain(session, branch_timezone="America/New_York", duration=60)
    session.add(
        WorkSchedule(
            employee_id=domain.employee.id,
            branch_id=domain.branch.id,
            organization_id=domain.organization.id,
            day_of_week=spring_forward.weekday(),
            start_time=time(0),
            end_time=time(4),
        )
    )
    session.flush()

    result = AvailabilityService(session).calculate(
        domain.branch.id, domain.employee.id, domain.service.id, spring_forward
    )

    assert len(result.slots) == 9
    assert all(item.start.hour != 2 for item in result.slots)
    assert any(item.start.hour == 1 and item.end.hour == 3 for item in result.slots)
    assert all(
        (item.end.astimezone(timezone.utc) - item.start.astimezone(timezone.utc)).seconds
        == 3600
        for item in result.slots
    )


def test_invalid_timezone_configuration_returns_explicit_error(session):
    domain = make_domain(session, branch_timezone="Invalid/Timezone")
    add_work(session, domain, time(9), time(11))

    with pytest.raises(AvailabilityError) as raised:
        calculate(session, domain)

    assert raised.value.code == "INVALID_TIMEZONE_CONFIGURATION"


def test_availability_api_is_authenticated_and_returns_exact_schema(client, session):
    domain = make_domain(session, timezone_name="Asia/Almaty", duration=30)
    add_work(session, domain, time(9), time(10))
    session.commit()
    login = client.post(
        "/auth/login",
        json={"email": domain.employee_user.email, "password": "Availability-Test-2026!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    params = {
        "branch_id": str(domain.branch.id),
        "employee_id": str(domain.employee.id),
        "service_id": str(domain.service.id),
        "date": MONDAY.isoformat(),
    }

    assert client.get("/availability", params=params).status_code == 401
    response = client.get("/availability", params=params, headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "date": "2026-09-21",
        "timezone": "Asia/Almaty",
        "service_duration_minutes": 30,
        "slot_interval_minutes": 15,
        "slots": [
            {"start": "2026-09-21T09:00:00+05:00", "end": "2026-09-21T09:30:00+05:00"},
            {"start": "2026-09-21T09:15:00+05:00", "end": "2026-09-21T09:45:00+05:00"},
            {"start": "2026-09-21T09:30:00+05:00", "end": "2026-09-21T10:00:00+05:00"},
        ],
    }


def test_query_count_is_constant_instead_of_per_generated_slot(session):
    domain = make_domain(session, duration=60)
    add_work(session, domain, time(9), time(18))
    session.commit()
    session.expunge_all()
    statements: list[str] = []

    def record_query(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    bind = session.get_bind()
    event.listen(bind, "before_cursor_execute", record_query)
    try:
        result = calculate(session, domain)
    finally:
        event.remove(bind, "before_cursor_execute", record_query)

    assert len(result.slots) == 33
    # Stage 4 adds one set-based appointment-overlap query, still independent of
    # the number of generated candidates.
    assert len(statements) == 10
