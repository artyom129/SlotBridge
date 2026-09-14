# SlotBridge Stage 4 — Transactional Booking Engine

## 1. SUMMARY

Stage 4 adds a first-party transactional appointment engine on top of the
completed Stage 1-3 foundation. It includes booking creation, client listing and
detail, cancellation, atomic rescheduling, controlled status transitions,
history, audit, persistent idempotency, availability integration, and a real
PostgreSQL overlap invariant. Stage 5 work was not started.

## 2. APPOINTMENT MODEL

`Appointment` stores tenant and resource identifiers, the authenticated client,
UTC start/end instants, status, idempotency key, optional note, cancellation
metadata, and timestamps. Composite foreign keys enforce organization
consistency for the branch, employee, service, and client membership. The
client cannot submit `organization_id`, `client_user_id`, or `ends_at`; the
server resolves them and derives the end instant from the effective duration.

## 3. STATUS LIFECYCLE

Statuses are `BOOKED`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`,
and `NO_SHOW`. Allowed transitions are:

- `BOOKED -> CONFIRMED | CANCELLED`
- `CONFIRMED -> IN_PROGRESS | CANCELLED | NO_SHOW`
- `IN_PROGRESS -> COMPLETED`
- `COMPLETED`, `CANCELLED`, and `NO_SHOW` are terminal

Cancellation is handled only by the dedicated cancellation command so its
reason and timestamp remain consistent.

## 4. DATABASE CONCURRENCY STRATEGY

Migration `20260911_0003` enables `btree_gist` and creates a partial GiST
exclusion constraint over employee equality and
`tstzrange(starts_at, ends_at, '[)')` overlap. The predicate includes only
`BOOKED`, `CONFIRMED`, and `IN_PROGRESS`. PostgreSQL is therefore the final
authority under races: adjacent appointments are accepted, while active partial
or full overlaps for one employee cannot both commit. Exclusion violations
(SQLSTATE `23P01`) become stable `SLOT_ALREADY_BOOKED` conflicts.

## 5. BOOKING SERVICE

`BookingService` owns booking business transactions rather than placing logic
in route handlers. It validates actor/resource/tenant state, reuses the Stage 3
availability calculator, computes the end instant, locks mutation targets,
writes history/audit records, flushes constraints, and translates expected
business/database failures into stable API errors.

## 6. AVAILABILITY INTEGRATION

The Stage 3 calculator now performs one set-based query for overlapping active
appointments and subtracts those intervals together with schedules, breaks,
exceptions, and blocks. It can exclude one appointment during rescheduling.
The query-count regression expectation increased by one and remains constant,
so the integration introduces no N+1 loading.

## 7. CANCELLATION

A client may cancel only their own future `BOOKED` or `CONFIRMED` appointment;
the assigned EMPLOYEE and tenant ADMIN may cancel their permitted active
records. The service row-locks the record, moves it to `CANCELLED`, stores reason
and timestamp, and appends status history plus a `CANCELLED` audit event in the
same transaction. A committed cancellation immediately releases the occupied
range.

## 8. RESCHEDULING

CLIENT may reschedule only their own future `BOOKED` or `CONFIRMED` appointment;
the assigned EMPLOYEE and tenant ADMIN may reschedule their permitted active
records. The target is always future. The row is locked, the new slot is
evaluated while excluding the current record, and start/end plus a `RESCHEDULED`
audit event are written atomically. A conflicting database write rolls back
completely, retaining the old interval.

## 9. IDEMPOTENCY

`POST /appointments` requires `Idempotency-Key`. A unique
`(client_user_id, idempotency_key)` constraint persists ownership of the key.
An immutable SHA-256 fingerprint records the canonical original create command,
so replay remains valid after a later reschedule. On PostgreSQL, a transaction
advisory lock serializes concurrent use of the same client/key before lookup. An
identical replay returns the same appointment; different booking details return
`IDEMPOTENCY_KEY_REUSED`.

## 10. RBAC / SECURITY

CLIENT can create/list/read/cancel/reschedule only their own bookings. EMPLOYEE
can read, cancel/reschedule, or change status only for an appointment assigned
to their active employee profile. ADMIN can read, cancel/reschedule, or change
status only with organization membership. Tenant consistency is checked in service queries and database
foreign keys. Unauthorized cross-owner/cross-tenant detail reads return not
found to reduce IDOR leakage. Role, client, organization, and end time are not
client-selectable booking fields.

## 11. AUDIT

Every appointment starts with one status-history row. Every accepted lifecycle
change appends another row. `AppointmentAuditLog` records `CREATED`,
`CANCELLED`, `RESCHEDULED`, and `STATUS_CHANGED`, including actor/reason and old
or new times where relevant. The application exposes no history/audit mutation
endpoint.

## 12. MIGRATION

`20260911_0003_transactional_booking.py` follows Stage 3 migration `0002`. It
creates `btree_gist`, PostgreSQL status/action enums, organization memberships,
appointments, status history, audit log, tenant constraints, indexes,
idempotency uniqueness, interval/state checks, and the partial exclusion
constraint. Offline Alembic SQL generation succeeds and `alembic heads` reports
only `20260911_0003 (head)`. Downgrade removes Stage 4 schema objects but leaves
the shared extension installed.

## 13. API ENDPOINTS

- `POST /appointments` — CLIENT create/idempotent replay
- `GET /appointments/me` — CLIENT own list with `view` and optional status
- `GET /appointments/{id}` — authorized detail with history and audit
- `POST /appointments/{id}/cancel` — owner/assigned EMPLOYEE/tenant ADMIN cancellation
- `POST /appointments/{id}/reschedule` — owner/assigned EMPLOYEE/tenant ADMIN atomic move
- `POST /appointments/{id}/status` — assigned EMPLOYEE or tenant ADMIN status

All handlers are thin adapters over `BookingService`. Expected failures use a
stable `{code, message}` detail body.

## 14. SEED

The development/demo seed remains environment-guarded and idempotent. It now
provisions organization membership for the five existing demo users and four
fictional appointments: upcoming `BOOKED`, upcoming `CONFIRMED`, historical
`COMPLETED`, and `CANCELLED`, each with initial history and a creation audit.
Dates use Tuesday to avoid the seed's fixed Monday exception/block examples.

## 15. TEST RESULTS

Final local result before packaging: `72 passed, 6 skipped`. The 72 executed
tests include all preserved Stage 1-3 behavior plus Stage 4 API, business,
security, audit, idempotency, cancellation, and reschedule coverage. The six
skips are intentionally PostgreSQL-only concurrency tests because the available
local runner used SQLite and no working local PostgreSQL/Docker engine was
available. Existing warnings are dependency deprecations, not test failures.

## 16. CONCURRENCY TEST RESULTS

Six real PostgreSQL concurrency tests were implemented, including the required
10 simultaneous claims for one interval with an expected `1 success / 9
conflicts`, partial-overlap rejection, adjacent interval acceptance,
cancellation range release, concurrent same-key idempotency, and conflicting
reschedule rollback.

**Actual PostgreSQL concurrency tests were not run successfully in this local
environment.** They were collected and skipped on SQLite as designed. CI is
configured with PostgreSQL 17 to run them separately after migration and seed,
but no CI run was initiated or observed during this task. No claim of a real
PostgreSQL concurrency pass is made.

## 17. FILES CREATED

- `alembic/versions/20260911_0003_transactional_booking.py` — Stage 4 schema and
  database invariants.
- `app/api/appointments.py` — appointment HTTP surface and response mapping.
- `app/services/booking.py` — transactional booking/lifecycle service.
- `docs/booking-engine.md` — booking design and operational semantics.
- `docs/STAGE_4.md` — this implementation/verification record.
- `tests/__init__.py` — makes shared Stage 4 test helpers importable.
- `tests/booking_support.py` — deterministic booking fixture/API helpers.
- `tests/test_booking_api.py` — create/list/detail/idempotency/cancel API tests.
- `tests/test_booking_business.py` — scheduling, lifecycle, cancellation, and
  reschedule business tests.
- `tests/test_booking_security.py` — owner, assigned employee, admin, tenant,
  and IDOR tests.
- `tests/test_booking_concurrency.py` — six PostgreSQL-only race tests.

## 18. FILES MODIFIED

- `app/models.py` — memberships, appointment/history/audit models and enums.
- `app/schemas.py` — strict appointment command and response schemas.
- `app/services/availability.py` — subtracts active appointments and supports
  reschedule exclusion.
- `app/main.py` — registers the Stage 4 router and updates API metadata.
- `scripts/seed_domain.py` — Stage 4 memberships and demo appointments.
- `tests/conftest.py` — cleans Stage 4 tables in PostgreSQL fixtures.
- `tests/test_availability.py` — accounts for one constant set-based booking
  query in the performance assertion.
- `tests/test_domain.py` — verifies Stage 4 seed counts and idempotency.
- `.github/workflows/tests.yml` — separates real PostgreSQL race tests from the
  regression/booking test step.
- `README.md` — documents Stage 4 behavior, APIs, limits, seed, and tests.

LICENSE and NOTICE were not modified. Existing Stage 1-3 implementation files
outside the list above were not intentionally changed for Stage 4.

## 19. KNOWN ISSUES

- Public registration creates a CLIENT account but intentionally does not infer
  or grant organization membership; onboarding/provisioning is still required.
- There is no membership-management API yet; the demo seed provisions the demo
  relationships directly.
- The PostgreSQL concurrency suite is implemented and CI-configured but could
  not be executed in the local environment used for this report.
- The appointment exclusion constraint prevents appointment-vs-appointment
  double booking. Concurrent administrator changes to schedules/blocks versus a
  booking are not serialized by a shared database invariant.
- Audit/history is append-only through the application surface, not protected by
  database triggers against privileged direct database updates/deletes.
- No waitlist, realtime/WebSocket, notifications, payments, AI, Flutter, or
  external-provider write synchronization was added.

## 20. EXACT RECOMMENDED SCOPE FOR STAGE 5

Stage 5 should be limited to booking operations hardening: add ADMIN membership
provisioning and client-to-organization onboarding; define organization booking
policies (minimum notice, booking horizon, cancellation/reschedule cutoff);
serialize booking against concurrent schedule/break/block mutations; add
database-enforced immutability for status history and audit logs; add an outbox
for future integrations without implementing delivery channels; and add
rate-limit/structured-observability hooks around booking commands. Preserve the
current API and PostgreSQL overlap contract. Waitlist, WebSocket/realtime,
notifications, payments, AI, Flutter, and provider write-back should remain out
of scope unless explicitly selected as a later stage.
