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
python scripts/seed_demo.py
python run.py
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
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
- `GET /api/conflicts`
- `GET /api/feasibility`
- `GET /api/sync-jobs`
- `GET /api/dead-letters`
- `POST /webhooks/mindbody`
- `POST /webhooks/vagaro`
- `POST /webhooks/google`
- `POST /api/reconcile`
- `POST /api/sync-plan/{appointment_id}?target=google`

## Notes about vendor connectors

The project is a **demonstration integration architecture**, not a claim of prior client work.

The Mindbody connector normalizes public appointment webhook shapes and marks appointment write capability as technically available, but live vendor calls are not performed without approved credentials and a client-specific mapping.

The Vagaro connector is webhook-ingress-first. It does not hardcode undocumented appointment write endpoints. If a supported outbound integration path exists for a client account, it can be added behind the same adapter interface.

Google Calendar is modeled as the central visibility layer. Demo mode simulates writes locally.

## Tests

```bash
pytest -q
```
