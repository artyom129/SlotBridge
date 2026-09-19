"""Add private smart waitlist.

Revision ID: 20260919_0005
Revises: 20260915_0004
"""
from alembic import op
import sqlalchemy as sa

revision = "20260919_0005"
down_revision = "20260915_0004"
branch_labels = None
depends_on = None

def upgrade():
    status = sa.Enum("WAITING", "MATCHED", "ACCEPTED", "CANCELLED", "EXPIRED", name="waitlist_status")
    op.create_table("waitlist_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("client_user_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid()),
        sa.Column("preferred_date", sa.Date(), nullable=False),
        sa.Column("preferred_start_time", sa.Time(), nullable=False),
        sa.Column("preferred_end_time", sa.Time(), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("matched_employee_id", sa.Uuid()),
        sa.Column("matched_starts_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("preferred_start_time < preferred_end_time", name="ck_waitlist_preferred_time_order"),
        sa.ForeignKeyConstraint(["branch_id", "organization_id"], ["branches.id", "branches.organization_id"], name="fk_waitlist_branch_org"),
        sa.ForeignKeyConstraint(["service_id", "organization_id"], ["services.id", "services.organization_id"], name="fk_waitlist_service_org"),
        sa.ForeignKeyConstraint(["client_user_id", "organization_id"], ["organization_memberships.user_id", "organization_memberships.organization_id"], name="fk_waitlist_client_membership"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], name="fk_waitlist_employee"),
        sa.ForeignKeyConstraint(["matched_employee_id"], ["employees.id"], name="fk_waitlist_matched_employee"))
    op.create_index("ix_waitlist_match", "waitlist_entries", ["organization_id", "branch_id", "preferred_date", "status"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DO $b$ DECLARE r text; BEGIN FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP IF EXISTS (SELECT FROM pg_roles WHERE rolname=r) THEN EXECUTE format('REVOKE ALL ON TABLE public.waitlist_entries FROM %I',r); END IF; END LOOP; REVOKE ALL ON TABLE public.waitlist_entries FROM PUBLIC; END $b$;")

def downgrade():
    op.drop_table("waitlist_entries")
    sa.Enum(name="waitlist_status").drop(op.get_bind(), checkfirst=True)
