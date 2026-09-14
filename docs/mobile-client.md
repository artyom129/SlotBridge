# SlotBridge mobile client

## Platform strategy

Stage 5 is one Flutter application with one set of screens and business logic:

```text
mobile/lib (shared Flutter application)
├── Android host: mobile/android
└── iOS host:     mobile/ios
```

Android is the primary local development and demonstration platform. The iOS
host project is generated and configured, but there is no parallel Swift UI and
no duplicated booking logic. Flutter widgets use safe areas, scrollable page
bodies, keyboard-aware forms, a constrained responsive content width, and
Material navigation that adapts to different phone sizes.

## Architecture

The client is split into small platform-neutral layers:

- `core/` — configuration, navigation, theme, secure token storage, HTTP client,
  shared error handling, and reusable responsive widgets;
- `domain/` — typed user, catalog, availability, appointment, and history models;
- `data/` — authentication, catalog, and booking repositories;
- `features/` — Riverpod controllers and screens for authentication, home,
  booking, appointments, details, cancellation, rescheduling, and profile.

`go_router` owns navigation and redirects unauthenticated sessions to login.
`flutter_riverpod` owns async state. `dio` adds the bearer token and provides a
single error boundary. `flutter_secure_storage` persists the JWT using native
encrypted storage on both Android and iOS.

## Authentication and errors

On startup the app reads the access token from secure storage and validates it
with `GET /auth/me`. Login uses `POST /auth/login`. A successfully authenticated
non-client role is rejected because Stage 5 intentionally implements the CLIENT
application only. Logout removes the local token.

FastAPI error bodies, including nested `{code, message}` details, are mapped into
stable client exceptions. SQL, stack traces, tokens, and raw transport errors
are never shown in the UI.

## Booking flow

The wizard loads active organizations, branches, services, employees, and
employee-service assignments from the existing backend. It then:

1. selects a service;
2. filters employees that actually provide it;
3. selects a date in the branch calendar;
4. requests server-calculated availability;
5. submits the selected server slot with a UUID `Idempotency-Key`;
6. opens the new appointment details.

The same idempotency key is retained when a network failure makes a booking
result uncertain. This lets the backend return the original appointment instead
of creating a duplicate.

The backend remains authoritative for duration, end time, timezone rules,
availability, permissions, and overlap protection. The app never calculates a
bookable end time locally.

## Appointment management

My Appointments supports upcoming, past, cancelled, and all views. Details show
the service, employee, branch, status, client note, cancellation data, and the
append-only status history. A future active appointment can be cancelled with a
reason or atomically moved to another server-provided slot.

Backend timestamps are transported as aware instants. Appointment list/detail
times are rendered in the device locale, while branch-local availability labels
preserve the wall-clock value and display the backend-provided IANA timezone.
This avoids accidentally changing a selected branch time through the device's
own timezone.

## Platform configuration

Android declares Internet access, uses minimum SDK 24, and permits cleartext
traffic only in the debug manifest for emulator/LAN development. iOS keeps the
standard Flutter runner and allows local-network development traffic. Deployed
environments should supply an HTTPS URL through
`SLOTBRIDGE_API_BASE_URL` at build/run time.

No Stage 5 dependency is Android-only: networking, routing, state, localization,
UUID generation, and secure storage all support Android and iOS.

## Verification

The deterministic tests cover timezone parsing, backend error mapping, login
validation/error display, and booking retry idempotency. An opt-in contract test
starts from a real demo backend and performs the complete client API journey:
login, catalog, availability, booking, list, detail, reschedule, idempotent
replay, cancel, and final verification.
