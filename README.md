<div align="center">

# SlotBridge

**Production-ready mobile booking and scheduling platform with AI-assisted workflows, smart availability, and post-appointment reviews.**

[![Status](https://img.shields.io/badge/Status-Production-2ea44f)](https://slotbridge-api.onrender.com)
[![Release](https://img.shields.io/badge/Android-v1.1.6-3DDC84?logo=android&logoColor=white)](https://github.com/artyom129/SlotBridge/releases/tag/v1.1.6)
[![CI](https://github.com/artyom129/SlotBridge/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/artyom129/SlotBridge/actions/workflows/tests.yml)
[![License](https://img.shields.io/badge/License-Proprietary-c62828)](LICENSE.md)

[![Flutter](https://img.shields.io/badge/Flutter-Mobile-02569B?logo=flutter&logoColor=white)](https://flutter.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Gemini](https://img.shields.io/badge/Gemini-AI-8E75B2?logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)

**[Download APK](https://github.com/artyom129/SlotBridge/releases/download/v1.1.6/SlotBridge-1.1.6-10-production.apk)** ·
**[Release v1.1.6](https://github.com/artyom129/SlotBridge/releases/tag/v1.1.6)** ·
**[Production API](https://slotbridge-api.onrender.com)** ·
**[Architecture](docs/architecture.md)** ·
**[Setup](docs/setup.md)**

</div>

> **Current Android version:** `1.1.6` · `versionCode 10`

## What is SlotBridge?

SlotBridge is a full client-server booking platform for service businesses.

A client can choose a service and specialist, see real availability, create an appointment, reschedule it, cancel it, and leave a review after the visit is completed. The backend owns the business rules, prevents conflicting bookings, keeps tenant data isolated, and stores production data in PostgreSQL.

The system also includes smarter scheduling flows such as **Smart Slots**, **Waitlist**, **Conflict Rescue**, **Multi-Service Smart Journey**, and **SlotBridge AI** powered by Google Gemini.

The production architecture is:

**Flutter → FastAPI → PostgreSQL**

with the backend deployed on Render and PostgreSQL hosted on Supabase.

## Core Features

| Area | Capabilities |
|---|---|
| Booking | Service, specialist, and real availability selection |
| Appointments | Create, reschedule, cancel, list, and inspect appointment history |
| Scheduling | Smart Slots, Waitlist, Conflict Rescue |
| Multi-service visits | Smart Journey with multiple route strategies |
| AI assistant | Natural-language booking, rescheduling, cancellation, and availability workflows |
| Reviews | Post-appointment reviews, specialist ratings, moderation, reports, and official replies |
| Review intelligence | Aggregated analytics and privacy-safe Gemini summaries |
| Profile | Registration, authentication, and profile editing |
| Localization | Russian and English |
| Appearance | Light, dark, and system theme |
| Updates | In-app release checks, APK download, SHA-256 verification, and Android installer handoff |
| Reliability | Transactions, idempotency, tenant isolation, and double-booking protection |

## Reviews and Specialist Ratings

Reviews are tied to real completed appointments.

A client can leave one review only when the appointment status is `COMPLETED`. The organization, service, specialist, and client are derived from the appointment on the backend instead of being trusted from the request body.

The review system supports:

- overall rating from 1 to 5;
- quality, service, and punctuality ratings;
- optional written feedback;
- anonymous public display;
- configurable edit window;
- specialist rating aggregates;
- 1-to-5-star distribution;
- moderation with `PUBLISHED`, `HIDDEN`, and `FLAGGED` states;
- duplicate-protected reports;
- official employee or organization replies;
- admin analytics;
- privacy-safe Gemini summaries.

For high ratings, SlotBridge can offer the client an explicit link to the organization's verified 2GIS page. Internal review content is never published to 2GIS automatically.

## SlotBridge AI

SlotBridge AI uses Google Gemini through the backend rather than giving the model direct access to the database.

It can:

- find services and specialists from natural-language requests;
- understand dates, weekdays, and times;
- check real availability;
- prepare bookings, rescheduling, and cancellations;
- handle multi-service requests;
- preserve context between steps;
- require explicit confirmation before data-changing actions.

Gemini does **not** receive direct PostgreSQL access, JWTs, passwords, or application secrets. All actions pass through approved backend tools and domain services.

## Multi-Service Smart Journey

Smart Journey combines multiple services into one visit and builds a route using real employee availability, service duration, waiting time, and specialist assignment.

Available strategies:

- **Fastest** — minimize total visit duration;
- **Earliest** — find the earliest valid start;
- **Fewer specialists** — minimize specialist changes.

The final journey is booked atomically. If any step conflicts with an occupied interval, the system does not create a partial booking.

## Architecture

```mermaid
flowchart LR
    M[Flutter Mobile] -->|HTTPS · JSON · JWT| B[FastAPI Backend]
    B -->|SQLAlchemy · Transactions| P[(PostgreSQL)]
    B --> A[AI Tools]
    A -->|HTTPS| G[Google Gemini]
    A --> S[Booking / Availability / Review Services]
    S --> P
```

More detail: [`docs/architecture.md`](docs/architecture.md).

## Technology Stack

| Layer | Stack |
|---|---|
| Mobile | Flutter, Dart, Riverpod, GoRouter, Dio, Secure Storage |
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| AI | Google Gemini API |
| Infrastructure | Render, Supabase PostgreSQL, GitHub Releases |
| Testing | Pytest, Flutter Test, GitHub Actions |

## Reliability and Security

- JWT authentication;
- RBAC and tenant isolation;
- Argon2 password hashing;
- PostgreSQL transactions;
- exclusion constraints for active booking intervals;
- idempotency for critical mutations;
- HMAC verification for webhook flows;
- explicit confirmation before AI-triggered mutations;
- backend-only secret storage;
- HTTPS production API;
- no production secrets committed to Git or embedded in the mobile client.

## Android Updater

The built-in updater can:

1. check release metadata;
2. download the latest APK from GitHub Releases;
3. verify its SHA-256 hash;
4. reuse an already verified package when possible;
5. hand the APK to the Android system installer.

## Production

| Component | Status |
|---|---|
| Android | **v1.1.6 · versionCode 10** |
| Backend | [Render](https://slotbridge-api.onrender.com) |
| Database | Supabase PostgreSQL |
| Transport | HTTPS |
| APK | [GitHub Releases](https://github.com/artyom129/SlotBridge/releases/tag/v1.1.6) |
| Health | `GET /api/v1/health/live` |

Render is currently used on a free tier, so the first request after an idle period can take longer because of cold start.

## Repository Structure

| Directory | Purpose |
|---|---|
| `app/` | FastAPI routes, models, schemas, and backend services |
| `mobile/` | Flutter Android client |
| `tests/` | Backend unit, integration, and concurrency tests |
| `alembic/` | PostgreSQL migrations |
| `docs/` | Architecture and setup documentation |
| `scripts/` | Startup, seed, verification, and helper scripts |
| `.github/workflows/` | CI workflows |

## Local Development

Full setup guide: [`docs/setup.md`](docs/setup.md).

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI: `http://127.0.0.1:8000/docs`

### Windows Native PostgreSQL

```powershell
.\start_slotbridge.bat
```

Stop:

```powershell
.\stop_slotbridge.bat
```

### Docker

```powershell
docker compose up --build
```

### Mobile

```powershell
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://192.168.100.7:8000
```

Production build:

```powershell
flutter build apk --release --dart-define=API_BASE_URL=https://slotbridge-api.onrender.com
```

## Environment Variables

`.env.example` contains safe placeholders.

| Variable | Purpose |
|---|---|
| `SLOTBRIDGE_ENVIRONMENT` | `development`, `test`, or `production` |
| `DATABASE_URL` | PostgreSQL connection URL |
| `JWT_SECRET` | JWT signing secret |
| `CORS_ALLOWED_ORIGINS` | Allowed origins |
| `GEMINI_API_KEY` | Backend-only Gemini API key |
| `GEMINI_MODEL` | Gemini model used by the backend |
| `REVIEW_EDIT_WINDOW_HOURS` | Review edit window, default `24` |

Production secrets belong in the hosting environment and should never be committed to the repository.

## Database Migrations

```powershell
alembic current
alembic upgrade head
```

Alembic manages schema evolution and PostgreSQL constraints.

The review module is introduced by migration `20260924_0006`, adding review, report, reply, audit-log, and 2GIS configuration support.

## Review API

| Endpoint | Purpose |
|---|---|
| `POST /reviews` | Create a review for a completed appointment |
| `GET/PATCH/DELETE /reviews/{id}` | Read, edit, or soft-delete a review |
| `GET /me/reviews` | Current client's review history |
| `GET /appointments/{id}/review` | Review for a specific appointment |
| `GET /employees/{id}/reviews` | Published specialist reviews |
| `GET /employees/{id}/rating` | Rating aggregates and star distribution |
| `POST /reviews/{id}/reports` | Report a review |
| `PUT /reviews/{id}/reply` | Create or update an official reply |
| `GET /admin/organizations/{id}/reviews` | Moderation queue |
| `PATCH /admin/organizations/{id}/review-settings` | Configure the verified 2GIS link |
| `PATCH /admin/reviews/{id}/moderation` | Hide, flag, or restore a review |
| `PATCH /admin/review-reports/{id}` | Resolve or dismiss a report |
| `GET /admin/organizations/{id}/reviews/analytics` | Aggregated analytics |
| `GET /admin/organizations/{id}/reviews/ai-summary` | Privacy-safe Gemini summary |

## Verification

Backend:

```powershell
python -m pytest
```

Flutter:

```powershell
cd mobile
flutter analyze
flutter test
```

GitHub Actions is also configured for automated checks.

## Author

**Artyom Koncha**  
Python Backend · Automation · Product Development

GitHub: [@artyom129](https://github.com/artyom129)

## License

SlotBridge is **proprietary source-available software**. The public repository exists for technical review, portfolio visibility, and evaluation of the product. Public access to the source code does **not** make the project open source.

Use, modification, redistribution, commercial exploitation, rebranding, or incorporation into another product requires permission unless expressly allowed by [`LICENSE.md`](LICENSE.md) or mandatory applicable law.

Full terms: [LICENSE](LICENSE.md) · [NOTICE](NOTICE)

**Copyright © 2026 Artyom Koncha. All Rights Reserved.**
