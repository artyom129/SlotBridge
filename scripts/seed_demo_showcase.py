"""Create two idempotent demo bookings around a one-hour recommendation gap.

Run explicitly; this script is never part of production startup.
"""
from datetime import datetime, timedelta, timezone
import secrets
from sqlalchemy import select
from app.config import get_settings
from app.database import SessionLocal
from app.models import Appointment, Employee, EmployeeService, Organization, OrganizationMembership, Service, User, UserRole
from app.security import hash_password
from app.services.availability import AvailabilityService
from app.services.booking import BookingService

def main():
    settings = get_settings()
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).where(Organization.slug == settings.public_demo_organization_slug))
        if organization is None: raise SystemExit('Demo organization not found; run the explicit domain seed first.')
        pair = session.execute(select(Employee, Service).join(EmployeeService, EmployeeService.employee_id == Employee.id).join(Service, Service.id == EmployeeService.service_id).where(Employee.organization_id == organization.id, Service.duration_minutes == 60, Employee.is_active.is_(True), Service.is_active.is_(True))).first()
        if pair is None: raise SystemExit('A 60-minute demo service is required.')
        employee, service = pair
        user = session.scalar(select(User).where(User.email == 'showcase-schedule@slotbridge.local'))
        if user is None:
            user = User(email='showcase-schedule@slotbridge.local', password_hash=hash_password(secrets.token_urlsafe(32)), first_name='Demo', last_name='Schedule', role=UserRole.CLIENT, is_active=True)
            session.add(user); session.flush(); session.add(OrganizationMembership(user_id=user.id, organization_id=organization.id)); session.flush()
        elif session.scalar(select(OrganizationMembership).where(OrganizationMembership.user_id == user.id, OrganizationMembership.organization_id == organization.id)) is None:
            raise SystemExit('Existing showcase user is not a member of the demo organization; refusing to modify it.')

        existing = list(session.scalars(select(Appointment).where(Appointment.client_user_id == user.id, Appointment.idempotency_key.like('showcase-%')).order_by(Appointment.starts_at)))
        if len(existing) >= 2:
            print(f'Showcase already seeded: {existing[0].starts_at.date().isoformat()}')
            return

        availability = AvailabilityService(session, settings.availability_slot_interval_minutes)
        selected = None
        today = datetime.now(timezone.utc).date()
        for offset in range(2, 91):
            candidate_date = today + timedelta(days=offset)
            result = availability.calculate(employee.branch_id, employee.id, service.id, candidate_date)
            starts = {slot.start: slot for slot in result.slots}
            step = timedelta(minutes=result.service_duration_minutes)
            for first in result.slots:
                if first.start + step in starts and first.start + (2 * step) in starts:
                    selected = (candidate_date, first.start, first.start + (2 * step))
                    break
            if selected is not None:
                break
        if selected is None:
            raise SystemExit('No three consecutive real demo slots are available in the next 90 days.')

        target, first_start, third_start = selected
        booking = BookingService(session, settings.availability_slot_interval_minutes)
        for label, start in (('first', first_start), ('third', third_start)):
            booking.create(user, branch_id=employee.branch_id, employee_id=employee.id, service_id=service.id, starts_at=start, client_note='SlotBridge showcase', idempotency_key=f'showcase-{target.isoformat()}-{label}')
        session.commit()
        print(f'Showcase ready: {target.isoformat()} with a real one-service-duration gap')

if __name__ == '__main__': main()
