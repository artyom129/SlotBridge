from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import (
    Appointment,
    AppointmentAuditLog,
    AppointmentStatusHistory,
    BlockedSlot,
    Branch,
    Employee,
    EmployeeService,
    Organization,
    OrganizationMembership,
    ScheduleBreak,
    ScheduleException,
    Service,
    User,
    UserRole,
    WorkSchedule,
)
from app.security import hash_password
from scripts.seed_domain import DEMO_PASSWORD, seed


def test_domain_relationships_and_employee_service_link(session):
    organization = Organization(name="Test Org", slug="test-org", timezone="UTC")
    user = User(
        email="employee@example.com",
        password_hash=hash_password("Employee-Test-2026!"),
        first_name="Test",
        last_name="Employee",
        role=UserRole.EMPLOYEE,
    )
    session.add_all([organization, user])
    session.flush()
    branch = Branch(
        organization_id=organization.id,
        name="Branch One",
        address="Test address",
    )
    service = Service(
        organization_id=organization.id,
        name="Consultation",
        description="Test service",
        duration_minutes=30,
        price=Decimal("10.00"),
    )
    session.add_all([branch, service])
    session.flush()
    employee = Employee(
        user_id=user.id,
        organization_id=organization.id,
        branch_id=branch.id,
        display_name="Test Employee",
    )
    session.add(employee)
    session.flush()
    session.add(
        EmployeeService(
            employee_id=employee.id,
            service_id=service.id,
            organization_id=organization.id,
        )
    )
    session.commit()

    assert employee.organization.id == organization.id
    assert employee.branch.id == branch.id
    assert employee.service_links[0].service.id == service.id
    assert organization.branches[0].id == branch.id


def test_employee_branch_must_belong_to_same_organization(session):
    first = Organization(name="First", slug="first", timezone="UTC")
    second = Organization(name="Second", slug="second", timezone="UTC")
    user = User(
        email="wrong-branch@example.com",
        password_hash=hash_password("Employee-Test-2026!"),
        first_name="Wrong",
        last_name="Branch",
        role=UserRole.EMPLOYEE,
    )
    session.add_all([first, second, user])
    session.flush()
    branch = Branch(organization_id=first.id, name="First Branch", address="Test")
    session.add(branch)
    session.flush()
    session.add(
        Employee(
            user_id=user.id,
            organization_id=second.id,
            branch_id=branch.id,
            display_name="Invalid Employee",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_employee_service_must_belong_to_same_organization(session):
    first = Organization(name="First", slug="first", timezone="UTC")
    second = Organization(name="Second", slug="second", timezone="UTC")
    user = User(
        email="cross-tenant@example.com",
        password_hash=hash_password("Employee-Test-2026!"),
        first_name="Cross",
        last_name="Tenant",
        role=UserRole.EMPLOYEE,
    )
    session.add_all([first, second, user])
    session.flush()
    branch = Branch(organization_id=first.id, name="First Branch", address="Test")
    service = Service(
        organization_id=second.id,
        name="Other Tenant Service",
        description="Must not be assignable",
        duration_minutes=30,
    )
    session.add_all([branch, service])
    session.flush()
    employee = Employee(
        user_id=user.id,
        organization_id=first.id,
        branch_id=branch.id,
        display_name="Cross Tenant Employee",
    )
    session.add(employee)
    session.flush()
    session.add(
        EmployeeService(
            employee_id=employee.id,
            service_id=service.id,
            organization_id=first.id,
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_seed_is_idempotent_and_core_api_reads_relationships(client):
    with SessionLocal.begin() as session:
        existing_client = User(
            email="existing.client@example.com",
            password_hash=hash_password("Existing-Client-2026!"),
            first_name="Existing",
            last_name="Client",
            role=UserRole.CLIENT,
            is_active=True,
        )
        session.add(existing_client)
        session.flush()
        existing_client_id = existing_client.id

    seed()
    seed()

    assert client.get("/organizations").status_code == 401

    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Organization)) == 1
        assert session.scalar(select(func.count()).select_from(Branch)) == 1
        assert session.scalar(select(func.count()).select_from(Service)) == 3
        assert session.scalar(select(func.count()).select_from(Employee)) == 2
        assert session.scalar(select(func.count()).select_from(EmployeeService)) == 4
        assert session.scalar(select(func.count()).select_from(User)) == 6
        assert session.scalar(select(func.count()).select_from(WorkSchedule)) == 10
        assert session.scalar(select(func.count()).select_from(ScheduleBreak)) == 5
        assert session.scalar(select(func.count()).select_from(ScheduleException)) == 1
        assert session.scalar(select(func.count()).select_from(BlockedSlot)) == 1
        assert session.scalar(select(func.count()).select_from(OrganizationMembership)) == 6
        assert session.scalar(select(func.count()).select_from(Appointment)) == 4
        assert session.scalar(select(func.count()).select_from(AppointmentStatusHistory)) == 4
        assert session.scalar(select(func.count()).select_from(AppointmentAuditLog)) == 4
        organization = session.scalar(select(Organization))
        branch = session.scalar(select(Branch))
        assert organization.timezone == "Asia/Almaty"
        assert branch.timezone == "Asia/Almaty"
        assert (
            session.get(
                OrganizationMembership,
                {
                    "user_id": existing_client_id,
                    "organization_id": organization.id,
                },
            )
            is not None
        )

    login = client.post(
        "/auth/login",
        json={"email": "client.a@slotbridge-demo.com", "password": DEMO_PASSWORD},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    organizations = client.get("/organizations", headers=headers)
    assert organizations.status_code == 200
    organization_id = organizations.json()[0]["id"]

    assert client.get(f"/organizations/{organization_id}", headers=headers).status_code == 200
    branches = client.get(f"/organizations/{organization_id}/branches", headers=headers)
    services = client.get(f"/organizations/{organization_id}/services", headers=headers)
    employees = client.get(f"/organizations/{organization_id}/employees", headers=headers)
    assert len(branches.json()) == 1
    assert len(services.json()) == 3
    assert len(employees.json()) == 2

    employee_services = client.get(
        f"/employees/{employees.json()[0]['id']}/services", headers=headers
    )
    assert employee_services.status_code == 200
    assert len(employee_services.json()) == 2
