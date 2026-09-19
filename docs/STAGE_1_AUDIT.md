# SlotBridge — Stage 1 repository audit

Audit date: 10 September 2026
Audit baseline: `main` at commit `cd5acbd`
Deadline used for planning: 28 September 2026
Scope: repository inspection, runtime checks, architecture plan, and documentation only

## Executive conclusion

The current SlotBridge is a small, coherent demonstration of an appointment
**integration control plane**. It accepts three example webhook shapes,
normalizes them into a canonical SQLite table, detects overlaps after ingestion,
and creates sync-plan records. It is not yet the mobile appointment platform
described in the target product brief.

The integration prototype should not be discarded. Its provider normalization
ideas, demo payloads, idempotency concept, feasibility matrix, and basic tests
are useful inputs to the future integrations module. The SQLite persistence,
global application structure, conflict algorithm, and public unprotected API
are not safe foundations for production booking.

The first implementation priority is a PostgreSQL-backed modular monolith with
explicit organization, staff, service, schedule, and appointment boundaries.
Availability is a calculation; booking is a database transaction. Redis may
support caching, fan-out, and jobs, but it must not be the source of truth for
whether a time interval is bookable.

## 1. CURRENT STATE

### Repository and runtime shape

The repository contains one Python application, one test module, a demo seeder,
three provider payload examples, Docker files, and CI. There is no `mobile/`
directory and no Flutter project.

```text
SlotBridge/
├── app/
│   ├── core.py              # SQLite schema, adapters, service logic
│   └── main.py              # FastAPI app, routes, HTML dashboard
├── data/.gitkeep
├── examples/                # Google, Mindbody, Vagaro demo payloads
├── scripts/seed_demo.py
├── tests/test_slotbridge.py
├── .github/workflows/tests.yml
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

The code is a compact monolith. `app.main` constructs global `DB` and `Service`
instances at import time. `app.core` combines database initialization, queries,
provider adapters, overlap detection, and orchestration in one module. There is
no ORM, repository abstraction, migration tool, dependency-injection boundary,
or separately modeled domain layer.

### Technologies actually used

- Python 3.12 in Docker and CI.
- FastAPI and Uvicorn for HTTP.
- Python `sqlite3`, using WAL mode.
- Dataclasses for the normalized provider event.
- `python-dotenv` and direct environment reads for configuration.
- Pytest for three unit-level tests.
- A server-rendered HTML operations dashboard assembled as escaped strings.
- Docker, Docker Compose, and GitHub Actions.

The following preferred target technologies are **not** currently present:
PostgreSQL, SQLAlchemy, Alembic, Redis, a job worker, WebSocket, JWT-based
authentication, and Flutter.

### Existing data model

Schema creation is embedded in `DB.init()` and runs at application startup.
There are five SQLite tables:

| Table | Purpose | Existing integrity |
|---|---|---|
| `webhooks` | Received provider payloads | unique `(provider, event_key)` |
| `appointments` | Canonical provider appointments/blocks | unique `(provider, external_id)` |
| `conflicts` | Recomputed overlap pairs | unique `(a_id, b_id)` |
| `sync_jobs` | Planned outbound operations | primary key only |
| `dead_letters` | Unsupported outbound plans | primary key only |

There are no declared foreign keys between these tables, no domain check
constraints, no migration history, and no organization, branch, user, employee,
service, schedule, waitlist, notification, or audit entities.

## 2. WHAT ALREADY WORKS

The following behavior exists and was verified from code and local execution:

- `GET /` renders the demo dashboard and escapes dynamic HTML values.
- Health, appointment, conflict, feasibility, sync-job, and dead-letter reads
  return responses.
- Appointment and conflict CSV exports return downloadable responses.
- `POST /webhooks/{provider}` recognizes `mindbody`, `vagaro`, and `google`.
- The three adapters normalize the example payload shapes into one `Event`.
- Duplicate delivery of the same `(provider, event_key)` is suppressed by a
  database unique constraint.
- Canonical rows are inserted or updated by `(provider, external_id)`.
- The reconciliation function finds half-open interval overlaps (`start < end`)
  after ingestion and records them as conflicts.
- Ingestion from Mindbody or Vagaro creates a Google sync-plan row.
- Planning to a connector without write capability creates an `unsupported`
  job and a dead-letter row.
- The demo seeder is deterministic when pointed to a disposable database.
- The supplied three tests pass.
- The Compose model is syntactically valid and the data directory is persisted
  through a named volume.
- CI installs dependencies and runs Pytest on pushes to `main`, pull requests,
  and manual dispatches.

Important boundaries:

- No connector makes a live vendor API call.
- A `pending` sync job is never executed.
- There is no retry scheduler despite retry/dead-letter wording in the README.
- `origin_token` is stored but not used for loop prevention.
- Conflict detection reports overlaps; it does not reserve a slot or prevent a
  conflicting write.
- There is no client booking API, availability engine, authentication, role
  model, notification, waitlist, realtime channel, or mobile client.

## 3. REUSABLE COMPONENTS

| Component | Decision | Reason and required treatment |
|---|---|---|
| Provider example payloads | **KEEP** | Valuable deterministic fixtures for adapter contract tests. |
| Mindbody/Vagaro/Google normalization rules | **REFACTOR** | Preserve observed mappings, move behind typed adapter interfaces, add strict schemas, source timestamps, signature metadata, and contract tests. |
| Database-backed webhook idempotency concept | **REFACTOR** | Keep the unique provider/event identity, but process inbox state and domain changes transactionally with retryable statuses. |
| Capability matrix/feasibility concept | **KEEP** | Useful for honest integration readiness; expose it only to administrators and derive it from validated configuration. |
| `Event` canonical vocabulary | **REFACTOR** | Split external integration events from first-class SlotBridge appointments and calendar blocks. Add typed IDs and UTC datetimes. |
| FastAPI entry point | **REFACTOR** | Keep FastAPI, introduce versioned routers, dependencies, settings, error contracts, and lifecycle-managed resources. |
| SQLite `DB` class and embedded DDL | **REPLACE** | PostgreSQL, SQLAlchemy, and Alembic are needed for constraints, concurrent transactions, migrations, and scale. SQLite may remain only as a legacy demo reference, not production storage. |
| `detect_conflicts()` | **REPLACE** | It compares every appointment with every other appointment, has no employee/resource scope, and only reacts after conflicts exist. Keep its interval-overlap test as a small unit-test idea. |
| `Service` orchestration | **REFACTOR** | Split booking, availability, integration inbox, sync planning, and reconciliation into explicit use cases. |
| Dashboard | **REFACTOR** | Useful as a demo/operations view; later protect it and consume supported APIs rather than globals. It is not the mobile client. |
| CSV export | **REFACTOR** | Keep export value, add authorization, pagination/streaming, selected columns, and spreadsheet-formula neutralization. |
| Demo seeder | **REFACTOR** | Preserve deterministic setup but make it idempotent, non-destructive by default, and populate the real booking domain. |
| Supplied tests | **KEEP** | Retain as regression tests while adding API, database, concurrency, security, and integration coverage. |
| Docker/Compose and CI | **REFACTOR** | Extend with PostgreSQL, Redis, health checks, non-root runtime, reproducible dependencies, migration checks, and broader tests. |
| README | **REFACTOR** | Keep the concise quick start but clearly label implemented, simulated, and planned capabilities. |

No current component needs immediate removal. Legacy-only code can be removed in
a later stage after its replacement has equivalent tests and migration paths.

## 4. PROBLEMS BY SEVERITY

Severity reflects the intended production-style booking product, not only the
small demo's stated scope.

### CRITICAL

1. **The booking invariant does not exist.** There is no availability endpoint,
   booking command, employee schedule, service duration, or database exclusion
   rule. Overlaps are accepted and reported afterward. Two callers therefore
   cannot be prevented from booking the same employee interval.
2. **All data and commands are unauthenticated.** Appointment rows include client
   names and raw provider payloads, and the list/export/dead-letter endpoints are
   public. Reconciliation and sync planning are public mutation endpoints. A
   deployed instance would expose personal and operational data and allow
   unauthorized changes.
3. **Webhook authenticity is not verified.** The code never validates a signature,
   shared token, timestamp, source IP policy, or replay window. The Vagaro token
   only changes a capability flag. Anyone who can reach the route can inject,
   cancel, or overwrite canonical appointments.
4. **A webhook can be permanently lost after a partial failure.**
   `record_webhook()` commits the idempotency row before `upsert()`, reconciliation,
   and sync planning. If any later step fails, the provider retry is returned as
   deduplicated and the event is never completed. Inbox receipt, processing
   status, domain write, and outbox creation need an explicit transactional design.

### HIGH

1. **The upsert is a select-then-write race.** Concurrent distinct events for the
   same external appointment can both observe no row and one can fail on the
   unique constraint. Reconciliation then deletes and rebuilds the entire
   conflict table in another transaction, making concurrent results unstable.
2. **Conflict identity is wrong.** Every active row is compared with every other
   row. Employee, branch, room/resource, provider mapping, organization, and time
   zone are ignored. Unrelated staff appointments are false conflicts; real
   duplicates cannot be reliably correlated.
3. **Datetime validation is unsafe.** Invalid datetimes quietly become `None` and
   are stored. Naive and timezone-aware values can reach Python comparisons and
   raise `TypeError`. End-before-start and zero-length intervals are not rejected.
4. **Out-of-order delivery can resurrect stale state.** No provider event time,
   version, sequence, or tombstone rule is stored. An older update arriving after
   a cancellation wins simply because it is processed later.
5. **Outbound synchronization is a stub.** Jobs are inserted but there is no
   executor, leasing, retry policy, backoff, terminal state transition, or live
   connector call. `origin_token` does not prevent provider feedback loops.
6. **Relational integrity is absent.** Conflict, job, and dead-letter IDs are not
   foreign keys; SQLite foreign-key enforcement is not enabled; statuses and
   intervals have no checks; deletion/orphan behavior is undefined.
7. **There is no migration path.** Startup DDL can create missing tables but cannot
   safely evolve existing installations or roll deployments forward/back.
8. **SQLite is the only runtime store.** WAL improves a local demo but does not
   provide the required PostgreSQL concurrency semantics, multi-instance access,
   or database-level interval exclusion.

### MEDIUM

1. Global database/service construction at import time causes filesystem side
   effects, complicates test isolation, and prevents clean application lifecycle
   management.
2. The async webhook handler performs synchronous SQLite work on the event loop.
3. List and CSV endpoints are unbounded. They expose internal/raw columns and can
   consume increasing memory as tables grow.
4. CSV cells are not neutralized against spreadsheet formula injection for
   values beginning with `=`, `+`, `-`, or `@`.
5. Configuration is not represented by a validated settings object. The demo-mode
   variable is ignored and the dashboard always labels itself demo mode.
6. Errors, logs, correlation IDs, metrics, traces, readiness checks, and job
   observability are absent. The health route does not test the database.
7. The Docker image runs as root, has no container health check, and mixes runtime
   and test dependencies.
8. Dependency ranges are broad and no lock/constraints file records a reproducible
   resolved set. A fresh install already emits a TestClient deprecation warning
   from the selected dependency combination.
9. Test coverage is three narrow tests. There are no route, invalid-input,
   persistence, transaction, authorization, webhook security, timezone,
   concurrency, or Docker runtime tests.
10. Raw third-party payloads and client names are stored without retention,
    redaction, encryption policy, or access boundaries.

### LOW

1. The README calls out retry/dead-letter behavior more strongly than the code
   supports; only planning and one unsupported-path dead letter exist.
2. Routes are unversioned and response/error envelopes are not standardized.
3. Business logic, adapters, persistence, and utility code are tightly packed in
   one module, with many one-line statements that make reviews harder.
4. Dashboard health and demo labels are hard-coded rather than based on runtime
   state.
5. The `DB.list(table)` helper interpolates a table name. Current call sites pass
   constants, so it is not directly exploitable today, but the API is unsafe to
   extend with user-controlled values.

## 5. TARGET ARCHITECTURE

Use a modular monolith: one deployable backend and worker, clear module
boundaries, one PostgreSQL database, Redis for ephemeral coordination, and one
Flutter client. This preserves delivery speed and transactional consistency.

```text
backend/
├── app/
│   ├── main.py
│   ├── core/                 # settings, logging, security, errors, time
│   ├── db/                   # session, base, shared types
│   ├── modules/
│   │   ├── auth/
│   │   ├── organizations/
│   │   ├── catalog/          # services and employee-service eligibility
│   │   ├── workforce/        # employees, schedules, breaks, blocks
│   │   ├── availability/
│   │   ├── appointments/
│   │   ├── waitlist/
│   │   ├── notifications/
│   │   ├── realtime/
│   │   ├── integrations/     # refactored current adapters/inbox/outbox
│   │   └── audit/
│   └── api/v1/
├── alembic/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── concurrency/
│   └── contract/
└── pyproject.toml
mobile/
├── lib/
├── test/
└── integration_test/
docs/
├── architecture/
├── adr/
├── api/
├── demo/
└── security/
infrastructure/
├── docker/
└── compose/
tests/
└── e2e/                      # backend + mobile/system scenarios
```

Inside each backend module, keep API schemas, use cases, domain rules, repository
ports, and SQLAlchemy implementations distinct enough to test, without creating
ceremonial layers for simple CRUD. Cross-module side effects should be emitted
through a transactional outbox. A worker claims outbox/job rows and Redis fans
committed events to WebSocket instances.

## 6. DATABASE PLAN

### Future domain model

Use UUID primary keys for externally visible domain entities and UTC
`timestamptz` instants. Keep organization/branch local time-zone identifiers as
IANA names; never store local wall-clock appointment times as the source of truth.

| Entity | Core relations and constraints |
|---|---|
| `users` | normalized unique email/phone as applicable; password hash; active state; verified timestamps |
| `organizations` | owner/tenant identity; unique slug; default timezone; active state |
| `organization_memberships` | user + organization + scoped role; unique membership; needed so roles are tenant-scoped |
| `branches` | organization FK; IANA timezone; unique name/code within organization |
| `employees` | organization FK; optional user FK; active state; avoid assuming one branch forever |
| `employee_branches` | unique employee/branch assignment if staff may work at several branches |
| `services` | organization FK; positive duration and optional before/after buffers; active state |
| `employee_services` | unique employee/service; optional employee-specific duration/price; eligibility checks |
| `work_schedules` | employee/branch, weekday, local start/end, validity range; checks for valid windows |
| `schedule_breaks` | schedule FK, local interval; contained/validated against work window |
| `schedule_exceptions` | date-specific closed or overridden hours; required for holidays and one-off changes |
| `blocked_slots` | employee/branch, UTC interval, reason, creator, active/cancelled state |
| `appointments` | organization, branch, client, employee, service FKs; UTC interval; status; idempotency key; version; cancellation metadata |
| `appointment_status_history` | append-only appointment/status/actor/reason/timestamp records |
| `waitlist` | client, service, optional employee, branch, acceptable date/time window, state and expiry |
| `notifications` | recipient, appointment/waitlist link, channel, template, state, attempts and scheduling timestamps |
| `audit_logs` | tenant, actor, action, target, correlation ID, timestamp, safe before/after metadata |
| `integration_inbox` | provider event identity, payload reference/hash, received/processed/error status and attempts |
| `integration_outbox` | committed domain event, delivery state, attempts, next-attempt time |

Use foreign keys for every relationship, check constraints for positive durations
and `starts_at < ends_at`, enums or constrained values for statuses, and
`created_at`/`updated_at` on mutable tables. Audit/history tables are append-only.

Minimum indexes include all foreign keys, tenant + active-state lookups,
`(employee_id, starts_at)`, `(branch_id, starts_at)`, waitlist matching fields,
notification/job state + scheduled time, and unique provider/event and
provider/external-object identities. Indexes should be confirmed with real query
plans rather than added indiscriminately.

### Concurrency and integrity

PostgreSQL must be the final authority:

1. Add a partial GiST exclusion constraint using half-open `tstzrange` intervals
   so active appointments for the same employee cannot overlap. Cancelled and
   other non-occupying statuses are excluded from the predicate.
2. Coordinate appointments and `blocked_slots` with a PostgreSQL transaction-level
   advisory lock keyed by employee and service date, used by every command that
   changes occupied time. For intervals crossing dates, acquire keys in sorted
   order. An alternative later design is one shared reservation table with a
   single exclusion constraint for appointments and blocks.
3. Re-read schedules, breaks, blocks, and active appointments inside the booking
   transaction. Never trust availability that was calculated earlier by the UI.
4. Use a client-supplied idempotency key with a scoped unique constraint so a
   retried request returns the original result rather than creating a duplicate.
5. Translate exclusion/unique violations into deterministic `409 SLOT_UNAVAILABLE`
   or idempotent replay responses.

## 7. API PLAN

Introduce `/api/v1` and a consistent error body containing code, message,
correlation ID, and safe field details.

| Group | Planned responsibility | Mapping from current API |
|---|---|---|
| `/auth` | register/login/refresh/logout/me | new |
| `/organizations` | organization and branch discovery/administration | new |
| `/employees` | employee discovery and admin management | new |
| `/services` | catalog and employee eligibility | new |
| `/schedules` | staff schedules, breaks, exceptions, blocks | new |
| `/availability` | read calculated slots and nearest alternatives | replaces post-factum conflict-oriented UX |
| `/appointments` | create/list/detail/reschedule/cancel/status transitions | current list becomes an authorized subset |
| `/waitlist` | join, leave, list, claim/offer flow | new |
| `/notifications` | user preferences and delivery history | new |
| `/admin` | tenant-scoped management, audit, operational reports | feasibility and safe dashboard data move here |
| `/integrations/webhooks/{provider}` | authenticated provider ingress | refactors current `/webhooks/{provider}` |

`/api/reconcile` should not remain an anonymous public command. Reconciliation
becomes an authorized admin operation or worker task. `/api/sync-plan` becomes an
internal integration use case. CSV export is an authorized admin/report endpoint.

Use cursor pagination for growing collections, explicit response schemas,
idempotency headers for appointment commands, optimistic version checks for
edits, and stable machine-readable errors. Generate OpenAPI and make the mobile
client models from the contract where practical.

## 8. MOBILE PLAN

Do not build the Flutter client until the first booking contract is stable.
Use a feature-first structure:

```text
mobile/lib/
├── app/                      # bootstrap, router, theme
├── core/
│   ├── api/                  # HTTP client, auth interceptor, DTO errors
│   ├── auth/                 # session coordinator and token refresh
│   ├── realtime/             # WebSocket lifecycle and event versions
│   ├── storage/              # secure credentials, non-sensitive cache
│   └── widgets/
└── features/
    ├── auth/
    ├── discovery/
    ├── availability/
    ├── appointments/
    ├── employee_schedule/
    └── admin/
```

- Navigation: `go_router` with role-aware guards and deep-link-safe redirects.
- State: Riverpod with immutable states; avoid global mutable singletons.
- API: typed DTOs, one error taxonomy, cancellation/timeouts, correlation IDs,
  and controlled token refresh with only one refresh request in flight.
- Tokens: short-lived access token in memory, refresh/session secret in platform
  secure storage. Do not store credentials in ordinary preferences.
- Realtime: authenticated WebSocket with exponential reconnect, heartbeat,
  subscription restoration, and monotonic event versions. Re-fetch availability
  after gaps instead of assuming every event was received.
- Network state: distinguish initial loading, refreshing, offline cache, empty,
  validation error, conflict, and server failure. Browsing may use stale cache;
  booking must always receive server confirmation.
- Roles: keep role-specific navigation/features but reuse domain/API components.

## 9. AUTOMATION / BOOKING ENGINE PLAN

### Availability calculation

For a requested branch, service, employee, and local date:

1. Validate organization scope, branch, active service, active employee, and
   employee-service eligibility.
2. Resolve the branch/employee IANA timezone and load recurring work windows plus
   date-specific schedule exceptions.
3. Convert valid local work windows to UTC instants with explicit daylight-saving
   handling.
4. Determine total occupied duration: service duration plus configured buffers.
5. Subtract schedule breaks.
6. Subtract active blocked intervals.
7. Subtract active appointments that occupy time.
8. Walk remaining windows using the configured slot granularity, retaining starts
   for which the complete occupied duration fits.
9. Apply booking horizon, minimum notice, employee/service rules, and current time.
10. Return slots in the requested display timezone with UTC instants and a
    schedule/availability version. If none fit, search outward within a bounded
    range and return nearest alternatives.

The interval convention must be half-open `[start, end)`, so an appointment
ending at 15:00 does not conflict with one beginning at 15:00.

### Atomic booking command

```text
request + idempotency key
  -> authenticate and authorize tenant/client
  -> begin PostgreSQL transaction
  -> acquire employee/date advisory transaction lock
  -> return prior result if idempotency key already completed
  -> re-read current schedule, breaks, blocks, and appointments
  -> recompute and validate the requested interval
  -> insert appointment (protected by exclusion constraint)
  -> append status history + audit log + outbox event
  -> commit
  -> worker publishes realtime/notification/waitlist effects
```

If two requests compete for 15:00, they serialize on the same employee/date key.
The first commits; the second re-checks current state and receives `409`. The
GiST constraint is the independent last line of defense if application locking
is missed. Redis locks are not used for this invariant.

Cancellation and rescheduling use the same transaction discipline. Rescheduling
should update or replace the reservation only after validating the new interval;
it must not release the old slot in a separate earlier transaction. Every commit
adds an outbox event. A worker then updates WebSocket subscribers, schedules
notifications, and evaluates matching waitlist entries with leasing/idempotency.

## 10. SECURITY PLAN

- Hash passwords with Argon2id using a maintained library; never store reversible
  passwords.
- Use short-lived signed access tokens and rotating refresh sessions stored
  server-side as hashes, with logout/revocation and device/session metadata.
- Enforce tenant-scoped RBAC at the use-case/query boundary: `CLIENT`, `EMPLOYEE`,
  and `ADMIN` do not imply cross-organization access.
- Check object ownership for every appointment, schedule, export, and realtime
  subscription; do not rely on the mobile UI hiding controls.
- Verify provider-specific webhook signatures/tokens, timestamps, replay windows,
  content type, and body-size limits before accepting inbox rows.
- Apply rate limits to login, registration, public availability, booking, and
  webhook routes, with stricter abuse controls for authentication.
- Validate every request and provider payload with strict schemas and bounded
  strings/lists. Reject invalid intervals and unsupported timezone data.
- Restrict CORS, require TLS outside local development, isolate database/Redis
  from public networks, use a non-root container user, and manage secrets outside
  source control.
- Minimize stored provider payloads, redact logs, define retention, encrypt
  backups, and document restore and credential-rotation procedures.
- Record immutable audit events for authentication, bookings, cancellations,
  reschedules, schedule edits, role changes, and admin actions.
- Neutralize spreadsheet formulas and authorize every export.
- Add dependency, secret, and container scanning in CI once dependencies are
  locked and findings have an owner.

## 11. TESTING PLAN

### Unit tests

- Schedule-window composition and interval subtraction.
- Duration, buffer, granularity, notice, and horizon rules.
- Half-open boundary behavior and nearest-alternative ranking.
- DST gaps/ambiguities, timezone conversion, overnight windows, and invalid data.
- Appointment state machine and authorization policies.
- Provider normalization, event ordering, loop prevention, and retry decisions.

### API integration tests

- Authentication/session lifecycle and stable error contracts.
- Role/tenant matrix for every protected route.
- Availability-to-book, cancel, reschedule, and status transitions.
- Idempotent command replay and stale version handling.
- Pagination, validation limits, and safe exports.
- Signed/unsigned, replayed, malformed, and oversized webhooks.

### Database and concurrency tests

Run against real PostgreSQL, not SQLite substitutes:

- Alembic upgrade from empty and from the previous release; schema downgrade only
  where the project explicitly supports it.
- Foreign-key, check, unique, and exclusion constraints.
- Transaction rollback and inbox/outbox atomicity under injected failures.
- Two parallel transactions request the same employee interval: exactly one
  appointment commits and the other returns `409`.
- Overlapping intervals, exact boundaries, different employees, cancellation,
  reschedule races, block-vs-book races, and idempotent retries.
- Worker leasing so multiple workers do not deliver one notification twice.

### Realtime and system tests

- Authorized subscription and cross-tenant denial.
- Commit triggers one versioned availability event; rollback triggers none.
- Disconnect/reconnect, event gap, and refetch recovery.
- Full two-client demo scenario across API, WebSocket, employee view, cancellation,
  and waitlist notification.
- Docker smoke test with PostgreSQL/Redis health and migrations.

CI should separate fast unit tests from PostgreSQL integration/concurrency tests,
then run both on pull requests. Flaky timing-based assertions are unacceptable;
use barriers and database-visible transaction coordination.

## 12. DEMO PLAN

Provide an explicit, idempotent demo command guarded against production. Seed:

- one organization and one branch with a named IANA timezone;
- three services with different durations;
- three employees and employee-service eligibility;
- recurring work schedules, one break, one exception, and one blocked interval;
- admin, employee, Client A, and Client B demo accounts;
- several past and future appointments;
- one waitlist request and clean notification history.

The primary scripted scenario is:

1. Client A and Client B open the same employee/date and both see 15:00.
2. Client A books 15:00; the server returns a confirmed appointment.
3. Client B receives a versioned realtime event and 15:00 disappears.
4. A forced simultaneous-booking action demonstrates that exactly one database
   transaction can win.
5. The employee view receives the appointment and changes its valid status.
6. Client A cancels; cancellation history and audit records are visible.
7. 15:00 returns to availability and a matching waitlist entry receives an offer
   or notification.

Prepare a reset command, a short presenter checklist, screenshots/video fallback,
and a degraded mode for the presentation if external push services are offline.
The booking database must remain real; only delivery adapters may be simulated.

## 13. ROADMAP TO 28 SEPTEMBER

Each stage ends with a runnable main branch and passing checks.

| Dates | Stage and verifiable exit condition |
|---|---|
| 10 Sep | **Stage 1 — audit.** Repository understood; risks, target architecture, license, and next scope documented. |
| 11–12 Sep | **Stage 2 — backend foundation.** Modular backend skeleton, PostgreSQL/SQLAlchemy/Alembic, validated settings, Compose services, base tenant/catalog models, migration and health tests. Existing demo remains runnable. |
| 13–15 Sep | **Stage 3 — schedules and availability.** Employee/service/schedule/break/exception/block models and deterministic availability API with unit/integration tests. |
| 16–18 Sep | **Stage 4 — atomic appointments.** Authenticated create/list/cancel/reschedule, state history, idempotency, PostgreSQL overlap protection, and required two-request concurrency test. |
| 19–21 Sep | **Stage 5 — focused Flutter client.** Login plus Client A/B discovery, availability, create/list/cancel flows; employee read view. Handle loading/offline/conflict states. |
| 22–23 Sep | **Stage 6 — realtime and outbox.** Transactional outbox, worker, Redis fan-out, authenticated WebSocket, mobile refresh, and realtime tests. |
| 24 Sep | **Stage 7 — waitlist and notifications.** Minimal match-on-release flow and reliable in-app/demo notification; external push is optional behind an adapter. |
| 25 Sep | **Stage 8 — demo data and observability.** Idempotent seed/reset, scripted demo, audit trail, logs/correlation IDs, readiness checks. Feature freeze at end of day. |
| 26–28 Sep | **Stabilization only.** Full regression, security pass, device/network edge cases, backup demo recording, documentation, packaging, and bug fixes. No major features. |

If schedule pressure appears, defer external calendar writes, push delivery,
analytics, multi-branch employee assignment, and sophisticated waitlist offers.
Do not defer database concurrency protection, authentication/authorization,
timezone correctness, or the core demo path.

## 14. FILES CHANGED

Only Stage 1 documentation/legal files were changed:

- `LICENSE` — adds the requested proprietary, all-rights-reserved terms.
- `NOTICE` — records author/copyright ownership, permitted publication purpose,
  prohibited uses, and preservation requirements.
- `README.md` — adds a visible copyright/license section pointing to those files.
- `docs/STAGE_1_AUDIT.md` — this audit and implementation plan.

No application code, tests, schemas, runtime configuration, or existing behavior
was changed.

## 15. TESTS / CHECKS EXECUTED

Environment: Windows host, Python 3.12.10, dependencies installed into an ignored
local virtual environment.

| Check | Result |
|---|---|
| Repository status before edits | clean, tracking `origin/main` |
| `python -m pytest -q` in isolated environment | **3 passed** |
| `python -m pip check` | **no broken requirements** |
| Python byte-compilation of `app`, `scripts`, `tests` | **passed** |
| Demo seed against disposable DB | **passed**: 3 appointments, 2 conflicts, 3 jobs, 1 dead letter; duplicate recognized |
| FastAPI TestClient smoke for dashboard and nine documented GET routes | **all HTTP 200** |
| Unknown webhook provider and sync target smoke | **HTTP 404** |
| `docker compose config --quiet` | **passed** |
| `docker compose build` | **not completed**: Docker Desktop Linux engine was not running on the audit host |

The selected fresh dependency versions emitted a Starlette/FastAPI TestClient
deprecation warning. It did not fail the smoke test but supports locking and
reviewing a compatible dependency set.

Not executed in Stage 1: live provider calls (no credentials/contracts), load
testing, mobile tests (no mobile app), PostgreSQL concurrency tests (no PostgreSQL
implementation), security penetration testing, or production deployment.
The Dockerfile was inspected and Compose configuration was parsed, but image
runtime behavior remains unverified until the Docker engine is available.

## 16. RISKS

1. **Deadline risk:** eighteen days is enough for a strong, narrow vertical slice,
   not every future feature. Feature freeze on 25 September is mandatory.
2. **Scope risk:** the existing repository solves integration visibility, while
   the requested product is first-party booking. Preserve the prototype, but do
   not mistake it for the booking core.
3. **Vendor risk:** Mindbody, Vagaro, and Google capabilities, credentials,
   webhook contracts, quotas, and approval timelines are unverified. The demo
   must not depend on external approval.
4. **Concurrency risk:** a solution demonstrated only on SQLite or protected only
   by UI/Redis locks will not meet the core invariant.
5. **Timezone risk:** DST and branch timezone rules can corrupt availability if
   local and UTC representations are mixed.
6. **Security/privacy risk:** the current API exposes PII and accepts unsigned
   writes. It must remain local/demo-only until protected.
7. **Migration risk:** replacing embedded SQLite DDL requires a deliberate cutover.
   With only demo data today, prefer a clean initial PostgreSQL migration and a
   separate one-time importer only if preserving existing local data is required.
8. **Mobile risk:** starting broad three-role Flutter screens before the booking
   contract stabilizes will create rework. Build the thin client vertical slice
   first.
9. **Legal text risk:** the proprietary files express the requested intent, but
   jurisdiction-specific enforcement and public-hosting implications may require
   review by a qualified professional chosen by the owner.

## 17. EXACT SCOPE OF STAGE 2

Stage 2 should contain **foundation only**, not availability or booking behavior.

### In scope

1. Create the `backend/` modular skeleton while preserving a documented way to
   run the current integration demo during transition.
2. Add validated environment profiles for development, test, and demo; fail fast
   on unsafe or missing production values.
3. Add PostgreSQL and Redis to development Compose with health checks. Redis is
   wired for future use but has no booking-lock responsibility.
4. Add SQLAlchemy session/transaction infrastructure and Alembic.
5. Create the first migration for `users`, `organizations`,
   `organization_memberships`, `branches`, `employees`, `services`, and
   `employee_services`, including foreign keys, checks, unique constraints,
   indexes, and timestamps.
6. Add `/api/v1/health/live` and `/api/v1/health/ready`; readiness verifies the
   database. Do not expose secrets in either response.
7. Add deterministic test factories and integration tests that start from an
   Alembic-created PostgreSQL schema and verify tenant/catalog constraints.
8. Add lint/type/test/migration checks to CI and record the resolved dependency
   set reproducibly.
9. Add an architecture decision record explaining modular monolith, PostgreSQL,
   transaction boundaries, Redis scope, and preservation of the legacy adapter
   prototype.

### Explicitly out of scope

- Availability calculation.
- Appointment creation, cancellation, or rescheduling.
- JWT/login endpoints beyond any interfaces strictly needed to shape the schema.
- WebSocket, workers, waitlist, and notifications.
- Flutter scaffolding.
- Live Mindbody, Vagaro, or Google API calls.
- Destructive removal of the current demo.

### Stage 2 acceptance criteria

- A fresh checkout starts PostgreSQL/Redis/backend through documented commands.
- Alembic upgrades an empty database successfully.
- The new liveness/readiness endpoints have automated tests.
- Tenant and catalog constraints are verified against PostgreSQL.
- Existing Stage 1 tests continue to pass or are moved with behavior preserved.
- The working tree contains no secrets or generated database files.

Stop after these criteria. Stage 3 begins only with a separate request.
