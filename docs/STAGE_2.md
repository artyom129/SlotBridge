# SlotBridge — Stage 2 implementation report

Date: 10 September 2026
Baseline: Stage 1 audit on `main` commit `cd5acbd`
Scope: PostgreSQL/domain/auth foundation; no booking, schedules, realtime, or Flutter

## 1. SUMMARY

Stage 2 adds a PostgreSQL-backed core domain to the existing FastAPI application.
SQLAlchemy provides models and request-scoped sessions; Alembic owns production
schema creation. Authentication uses Argon2 password hashes and short-lived JWT
access tokens. Reusable dependencies enforce `CLIENT`, `EMPLOYEE`, and `ADMIN`
roles, and the ADMIN path is covered by positive and negative tests.

The original Mindbody/Vagaro/Google integration gateway remains in place with
its existing SQLite demo store and original service-level tests. Security around
its HTTP surface is improved without pretending that generic HMAC is a vendor's
native signature protocol.

No appointment, availability, schedule, waitlist, realtime, notification, or
mobile feature was added.

## 2. ARCHITECTURE CHANGES

The application remains one deployable modular monolith:

```text
FastAPI application
├── auth API
├── core-domain read API
├── ADMIN commands
├── liveness/readiness API
├── SQLAlchemy + request transaction dependency
│   └── PostgreSQL (primary new-domain store)
└── preserved integration gateway
    └── SQLite (temporary legacy/demo store)

Alembic -> PostgreSQL schema
Docker entrypoint -> migrate -> start Uvicorn
```

Configuration is centralized in a validated `Settings` object. A production
profile refuses SQLite and refuses unsigned webhook demo mode. The database
dependency yields one SQLAlchemy session per request, commits once after a
successful handler, and rolls back on any exception.

The dual-database arrangement is intentional and temporary: it avoids rewriting
working integration logic during the domain/auth foundation stage. Integration
data migration belongs to a later integration-hardening stage, not booking work.

## 3. DATABASE MODELS CREATED

All domain IDs are UUIDs. Mutable entities have timezone-aware creation/update
timestamps and active-state flags where applicable.

| Model | Main fields and guarantees |
|---|---|
| `User` | unique normalized email, Argon2 hash, names, nullable phone, `CLIENT/EMPLOYEE/ADMIN` enum, active state |
| `Organization` | unique slug, name, IANA timezone, active state |
| `Branch` | organization FK, organization-scoped unique name, address, nullable timezone override |
| `Employee` | user FK, organization FK, branch/organization composite FK, unique user per organization, display name |
| `Service` | organization FK, organization-scoped unique name, description, positive duration, non-negative nullable price |
| `EmployeeService` | employee/service many-to-many link, optional positive duration override, tenant-consistency composite FKs |

Deletion is conservative: users, organizations, branches, employees, and
services referenced by core entities use `RESTRICT`. EmployeeService links use
`CASCADE` when their employee or service is removed. Cross-organization branch
assignment and cross-organization employee-service assignment are rejected by
database constraints, not only application checks.

Indexes cover case-insensitive email uniqueness, organization active lookups,
branch/employee active lookups, service lookups, and association traversal.

## 4. MIGRATIONS CREATED

Alembic revision `20260910_0001` creates the entire Stage 2 core domain:

- PostgreSQL `user_role` enum;
- six domain tables;
- primary, foreign, composite foreign, unique, and check constraints;
- supporting indexes;
- UTC-capable `timestamptz` columns;
- reverse-order downgrade.

Application startup never calls `create_all()`. The container entrypoint executes
`alembic upgrade head` before Uvicorn. `create_all()` is present only in the
isolated SQLite test fixture and is explicitly documented there.

Locally, Alembic history and PostgreSQL offline SQL generation passed. CI is
configured to run a real PostgreSQL service, apply the migration, run
`alembic check`, and execute the seed before tests. A live local migration could
not be executed because neither PostgreSQL nor the Docker Linux engine was
running on the audit host.

## 5. AUTH IMPLEMENTATION

Implemented endpoints:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

Public registration always creates `CLIENT`; the request has no role field, so a
caller cannot self-promote. Email is normalized to lowercase and is protected by
both exact and case-insensitive database uniqueness. Passwords are validated,
hashed with the maintained `pwdlib` Argon2 implementation, and never returned.

Login verifies the password hash and active state, then issues an HS256 JWT with
subject, role snapshot, token type, issued-at time, and expiration. The signing
secret and lifetime come only from environment configuration; the secret must be
at least 32 characters. Authorization reloads the user and current role from the
database, so a stale token role is not trusted as the source of truth.

Stage 2 intentionally provides access tokens only. Refresh-token rotation,
revocation, device sessions, password reset, and email verification are listed as
future auth hardening, not falsely described as implemented.

## 6. RBAC IMPLEMENTATION

Reusable dependencies now provide:

- authenticated active user;
- `require_roles(...)`;
- `require_client`;
- `require_employee`;
- `require_admin`.

The organization creation command and sensitive legacy operations use
`require_admin`. Tests prove that unauthenticated requests receive `401`, CLIENT
and EMPLOYEE receive `403` for an ADMIN operation, and ADMIN succeeds.

Roles are global in this first model. Organization-scoped memberships/permissions
remain a known requirement before true multi-tenancy; Stage 2 domain foreign keys
already prevent cross-organization employee/branch/service relationships.

## 7. API ENDPOINTS CREATED/CHANGED

### Created

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `GET /organizations`
- `GET /organizations/{id}`
- `GET /organizations/{id}/branches`
- `GET /organizations/{id}/services`
- `GET /organizations/{id}/employees`
- `GET /employees/{id}/services`
- `POST /admin/organizations` (ADMIN)
- `GET /api/v1/health/live`
- `GET /api/v1/health/ready` (executes `SELECT 1`)

All domain reads require a valid token and use explicit response schemas. Lists
are bounded to 100 rows for this foundation stage.

### Changed without removal

Existing route names remain. Appointment/conflict/feasibility/sync-job/dead-letter
reads and manual reconcile/sync-plan operations now require ADMIN. Legacy
appointment responses omit `raw` and `origin_token`. Dashboard appointment rows
no longer display client names. Webhook routes now apply the verification policy
before JSON parsing/ingestion and reject bodies over 1 MB.

## 8. SECURITY FIXES

- Argon2 password hashing; no plaintext password storage.
- JWT secret and expiry are environment-controlled and validated.
- Public registration cannot choose a privileged role.
- Reusable backend authorization; protection is not delegated to the future UI.
- Sensitive legacy routes require ADMIN.
- Raw webhook payload and origin token removed from legacy appointment output.
- Client names removed from the public demo dashboard.
- CSV values with spreadsheet formula prefixes are neutralized.
- Webhook body-size limit.
- Constant-time HMAC-SHA256 comparison for configured shared-secret ingress.
- Configured JWT and HMAC secrets have enforced minimum lengths.
- Unsigned webhooks denied by default and impossible to enable in production.
- PostgreSQL required by production configuration.
- Docker backend runs as a non-root user.
- `.dockerignore` excludes `.env`, virtual environments, Git metadata, caches,
  and generated SQLite data from the image build context.
- Secrets and demo database files remain ignored by Git.

The HMAC header is a secure SlotBridge/proxy mechanism and extension point. It is
not labeled as Mindbody, Vagaro, or Google native verification. Native provider
verification requires confirmed vendor documentation and credentials.

## 9. SEED DATA

`scripts/seed_domain.py` is idempotent and refuses production execution. It
creates fictional data only:

- `SlotBridge Demo` organization;
- `Main Branch`;
- one ADMIN, two EMPLOYEE, two CLIENT users;
- Haircut (60), Consultation (30), Extended Service (90);
- two Employee profiles;
- four EmployeeService assignments with different capabilities.

All accounts use the explicitly documented development/demo password
`SlotBridgeDemo!2026`. The script does not print the password. Re-running does
not duplicate entities or reset an existing account password.

The old `scripts/seed_demo.py` remains unchanged and was separately verified.

## 10. FILES CREATED

| File | Reason |
|---|---|
| `app/config.py` | validated environment settings and production safety checks |
| `app/database.py` | engine, session factory, request transaction, readiness query |
| `app/models.py` | Stage 2 SQLAlchemy domain and relational constraints |
| `app/schemas.py` | strict auth/domain request and response contracts |
| `app/security.py` | maintained Argon2 hashing and JWT encode/decode |
| `app/dependencies.py` | authenticated-user and reusable role dependencies |
| `app/webhook_security.py` | honest HMAC extension point and safe demo policy |
| `app/api/__init__.py` | API package boundary |
| `app/api/auth.py` | register/login/me endpoints |
| `app/api/domain.py` | authenticated organization/branch/service/employee reads |
| `app/api/admin.py` | minimal ADMIN command proving RBAC |
| `app/api/health.py` | liveness and database readiness |
| `alembic.ini` | Alembic configuration |
| `alembic/env.py` | metadata/environment migration runtime |
| `alembic/script.py.mako` | migration template |
| `alembic/versions/20260910_0001_core_domain.py` | initial PostgreSQL schema |
| `scripts/seed_domain.py` | idempotent fictional Stage 2 seed |
| `scripts/entrypoint.sh` | migrate-before-start container entrypoint |
| `.dockerignore` | prevent secrets, local environments, caches, and demo DBs entering images |
| `tests/conftest.py` | isolated SQLite locally and migrated PostgreSQL in CI fixtures |
| `tests/test_auth.py` | registration/login/me and password-storage tests |
| `tests/test_rbac.py` | CLIENT/EMPLOYEE/ADMIN authorization matrix |
| `tests/test_domain.py` | constraints, relationships, seed, and core API tests |
| `tests/test_webhook_security.py` | HMAC and protected legacy-route tests |
| `tests/test_config.py` | production PostgreSQL and webhook safety guards |
| `docs/STAGE_2.md` | this implementation report |

## 11. FILES MODIFIED

| File | Reason |
|---|---|
| `requirements.txt` | SQLAlchemy, Alembic, psycopg, PyJWT, pwdlib/Argon2, email validation |
| `.env.example` | PostgreSQL, JWT, environment, and webhook security configuration |
| `app/main.py` | register routers; protect/sanitize legacy HTTP surface; HMAC and CSV safety |
| `Dockerfile` | non-root runtime and migration entrypoint |
| `docker-compose.yml` | PostgreSQL service, health checks, persistent volumes, startup dependency |
| `.github/workflows/tests.yml` | real PostgreSQL migration/check/seed CI service |
| `README.md` | accurate Stage 2 setup, API, seed, migration, security, and limitations |

`LICENSE`, `NOTICE`, and `docs/STAGE_1_AUDIT.md` were preserved unchanged.
Existing integration core, examples, and legacy seed were not rewritten.

## 12. TEST RESULTS

Local final checks:

| Check | Result |
|---|---|
| Full Pytest suite | **16 passed**, including all 3 original Stage 1 tests |
| Stage 1 tests separately | **3 passed** |
| Python compileall | **passed** |
| pip dependency consistency | **no broken requirements** |
| Git diff whitespace check | **passed**; only Git CRLF notices on Windows |
| Alembic history | one linear head: `20260910_0001` |
| PostgreSQL offline migration SQL | **generated successfully** |
| Legacy demo seed | **passed**: 3 appointments, 2 conflicts, 3 jobs, 1 dead letter |
| Stage 2 seed | **passed twice in tests**, counts remained 1 org, 1 branch, 5 users, 2 employees, 3 services, 4 assignments |

The suite verifies registration, case-insensitive duplicate email, login success,
wrong password, `/auth/me` with/without token, password hash storage, RBAC denial
and success, organization/branch/employee/service relations, branch tenant
constraint, EmployeeService tenant constraint, all requested read APIs, seed
idempotency, liveness/readiness, HMAC acceptance/rejection, and legacy data
protection.

Local tests use SQLite with foreign keys enabled for speed and isolation. When
`DATABASE_URL` is supplied by CI, the fixture preserves it, truncates the
Alembic-created PostgreSQL tables between tests, and runs the same suite against
PostgreSQL.

Two deprecation warnings originate from the freshly resolved
FastAPI/Starlette/TestClient dependency combination. They are non-failing but
should be removed when the dependency set is locked/reconciled.

## 13. DOCKER RESULTS

- `docker compose config --quiet`: **passed** with `.env` copied from the example.
- Docker CLI and Compose are installed.
- `docker compose build`: **not executed successfully** because the Docker Desktop
  Linux engine pipe was absent.
- Container startup, online Alembic migration, seed inside the container, and
  container health checks: **not executable on this host while the engine is off**.

This is recorded as an environment limitation, not presented as a successful
runtime check. The same online migration/seed path is configured for PostgreSQL
in GitHub Actions.

## 14. KNOWN ISSUES

1. The Docker image and online PostgreSQL migration still need one run on a host
   with Docker engine or PostgreSQL available.
2. The integration gateway remains on SQLite and its inbox/upsert/reconcile/job
   flow is not one atomic transaction. A failure after recording a webhook can
   still leave it marked as consumed.
3. Real vendor signature protocols are not implemented without confirmed vendor
   contracts; only the real generic SlotBridge HMAC mechanism exists.
4. JWT refresh rotation, revocation, rate limiting, password reset, and email
   verification are not part of Stage 2.
5. Roles are global; organization memberships and tenant-scoped admin/employee
   grants are not yet modeled.
6. Core domain administration intentionally exposes only organization creation;
   branch/service/employee writes currently come from the controlled seed.
7. Dependency resolution is range-based and emits two TestClient deprecations.
8. API lists use a protective fixed limit rather than cursor pagination.
9. Direct database writes can bypass IANA timezone validation; the implemented
   ADMIN API validates organization timezones.

## 15. RISKS FOR NEXT STAGE

- Schedule rules must not be modeled as JSON blobs; recurring windows, breaks,
  exceptions, and blocks need relational constraints and explicit timezone rules.
- Availability calculations must not reuse the legacy global overlap detector;
  it lacks employee/resource scope and accepts invalid timestamps.
- DST gaps/ambiguities, branch overrides, overnight shifts, buffers, and
  half-open intervals need tests before appointment writes exist.
- Introducing booking in the same change as schedules/availability would weaken
  reviewability. Establish and test a deterministic read-only availability engine
  first.
- True tenant authorization should be designed before exposing broad admin CRUD.
- Do not use Redis or UI state as the future booking source of truth; PostgreSQL
  constraints and transactions must enforce reservations.

## 16. EXACT RECOMMENDED SCOPE FOR STAGE 3

Stage 3 should implement **schedules and read-only availability**, not booking.

### In scope

1. Add relational `work_schedules`, `schedule_breaks`, `schedule_exceptions`, and
   `blocked_slots` models and one Alembic revision.
2. Define half-open interval rules, positive durations, overlap policy, IANA
   timezone ownership, and organization/employee/branch composite integrity.
3. Add ADMIN schedule configuration commands and EMPLOYEE self-schedule/block
   commands with tenant/object authorization.
4. Implement a pure availability service:
   service -> eligible employee -> work windows -> exceptions -> breaks -> blocks
   -> candidate slots. There are no appointments to subtract yet.
5. Add `GET /availability` with employee, service, branch, date, timezone, slot
   granularity, and bounded horizon validation.
6. Add nearest available date/slot suggestions within a bounded search window.
7. Test normal days, multiple windows, boundaries, breaks, blocks, inactive
   entities, different employees, tenant isolation, overnight rules, DST gaps and
   repeated times, and duration overrides.
8. Add deterministic Stage 3 schedules/blocks to the demo seed and document a
   reproducible availability walkthrough.
9. Run the full Stage 2 regression suite and a real PostgreSQL migration check.

### Explicitly out of scope

- Appointment tables or booking commands.
- Double-booking transaction/exclusion constraint.
- Cancellation/rescheduling/status history.
- Waitlist, notifications, workers, Redis, WebSocket/realtime.
- Flutter/mobile code.
- Live provider writes or legacy SQLite migration.

Stage 4 should then introduce appointments and the mandatory parallel-booking
test against PostgreSQL. Stage 3 must stop after deterministic availability is
demonstrated and tested.
