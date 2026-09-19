"""Create two idempotent demo bookings around a one-hour recommendation gap.

Run explicitly; this script is never part of production startup.
"""
from datetime import date, datetime, time, timedelta
import secrets
from sqlalchemy import select
from app.config import get_settings
from app.database import SessionLocal
from app.models import Employee, EmployeeService, Organization, OrganizationMembership, Service, User, UserRole, WorkSchedule
from app.security import hash_password
from app.services.booking import BookingError, BookingService

def main():
    settings = get_settings()
    with SessionLocal() as session:
        organization = session.scalar(select(Organization).where(Organization.slug == settings.public_demo_organization_slug))
        if organization is None: raise SystemExit('Demo organization not found; run the explicit domain seed first.')
        pair = session.execute(select(Employee, Service).join(EmployeeService, EmployeeService.employee_id == Employee.id).join(Service, Service.id == EmployeeService.service_id).where(Employee.organization_id == organization.id, Service.duration_minutes == 60, Employee.is_active.is_(True), Service.is_active.is_(True))).first()
        if pair is None: raise SystemExit('A 60-minute demo service is required.')
        employee, service = pair
        schedules = list(session.scalars(select(WorkSchedule).where(WorkSchedule.employee_id == employee.id, WorkSchedule.is_active.is_(True), WorkSchedule.start_time <= time(9), WorkSchedule.end_time >= time(12))))
        if not schedules: raise SystemExit('A 09:00–12:00 demo schedule is required.')
        target = date.today() + timedelta(days=2)
        weekdays = {x.day_of_week for x in schedules}
        while target.weekday() not in weekdays: target += timedelta(days=1)
        user = session.scalar(select(User).where(User.email == 'showcase-schedule@slotbridge.local'))
        if user is None:
            user = User(email='showcase-schedule@slotbridge.local', password_hash=hash_password(secrets.token_urlsafe(32)), first_name='Demo', last_name='Schedule', role=UserRole.CLIENT, is_active=True)
            session.add(user); session.flush(); session.add(OrganizationMembership(user_id=user.id, organization_id=organization.id)); session.flush()
        zone = __import__('zoneinfo').ZoneInfo(employee.branch.timezone or organization.timezone)
        booking = BookingService(session, settings.availability_slot_interval_minutes)
        for hour in (9, 11):
            try:
                booking.create(user, branch_id=employee.branch_id, employee_id=employee.id, service_id=service.id, starts_at=datetime.combine(target, time(hour), zone), client_note='SlotBridge showcase', idempotency_key=f'showcase-{target.isoformat()}-{hour}')
            except BookingError as error:
                if error.code not in {'SLOT_ALREADY_BOOKED', 'SLOT_NOT_AVAILABLE'}: raise
        session.commit()
        print(f'Showcase ready: {target.isoformat()} 09:00 booked, 10:00 gap, 11:00 booked')

if __name__ == '__main__': main()
