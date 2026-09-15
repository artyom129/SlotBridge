# SlotBridge Mobile

One Flutter application for SlotBridge clients, targeting Android and iOS from
the same Dart codebase. Android is the primary development target; the standard
`ios/` project is kept ready for macOS/Xcode builds without duplicating screens
or business logic.

## Client flow

The application implements the complete Stage 5 journey:

```text
Login → Home → Service → Employee → Date → Availability → Booking
      → My Appointments → Details → Cancel / Reschedule
```

Only users with the backend `CLIENT` role may enter this client application.
The JWT is stored with `flutter_secure_storage`, and API errors are converted to
safe user-facing messages.

## Requirements

- Flutter stable 3.47 or compatible
- a running and seeded SlotBridge FastAPI backend
- Android Studio/Android SDK for Android builds
- macOS with Xcode for iOS builds

Install packages and run checks:

```bash
flutter pub get
flutter analyze
flutter test
```

## Backend address

The default debug URL is selected per platform:

- Android emulator: `http://10.0.2.2:8000`
- iOS simulator and other platforms: `http://127.0.0.1:8000`

Override it for a physical device, remote environment, or HTTPS deployment:

```bash
flutter run --dart-define=SLOTBRIDGE_API_BASE_URL=https://api.example.com
```

Release builds default to the deployed production API:
`https://slotbridge-api.onrender.com`. The production network timeout is long
enough for a Render Free cold start. A different production backend can still
be supplied with `--dart-define`; non-HTTPS release URLs are rejected.

For a physical device on the same network, use the development computer's LAN
address instead of `127.0.0.1`. Plain HTTP is allowed only in the Android debug
manifest for local development. Production builds should use HTTPS.

## Run on Android

Start the backend, launch an emulator or connect a device, then run:

```bash
flutter run -d android
```

Build a debug APK:

```bash
flutter build apk --debug
```

The current Android build requires API 24 (Android 7.0) or newer. Encrypted
platform storage is used for the access token.

## Run on iOS

On macOS with Xcode and CocoaPods installed:

```bash
flutter run -d ios
```

The generated `ios/` project contains the normal Flutter host only. All UI,
navigation, networking, state management, and business flow stay in `lib/`.
An `.ipa` or iOS Simulator build cannot be produced locally on Windows.

## Demo client

After running `python scripts/seed_domain.py` in the backend project:

- email: `client.a@slotbridge-demo.com`
- password: `SlotBridgeDemo!2026`

These credentials are for local development/demo only.

## Real backend contract test

The test is opt-in so the normal unit suite remains deterministic:

```bash
SLOTBRIDGE_E2E_BASE_URL=http://127.0.0.1:8765 \
  flutter test test/backend_contract_e2e_test.dart
```

It exercises login, catalog selection, availability, booking, list, detail,
atomic rescheduling, idempotent replay, cancellation, and final detail against a
real FastAPI process.
