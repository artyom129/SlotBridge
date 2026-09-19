from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from uuid import uuid4

from app.models import (
    Branch,
    Employee,
    EmployeeService,
    Organization,
    OrganizationMembership,
    Service,
    User,
    UserRole,
    WorkSchedule,
)
from app.security import hash_password


BOOKING_DATE = date(2099, 1, 5)  # Monday
PASSWORD = "Booking-Test-Password-2026!"


@dataclass
class BookingDomain:
    organization: Organization
    branch: Branch
    service: Service
    employee: Employee
    employee_user: User
    admin: User
    client_a: User
    client_b: User


def create_booking_domain(
    session,
    *,
    timezone_name: str = "UTC",
    duration_minutes: int = 60,
    employee_active: bool = True,
    service_active: bool = True,
    branch_active: bool = True,
    organization_active: bool = True,
    with_assignment: bool = True,
) -> BookingDomain:
    marker = uuid4().hex
    password_hash = hash_password(PASSWORD)
    organization = Organization(
        name=f"Booking Org {marker}",
        slug=f"booking-{marker}",
        timezone=timezone_name,
        is_active=organization_active,
    )
    admin = User(
        email=f"admin-{marker}@example.com",
        password_hash=password_hash,
        first_name="Booking",
        last_name="Admin",
        role=UserRole.ADMIN,
    )
    client_a = User(
        email=f"client-a-{marker}@example.com",
        password_hash=password_hash,
        first_name="Client",
        last_name="A",
        role=UserRole.CLIENT,
    )
    client_b = User(
        email=f"client-b-{marker}@example.com",
        password_hash=password_hash,
        first_name="Client",
        last_name="B",
        role=UserRole.CLIENT,
    )
    employee_user = User(
        email=f"employee-{marker}@example.com",
        password_hash=password_hash,
        first_name="Assigned",
        last_name="Employee",
        role=UserRole.EMPLOYEE,
    )
    session.add_all([organization, admin, client_a, client_b, employee_user])
    session.flush()
    for user in (admin, client_a, client_b):
        session.add(
            OrganizationMembership(
                user_id=user.id,
                organization_id=organization.id,
            )
        )
    branch = Branch(
        organization_id=organization.id,
        name="Booking Branch",
        address="Test address",
        timezone=timezone_name,
        is_active=branch_active,
    )
    service = Service(
        organization_id=organization.id,
        name="Booking Service",
        description="Test service",
        duration_minutes=duration_minutes,
        price=Decimal("25.00"),
        is_active=service_active,
    )
    session.add_all([branch, service])
    session.flush()
    employee = Employee(
        user_id=employee_user.id,
        organization_id=organization.id,
        branch_id=branch.id,
        display_name="Assigned Employee",
        is_active=employee_active,
    )
    session.add(employee)
    session.flush()
    if with_assignment:
        session.add(
            EmployeeService(
                employee_id=employee.id,
                service_id=service.id,
                organization_id=organization.id,
            )
        )
    session.add(
        WorkSchedule(
            employee_id=employee.id,
            branch_id=branch.id,
            organization_id=organization.id,
            day_of_week=BOOKING_DATE.weekday(),
            start_time=time(9),
            end_time=time(18),
        )
    )
    session.commit()
    return BookingDomain(
        organization,
        branch,
        service,
        employee,
        employee_user,
        admin,
        client_a,
        client_b,
    )

def auth_headers(client, user: User) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def booking_payload(
    domain: BookingDomain,
    hour: int,
    minute: int = 0,
    *,
    booking_date: date = BOOKING_DATE,
    note: str | None = None,
) -> dict:
    starts_at = datetime(
        booking_date.year,
        booking_date.month,
        booking_date.day,
        hour,
        minute,
        tzinfo=timezone.utc,
    )
    return {
        "branch_id": str(domain.branch.id),
        "employee_id": str(domain.employee.id),
        "service_id": str(domain.service.id),
        "starts_at": starts_at.isoformat().replace("+00:00", "Z"),
        "client_note": note,
    }


def book(
    client,
    domain: BookingDomain,
    user: User,
    key: str,
    hour: int,
    minute: int = 0,
    *,
    booking_date: date = BOOKING_DATE,
):
    return client.post(
        "/appointments",
        json=booking_payload(
            domain,
            hour,
            minute,
            booking_date=booking_date,
        ),
        headers={
            **auth_headers(client, user),
            "Idempotency-Key": key,
        },
    )
