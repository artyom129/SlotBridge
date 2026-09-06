# SlotBridge

[English](README.md) | **Русский**

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
