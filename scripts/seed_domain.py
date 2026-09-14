from __future__ import annotations

import sys
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Appointment,
    AppointmentAuditAction,
    AppointmentAuditLog,
    AppointmentStatus,
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
from app.security import hash_password  # noqa: E402


DEMO_PASSWORD = "SlotBridgeDemo!2026"


def ensure_user(
    session,
    email: str,
    first_name: str,
    last_name: str,
    role: UserRole,
    *,
    password: str = DEMO_PASSWORD,
) -> User:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
        )
        session.add(user)
        session.flush()
    else:
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = True
    return user


def ensure_recurring_interval(
    session,
    model,
    employee: Employee,
    branch: Branch,
    day_of_week: int,
    start_time: time,
    end_time: time,
):
    item = session.scalar(
        select(model).where(
            model.employee_id == employee.id,
            model.branch_id == branch.id,
            model.day_of_week == day_of_week,
            model.start_time == start_time,
            model.end_time == end_time,
        )
    )
    if item is None:
        item = model(
            employee_id=employee.id,
            branch_id=branch.id,
            organization_id=employee.organization_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            is_active=True,
        )
        session.add(item)
    else:
        item.is_active = True
    return item


def ensure_membership(session, user: User, organization: Organization) -> None:
    key = {"user_id": user.id, "organization_id": organization.id}
    if session.get(OrganizationMembership, key) is None:
        session.add(OrganizationMembership(**key))


def ensure_appointment(
    session,
    *,
    organization: Organization,
    branch: Branch,
    client: User,
    employee: Employee,
    service: Service,
    starts_at: datetime,
    status: AppointmentStatus,
    idempotency_key: str,
) -> Appointment:
    appointment = session.scalar(
        select(Appointment).where(
            Appointment.client_user_id == client.id,
            Appointment.idempotency_key == idempotency_key,
        )
    )
    if appointment is not None:
        appointment.client_note = "Демонстрационная запись"
        if appointment.status is AppointmentStatus.CANCELLED:
            appointment.cancellation_reason = "Демонстрационная отмена"
        for history_item in appointment.status_history:
            if history_item.reason == "Demo seed initial state":
                history_item.reason = "Начальное состояние демонстрационной записи"
        for audit_item in appointment.audit_events:
            if audit_item.reason == "Demo seed":
                audit_item.reason = "Демонстрационные данные"
        return appointment
    starts_utc = starts_at.astimezone(timezone.utc)
    appointment = Appointment(
        organization_id=organization.id,
        branch_id=branch.id,
        client_user_id=client.id,
        employee_id=employee.id,
        service_id=service.id,
        starts_at=starts_utc,
        ends_at=starts_utc + timedelta(minutes=service.duration_minutes),
        status=status,
        idempotency_key=idempotency_key,
        idempotency_fingerprint=sha256(
            f"seed:{idempotency_key}".encode("utf-8")
        ).hexdigest(),
        client_note="Демонстрационная запись",
        cancellation_reason="Демонстрационная отмена"
        if status is AppointmentStatus.CANCELLED
        else None,
        cancelled_at=datetime.now(timezone.utc)
        if status is AppointmentStatus.CANCELLED
        else None,
    )
    session.add(appointment)
    session.flush()
    session.add_all(
        [
            AppointmentStatusHistory(
                appointment_id=appointment.id,
                organization_id=organization.id,
                old_status=None,
                new_status=status,
                changed_by_user_id=client.id,
                reason="Начальное состояние демонстрационной записи",
            ),
            AppointmentAuditLog(
                appointment_id=appointment.id,
                organization_id=organization.id,
                action=AppointmentAuditAction.CREATED,
                changed_by_user_id=client.id,
                reason="Демонстрационные данные",
                new_starts_at=appointment.starts_at,
                new_ends_at=appointment.ends_at,
            ),
        ]
    )
    return appointment


def seed(*, allow_production: bool = False) -> None:
    settings = get_settings()
    if settings.slotbridge_environment == "production":
        if not allow_production:
            raise SystemExit(
                "Production demo seed requires scripts/seed_production_demo.py"
            )
        if not settings.production_demo_seed_enabled:
            raise SystemExit(
                "Set PRODUCTION_DEMO_SEED_ENABLED=true only for the explicit seed run"
            )
        if settings.demo_password is None:
            raise SystemExit("DEMO_PASSWORD is required for the production demo seed")
        demo_password = settings.demo_password.get_secret_value()
    elif settings.slotbridge_environment in {"development", "test", "demo"}:
        demo_password = DEMO_PASSWORD
    else:
        raise SystemExit("Demo seed is disabled outside development/test/demo environments")

    with SessionLocal.begin() as session:
        organization = session.scalar(
            select(Organization).where(Organization.slug == "slotbridge-demo")
        )
        if organization is None:
            organization = Organization(
                name="SlotBridge Демо",
                slug="slotbridge-demo",
                timezone="Asia/Almaty",
                is_active=True,
            )
            session.add(organization)
            session.flush()
        else:
            organization.name = "SlotBridge Демо"
            organization.timezone = "Asia/Almaty"
            organization.is_active = True

        branch = session.scalar(
            select(Branch).where(
                Branch.organization_id == organization.id,
                Branch.name.in_(("Главный филиал", "Main Branch")),
            )
        )
        if branch is None:
            branch = Branch(
                organization_id=organization.id,
                name="Главный филиал",
                address="Демонстрационный адрес",
                timezone="Asia/Almaty",
                is_active=True,
            )
            session.add(branch)
            session.flush()
        else:
            branch.name = "Главный филиал"
            branch.address = "Демонстрационный адрес"
            branch.timezone = "Asia/Almaty"
            branch.is_active = True

        admin = ensure_user(
            session,
            "admin@slotbridge-demo.com",
            "Демо",
            "Администратор",
            UserRole.ADMIN,
            password=demo_password,
        )
        employee_alex = ensure_user(
            session,
            "alex.employee@slotbridge-demo.com",
            "Алекс",
            "Сотрудник",
            UserRole.EMPLOYEE,
            password=demo_password,
        )
        employee_sam = ensure_user(
            session,
            "sam.employee@slotbridge-demo.com",
            "Сэм",
            "Сотрудник",
            UserRole.EMPLOYEE,
            password=demo_password,
        )
        client_a = ensure_user(
            session,
            "client.a@slotbridge-demo.com",
            "Клиент",
            "А",
            UserRole.CLIENT,
            password=demo_password,
        )
        client_b = ensure_user(
            session,
            "client.b@slotbridge-demo.com",
            "Клиент",
            "Б",
            UserRole.CLIENT,
            password=demo_password,
        )

        membership_users = {
            user.id: user
            for user in (admin, employee_alex, employee_sam, client_a, client_b)
        }
        for user in session.scalars(
            select(User).where(
                User.role == UserRole.CLIENT,
                User.is_active.is_(True),
            )
        ):
            membership_users[user.id] = user
        for user in membership_users.values():
            ensure_membership(session, user, organization)

        employees: dict[str, Employee] = {}
        for user, display_name in (
            (employee_alex, "Алекс — специалист"),
            (employee_sam, "Сэм — специалист"),
        ):
            employee = session.scalar(
                select(Employee).where(
                    Employee.user_id == user.id,
                    Employee.organization_id == organization.id,
                )
            )
            if employee is None:
                employee = Employee(
                    user_id=user.id,
                    organization_id=organization.id,
                    branch_id=branch.id,
                    display_name=display_name,
                    is_active=True,
                )
                session.add(employee)
                session.flush()
            else:
                employee.branch_id = branch.id
                employee.display_name = display_name
                employee.is_active = True
            employees[user.email] = employee

        service_specs = (
            (
                "Haircut",
                "Стрижка",
                "Стрижка продолжительностью 60 минут",
                60,
                Decimal("45.00"),
            ),
            (
                "Consultation",
                "Консультация",
                "Консультация продолжительностью 30 минут",
                30,
                Decimal("20.00"),
            ),
            (
                "Extended Service",
                "Расширенная услуга",
                "Услуга продолжительностью 90 минут",
                90,
                Decimal("75.00"),
            ),
        )
        services: dict[str, Service] = {}
        for legacy_name, name, description, duration, price in service_specs:
            service = session.scalar(
                select(Service).where(
                    Service.organization_id == organization.id,
                    Service.name.in_((name, legacy_name)),
                )
            )
            if service is None:
                service = Service(
                    organization_id=organization.id,
                    name=name,
                    description=description,
                    duration_minutes=duration,
                    price=price,
                    is_active=True,
                )
                session.add(service)
                session.flush()
            else:
                service.name = name
                service.description = description
                service.duration_minutes = duration
                service.price = price
                service.is_active = True
            services[legacy_name] = service

        assignments = (
            (employees["alex.employee@slotbridge-demo.com"], services["Haircut"]),
            (employees["alex.employee@slotbridge-demo.com"], services["Consultation"]),
            (employees["sam.employee@slotbridge-demo.com"], services["Consultation"]),
            (employees["sam.employee@slotbridge-demo.com"], services["Extended Service"]),
        )
        for employee, service in assignments:
            key = {"employee_id": employee.id, "service_id": service.id}
            if session.get(EmployeeService, key) is None:
                session.add(EmployeeService(**key, organization_id=organization.id))

        alex = employees["alex.employee@slotbridge-demo.com"]
        sam = employees["sam.employee@slotbridge-demo.com"]
        for day_of_week in range(5):
            ensure_recurring_interval(
                session, WorkSchedule, alex, branch, day_of_week, time(9), time(18)
            )
            ensure_recurring_interval(
                session, WorkSchedule, sam, branch, day_of_week, time(10), time(19)
            )
            ensure_recurring_interval(
                session, ScheduleBreak, alex, branch, day_of_week, time(13), time(14)
            )

        exception_date = date(2026, 9, 21)
        exception = session.scalar(
            select(ScheduleException).where(
                ScheduleException.employee_id == alex.id,
                ScheduleException.branch_id == branch.id,
                ScheduleException.local_date == exception_date,
                ScheduleException.is_day_off.is_(True),
            )
        )
        if exception is None:
            session.add(
                ScheduleException(
                    employee_id=alex.id,
                    branch_id=branch.id,
                    organization_id=organization.id,
                    local_date=exception_date,
                    is_day_off=True,
                    is_active=True,
                )
            )
        else:
            exception.is_active = True

        demo_zone = ZoneInfo("Asia/Almaty")
        block_start = datetime(2026, 9, 21, 11, tzinfo=demo_zone).astimezone(timezone.utc)
        block_end = datetime(2026, 9, 21, 12, tzinfo=demo_zone).astimezone(timezone.utc)
        blocked = session.scalar(
            select(BlockedSlot).where(
                BlockedSlot.employee_id == sam.id,
                BlockedSlot.branch_id == branch.id,
                BlockedSlot.starts_at == block_start,
                BlockedSlot.ends_at == block_end,
            )
        )
        if blocked is None:
            session.add(
                BlockedSlot(
                    employee_id=sam.id,
                    branch_id=branch.id,
                    organization_id=organization.id,
                    starts_at=block_start,
                    ends_at=block_end,
                    reason="Демонстрационное обучение",
                    created_by_user_id=admin.id,
                    is_active=True,
                )
            )
        else:
            blocked.reason = "Демонстрационное обучение"
            blocked.is_active = True

        local_today = datetime.now(demo_zone).date()
        # Tuesday avoids the fixed Monday exception/block demo while remaining
        # inside both employees' recurring Monday-Friday schedules.
        days_to_tuesday = (1 - local_today.weekday()) % 7 or 7
        next_tuesday = local_today + timedelta(days=days_to_tuesday)
        days_from_tuesday = (local_today.weekday() - 1) % 7 or 7
        previous_tuesday = local_today - timedelta(days=days_from_tuesday)

        appointment_specs = (
            (
                client_a,
                alex,
                services["Haircut"],
                datetime.combine(next_tuesday, time(9), demo_zone),
                AppointmentStatus.BOOKED,
                "demo-stage4-upcoming-booked",
            ),
            (
                client_b,
                sam,
                services["Consultation"],
                datetime.combine(next_tuesday, time(12), demo_zone),
                AppointmentStatus.CONFIRMED,
                "demo-stage4-upcoming-confirmed",
            ),
            (
                client_a,
                alex,
                services["Consultation"],
                datetime.combine(previous_tuesday, time(10), demo_zone),
                AppointmentStatus.COMPLETED,
                "demo-stage4-historical-completed",
            ),
            (
                client_b,
                sam,
                services["Extended Service"],
                datetime.combine(next_tuesday, time(15), demo_zone),
                AppointmentStatus.CANCELLED,
                "demo-stage4-cancelled",
            ),
        )
        for client, employee, service, starts_at, appointment_status, key in appointment_specs:
            ensure_appointment(
                session,
                organization=organization,
                branch=branch,
                client=client,
                employee=employee,
                service=service,
                starts_at=starts_at,
                status=appointment_status,
                idempotency_key=key,
            )

    print("Демонстрационные данные SlotBridge подготовлены.")
    print("Созданы: администратор, два сотрудника и два клиента @slotbridge-demo.com")
    if settings.slotbridge_environment == "production":
        print("Production seed выполнен явно; пароль получен только из environment.")
    else:
        print("Только для development/demo. Данные для входа указаны в README.md.")


if __name__ == "__main__":
    seed()
