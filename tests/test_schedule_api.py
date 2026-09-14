from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.models import Branch, Employee, Organization, User, UserRole
from app.security import hash_password


PASSWORD = "Schedule-API-Test-2026!"


@dataclass
class ManagementScope:
    branch: Branch
    employee: Employee
    other_employee: Employee
    admin: User
    client: User
    employee_user: User
    other_employee_user: User


def setup_scope(session) -> ManagementScope:
    marker = uuid4().hex
    organization = Organization(
        name="Schedule API Org",
        slug=f"schedule-api-{marker}",
        timezone="Asia/Almaty",
    )
    users = [
        User(
            email=f"admin-{marker}@example.com",
            password_hash=hash_password(PASSWORD),
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
        ),
        User(
            email=f"client-{marker}@example.com",
            password_hash=hash_password(PASSWORD),
            first_name="Client",
            last_name="User",
            role=UserRole.CLIENT,
        ),
        User(
            email=f"employee-{marker}@example.com",
            password_hash=hash_password(PASSWORD),
            first_name="First",
            last_name="Employee",
            role=UserRole.EMPLOYEE,
        ),
        User(
            email=f"other-{marker}@example.com",
            password_hash=hash_password(PASSWORD),
            first_name="Other",
            last_name="Employee",
            role=UserRole.EMPLOYEE,
        ),
    ]
    session.add(organization)
    session.add_all(users)
    session.flush()
    branch = Branch(
        organization_id=organization.id,
        name="Main",
        address="Test",
        timezone="Asia/Almaty",
    )
    session.add(branch)
    session.flush()
    employee = Employee(
        user_id=users[2].id,
        organization_id=organization.id,
        branch_id=branch.id,
        display_name="First Employee",
    )
    other_employee = Employee(
        user_id=users[3].id,
        organization_id=organization.id,
        branch_id=branch.id,
        display_name="Other Employee",
    )
    session.add_all([employee, other_employee])
    session.commit()
    return ManagementScope(
        branch, employee, other_employee, users[0], users[1], users[2], users[3]
    )


def headers_for(client, user: User) -> dict[str, str]:
    response = client.post(
        "/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def recurring_payload(scope: ManagementScope, *, employee: Employee | None = None):
    return {
        "employee_id": str((employee or scope.employee).id),
        "branch_id": str(scope.branch.id),
        "day_of_week": 0,
        "start_time": "09:00:00",
        "end_time": "18:00:00",
        "is_active": True,
    }


def block_payload(scope: ManagementScope, *, employee: Employee | None = None):
    return {
        "employee_id": str((employee or scope.employee).id),
        "branch_id": str(scope.branch.id),
        "starts_at": "2026-09-21T06:00:00Z",
        "ends_at": "2026-09-21T07:00:00Z",
        "reason": "Training",
        "is_active": True,
    }


def test_admin_can_create_and_update_each_schedule_resource(client, session):
    scope = setup_scope(session)
    headers = headers_for(client, scope.admin)

    work = client.post(
        "/admin/work-schedules", json=recurring_payload(scope), headers=headers
    )
    assert work.status_code == 201
    work_update = {**recurring_payload(scope), "end_time": "17:00:00"}
    response = client.put(
        f"/admin/work-schedules/{work.json()['id']}", json=work_update, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["end_time"] == "17:00:00"

    schedule_break = client.post(
        "/admin/schedule-breaks",
        json={
            **recurring_payload(scope),
            "start_time": "13:00:00",
            "end_time": "14:00:00",
        },
        headers=headers,
    )
    assert schedule_break.status_code == 201
    response = client.put(
        f"/admin/schedule-breaks/{schedule_break.json()['id']}",
        json={
            **recurring_payload(scope),
            "start_time": "12:30:00",
            "end_time": "13:30:00",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["start_time"] == "12:30:00"

    exception_payload = {
        "employee_id": str(scope.employee.id),
        "branch_id": str(scope.branch.id),
        "local_date": "2026-09-22",
        "is_day_off": False,
        "start_time": "12:00:00",
        "end_time": "16:00:00",
        "is_active": True,
    }
    exception = client.post(
        "/admin/schedule-exceptions", json=exception_payload, headers=headers
    )
    assert exception.status_code == 201
    response = client.put(
        f"/admin/schedule-exceptions/{exception.json()['id']}",
        json={**exception_payload, "start_time": "11:00:00", "end_time": "15:00:00"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["start_time"] == "11:00:00"

    blocked = client.post(
        "/admin/blocked-slots", json=block_payload(scope), headers=headers
    )
    assert blocked.status_code == 201
    response = client.put(
        f"/admin/blocked-slots/{blocked.json()['id']}",
        json={**block_payload(scope), "ends_at": "2026-09-21T07:30:00Z"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["ends_at"] == "2026-09-21T07:30:00Z"


def test_client_cannot_change_any_schedule_resource(client, session):
    scope = setup_scope(session)
    headers = headers_for(client, scope.client)
    requests = [
        ("/admin/work-schedules", recurring_payload(scope)),
        (
            "/admin/schedule-breaks",
            {**recurring_payload(scope), "start_time": "13:00:00", "end_time": "14:00:00"},
        ),
        (
            "/admin/schedule-exceptions",
            {
                "employee_id": str(scope.employee.id),
                "branch_id": str(scope.branch.id),
                "local_date": "2026-09-22",
                "is_day_off": True,
                "is_active": True,
            },
        ),
        ("/admin/blocked-slots", block_payload(scope)),
        ("/employee/blocked-slots", block_payload(scope)),
    ]

    assert [
        client.post(path, json=payload, headers=headers).status_code
        for path, payload in requests
    ] == [403, 403, 403, 403, 403]


def test_employee_can_manage_only_own_blocked_slots(client, session):
    scope = setup_scope(session)
    employee_headers = headers_for(client, scope.employee_user)
    admin_headers = headers_for(client, scope.admin)

    own = client.post(
        "/employee/blocked-slots",
        json=block_payload(scope),
        headers=employee_headers,
    )
    assert own.status_code == 201
    assert own.json()["created_by_user_id"] == str(scope.employee_user.id)

    own_update = client.put(
        f"/employee/blocked-slots/{own.json()['id']}",
        json={**block_payload(scope), "reason": "Updated personal block"},
        headers=employee_headers,
    )
    assert own_update.status_code == 200
    assert own_update.json()["reason"] == "Updated personal block"

    assert client.post(
        "/employee/blocked-slots",
        json=block_payload(scope, employee=scope.other_employee),
        headers=employee_headers,
    ).status_code == 403
    assert client.post(
        "/admin/work-schedules",
        json=recurring_payload(scope),
        headers=employee_headers,
    ).status_code == 403

    other = client.post(
        "/admin/blocked-slots",
        json=block_payload(scope, employee=scope.other_employee),
        headers=admin_headers,
    )
    assert other.status_code == 201
    forbidden_update = client.put(
        f"/employee/blocked-slots/{other.json()['id']}",
        json=block_payload(scope, employee=scope.other_employee),
        headers=employee_headers,
    )
    assert forbidden_update.status_code == 403


def test_day_off_cannot_coexist_with_active_replacement_exception(client, session):
    scope = setup_scope(session)
    headers = headers_for(client, scope.admin)
    day_off = {
        "employee_id": str(scope.employee.id),
        "branch_id": str(scope.branch.id),
        "local_date": "2026-09-22",
        "is_day_off": True,
        "is_active": True,
    }
    assert client.post(
        "/admin/schedule-exceptions", json=day_off, headers=headers
    ).status_code == 201

    replacement = {
        **day_off,
        "is_day_off": False,
        "start_time": "12:00:00",
        "end_time": "16:00:00",
    }
    response = client.post(
        "/admin/schedule-exceptions", json=replacement, headers=headers
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "AMBIGUOUS_SCHEDULE_EXCEPTION"
