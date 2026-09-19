"""Create Stage 2 core domain.

Revision ID: 20260910_0001
Revises: None
Create Date: 2026-09-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260910_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role = postgresql.ENUM("CLIENT", "EMPLOYEE", "ADMIN", name="user_role")


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
    user_role.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column(
            "role",
            postgresql.ENUM(
                "CLIENT", "EMPLOYEE", "ADMIN", name="user_role", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )

    op.create_table(
        "branches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_branches_id_org"),
        sa.UniqueConstraint("organization_id", "name", name="uq_branches_org_name"),
    )
    op.create_index(
        "ix_branches_organization_active",
        "branches",
        ["organization_id", "is_active"],
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["branch_id", "organization_id"],
            ["branches.id", "branches.organization_id"],
            name="fk_employees_branch_org",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_employees_id_org"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_employees_user_org"),
    )
    op.create_index("ix_employees_org_active", "employees", ["organization_id", "is_active"])
    op.create_index("ix_employees_branch_active", "employees", ["branch_id", "is_active"])

    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("duration_minutes > 0", name="ck_services_duration_positive"),
        sa.CheckConstraint("price IS NULL OR price >= 0", name="ck_services_price_nonnegative"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_services_id_org"),
        sa.UniqueConstraint("organization_id", "name", name="uq_services_org_name"),
    )
    op.create_index(
        "ix_services_organization_active",
        "services",
        ["organization_id", "is_active"],
    )

    op.create_table(
        "employee_services",
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("duration_override_minutes", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "duration_override_minutes IS NULL OR duration_override_minutes > 0",
            name="ck_employee_services_duration_positive",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id", "organization_id"],
            ["employees.id", "employees.organization_id"],
            name="fk_employee_services_employee_org",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_id", "organization_id"],
            ["services.id", "services.organization_id"],
            name="fk_employee_services_service_org",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("employee_id", "service_id"),
    )
    op.create_index(
        "ix_employee_services_service", "employee_services", ["service_id"]
    )
    op.create_index(
        "ix_employee_services_organization", "employee_services", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_employee_services_organization", table_name="employee_services")
    op.drop_index("ix_employee_services_service", table_name="employee_services")
    op.drop_table("employee_services")
    op.drop_index("ix_services_organization_active", table_name="services")
    op.drop_table("services")
    op.drop_index("ix_employees_branch_active", table_name="employees")
    op.drop_index("ix_employees_org_active", table_name="employees")
    op.drop_table("employees")
    op.drop_index("ix_branches_organization_active", table_name="branches")
    op.drop_table("branches")
    op.drop_table("organizations")
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_table("users")
    user_role.drop(op.get_bind(), checkfirst=True)
