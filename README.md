# SlotBridge

Cross-platform scheduling system with one Flutter client for Android and iOS,
a FastAPI backend, timezone-aware availability, transactional first-party
booking, and the original Mindbody/Vagaro/Google Calendar integration demo.

Copyright © 2026 Artyom Koncha. All Rights Reserved.

## Implemented state

Stage 5 provides everything from Stages 1-4 plus:

- one shared Flutter application under `mobile/`, with standard Android and iOS
  platform projects;
- CLIENT login/session restoration backed by encrypted platform storage;
- a responsive end-to-end booking flow from service and employee selection to
  server-provided availability and confirmation;
- appointment lists, details, status history, cancellation, and atomic
  rescheduling;
- mobile-safe idempotency retry behavior and typed backend error handling;
- Flutter analysis, widget/unit tests, and an opt-in real FastAPI contract E2E.

Stage 4 provides the transactional backend foundation:

- first-party Appointment records with a strict lifecycle: `BOOKED`,
  `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, and `NO_SHOW`;
- transactional create, cancel, reschedule, detail, list, and status APIs;
- server-owned organization, client, and end time (derived from the selected
  service/employee-service duration);
- PostgreSQL `btree_gist` exclusion protection against overlapping active
  appointments for one employee, using half-open `[start, end)` intervals;
- persistent client-scoped `Idempotency-Key` handling;
- availability subtraction of active appointments;
- tenant-scoped authorization for clients, assigned employees, and organization
  administrators;
- append-only status history and booking audit events;
- six PostgreSQL-only race-condition tests in CI.

The preserved foundation also provides:

- PostgreSQL as the primary database for the new core domain;
- SQLAlchemy session/transaction management and FastAPI dependency injection;
- Alembic migrations;
- User, Organization, Branch, Employee, Service, and EmployeeService models;
- WorkSchedule, ScheduleBreak, ScheduleException, and BlockedSlot models with
  database-level tenant consistency and interval checks;
- Argon2 password hashing, JWT access tokens, and role-based access control;
- registration, login, and current-user APIs;
- authenticated read APIs for organizations, branches, employees, and services;
- read-only slot calculation based on local schedules, service duration,
  date-specific exceptions, recurring breaks, and absolute blocked intervals;
- ADMIN schedule commands and EMPLOYEE self-service blocked-slot commands;
- effective timezone selection (`Branch.timezone` then `Organization.timezone`)
  with IANA `zoneinfo` conversion;
- configurable slot-start interval (`AVAILABILITY_SLOT_INTERVAL_MINUTES`, default 15);
- liveness and PostgreSQL readiness checks;
- an idempotent development/demo seed;
- PostgreSQL migration/seed checks in CI;
- the existing SQLite-backed integration gateway, dashboard, normalizers,
  conflict report, feasibility matrix, and sync-plan demo.

Not implemented yet: waitlist, realtime/WebSocket, notifications, payments, or
AI. The legacy gateway remains separate from the first-party booking
engine and only detects imported overlaps after ingestion. Reading
`/availability` does not reserve a slot; only a successful `POST /appointments`
does.

## Architecture

The mobile application is a shared Flutter codebase. Its repositories call a
modular FastAPI monolith. The new backend domain uses PostgreSQL; the preserved
integration demo temporarily retains its own SQLite store.

```text
Flutter (shared lib/)
├── Android host
└── iOS host
        │ HTTPS / JSON
        ▼
FastAPI
├── /auth                         JWT authentication
├── /organizations, /employees   core domain API
├── /availability                 read-only slot calculation
├── /appointments                 transactional booking lifecycle
├── /admin                        ADMIN-only domain/schedule commands
├── /employee/blocked-slots       employee-owned blocks
├── /api/v1/health                liveness/readiness
└── legacy integration routes
      ├── provider normalization
      ├── SQLite canonical schedule
      └── conflict/sync-plan demo

PostgreSQL <- SQLAlchemy <- request-scoped transaction
             Alembic migrations
```

See [`docs/STAGE_1_AUDIT.md`](docs/STAGE_1_AUDIT.md) for the original audit and
[`docs/STAGE_2.md`](docs/STAGE_2.md) for the foundation history. The implemented
scheduling rules and Stage 3 verification are in [`docs/STAGE_3.md`](docs/STAGE_3.md).
The Stage 4 design is documented in
[`docs/booking-engine.md`](docs/booking-engine.md), with the implementation and
verification record in [`docs/STAGE_4.md`](docs/STAGE_4.md). The mobile design
and platform setup are in [`docs/mobile-client.md`](docs/mobile-client.md), and
the Stage 5 verification record is in [`docs/STAGE_5.md`](docs/STAGE_5.md).

## Local Windows quick start (without Docker)

SlotBridge's booking engine uses a native PostgreSQL Windows service in this
mode. SQLite is not used for the booking database. Install the official
PostgreSQL 17 distribution from `PostgreSQL.PostgreSQL.17` with WinGet or from
<https://www.postgresql.org/download/windows/>. Use port `5432`, enable the
Windows service, and remember the PostgreSQL administrator password. The
program and data directories may be placed on `D:` when space on `C:` is
limited.

One-time database setup in `psql` as the `postgres` administrator:

```sql
CREATE ROLE slotbridge LOGIN PASSWORD '<the password used in .env>';
CREATE DATABASE slotbridge OWNER slotbridge;
```

Copy `.env.example` to `.env`, replace the development placeholders with local
secrets, and keep this host URL:

```text
DATABASE_URL=postgresql+psycopg://slotbridge:<URL-encoded-password>@127.0.0.1:5432/slotbridge
```

`.env` and the local Python environment are excluded from Git. After the
one-time setup, double-click [`start_slotbridge.bat`](start_slotbridge.bat). It
checks Python and the PostgreSQL Windows service, creates `.venv` when needed,
installs changed requirements only, applies Alembic migrations, runs the
idempotent domain seed, detects the LAN IPv4 address, and starts FastAPI on
`0.0.0.0:8000`. Keep its window open. Double-click
[`stop_slotbridge.bat`](stop_slotbridge.bat) to stop only FastAPI; PostgreSQL
continues running as a Windows service.

If the phone cannot open `http://<LAN-IP>:8000/api/v1/health/live`, allow TCP
port `8000` (or the local Python executable) for **Private networks** in Windows
Firewall. Do not disable the firewall. The laptop and phone must be on the same
Wi-Fi network.

The native service and Docker PostgreSQL cannot both publish host port `5432`.
Run `docker compose down` before native mode, or stop the Windows PostgreSQL
service before the Docker alternative.

## Docker quick start (alternative)

Docker Compose starts PostgreSQL, waits for it to become healthy, runs Alembic,
and then starts the backend.

```bash
cp .env.example .env
docker compose up --build
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Seed the new PostgreSQL domain after the backend is running:

```bash
docker compose exec slotbridge python scripts/seed_domain.py
```

Open:

- Dashboard: `http://127.0.0.1:8000`
- OpenAPI/Swagger: `http://127.0.0.1:8000/docs`
- Liveness: `http://127.0.0.1:8000/api/v1/health/live`
- PostgreSQL readiness: `http://127.0.0.1:8000/api/v1/health/ready`

## Production deployment

The zero-cost portfolio target is a Render Free Docker Web Service plus
Supabase Free PostgreSQL. Supabase is used only as a database: SlotBridge keeps
its FastAPI API, SQLAlchemy models, Alembic migrations, JWT auth, RBAC, tenant
isolation, and booking engine. The checked-in `render.yaml` creates no paid
resources and asks Render to generate the JWT secret.

Production API: <https://slotbridge-api.onrender.com>

```text
Mobile App
    │ HTTPS
    ▼
Render Free / FastAPI
    │
    ▼
Supabase Free / PostgreSQL
```

The container waits for PostgreSQL, applies Alembic migrations, and starts
Uvicorn on the hosting provider's `PORT`. It does not seed data automatically.
Configure the production readiness health check as
`/api/v1/health/ready`. Full setup, security decisions, and the verification
gate are documented in
[`docs/production-deployment.md`](docs/production-deployment.md).

Free-tier limits are explicit: Render sleeps after 15 idle minutes and wakes on
the next request; Supabase may pause a low-activity free project after one
week. A cold start can delay the first request, but the app remains independent
of the laptop. Persistent booking data stays in Supabase PostgreSQL, not on
Render's ephemeral filesystem.

## Local development

Python 3.12 and a reachable PostgreSQL instance are required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python scripts/seed_domain.py
python run.py
```

Windows PowerShell activation and environment copy:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python scripts/seed_domain.py
python run.py
```

The `DATABASE_URL` in `.env` is for host commands. Compose replaces it inside the
backend container with `DATABASE_URL_DOCKER`.

Do not use the example PostgreSQL password or JWT secret outside local
development/demo. Real secrets belong in deployment environment/secret storage,
never in Git.

## Environment variables

`.env.example` is the safe local-development template.
`.env.production.example` lists production keys with placeholders only.
`.env` and every non-example `.env.*` file are ignored by Git.

The runtime mode is selected with `SLOTBRIDGE_ENVIRONMENT`:

| Mode | Database | Seed | Security |
|---|---|---|---|
| `development` | local PostgreSQL | explicit local demo seed | HTTP LAN allowed for debug app |
| `test` | isolated test database | test-owned fixtures | deterministic test secrets |
| `production` | managed PostgreSQL only | separate guarded one-shot command | generated JWT secret and HTTPS client |

Production requires the Supabase **Session pooler** URL on port `5432` with
`sslmode=require`, a generated `JWT_SECRET`, and
`SLOTBRIDGE_ENVIRONMENT=production`. Native Flutter does not require CORS;
leave `CORS_ALLOWED_ORIGINS` empty unless an HTTPS browser origin actually
exists. Never copy local database passwords, JWT secrets, or the development
demo password into production.

## Mobile build configuration

The API URL has one source: `SLOTBRIDGE_API_BASE_URL`. Release builds default
to `https://slotbridge-api.onrender.com`; `--dart-define` can override it for a
different HTTPS deployment. No source edit is needed when switching modes.

Local Android debug/LAN example:

```powershell
flutter run --dart-define=SLOTBRIDGE_ENVIRONMENT=development --dart-define=SLOTBRIDGE_API_BASE_URL=http://192.168.100.7:8000
```

Production APK:

```powershell
flutter build apk --release
```

The deployed production command is:

```powershell
flutter build apk --release --dart-define=SLOTBRIDGE_ENVIRONMENT=production --dart-define=SLOTBRIDGE_API_BASE_URL=https://slotbridge-api.onrender.com
```

Production uses a 90-second receive timeout so the first request can survive a
Render Free cold start. Release builds reject non-HTTPS URLs.
Android cleartext traffic is disabled in release and remains enabled only in
the debug manifest for local development. The application ID remains
`com.slotbridge.slotbridge_mobile`.

## Authentication and core API

Authentication:

- `POST /auth/register` — public CLIENT registration; callers cannot choose a role.
- `POST /auth/login` — returns a short-lived JWT access token.
- `GET /auth/me` — requires `Authorization: Bearer <token>`.

Authenticated domain reads:

- `GET /organizations`
- `GET /organizations/{id}`
- `GET /organizations/{id}/branches`
- `GET /organizations/{id}/services`
- `GET /organizations/{id}/employees`
- `GET /employees/{id}/services`

ADMIN-only command:

- `POST /admin/organizations`

## Scheduling and availability

`day_of_week` is ISO-style and unambiguous: `0 = Monday` through `6 = Sunday`.
An employee may have several working intervals and several recurring breaks on
the same weekday. Overlapping or adjacent working intervals are normalized.
Overlapping breaks and blocked intervals are merged before subtraction.

A date with one or more active `ScheduleException` rows replaces the recurring
work schedule for that date. An active day-off exception makes the whole date
unavailable and cannot coexist with active replacement intervals through the
management API. Recurring breaks still apply to replacement hours. Absolute
blocked slots are persisted as timezone-aware instants and transported in UTC.

The authenticated availability endpoint accepts a date in the branch's local
calendar:

```http
GET /availability?branch_id=<uuid>&employee_id=<uuid>&service_id=<uuid>&date=2026-09-21
Authorization: Bearer <access-token>
```

Example response:

```json
{
  "date": "2026-09-21",
  "timezone": "Asia/Almaty",
  "service_duration_minutes": 60,
  "slot_interval_minutes": 15,
  "slots": [
    {
      "start": "2026-09-21T09:00:00+05:00",
      "end": "2026-09-21T10:00:00+05:00"
    }
  ]
}
```

The engine rejects inactive or cross-tenant resources, a branch mismatch, and
an employee-service mismatch. It returns schemas rather than ORM objects and
does not create or hold a booking. Active `BOOKED`, `CONFIRMED`, and
`IN_PROGRESS` appointments are subtracted from the same availability result.

ADMIN can create and fully update:

- `POST|PUT /admin/work-schedules[/{id}]`
- `POST|PUT /admin/schedule-breaks[/{id}]`
- `POST|PUT /admin/schedule-exceptions[/{id}]`
- `POST|PUT /admin/blocked-slots[/{id}]`

EMPLOYEE can create and update only a block belonging to their own employee
profile through `POST|PUT /employee/blocked-slots[/{id}]`. CLIENT cannot mutate
scheduling data.

Passwords are hashed with Argon2. JWT signing secret and expiration come from
environment configuration. Authentication credentials and password hashes are
not returned by the API.

## Transactional booking API

Clients create a booking by sending only the branch, employee, service, local
choice as an aware timestamp, and an optional note. `organization_id`,
`client_user_id`, and `ends_at` are always resolved by the server.

```http
POST /appointments
Authorization: Bearer <client-access-token>
Idempotency-Key: <stable-client-generated-key>
Content-Type: application/json

{
  "branch_id": "<uuid>",
  "employee_id": "<uuid>",
  "service_id": "<uuid>",
  "starts_at": "2026-09-22T09:00:00+05:00",
  "client_note": "Optional note"
}
```

The same client and key replay the same appointment when the payload is the
same; an immutable command fingerprint keeps this valid even after a later
reschedule. Reusing the key for different booking details returns a stable
conflict. Final race protection is enforced in PostgreSQL, not only by an
application-level availability check.

Client endpoints:

- `POST /appointments`
- `GET /appointments/me?view=all|upcoming|past|cancelled&status=<status>`
- `GET /appointments/{id}`
- `POST /appointments/{id}/cancel`
- `POST /appointments/{id}/reschedule`

Assigned employees and organization administrators can read, cancel, or
reschedule permitted appointments and move them through the allowed lifecycle
with `POST /appointments/{id}/status`. Every creation, cancellation, reschedule,
and status change is written to the audit trail. Cross-tenant and non-owner
reads return a not-found response to avoid leaking appointment existence.

Clients and administrators must have an `OrganizationMembership` for the
appointment organization. The demo seed provisions these memberships. In
development/test/demo only, public registration joins a new CLIENT to the
active `slotbridge-demo` organization when it exists. Production makes that
association only when `PUBLIC_DEMO_REGISTRATION_ENABLED=true` and the
configured active demo organization exists. Tenant isolation and RBAC remain
unchanged.

## Demo data

`python scripts/seed_domain.py` is idempotent and remains limited to
development/test/demo. Production has a separate, opt-in
`python scripts/seed_production_demo.py` command that requires
`PRODUCTION_DEMO_SEED_ENABLED=true` and a non-development
`DEMO_PASSWORD` from hosting secret storage. Neither seed runs during
production startup. Both create only fictional data:

- organization `SlotBridge Демо`;
- branch `Главный филиал`;
- one ADMIN, two EMPLOYEE, and two CLIENT users;
- Стрижка (60 мин), Консультация (30 мин), Расширенная услуга (90 мин);
- two employee profiles with different service assignments.
- organization memberships for all five demo users;
- branch and organization timezone `Asia/Almaty`;
- Monday-Friday work hours `09:00-18:00` and `10:00-19:00`;
- Alex's recurring `13:00-14:00` break;
- one day-off exception and one absolute blocked interval.
- four appointments covering upcoming `BOOKED`/`CONFIRMED`, historical
  `COMPLETED`, and `CANCELLED` examples, with history and audit rows.

Development/demo credentials only:

| Role | Email | Password |
|---|---|---|
| ADMIN | `admin@slotbridge-demo.com` | `SlotBridgeDemo!2026` |
| EMPLOYEE | `alex.employee@slotbridge-demo.com` | `SlotBridgeDemo!2026` |
| EMPLOYEE | `sam.employee@slotbridge-demo.com` | `SlotBridgeDemo!2026` |
| CLIENT | `client.a@slotbridge-demo.com` | `SlotBridgeDemo!2026` |
| CLIENT | `client.b@slotbridge-demo.com` | `SlotBridgeDemo!2026` |

The separate legacy demo remains available:

```bash
python scripts/seed_demo.py
```

## Legacy integration gateway and security

The existing route names remain available. Operational reads, exports, manual
reconciliation, and sync planning now require an ADMIN JWT. Appointment output
no longer exposes stored raw provider payloads or origin tokens. The public
dashboard no longer displays client names.

Webhook routes remain at:

- `POST /webhooks/mindbody`
- `POST /webhooks/vagaro`
- `POST /webhooks/google`

For controlled ingress, configure the corresponding `*_WEBHOOK_SECRET` and send:

```text
X-SlotBridge-Signature: sha256=<hex HMAC-SHA256 of the exact request body>
```

This is a real SlotBridge shared-secret verification mechanism and an extension
point, not a claim that each vendor natively uses this header. Provider-native
verification must follow the vendor's documented contract when live credentials
are introduced.

Unsigned webhook requests are rejected by default. They can be enabled only by
an explicit `ALLOW_UNSIGNED_DEMO_WEBHOOKS=true` in development/test/demo; the
configuration validator rejects that option in production.

## Database migrations

```bash
alembic current
alembic upgrade head
alembic check
```

Application startup does not call `create_all()`. Schema changes belong in
Alembic. `Base.metadata.create_all()` is used only by the isolated SQLite test
fixture and is clearly separated from production startup.

## Tests

```bash
pytest -q
```

The suite covers the preserved Stage 1/2 behavior plus exact slot generation,
interval merging/subtraction, 30/60/90-minute services, multiple work windows,
breaks, blocks, date exceptions, inactive and cross-tenant rejection, two IANA
timezones, invalid configuration, scheduling RBAC, seed idempotency, health,
protected legacy data, and HMAC webhook ingress. Stage 4 adds booking ownership,
tenant isolation, lifecycle, cancellation, atomic rescheduling, audit/history,
idempotency, and business-rule coverage.

GitHub Actions is configured to start PostgreSQL, apply Alembic, check for model
drift, run the domain seed and regression suite, then run the six real
PostgreSQL concurrency tests separately. Those tests verify simultaneous claims
for one slot, partial overlaps, adjacent half-open intervals, cancellation range
release, same-key idempotency, and failed-reschedule rollback. They skip outside
PostgreSQL by design rather than simulating database guarantees with SQLite.

## License

SlotBridge is published solely for educational review and portfolio
demonstration. It is proprietary software, not open-source software. See
[`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). These files and copyright/author
information must not be removed or replaced.
