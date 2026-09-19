from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Appointment, OCCUPYING_APPOINTMENT_STATUSES
from app.services.availability import AvailabilityResult

@dataclass(frozen=True)
class Recommendation:
    start: datetime
    end: datetime
    reason: str

def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

def recommend_slots(session: Session, employee_id, availability: AvailabilityResult, limit: int = 3):
    if not availability.slots:
        return []
    first = _utc(availability.slots[0].start).replace(hour=0, minute=0, second=0, microsecond=0)
    appointments = list(session.scalars(select(Appointment).where(Appointment.employee_id == employee_id, Appointment.starts_at >= first, Appointment.starts_at < first + timedelta(days=1), Appointment.status.in_(OCCUPYING_APPOINTMENT_STATUSES))))
    ranked = []
    for index, slot in enumerate(availability.slots):
        start, end = _utc(slot.start), _utc(slot.end)
        previous = any(abs((start - _utc(a.ends_at)).total_seconds()) < 1 for a in appointments)
        following = any(abs((_utc(a.starts_at) - end).total_seconds()) < 1 for a in appointments)
        fills = previous and following
        score = (120 if fills else 45 if previous or following else 0) - index
        reason = "FILL_GAP" if fills else ("EARLIEST" if index == 0 else "BEST_FIT")
        ranked.append((score, start, Recommendation(slot.start, slot.end, reason)))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked[:limit]]
