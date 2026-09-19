"""Keep SlotBridge tables private when hosted on Supabase PostgreSQL.

Revision ID: 20260915_0004
Revises: 20260911_0003
"""

from alembic import op


revision = "20260915_0004"
down_revision = "20260911_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    # Supabase grants Data API roles access to new public tables by default.
    # These roles must never bypass FastAPI's JWT/RBAC/tenant checks. The
    # database owner used by SQLAlchemy keeps its existing privileges.
    op.execute(
        """
        DO $slotbridge$
        DECLARE
            api_role text;
            app_tables constant text :=
                'public.alembic_version, public.appointment_audit_log, '
                'public.appointment_status_history, public.appointments, '
                'public.blocked_slots, public.branches, public.employee_services, '
                'public.employees, public.organization_memberships, '
                'public.organizations, public.schedule_breaks, '
                'public.schedule_exceptions, public.services, public.users, '
                'public.work_schedules';
        BEGIN
            FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role']
            LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
                    EXECUTE format(
                        'REVOKE ALL PRIVILEGES ON TABLE %s FROM %I',
                        app_tables, api_role
                    );
                    EXECUTE format(
                        'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        'REVOKE ALL PRIVILEGES ON TABLES FROM %I', api_role
                    );
                END IF;
            END LOOP;
            EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE ' || app_tables || ' FROM PUBLIC';
        END
        $slotbridge$;
        """
    )


def downgrade() -> None:
    # Deliberately retain the security boundary on rollback. Re-granting
    # Supabase API access could expose password hashes and cross-tenant data.
    pass
