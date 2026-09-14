"""Add Stage 3 scheduling and availability data.

Revision ID: 20260911_0002
Revises: 20260910_0001
Create Date: 2026-09-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260911_0002"
down_revision: Union[str, None] = "20260910_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    op.create_unique_constraint(
        "uq_employees_id_branch_org",
        "employees",
        ["id", "branch_id", "organization_id"],
    )

    op.create_table(
        "work_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "day_of_week BETWEEN 0 AND 6",
            name="ck_work_schedules_weekday",
        ),
        sa.CheckConstraint("start_time < end_time", name="ck_work_schedules_time_order"),
        sa.ForeignKeyConstraint(
            ["employee_id", "branch_id", "organization_id"],
            ["employees.id", "employees.branch_id", "employees.organization_id"],
            name="fk_work_schedules_employee_branch_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_work_schedules_branch_org",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "employee_id",
            "branch_id",
            "day_of_week",
            "start_time",
            "end_time",
            name="uq_work_schedules_exact_window",
        ),
    )
    op.create_index(
        "ix_work_schedules_lookup",
        "work_schedules",
        ["employee_id", "branch_id", "day_of_week", "is_active"],
    )

    op.create_table(
        "schedule_breaks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "day_of_week BETWEEN 0 AND 6",
            name="ck_schedule_breaks_weekday",
        ),
        sa.CheckConstraint("start_time < end_time", name="ck_schedule_breaks_time_order"),
        sa.ForeignKeyConstraint(
            ["employee_id", "branch_id", "organization_id"],
            ["employees.id", "employees.branch_id", "employees.organization_id"],
            name="fk_schedule_breaks_employee_branch_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_schedule_breaks_branch_org",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "employee_id",
            "branch_id",
            "day_of_week",
            "start_time",
            "end_time",
            name="uq_schedule_breaks_exact_window",
        ),
    )
    op.create_index(
        "ix_schedule_breaks_lookup",
        "schedule_breaks",
        ["employee_id", "branch_id", "day_of_week", "is_active"],
    )

    op.create_table(
        "schedule_exceptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("is_day_off", sa.Boolean(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "(is_day_off AND start_time IS NULL AND end_time IS NULL) OR "
            "(NOT is_day_off AND start_time IS NOT NULL AND end_time IS NOT NULL "
            "AND start_time < end_time)",
            name="ck_schedule_exceptions_shape",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id", "branch_id", "organization_id"],
            ["employees.id", "employees.branch_id", "employees.organization_id"],
            name="fk_schedule_exceptions_employee_branch_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_schedule_exceptions_branch_org",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "employee_id",
            "branch_id",
            "local_date",
            "start_time",
            "end_time",
            name="uq_schedule_exceptions_exact_window",
        ),
    )
    op.create_index(
        "ix_schedule_exceptions_lookup",
        "schedule_exceptions",
        ["employee_id", "branch_id", "local_date", "is_active"],
    )
    op.create_index(
        "uq_schedule_exceptions_active_day_off",
        "schedule_exceptions",
        ["employee_id", "branch_id", "local_date"],
        unique=True,
        postgresql_where=sa.text("is_day_off AND is_active"),
    )

    op.create_table(
        "blocked_slots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("starts_at < ends_at", name="ck_blocked_slots_time_order"),
        sa.ForeignKeyConstraint(
            ["employee_id", "branch_id", "organization_id"],
            ["employees.id", "employees.branch_id", "employees.organization_id"],
            name="fk_blocked_slots_employee_branch_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_blocked_slots_branch_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_blocked_slots_lookup",
        "blocked_slots",
        ["employee_id", "branch_id", "starts_at", "ends_at", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_blocked_slots_lookup", table_name="blocked_slots")
    op.drop_table("blocked_slots")
    op.drop_index(
        "uq_schedule_exceptions_active_day_off", table_name="schedule_exceptions"
    )
    op.drop_index("ix_schedule_exceptions_lookup", table_name="schedule_exceptions")
    op.drop_table("schedule_exceptions")
    op.drop_index("ix_schedule_breaks_lookup", table_name="schedule_breaks")
    op.drop_table("schedule_breaks")
    op.drop_index("ix_work_schedules_lookup", table_name="work_schedules")
    op.drop_table("work_schedules")
    op.drop_constraint("uq_employees_id_branch_org", "employees", type_="unique")
