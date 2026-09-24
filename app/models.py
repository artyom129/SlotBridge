from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Time,
    Text,
    UniqueConstraint,
    func,
    literal_column,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, Enum):
    CLIENT = "CLIENT"
    EMPLOYEE = "EMPLOYEE"
    ADMIN = "ADMIN"


class AppointmentStatus(str, Enum):
    BOOKED = "BOOKED"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class AppointmentAuditAction(str, Enum):
    CREATED = "CREATED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"
    STATUS_CHANGED = "STATUS_CHANGED"


class WaitlistStatus(str, Enum):
    WAITING = "WAITING"
    MATCHED = "MATCHED"
    ACCEPTED = "ACCEPTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ReviewStatus(str, Enum):
    PUBLISHED = "PUBLISHED"
    HIDDEN = "HIDDEN"
    FLAGGED = "FLAGGED"


class ReviewReportStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class ReviewAuditAction(str, Enum):
    REVIEW_CREATED = "REVIEW_CREATED"
    REVIEW_UPDATED = "REVIEW_UPDATED"
    REVIEW_HIDDEN = "REVIEW_HIDDEN"
    REVIEW_RESTORED = "REVIEW_RESTORED"
    REVIEW_REPORTED = "REVIEW_REPORTED"
    REVIEW_REPLY_CREATED = "REVIEW_REPLY_CREATED"
    REVIEW_REPLY_UPDATED = "REVIEW_REPLY_UPDATED"


OCCUPYING_APPOINTMENT_STATUSES = (
    AppointmentStatus.BOOKED,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.IN_PROGRESS,
)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", validate_strings=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("uq_users_email_lower", func.lower(email), unique=True),
    )

    employee_profiles: Mapped[list["Employee"]] = relationship(
        back_populates="user", passive_deletes=True
    )


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    __table_args__ = (UniqueConstraint("slug", name="uq_organizations_slug"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    external_review_url_2gis: Mapped[str | None] = mapped_column(String(1000))

    branches: Mapped[list["Branch"]] = relationship(
        back_populates="organization", passive_deletes=True
    )
    employees: Mapped[list["Employee"]] = relationship(
        back_populates="organization",
        foreign_keys="Employee.organization_id",
        passive_deletes=True,
        overlaps="branch,employees",
    )
    services: Mapped[list["Service"]] = relationship(
        back_populates="organization", passive_deletes=True
    )


class Branch(TimestampMixin, Base):
    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_branches_org_name"),
        UniqueConstraint("id", "organization_id", name="uq_branches_id_org"),
        Index("ix_branches_organization_active", "organization_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    timezone: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="branches")
    employees: Mapped[list["Employee"]] = relationship(
        back_populates="branch",
        foreign_keys="[Employee.branch_id, Employee.organization_id]",
        passive_deletes=True,
        overlaps="employees,organization",
    )


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_employees_user_org"),
        UniqueConstraint("id", "organization_id", name="uq_employees_id_org"),
        UniqueConstraint(
            "id", "branch_id", "organization_id", name="uq_employees_id_branch_org"
        ),
        ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_employees_branch_org",
            ondelete="RESTRICT",
        ),
        Index("ix_employees_org_active", "organization_id", "is_active"),
        Index("ix_employees_branch_active", "branch_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="employee_profiles")
    organization: Mapped[Organization] = relationship(
        back_populates="employees",
        foreign_keys=[organization_id],
        overlaps="branch,employees",
    )
    branch: Mapped[Branch] = relationship(
        back_populates="employees",
        foreign_keys=[branch_id, organization_id],
        overlaps="employees,organization",
    )
    service_links: Mapped[list["EmployeeService"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="[EmployeeService.employee_id, EmployeeService.organization_id]",
        overlaps="service,employee_links",
    )


class Service(TimestampMixin, Base):
    __tablename__ = "services"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_services_org_name"),
        UniqueConstraint("id", "organization_id", name="uq_services_id_org"),
        CheckConstraint("duration_minutes > 0", name="ck_services_duration_positive"),
        CheckConstraint("price IS NULL OR price >= 0", name="ck_services_price_nonnegative"),
        Index("ix_services_organization_active", "organization_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="services")
    employee_links: Mapped[list["EmployeeService"]] = relationship(
        back_populates="service",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="[EmployeeService.service_id, EmployeeService.organization_id]",
        overlaps="employee,service_links",
    )


class EmployeeService(TimestampMixin, Base):
    __tablename__ = "employee_services"
    __table_args__ = (
        CheckConstraint(
            "duration_override_minutes IS NULL OR duration_override_minutes > 0",
            name="ck_employee_services_duration_positive",
        ),
        ForeignKeyConstraint(
            ["employee_id", "organization_id"],
            ["employees.id", "employees.organization_id"],
            name="fk_employee_services_employee_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["service_id", "organization_id"],
            ["services.id", "services.organization_id"],
            name="fk_employee_services_service_org",
            ondelete="CASCADE",
        ),
        Index("ix_employee_services_service", "service_id"),
        Index("ix_employee_services_organization", "organization_id"),
    )

    employee_id: Mapped[UUID] = mapped_column(
        primary_key=True
    )
    service_id: Mapped[UUID] = mapped_column(
        primary_key=True
    )
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    duration_override_minutes: Mapped[int | None] = mapped_column(Integer)

    employee: Mapped[Employee] = relationship(
        back_populates="service_links",
        foreign_keys=[employee_id, organization_id],
        overlaps="employee_links,service",
    )
    service: Mapped[Service] = relationship(
        back_populates="employee_links",
        foreign_keys=[service_id, organization_id],
        overlaps="employee,service_links",
    )


class WorkSchedule(TimestampMixin, Base):
    """Recurring employee work window; day_of_week uses 0=Monday through 6=Sunday."""

    __tablename__ = "work_schedules"
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_work_schedules_weekday"),
        CheckConstraint("start_time < end_time", name="ck_work_schedules_time_order"),
        ForeignKeyConstraint(
            ["employee_id", "branch_id", "organization_id"],
            ["employees.id", "employees.branch_id", "employees.organization_id"],
            name="fk_work_schedules_employee_branch_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_work_schedules_branch_org",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "employee_id",
            "branch_id",
            "day_of_week",
            "start_time",
            "end_time",
            name="uq_work_schedules_exact_window",
        ),
        Index(
            "ix_work_schedules_lookup",
            "employee_id",
            "branch_id",
            "day_of_week",
            "is_active",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(nullable=False)
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ScheduleBreak(TimestampMixin, Base):
    """Recurring unavailable window; overlapping rows are merged by the engine."""

    __tablename__ = "schedule_breaks"
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_schedule_breaks_weekday"),
        CheckConstraint("start_time < end_time", name="ck_schedule_breaks_time_order"),
        ForeignKeyConstraint(
            ["employee_id", "branch_id", "organization_id"],
            ["employees.id", "employees.branch_id", "employees.organization_id"],
            name="fk_schedule_breaks_employee_branch_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_schedule_breaks_branch_org",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "employee_id",
            "branch_id",
            "day_of_week",
            "start_time",
            "end_time",
            name="uq_schedule_breaks_exact_window",
        ),
        Index(
            "ix_schedule_breaks_lookup",
            "employee_id",
            "branch_id",
            "day_of_week",
            "is_active",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(nullable=False)
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ScheduleException(TimestampMixin, Base):
    """Date-specific replacement windows or a complete day off."""

    __tablename__ = "schedule_exceptions"
    __table_args__ = (
        CheckConstraint(
            "(is_day_off AND start_time IS NULL AND end_time IS NULL) OR "
            "(NOT is_day_off AND start_time IS NOT NULL AND end_time IS NOT NULL "
            "AND start_time < end_time)",
            name="ck_schedule_exceptions_shape",
        ),
        ForeignKeyConstraint(
            ["employee_id", "branch_id", "organization_id"],
            ["employees.id", "employees.branch_id", "employees.organization_id"],
            name="fk_schedule_exceptions_employee_branch_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_schedule_exceptions_branch_org",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "employee_id",
            "branch_id",
            "local_date",
            "start_time",
            "end_time",
            name="uq_schedule_exceptions_exact_window",
        ),
        Index(
            "uq_schedule_exceptions_active_day_off",
            "employee_id",
            "branch_id",
            "local_date",
            unique=True,
            postgresql_where=text("is_day_off AND is_active"),
            sqlite_where=text("is_day_off = 1 AND is_active = 1"),
        ),
        Index(
            "ix_schedule_exceptions_lookup",
            "employee_id",
            "branch_id",
            "local_date",
            "is_active",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(nullable=False)
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_day_off: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BlockedSlot(TimestampMixin, Base):
    """Absolute occupied interval stored and transported as a timezone-aware instant."""

    __tablename__ = "blocked_slots"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="ck_blocked_slots_time_order"),
        ForeignKeyConstraint(
            ["employee_id", "branch_id", "organization_id"],
            ["employees.id", "employees.branch_id", "employees.organization_id"],
            name="fk_blocked_slots_employee_branch_org",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_blocked_slots_branch_org",
            ondelete="CASCADE",
        ),
        Index(
            "ix_blocked_slots_lookup",
            "employee_id",
            "branch_id",
            "starts_at",
            "ends_at",
            "is_active",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    employee_id: Mapped[UUID] = mapped_column(nullable=False)
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class OrganizationMembership(TimestampMixin, Base):
    """Explicit user access to an organization for booking tenant policies."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        Index("ix_organization_memberships_org", "organization_id", "user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )


class Appointment(TimestampMixin, Base):
    """First-party booking protected by a PostgreSQL active-time exclusion rule."""

    __tablename__ = "appointments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    client_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    employee_id: Mapped[UUID] = mapped_column(nullable=False)
    service_id: Mapped[UUID] = mapped_column(nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        SAEnum(AppointmentStatus, name="appointment_status", validate_strings=True),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    client_note: Mapped[str | None] = mapped_column(Text)
    cancellation_reason: Mapped[str | None] = mapped_column(String(500))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="ck_appointments_time_order"),
        CheckConstraint(
            "(status = 'CANCELLED' AND cancelled_at IS NOT NULL) OR "
            "(status <> 'CANCELLED' AND cancelled_at IS NULL)",
            name="ck_appointments_cancellation_state",
        ),
        ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_appointments_branch_org",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["employee_id", "branch_id", "organization_id"],
            ["employees.id", "employees.branch_id", "employees.organization_id"],
            name="fk_appointments_employee_branch_org",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["service_id", "organization_id"],
            ["services.id", "services.organization_id"],
            name="fk_appointments_service_org",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["client_user_id", "organization_id"],
            ["organization_memberships.user_id", "organization_memberships.organization_id"],
            name="fk_appointments_client_membership",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "organization_id", name="uq_appointments_id_org"),
        UniqueConstraint(
            "client_user_id",
            "idempotency_key",
            name="uq_appointments_client_idempotency_key",
        ),
        Index(
            "ix_appointments_client_start_status",
            "client_user_id",
            "starts_at",
            "status",
        ),
        Index(
            "ix_appointments_employee_start_status",
            "employee_id",
            "starts_at",
            "status",
        ),
        Index(
            "ix_appointments_org_branch_start",
            "organization_id",
            "branch_id",
            "starts_at",
        ),
        postgresql.ExcludeConstraint(
            ("employee_id", "="),
            (
                func.tstzrange(starts_at, ends_at, literal_column("'[)'")),
                "&&",
            ),
            where=text(
                "status IN ('BOOKED', 'CONFIRMED', 'IN_PROGRESS')"
            ),
            using="gist",
            name="ex_appointments_employee_time_active",
        ).ddl_if(dialect="postgresql"),
    )

    organization: Mapped[Organization] = relationship(
        foreign_keys=[organization_id], viewonly=True
    )
    branch: Mapped[Branch] = relationship(
        foreign_keys=[branch_id, organization_id], viewonly=True
    )
    employee: Mapped[Employee] = relationship(
        foreign_keys=[employee_id, branch_id, organization_id],
        viewonly=True,
    )
    service: Mapped[Service] = relationship(
        foreign_keys=[service_id, organization_id], viewonly=True
    )
    client: Mapped[User] = relationship(
        foreign_keys=[client_user_id], viewonly=True
    )
    status_history: Mapped[list["AppointmentStatusHistory"]] = relationship(
        back_populates="appointment",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AppointmentStatusHistory.created_at",
    )
    audit_events: Mapped[list["AppointmentAuditLog"]] = relationship(
        back_populates="appointment",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AppointmentAuditLog.created_at",
    )
    review: Mapped["Review | None"] = relationship(
        back_populates="appointment",
        uselist=False,
        passive_deletes=True,
        lazy="selectin",
    )


class WaitlistEntry(TimestampMixin, Base):
    __tablename__ = "waitlist_entries"
    __table_args__ = (
        CheckConstraint("preferred_start_time < preferred_end_time", name="ck_waitlist_preferred_time_order"),
        ForeignKeyConstraint(["branch_id", "organization_id"], ["branches.id", "branches.organization_id"], name="fk_waitlist_branch_org"),
        ForeignKeyConstraint(["service_id", "organization_id"], ["services.id", "services.organization_id"], name="fk_waitlist_service_org"),
        ForeignKeyConstraint(["client_user_id", "organization_id"], ["organization_memberships.user_id", "organization_memberships.organization_id"], name="fk_waitlist_client_membership"),
        Index("ix_waitlist_match", "organization_id", "branch_id", "preferred_date", "status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    client_user_id: Mapped[UUID] = mapped_column(nullable=False)
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    service_id: Mapped[UUID] = mapped_column(nullable=False)
    employee_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"))
    preferred_date: Mapped[date] = mapped_column(Date, nullable=False)
    preferred_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    preferred_end_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[WaitlistStatus] = mapped_column(SAEnum(WaitlistStatus, name="waitlist_status", validate_strings=True), nullable=False, default=WaitlistStatus.WAITING)
    matched_employee_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"))
    matched_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AppointmentStatusHistory(Base):
    """Append-only lifecycle transition history."""

    __tablename__ = "appointment_status_history"
    __table_args__ = (
        CheckConstraint(
            "old_status IS NULL OR old_status <> new_status",
            name="ck_appointment_status_history_changed",
        ),
        ForeignKeyConstraint(
            ["appointment_id", "organization_id"],
            ["appointments.id", "appointments.organization_id"],
            name="fk_appointment_status_history_appointment_org",
            ondelete="CASCADE",
        ),
        Index(
            "ix_appointment_status_history_appointment_created",
            "appointment_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    appointment_id: Mapped[UUID] = mapped_column(nullable=False)
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    old_status: Mapped[AppointmentStatus | None] = mapped_column(
        SAEnum(AppointmentStatus, name="appointment_status", validate_strings=True)
    )
    new_status: Mapped[AppointmentStatus] = mapped_column(
        SAEnum(AppointmentStatus, name="appointment_status", validate_strings=True),
        nullable=False,
    )
    changed_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    appointment: Mapped[Appointment] = relationship(back_populates="status_history")


class AppointmentAuditLog(Base):
    """Append-only audit record for critical booking actions."""

    __tablename__ = "appointment_audit_log"
    __table_args__ = (
        ForeignKeyConstraint(
            ["appointment_id", "organization_id"],
            ["appointments.id", "appointments.organization_id"],
            name="fk_appointment_audit_log_appointment_org",
            ondelete="CASCADE",
        ),
        Index(
            "ix_appointment_audit_log_appointment_created",
            "appointment_id",
            "created_at",
        ),
        Index(
            "ix_appointment_audit_log_org_created",
            "organization_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    appointment_id: Mapped[UUID] = mapped_column(nullable=False)
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    action: Mapped[AppointmentAuditAction] = mapped_column(
        SAEnum(
            AppointmentAuditAction,
            name="appointment_audit_action",
            validate_strings=True,
        ),
        nullable=False,
    )
    changed_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(500))
    old_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    old_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    new_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    new_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    appointment: Mapped[Appointment] = relationship(back_populates="audit_events")


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("appointment_id", name="uq_reviews_appointment"),
        UniqueConstraint("id", "organization_id", name="uq_reviews_id_org"),
        CheckConstraint("overall_rating BETWEEN 1 AND 5", name="ck_reviews_overall_rating"),
        CheckConstraint("quality_rating IS NULL OR quality_rating BETWEEN 1 AND 5", name="ck_reviews_quality_rating"),
        CheckConstraint("service_rating IS NULL OR service_rating BETWEEN 1 AND 5", name="ck_reviews_service_rating"),
        CheckConstraint("punctuality_rating IS NULL OR punctuality_rating BETWEEN 1 AND 5", name="ck_reviews_punctuality_rating"),
        ForeignKeyConstraint(["appointment_id", "organization_id"], ["appointments.id", "appointments.organization_id"], name="fk_reviews_appointment_org", ondelete="CASCADE"),
        ForeignKeyConstraint(["client_user_id", "organization_id"], ["organization_memberships.user_id", "organization_memberships.organization_id"], name="fk_reviews_client_membership", ondelete="RESTRICT"),
        ForeignKeyConstraint(["employee_id", "organization_id"], ["employees.id", "employees.organization_id"], name="fk_reviews_employee_org", ondelete="RESTRICT"),
        ForeignKeyConstraint(["service_id", "organization_id"], ["services.id", "services.organization_id"], name="fk_reviews_service_org", ondelete="RESTRICT"),
        Index("ix_reviews_employee_status_created", "employee_id", "status", "created_at"),
        Index("ix_reviews_org_status_created", "organization_id", "status", "created_at"),
        Index("ix_reviews_service_status", "service_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    appointment_id: Mapped[UUID] = mapped_column(nullable=False)
    client_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    employee_id: Mapped[UUID] = mapped_column(nullable=False)
    service_id: Mapped[UUID] = mapped_column(nullable=False)
    overall_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_rating: Mapped[int | None] = mapped_column(Integer)
    service_rating: Mapped[int | None] = mapped_column(Integer)
    punctuality_rating: Mapped[int | None] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(SAEnum(ReviewStatus, name="review_status", validate_strings=True), default=ReviewStatus.PUBLISHED, nullable=False)
    moderation_note: Mapped[str | None] = mapped_column(String(1000))
    appointment: Mapped[Appointment] = relationship(back_populates="review")
    organization: Mapped[Organization] = relationship(
        foreign_keys=[organization_id], viewonly=True
    )
    client: Mapped[User] = relationship(foreign_keys=[client_user_id], viewonly=True)
    employee: Mapped[Employee] = relationship(foreign_keys=[employee_id, organization_id], viewonly=True)
    service: Mapped[Service] = relationship(foreign_keys=[service_id, organization_id], viewonly=True)
    reports: Mapped[list["ReviewReport"]] = relationship(back_populates="review", cascade="all, delete-orphan", passive_deletes=True)
    reply: Mapped["ReviewReply | None"] = relationship(back_populates="review", uselist=False, cascade="all, delete-orphan", passive_deletes=True)
    audit_events: Mapped[list["ReviewAuditLog"]] = relationship(back_populates="review", cascade="all, delete-orphan", passive_deletes=True, order_by="ReviewAuditLog.created_at")


class ReviewReport(TimestampMixin, Base):
    __tablename__ = "review_reports"
    __table_args__ = (
        UniqueConstraint("review_id", "reporter_user_id", name="uq_review_reports_reporter"),
        ForeignKeyConstraint(["review_id", "organization_id"], ["reviews.id", "reviews.organization_id"], name="fk_review_reports_review_org", ondelete="CASCADE"),
        Index("ix_review_reports_org_status_created", "organization_id", "status", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    review_id: Mapped[UUID] = mapped_column(nullable=False)
    reporter_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[ReviewReportStatus] = mapped_column(SAEnum(ReviewReportStatus, name="review_report_status", validate_strings=True), default=ReviewReportStatus.OPEN, nullable=False)
    review: Mapped[Review] = relationship(back_populates="reports")


class ReviewReply(TimestampMixin, Base):
    __tablename__ = "review_replies"
    __table_args__ = (
        UniqueConstraint("review_id", name="uq_review_replies_review"),
        ForeignKeyConstraint(["review_id", "organization_id"], ["reviews.id", "reviews.organization_id"], name="fk_review_replies_review_org", ondelete="CASCADE"),
        Index("ix_review_replies_org_created", "organization_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    review_id: Mapped[UUID] = mapped_column(nullable=False)
    author_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    review: Mapped[Review] = relationship(back_populates="reply")
    author: Mapped[User] = relationship(foreign_keys=[author_user_id], viewonly=True)


class ReviewAuditLog(Base):
    __tablename__ = "review_audit_log"
    __table_args__ = (
        ForeignKeyConstraint(["review_id", "organization_id"], ["reviews.id", "reviews.organization_id"], name="fk_review_audit_log_review_org", ondelete="CASCADE"),
        Index("ix_review_audit_review_created", "review_id", "created_at"),
        Index("ix_review_audit_org_created", "organization_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    review_id: Mapped[UUID] = mapped_column(nullable=False)
    organization_id: Mapped[UUID] = mapped_column(nullable=False)
    action: Mapped[ReviewAuditAction] = mapped_column(SAEnum(ReviewAuditAction, name="review_audit_action", validate_strings=True), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)
    review: Mapped[Review] = relationship(back_populates="audit_events")
