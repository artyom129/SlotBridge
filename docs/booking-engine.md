# SlotBridge booking engine

This document describes the first-party transactional booking engine introduced
in Stage 4. It is intentionally limited to appointments and their lifecycle. It
does not implement waitlists, realtime delivery, notifications, payments, AI,
or a mobile client.

## Core record

`Appointment` is the source of truth for a booking. It stores the organization,
branch, client, employee, service, UTC start/end instants, status, a
client-scoped idempotency key, optional client note, and cancellation metadata.

The create request accepts only:

- `branch_id`
- `employee_id`
- `service_id`
- timezone-aware `starts_at`
- optional `client_note`

The authenticated client, organization, and end instant are server-owned. The
end instant is calculated from the effective employee-service duration (falling
back to the service duration), so a client cannot shorten a booking to evade
conflict checks.

Tenant-consistency foreign keys ensure that the branch, employee, service,
client membership, and appointment all belong to the same organization.

## Status lifecycle

The service accepts only these transitions:

| Current | Allowed next status |
|---|---|
| `BOOKED` | `CONFIRMED`, `CANCELLED` |
| `CONFIRMED` | `IN_PROGRESS`, `CANCELLED`, `NO_SHOW` |
| `IN_PROGRESS` | `COMPLETED` |
| `COMPLETED` | none |
| `CANCELLED` | none |
| `NO_SHOW` | none |

Cancellation has a dedicated command because it also records the reason and
timestamp. The generic status command does not accept `CANCELLED`.

Only `BOOKED`, `CONFIRMED`, and `IN_PROGRESS` occupy employee time.
`COMPLETED`, `CANCELLED`, and `NO_SHOW` are terminal and do not block future
availability queries.

## Database concurrency guarantee

PostgreSQL is the authority for overlap prevention. Migration
`20260911_0003_transactional_booking` enables `btree_gist` and creates a partial
GiST exclusion constraint equivalent to:

```sql
EXCLUDE USING gist (
  employee_id WITH =,
  tstzrange(starts_at, ends_at, '[)') WITH &&
)
WHERE (status IN ('BOOKED', 'CONFIRMED', 'IN_PROGRESS'))
```

The half-open `[start, end)` convention means `10:00-11:00` and
`11:00-12:00` are adjacent rather than overlapping. A preliminary application
check gives an early, readable response, but correctness does not depend on
that check. If concurrent transactions race, the database permits only one
active overlapping range and the service maps SQLSTATE `23P01` to the stable
`SLOT_ALREADY_BOOKED` conflict.

## Create transaction

`BookingService.create` performs one transaction:

1. validate the authenticated `CLIENT` and required idempotency key;
2. serialize the client/key pair with a PostgreSQL transaction advisory lock;
3. replay an existing identical request or reject changed details for that key;
4. resolve and validate active tenant resources and client membership;
5. call the shared availability engine and verify the exact requested slot;
6. calculate the server-owned end instant;
7. insert the appointment, initial status-history row, and `CREATED` audit row;
8. flush so database constraint errors are translated before commit.

The unique `(client_user_id, idempotency_key)` constraint persists replay
semantics across processes and restarts. An immutable SHA-256 fingerprint of the
canonical original create command distinguishes a valid replay from key reuse,
even after the appointment itself has been rescheduled. The advisory lock closes
the check-before-insert race for identical keys on PostgreSQL.

## Availability integration

`AvailabilityService` continues to calculate work windows from the branch or
organization timezone, recurring schedules, replacement/day-off exceptions,
breaks, blocks, and service duration. Stage 4 adds one set-based appointment
query and subtracts all overlapping active appointment intervals before slots
are generated.

Rescheduling passes the current appointment ID as an exclusion, allowing it to
test its proposed new range without treating its old range as an external
conflict. PostgreSQL still performs the final overlap check at write time.

## Cancellation and rescheduling

Cancellation locks the appointment row, validates authorization and lifecycle,
changes the status to `CANCELLED`, stores the reason/timestamp, and appends both
history and audit records in one transaction. CLIENT is limited to an own future
appointment; the assigned EMPLOYEE and tenant ADMIN may cancel their permitted
active records. Once committed, the partial exclusion constraint and
availability engine stop treating the range as busy.

Rescheduling also locks the row. It validates authorization and active status;
CLIENT is limited to an own future appointment, and every target must be in the
future. It resolves the new slot through the shared availability engine and
updates start/end plus a `RESCHEDULED` audit event atomically. If the new range
conflicts at the database boundary, the transaction rolls back; the old range
remains unchanged and occupied.

## Authorization and tenant isolation

- `CLIENT` can create and list only their own appointments, read only their own
  detail, and cancel/reschedule only an eligible own appointment.
- `EMPLOYEE` can read, cancel/reschedule, or change status only when the
  appointment is assigned to their active employee profile.
- `ADMIN` can read, cancel/reschedule, or change status only with membership in
  the appointment's organization.
- Cross-tenant or non-owner detail access is returned as not found, preventing
  appointment-ID enumeration from disclosing existence.

Public registration does not infer an organization. A client must be provisioned
with `OrganizationMembership` before booking there. The demo seed does this for
its fictional accounts.

## History and audit

`AppointmentStatusHistory` is append-only in the application and records every
accepted status transition, including the initial state, actor, reason, and
timestamp. No update/delete route is exposed.

`AppointmentAuditLog` minimally records `CREATED`, `CANCELLED`, `RESCHEDULED`,
and `STATUS_CHANGED`. Reschedule entries include the old and new instants.

## HTTP surface

| Method | Path | Access | Purpose |
|---|---|---|---|
| `POST` | `/appointments` | CLIENT | Create or idempotently replay |
| `GET` | `/appointments/me` | CLIENT | Filter own bookings |
| `GET` | `/appointments/{id}` | owner/assigned employee/org admin | Detail, history, audit |
| `POST` | `/appointments/{id}/cancel` | owner/assigned employee/org admin | Cancel an active booking; CLIENT is future-only |
| `POST` | `/appointments/{id}/reschedule` | owner/assigned employee/org admin | Atomically move an active booking to a future slot |
| `POST` | `/appointments/{id}/status` | assigned EMPLOYEE/org ADMIN | Apply an allowed status transition |

Errors use a stable JSON detail object containing `code` and `message`.

## Verification

Business and security tests run on the standard isolated test database. A
separate six-test module is explicitly PostgreSQL-only and checks the actual
exclusion constraint and transaction behavior:

1. ten simultaneous clients claiming one interval produce one success and nine
   conflicts;
2. partial overlaps conflict;
3. adjacent half-open intervals both succeed;
4. cancellation releases the database range;
5. simultaneous requests with one idempotency key return one appointment;
6. a conflicting reschedule rolls back and preserves the old interval.

CI provisions PostgreSQL 17, upgrades Alembic, seeds the domain, runs the
regression/booking suite, and then runs this concurrency module separately.
