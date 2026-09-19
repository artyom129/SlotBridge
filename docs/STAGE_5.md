# Stage 5 — Flutter client

## Summary

Stage 5 adds a real cross-platform Flutter client in `mobile/`. It uses one Dart
codebase for Android and iOS and connects directly to the existing FastAPI
authentication, catalog, availability, and transactional appointment APIs.

The implemented CLIENT journey is:

```text
Login → Home → Service → Employee → Date → Availability → Booking
      → My Appointments → Details → Cancel / Reschedule
```

Stage 6 has not been started.

## Flutter project and platforms

- standard Flutter `android/` and `ios/` hosts are present;
- shared application code lives entirely under `mobile/lib/`;
- Android is configured with Internet access, minimum SDK 24, and debug-only
  local HTTP support;
- iOS has the standard Runner/Xcode project and local-network development
  transport configuration;
- no separate iOS UI, Swift business layer, or duplicated Flutter screens were
  created;
- all direct dependencies used by the application support Android and iOS.

## Application architecture

- Riverpod async controllers and providers for session and feature state;
- GoRouter with an authentication guard and nested client navigation;
- Dio API client with bearer-token injection and safe FastAPI error mapping;
- platform secure storage for the JWT;
- repository boundary for auth, catalog, and booking calls;
- typed domain models with explicit timezone handling;
- responsive, scrollable, safe-area-aware screens.

## Completed client functionality

- startup session restoration and CLIENT-only login;
- home summary and upcoming appointment preview;
- service-first booking wizard with valid employee filtering;
- branch-local date selection and live backend availability;
- booking confirmation with persistent idempotency behavior across uncertain
  network retries;
- upcoming, past, cancelled, and all appointment lists;
- appointment detail and status-history display;
- cancellation with an optional reason;
- selection of a new date/slot and atomic backend rescheduling;
- profile, backend-address display, and logout.

## Backend integration

The Flutter client uses the existing Stage 2–4 endpoints. It does not reproduce
scheduling or booking rules locally. Service duration, slot validity, tenant
permissions, appointment end time, atomic rescheduling, idempotency persistence,
and database overlap protection remain backend responsibilities.

The Android emulator default URL is `http://10.0.2.2:8000`; the iOS simulator
default is `http://127.0.0.1:8000`. Any deployment or physical device can supply
`SLOTBRIDGE_API_BASE_URL` with `--dart-define`.

## Test results

Executed on Windows with Flutter 3.47.3 / Dart 3.13.3:

- `flutter analyze`: passed with no issues;
- normal Flutter suite: 5 passed, 1 opt-in backend contract test skipped;
- real FastAPI contract E2E: 1 passed;
- E2E operations: login, catalog, availability, create, list, detail,
  reschedule, same-key replay, cancel, and final detail verification.

The E2E backend uses an isolated test-only SQLite database and the real FastAPI
application/service routes. It verifies the client contract and complete flow;
it does not replace Stage 4's PostgreSQL-only concurrency tests.

## Build verification

The Windows Android toolchain was installed and configured, and
`flutter build apk --debug` completed successfully. The verified development APK
is available as `D:\SlotBridge-debug.apk`. That artifact was
built with `SLOTBRIDGE_API_BASE_URL=http://192.168.100.7:8000` for physical-device
testing on the current LAN.

The standard iOS codebase and configuration are present. Flutter does not expose
the iOS build target on Windows, so an `.ipa` or iOS Simulator build requires
macOS plus Xcode. Per Stage 5 scope, this does not block completion.

## Key files created

- `mobile/android/` and `mobile/ios/`
- `mobile/lib/core/`, `mobile/lib/domain/`, `mobile/lib/data/`
- `mobile/lib/features/auth/`, `home/`, `booking/`, `appointments/`, `profile/`
- `mobile/test/`
- `scripts/mobile_e2e_backend.py`
- `docs/mobile-client.md`
- `docs/STAGE_5.md`

## Known limitations

- iOS signing/simulator verification must be performed on macOS with Xcode;
- the Stage 5 app is intentionally CLIENT-only;
- realtime updates, push notifications, reminders, payments, waitlist, and
  external calendar redesign remain outside Stage 5.

`LICENSE`, `NOTICE`, copyright, and author information were not changed.
