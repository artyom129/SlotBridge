from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import WaitlistEntry, WaitlistStatus

def match_released_slot(session: Session, appointment, starts_at: datetime) -> int:
    branch = appointment.branch
    organization = appointment.organization
    zone = ZoneInfo(branch.timezone or organization.timezone)
    local = _utc(starts_at).astimezone(zone)
    entries = list(session.scalars(select(WaitlistEntry).where(
        WaitlistEntry.organization_id == appointment.organization_id,
        WaitlistEntry.branch_id == appointment.branch_id,
        WaitlistEntry.service_id == appointment.service_id,
        WaitlistEntry.preferred_date == local.date(),
        WaitlistEntry.preferred_start_time <= local.time().replace(tzinfo=None),
        WaitlistEntry.preferred_end_time > local.time().replace(tzinfo=None),
        WaitlistEntry.status == WaitlistStatus.WAITING,
    ).with_for_update()))
    matched = 0
    for entry in entries:
        if entry.employee_id is None or entry.employee_id == appointment.employee_id:
            entry.status = WaitlistStatus.MATCHED
            entry.matched_employee_id = appointment.employee_id
            entry.matched_starts_at = _utc(starts_at)
            matched += 1
    return matched

def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
