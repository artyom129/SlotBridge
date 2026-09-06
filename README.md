<a id="english"></a>

<div align="center">

**🇬🇧 English** · [🇷🇺 Русский](#russian)

</div>

# SlotBridge

Appointment synchronization control plane for businesses that use multiple booking systems.

**Stack:** Python, FastAPI, SQLite, webhooks, Google Calendar, Docker, Pytest.

## What it demonstrates

- canonical appointment normalization
- Mindbody-style appointment webhook ingestion
- Vagaro webhook ingestion
- Google Calendar event/block ingestion
- duplicate webhook protection
- cross-provider double-booking detection
- provider capability matrix
- Phase-1 feasibility audit
- sync planning
- retry / dead-letter state
- demo mode that works without vendor credentials
- CSV exports and REST API
- a dark operations dashboard

## Architecture

```text
Mindbody webhook ─┐
                  ├─> normalize ─> idempotency ─> canonical schedule
Vagaro webhook ───┘                       │
                                         ├─> conflict detection
Google Calendar ──────────────────────────┤
                                         ├─> capability-aware sync plan
                                         └─> retry / dead-letter review
```

SlotBridge intentionally does **not** assume that every provider exposes identical write capabilities. The feasibility report separates technical capability, live configuration, and unsupported paths before a larger integration is promised.

## Quick start

```bash
python -m venv .venv
```

Windows:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/seed_demo.py
python run.py
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/seed_demo.py
python run.py
```

Open:

- Dashboard: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Feasibility API: `http://127.0.0.1:8000/api/feasibility`

## API

- `GET /api/health`
- `GET /api/appointments`
- `GET /api/appointments.csv`
- `GET /api/conflicts`
- `GET /api/conflicts.csv`
- `GET /api/feasibility`
- `GET /api/sync-jobs`
- `GET /api/dead-letters`
- `POST /webhooks/mindbody`
- `POST /webhooks/vagaro`
- `POST /webhooks/google`
- `POST /api/reconcile`
- `POST /api/sync-plan/{appointment_id}?target=google`

## Configuration

Copy `.env.example` to `.env`. The repository ships with no secrets or vendor credentials.

The `data/` directory is kept in Git, but SQLite runtime files are ignored.

## Notes about vendor connectors

The project is a **demonstration integration architecture**, not a claim of prior client work.

The Mindbody connector normalizes public appointment webhook shapes and marks appointment write capability as technically available, but live vendor calls are not performed without approved credentials and a client-specific mapping.

The Vagaro connector is webhook-ingress-first. It does not hardcode undocumented appointment write endpoints. If a supported outbound integration path exists for a client account, it can be added behind the same adapter interface.

Google Calendar is modeled as the central visibility layer. Demo mode simulates writes locally.

## Tests

```bash
pytest -q
```

GitHub Actions runs the test suite on pushes and pull requests.

---

<a id="russian"></a>

<div align="center">

[🇬🇧 English](#english) · **🇷🇺 Русский**

</div>

# SlotBridge — Русская версия

SlotBridge — control plane для синхронизации записей и расписаний между несколькими booking-системами.

**Стек:** Python, FastAPI, SQLite, webhooks, Google Calendar, Docker, Pytest.

## Что демонстрирует проект

- приведение записей разных сервисов к единой модели;
- приём Mindbody-style webhook'ов;
- приём Vagaro webhook'ов;
- импорт событий и блокировок Google Calendar;
- защита от повторной обработки webhook'ов;
- поиск двойных бронирований между провайдерами;
- capability matrix для внешних сервисов;
- предварительный feasibility audit перед интеграцией;
- построение плана синхронизации;
- retry и dead-letter состояния;
- demo-режим без реальных vendor credentials;
- CSV exports и REST API;
- веб-панель для контроля операций.

## Архитектура

```text
Mindbody webhook ─┐
                  ├─> normalize ─> idempotency ─> canonical schedule
Vagaro webhook ───┘                       │
                                         ├─> conflict detection
Google Calendar ──────────────────────────┤
                                         ├─> capability-aware sync plan
                                         └─> retry / dead-letter review
```

SlotBridge специально не предполагает, что каждый booking-провайдер имеет одинаковые возможности записи. Сначала система определяет доступные integration paths, а уже затем строит план синхронизации.

## Запуск

Windows:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/seed_demo.py
python run.py
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/seed_demo.py
python run.py
```

Открыть:

- Dashboard: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Feasibility API: `http://127.0.0.1:8000/api/feasibility`

## Основные API endpoints

- `GET /api/appointments`
- `GET /api/conflicts`
- `GET /api/feasibility`
- `GET /api/sync-jobs`
- `GET /api/dead-letters`
- `POST /webhooks/mindbody`
- `POST /webhooks/vagaro`
- `POST /webhooks/google`
- `POST /api/reconcile`

Проект является демонстрацией архитектуры интеграции и не заявляет о выполненной клиентской интеграции с перечисленными сервисами.
