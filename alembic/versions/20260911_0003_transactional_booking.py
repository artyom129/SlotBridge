"""Add Stage 4 transactional booking core.

Revision ID: 20260911_0003
Revises: 20260911_0002
Create Date: 2026-09-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260911_0003"
down_revision: Union[str, None] = "20260911_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


appointment_status = postgresql.ENUM(
    "BOOKED",
    "CONFIRMED",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
    "NO_SHOW",
    name="appointment_status",
)
appointment_audit_action = postgresql.ENUM(
    "CREATED",
    "CANCELLED",
    "RESCHEDULED",
    "STATUS_CHANGED",
    name="appointment_audit_action",
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    appointment_status.create(bind, checkfirst=True)
    appointment_audit_action.create(bind, checkfirst=True)

    op.create_table(
        "organization_memberships",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "organization_id"),
    )
    op.create_index(
        "ix_organization_memberships_org",
        "organization_memberships",
        ["organization_id", "user_id"],
    )

    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("client_user_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "BOOKED",
                "CONFIRMED",
                "IN_PROGRESS",
                "COMPLETED",
                "CANCELLED",
                "NO_SHOW",
                name="appointment_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("idempotency_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("client_note", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("starts_at < ends_at", name="ck_appointments_time_order"),
        sa.CheckConstraint(
            "(status = 'CANCELLED' AND cancelled_at IS NOT NULL) OR "
            "(status <> 'CANCELLED' AND cancelled_at IS NULL)",
            name="ck_appointments_cancellation_state",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["client_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_appointments_branch_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id", "branch_id", "organization_id"],
            ["employees.id", "employees.branch_id", "employees.organization_id"],
            name="fk_appointments_employee_branch_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["service_id", "organization_id"],
            ["services.id", "services.organization_id"],
            name="fk_appointments_service_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["client_user_id", "organization_id"],
            [
                "organization_memberships.user_id",
                "organization_memberships.organization_id",
            ],
            name="fk_appointments_client_membership",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_appointments_id_org"),
        sa.UniqueConstraint(
            "client_user_id",
            "idempotency_key",
            name="uq_appointments_client_idempotency_key",
        ),
        postgresql.ExcludeConstraint(
            ("employee_id", "="),
            (sa.text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            where=sa.text(
                "status IN ('BOOKED', 'CONFIRMED', 'IN_PROGRESS')"
            ),
            using="gist",
            name="ex_appointments_employee_time_active",
        ),
    )
    op.create_index(
        "ix_appointments_client_start_status",
        "appointments",
        ["client_user_id", "starts_at", "status"],
    )
    op.create_index(
        "ix_appointments_employee_start_status",
        "appointments",
        ["employee_id", "starts_at", "status"],
    )
    op.create_index(
        "ix_appointments_org_branch_start",
        "appointments",
        ["organization_id", "branch_id", "starts_at"],
    )

    op.create_table(
        "appointment_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column(
            "old_status",
            postgresql.ENUM(
                "BOOKED",
                "CONFIRMED",
                "IN_PROGRESS",
                "COMPLETED",
                "CANCELLED",
                "NO_SHOW",
                name="appointment_status",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "new_status",
            postgresql.ENUM(
                "BOOKED",
                "CONFIRMED",
                "IN_PROGRESS",
                "COMPLETED",
                "CANCELLED",
                "NO_SHOW",
                name="appointment_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "old_status IS NULL OR old_status <> new_status",
            name="ck_appointment_status_history_changed",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id", "organization_id"],
            ["appointments.id", "appointments.organization_id"],
            name="fk_appointment_status_history_appointment_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_appointment_status_history_appointment_created",
        "appointment_status_history",
        ["appointment_id", "created_at"],
    )

    op.create_table(
        "appointment_audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action",
            postgresql.ENUM(
                "CREATED",
                "CANCELLED",
                "RESCHEDULED",
                "STATUS_CHANGED",
                name="appointment_audit_action",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("old_starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("old_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id", "organization_id"],
            ["appointments.id", "appointments.organization_id"],
            name="fk_appointment_audit_log_appointment_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_appointment_audit_log_appointment_created",
        "appointment_audit_log",
        ["appointment_id", "created_at"],
    )
    op.create_index(
        "ix_appointment_audit_log_org_created",
        "appointment_audit_log",
        ["organization_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_appointment_audit_log_org_created",
        table_name="appointment_audit_log",
    )
    op.drop_index(
        "ix_appointment_audit_log_appointment_created",
        table_name="appointment_audit_log",
    )
    op.drop_table("appointment_audit_log")
    op.drop_index(
        "ix_appointment_status_history_appointment_created",
        table_name="appointment_status_history",
    )
    op.drop_table("appointment_status_history")
    op.drop_index("ix_appointments_org_branch_start", table_name="appointments")
    op.drop_index(
        "ix_appointments_employee_start_status", table_name="appointments"
    )
    op.drop_index("ix_appointments_client_start_status", table_name="appointments")
    op.drop_table("appointments")
    op.drop_index(
        "ix_organization_memberships_org",
        table_name="organization_memberships",
    )
    op.drop_table("organization_memberships")
    appointment_audit_action.drop(op.get_bind(), checkfirst=True)
    appointment_status.drop(op.get_bind(), checkfirst=True)
