# SlotBridge deployment verification — 2026-09-15

## Hosting and architecture

- Backend: Render Free Docker Web Service, `slotbridge-api`, Frankfurt.
- API: <https://slotbridge-api.onrender.com>.
- Database: Supabase Free PostgreSQL, project `slotbridge`, `eu-central-1`.
- Both resources use free plans. No paid resource or payment method was added.
- Supabase is PostgreSQL only; SlotBridge still uses FastAPI, SQLAlchemy,
  psycopg, Alembic, its own JWT authentication, RBAC and booking engine.
- The database uses the IPv4-compatible Session pooler on port `5432`, with
  `sslmode=require`. Transaction pooler port `6543` is not used.
- Current migration: `20260915_0004 (head)`. The `btree_gist` extension and
  `ex_appointments_employee_time_active` exclusion constraint remain present.
- Deployment migration `0004` removes table access for Supabase Data API roles.
  Verified exposed table count: **0**. FastAPI's database owner retains access.
- Production startup waits for PostgreSQL, migrates and listens on Render's
  `PORT`; it never invokes the demo seed. The idempotent production demo seed
  was run explicitly once.
- `DATABASE_URL` and the random `JWT_SECRET` are Render environment secrets.
  Generated deployment credentials are also stored outside Git in Windows
  DPAPI-encrypted files under `%APPDATA%\SlotBridge`. No production secret was
  found in tracked source files; `.env` remains ignored.

## Verification results

- HTTPS liveness: **200**, `{"status":"ok","service":"slotbridge"}`.
- HTTPS readiness: **200**, `{"status":"ready","database":"ok"}`.
- SQLAlchemy driver: **psycopg**; client PostgreSQL TLS: **enabled**.
- Remote Flutter E2E: **PASS** — register, login, `/auth/me`, organization,
  location, service, employee, availability, booking, My Appointments, detail,
  reschedule, idempotent replay, cancel and released-slot availability.
- Remote concurrency, exactly two requests: **201 + 409**; the winning test
  appointment was cancelled. No load test was performed.
- Production RBAC: CLIENT admin request **403**; another client's appointment
  detail **404**; `/auth/me` without JWT **401**.
- Backend suite: **86 passed, 6 skipped** in isolated SQLite test storage.
  PostgreSQL concurrency is checked separately against the remote database.
  Existing RBAC, tenant isolation and HMAC/webhook tests remain passing.
- Flutter analyze: **no issues**.
- Flutter test: **18 passed**, including the real remote E2E.
- Local Windows: `start_slotbridge.bat` passed migrations and demo seed;
  local liveness/readiness **200**. `stop_slotbridge.bat` stopped only backend.
- Docker Compose configuration: **valid**. Docker Desktop is off, so container
  runtime startup was **not tested** in this verification run. Windows batch
  CRLF and shell-script LF are enforced; mobile artifacts are excluded from
  the backend Docker image.
- LICENSE, NOTICE, copyright, Russian UI and booking rules were not changed.

## Persistence after backend redeploy

Render redeployed from `d4d723d` to `b5bb015` successfully. Counts immediately
before and after redeploy were identical:

- users: **8**;
- organization memberships: **8**;
- appointments: **6**;
- organizations: **1**;
- branches: **1**;
- employees: **2**;
- services: **3**;
- work schedules: **10**.

Later verification runs add their own test clients and cancelled appointments.
The Supabase database was not recreated during redeploy.

## Android APK

- Build: **release**, non-debuggable. Production HTTPS URL is verified inside
  the APK; Internet permission is present and cleartext traffic is denied.
- Package: `com.slotbridge.slotbridge_mobile` (unchanged).
- versionName: **1.0.0**; versionCode: **3** (previous APK: **2**).
- Signature: **valid APK Signature Scheme v2**. Signer matches the previous APK:
  `54bf508b514330174fafa56159ab58663baebfbfee87b541c1af850281100923`.
  The existing Android Debug certificate is retained for update compatibility;
  this is not a Play Store signing setup.
- zipalign: **PASS**, including 16 KB native-library alignment.
- Size: **55,501,227 bytes**.
- SHA-256:
  `f52e6933726c6fe81332a538eb7f6757a771eb7690c25d87502ab34e4cd3f1f6`.
- Exact saved artifact path:

```text
C:\Users\User\Documents\Codex\2026-09-10\files-pasted-by-the-user-https\work\SlotBridge\artifacts\android\SlotBridge-1.0.0-3-production.apk
```

The APK is deliberately ignored by Git and excluded from the backend image.

## Laptop independence and free-tier caveats

Remote tests and health checks passed while the local backend was stopped and
Docker Desktop was off. The app's production backend does not run on the
laptop. No Android device is connected, so APK installation, mobile-data use
and physically switching the laptop off have **not been tested**.

Local accounts and appointments were not copied to production. Register a new
production account; the existing local database is preserved independently.

Free hosting is not an always-warm 24/7 guarantee: Render sleeps after 15
minutes of idle time and wakes on a request (about a minute). The production
Flutter response timeout is 90 seconds. Supabase Free can pause after a week
of inactivity. No paid always-warm feature or keep-alive workaround is used.
See [Render Free limits](https://render.com/docs/free) and
[Supabase Free limits](https://supabase.com/pricing).
