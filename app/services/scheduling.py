from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Branch, Employee, Organization, ScheduleException


class SchedulingError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ScheduleScope:
    employee: Employee
    branch: Branch
    organization_id: UUID


def resolve_schedule_scope(
    session: Session, employee_id: UUID, branch_id: UUID
) -> ScheduleScope:
    employee = session.get(Employee, employee_id)
    branch = session.get(Branch, branch_id)
    if employee is None or branch is None:
        raise SchedulingError("SCHEDULE_SCOPE_NOT_FOUND", "Employee or branch not found", 404)
    if employee.branch_id != branch.id or employee.organization_id != branch.organization_id:
        raise SchedulingError("SCHEDULE_SCOPE_NOT_FOUND", "Employee or branch not found", 404)
    organization = session.get(Organization, employee.organization_id)
    if organization is None:
        raise SchedulingError("SCHEDULE_SCOPE_NOT_FOUND", "Employee or branch not found", 404)
    if not employee.is_active or not branch.is_active or not organization.is_active:
        raise SchedulingError(
            "SCHEDULE_SCOPE_INACTIVE",
            "Organization, employee, or branch is inactive",
            409,
        )
    return ScheduleScope(employee, branch, employee.organization_id)


def ensure_exception_compatibility(
    session: Session,
    employee_id: UUID,
    branch_id: UUID,
    local_date: date,
    is_day_off: bool,
    is_active: bool,
    excluding_id: UUID | None = None,
) -> None:
    if not is_active:
        return
    statement = select(ScheduleException).where(
        ScheduleException.employee_id == employee_id,
        ScheduleException.branch_id == branch_id,
        ScheduleException.local_date == local_date,
        ScheduleException.is_active.is_(True),
    )
    if excluding_id is not None:
        statement = statement.where(ScheduleException.id != excluding_id)
    existing = list(session.scalars(statement))
    if not existing:
        return
    if is_day_off or any(item.is_day_off for item in existing):
        raise SchedulingError(
            "AMBIGUOUS_SCHEDULE_EXCEPTION",
            "A day off cannot coexist with active replacement intervals",
            409,
        )
