from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthenticatedUser
from app.models import Branch, Employee, EmployeeService, Organization, Service
from app.schemas import BranchOut, EmployeeOut, OrganizationOut, ServiceOut


router = APIRouter(tags=["core-domain"])


def _not_found(entity: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity} not found")


@router.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(
    _user: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[Organization]:
    return list(session.scalars(select(Organization).order_by(Organization.name).limit(100)))


@router.get("/organizations/{organization_id}", response_model=OrganizationOut)
def get_organization(
    organization_id: UUID,
    _user: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
) -> Organization:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise _not_found("Organization")
    return organization


@router.get("/organizations/{organization_id}/branches", response_model=list[BranchOut])
def list_branches(
    organization_id: UUID,
    _user: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[Branch]:
    if session.get(Organization, organization_id) is None:
        raise _not_found("Organization")
    statement = (
        select(Branch)
        .where(Branch.organization_id == organization_id)
        .order_by(Branch.name)
        .limit(100)
    )
    return list(session.scalars(statement))


@router.get("/organizations/{organization_id}/services", response_model=list[ServiceOut])
def list_services(
    organization_id: UUID,
    _user: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[Service]:
    if session.get(Organization, organization_id) is None:
        raise _not_found("Organization")
    statement = (
        select(Service)
        .where(Service.organization_id == organization_id)
        .order_by(Service.name)
        .limit(100)
    )
    return list(session.scalars(statement))


@router.get("/organizations/{organization_id}/employees", response_model=list[EmployeeOut])
def list_employees(
    organization_id: UUID,
    _user: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[Employee]:
    if session.get(Organization, organization_id) is None:
        raise _not_found("Organization")
    statement = (
        select(Employee)
        .where(Employee.organization_id == organization_id)
        .order_by(Employee.display_name)
        .limit(100)
    )
    return list(session.scalars(statement))


@router.get("/employees/{employee_id}/services", response_model=list[ServiceOut])
def list_employee_services(
    employee_id: UUID,
    _user: AuthenticatedUser,
    session: Annotated[Session, Depends(get_db)],
) -> list[Service]:
    if session.get(Employee, employee_id) is None:
        raise _not_found("Employee")
    statement = (
        select(Service)
        .join(EmployeeService, EmployeeService.service_id == Service.id)
        .where(EmployeeService.employee_id == employee_id)
        .order_by(Service.name)
        .limit(100)
    )
    return list(session.scalars(statement))
