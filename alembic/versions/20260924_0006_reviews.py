"""Add tenant-scoped reviews, reports, replies, and audit trail.

Revision ID: 20260924_0006
Revises: 20260919_0005
"""
from alembic import op
import sqlalchemy as sa

revision = "20260924_0006"
down_revision = "20260919_0005"
branch_labels = None
depends_on = None


def upgrade():
    review_status = sa.Enum("PUBLISHED", "HIDDEN", "FLAGGED", name="review_status")
    report_status = sa.Enum("OPEN", "RESOLVED", "DISMISSED", name="review_report_status")
    audit_action = sa.Enum("REVIEW_CREATED", "REVIEW_UPDATED", "REVIEW_HIDDEN", "REVIEW_RESTORED", "REVIEW_REPORTED", "REVIEW_REPLY_CREATED", "REVIEW_REPLY_UPDATED", name="review_audit_action")
    op.add_column("organizations", sa.Column("external_review_url_2gis", sa.String(1000)))
    op.create_table(
        "reviews",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False), sa.Column("client_user_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False), sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("overall_rating", sa.Integer(), nullable=False), sa.Column("quality_rating", sa.Integer()),
        sa.Column("service_rating", sa.Integer()), sa.Column("punctuality_rating", sa.Integer()),
        sa.Column("comment", sa.Text()), sa.Column("is_anonymous", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("status", review_status, server_default="PUBLISHED", nullable=False), sa.Column("moderation_note", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("overall_rating BETWEEN 1 AND 5", name="ck_reviews_overall_rating"),
        sa.CheckConstraint("quality_rating IS NULL OR quality_rating BETWEEN 1 AND 5", name="ck_reviews_quality_rating"),
        sa.CheckConstraint("service_rating IS NULL OR service_rating BETWEEN 1 AND 5", name="ck_reviews_service_rating"),
        sa.CheckConstraint("punctuality_rating IS NULL OR punctuality_rating BETWEEN 1 AND 5", name="ck_reviews_punctuality_rating"),
        sa.UniqueConstraint("appointment_id", name="uq_reviews_appointment"), sa.UniqueConstraint("id", "organization_id", name="uq_reviews_id_org"),
        sa.ForeignKeyConstraint(["appointment_id", "organization_id"], ["appointments.id", "appointments.organization_id"], name="fk_reviews_appointment_org", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_reviews_organization", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["client_user_id", "organization_id"], ["organization_memberships.user_id", "organization_memberships.organization_id"], name="fk_reviews_client_membership", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["client_user_id"], ["users.id"], name="fk_reviews_client_user", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["employee_id", "organization_id"], ["employees.id", "employees.organization_id"], name="fk_reviews_employee_org", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_id", "organization_id"], ["services.id", "services.organization_id"], name="fk_reviews_service_org", ondelete="RESTRICT"),
    )
    op.create_index("ix_reviews_employee_status_created", "reviews", ["employee_id", "status", "created_at"])
    op.create_index("ix_reviews_org_status_created", "reviews", ["organization_id", "status", "created_at"])
    op.create_index("ix_reviews_service_status", "reviews", ["service_id", "status"])
    op.create_table(
        "review_reports",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("review_id", sa.Uuid(), nullable=False), sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(100), nullable=False), sa.Column("comment", sa.String(1000)),
        sa.Column("status", report_status, server_default="OPEN", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("review_id", "reporter_user_id", name="uq_review_reports_reporter"),
        sa.ForeignKeyConstraint(["review_id", "organization_id"], ["reviews.id", "reviews.organization_id"], name="fk_review_reports_review_org", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], name="fk_review_reports_reporter_user", ondelete="RESTRICT"),
    )
    op.create_index("ix_review_reports_org_status_created", "review_reports", ["organization_id", "status", "created_at"])
    op.create_table(
        "review_replies",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("review_id", sa.Uuid(), nullable=False), sa.Column("author_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("review_id", name="uq_review_replies_review"),
        sa.ForeignKeyConstraint(["review_id", "organization_id"], ["reviews.id", "reviews.organization_id"], name="fk_review_replies_review_org", ondelete="CASCADE"),
    )
    op.create_index("ix_review_replies_org_created", "review_replies", ["organization_id", "created_at"])
    op.create_table(
        "review_audit_log",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False), sa.Column("action", audit_action, nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["review_id", "organization_id"], ["reviews.id", "reviews.organization_id"], name="fk_review_audit_log_review_org", ondelete="CASCADE"),
    )
    op.create_index("ix_review_audit_review_created", "review_audit_log", ["review_id", "created_at"])
    op.create_index("ix_review_audit_org_created", "review_audit_log", ["organization_id", "created_at"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DO $b$ DECLARE r text; t text; BEGIN FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP IF EXISTS (SELECT FROM pg_roles WHERE rolname=r) THEN FOREACH t IN ARRAY ARRAY['reviews','review_reports','review_replies','review_audit_log'] LOOP EXECUTE format('REVOKE ALL ON TABLE public.%I FROM %I',t,r); END LOOP; END IF; END LOOP; REVOKE ALL ON TABLE public.reviews, public.review_reports, public.review_replies, public.review_audit_log FROM PUBLIC; END $b$;")


def downgrade():
    op.drop_table("review_audit_log")
    op.drop_table("review_replies")
    op.drop_table("review_reports")
    op.drop_table("reviews")
    op.drop_column("organizations", "external_review_url_2gis")
    sa.Enum(name="review_audit_action").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="review_report_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="review_status").drop(op.get_bind(), checkfirst=True)
