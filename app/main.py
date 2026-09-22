from __future__ import annotations

import csv
import io
import json
import os
import re
from html import escape
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import admin, appointments as appointment_api, auth, domain, health as health_api, journeys, schedules, version, waitlist, ai
from app.config import Settings, get_settings
from app.core import DB, Service
from app.database import get_db
from app.dependencies import require_admin, require_client
from app.models import (
    Employee,
    EmployeeService,
    OrganizationMembership,
    Service as ServiceModel,
    User,
)
from app.webhook_security import verify_webhook

load_dotenv()

DB_PATH = os.getenv("SLOTBRIDGE_DB_PATH", "data/slotbridge.db")
db = DB(DB_PATH)
configured = {
    "mindbody": bool(os.getenv("MINDBODY_API_KEY") and os.getenv("MINDBODY_SITE_ID")),
    "vagaro": bool(os.getenv("VAGARO_VERIFICATION_TOKEN")),
    "google": bool(os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN")),
}
svc = Service(db, configured)
settings = get_settings()

app = FastAPI(
    title="SlotBridge",
    version="4.0.0",
    description="Transactional booking, timezone-aware availability, and the preserved integration gateway.",
)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        expose_headers=["Idempotency-Replayed"],
    )


_WEEKDAY_SHORTCUTS = {
    "пн": "понедельник",
    "вт": "вторник",
    "ср": "среда",
    "чт": "четверг",
    "пт": "пятница",
    "сб": "суббота",
    "вс": "воскресенье",
}


def _expand_weekday_shortcuts(message: str) -> str:
    expanded = message
    for short, full in _WEEKDAY_SHORTCUTS.items():
        expanded = re.sub(
            rf"(?<!\w){re.escape(short)}(?:\.)?(?!\w)",
            full,
            expanded,
            flags=re.IGNORECASE,
        )
    return expanded


def _client_organization_id(session: Session, client: User):
    return session.scalar(
        select(OrganizationMembership.organization_id).where(
            OrganizationMembership.user_id == client.id
        )
    )


def _requested_employee_from_message(
    session: Session,
    organization_id,
    branch_id,
    message: str,
) -> str | None:
    words = re.findall(r"[a-zа-яё]+", message.casefold())
    if not words:
        return None

    employees = list(
        session.scalars(
            select(Employee).where(
                Employee.organization_id == organization_id,
                Employee.branch_id == branch_id,
                Employee.is_active.is_(True),
            )
        )
    )
    for employee in employees:
        label = employee.display_name.strip()
        lowered_label = label.casefold()
        if lowered_label and lowered_label in message.casefold():
            return label

        base = re.split(r"\s+[—–-]\s+", lowered_label, maxsplit=1)[0].strip()
        aliases = {base}
        if base:
            aliases.add(base.split()[0])

        for alias in aliases:
            if len(alias) < 3:
                continue
            stems = {alias}
            if alias[-1:] in {"а", "я", "ь", "й"} and len(alias) > 3:
                stems.add(alias[:-1])
            for stem in stems:
                if len(stem) < 3:
                    continue
                if any(
                    word.startswith(stem) and len(word) - len(stem) <= 3
                    for word in words
                ):
                    return label
    return None


def _attach_guard_state(result: dict, state: dict) -> dict:
    if state.get("requested_employee"):
        response_state = dict(result.get("state") or {})
        response_state["requested_employee"] = state["requested_employee"]
        result["state"] = response_state
    if isinstance(result.get("text"), str):
        result["text"] = result["text"].replace("**", "")
    return result


def _handle_requested_service_selection(
    *,
    payload: ai.ChatRequest,
    state: dict,
    client: User,
    session: Session,
    app_settings: Settings,
    organization_id,
):
    requested_employee = state.get("requested_employee")
    if not requested_employee or not state.get("service"):
        return None

    branch = ai._scope(session, organization_id)
    service = session.scalar(
        select(ServiceModel).where(
            ServiceModel.organization_id == organization_id,
            ServiceModel.name == state["service"],
            ServiceModel.is_active.is_(True),
        )
    )
    if service is None:
        raise HTTPException(
            409,
            detail={
                "code": "AI_STALE_SELECTION",
                "message": "The selected service is no longer available",
            },
        )

    employee = session.scalar(
        select(Employee)
        .join(EmployeeService, EmployeeService.employee_id == Employee.id)
        .where(
            Employee.organization_id == organization_id,
            Employee.branch_id == branch.id,
            Employee.is_active.is_(True),
            Employee.display_name == requested_employee,
            EmployeeService.organization_id == organization_id,
            EmployeeService.service_id == service.id,
        )
    )
    if employee is None:
        state.pop("employee", None)
        state.pop("requested_employee", None)
        result = ai._execute(
            "find_employees",
            {"service_name": service.name},
            payload.locale,
            organization_id,
            client,
            session,
            app_settings,
            payload.selection,
        )
        result["state"] = {**state, **result.get("state", {})}
        result.pop("_model_result", None)
        result["text"] = (
            "Этот специалист не выполняет выбранную услугу. Выберите другого."
            if payload.locale == "ru"
            else "That specialist does not provide this service. Choose another specialist."
        )
        return result

    state["employee"] = employee.display_name
    if not state.get("date"):
        return {
            "text": (
                "На какой день вы хотите записаться?"
                if payload.locale == "ru"
                else "What day would you like to book?"
            ),
            "items": [],
            "state": state,
        }

    availability = ai._execute(
        "get_availability",
        {
            "service_name": service.name,
            "employee_name": employee.display_name,
            "date": state["date"],
            "after_time": state.get("time", ""),
        },
        payload.locale,
        organization_id,
        client,
        session,
        app_settings,
        payload.selection,
    )
    availability["state"] = {**state, **availability.get("state", {})}
    availability.pop("_model_result", None)

    requested_time = state.get("time")
    if not requested_time:
        return _attach_guard_state(availability, state)

    exact_slot = any(
        item.get("type") == "slot" and item.get("time") == requested_time
        for item in availability.get("items", [])
    )
    if exact_slot:
        prepared = ai._execute(
            "prepare_booking",
            {
                "service_name": service.name,
                "employee_name": employee.display_name,
                "date": state["date"],
                "start_time": requested_time,
            },
            payload.locale,
            organization_id,
            client,
            session,
            app_settings,
            payload.selection,
        )
        prepared["state"] = {**state, **prepared.get("state", {})}
        prepared.pop("_model_result", None)
        prepared["text"] = (
            f"Время {requested_time} свободно. Подтвердите запись."
            if payload.locale == "ru"
            else f"{requested_time} is available. Confirm the booking."
        )
        return _attach_guard_state(prepared, state)

    availability["text"] = (
        (
            f"{requested_time} занято. Вот ближайшее свободное время."
            if availability.get("items")
            else f"На {requested_time} свободных слотов нет."
        )
        if payload.locale == "ru"
        else (
            f"{requested_time} is unavailable. Here are the nearest free times."
            if availability.get("items")
            else f"There are no free slots at {requested_time}."
        )
    )
    return _attach_guard_state(availability, state)


@app.post("/ai/chat", include_in_schema=False)
def ai_chat_guard(
    payload: ai.ChatRequest,
    client: Annotated[User, Depends(require_client)],
    session: Annotated[Session, Depends(get_db)],
    app_settings: Annotated[Settings, Depends(get_settings)],
):
    state = dict(payload.state)
    selection = payload.selection
    raw_message = payload.message.strip()
    message = raw_message.casefold()
    organization_id = _client_organization_id(session, client)

    if selection is None and message in {"записаться", "book appointment"}:
        state = {}

    if selection is None and organization_id is not None:
        branch = ai._scope(session, organization_id)
        expanded_message = _expand_weekday_shortcuts(raw_message)
        inferred = ai._infer_booking_context(
            session,
            organization_id,
            expanded_message,
            branch,
        )
        for key in ("date", "time"):
            if inferred.get(key):
                state[key] = inferred[key]

        requested_employee = _requested_employee_from_message(
            session,
            organization_id,
            branch.id,
            raw_message,
        )
        if requested_employee:
            state["employee"] = requested_employee
            state["requested_employee"] = requested_employee

    if selection is not None and selection.type == "service":
        state["service"] = selection.label
        state.pop("candidate_slots", None)
        state.pop("pending_action", None)
        requested_employee = state.get("requested_employee")
        if requested_employee:
            state["employee"] = requested_employee
        else:
            state.pop("employee", None)
            state.pop("date", None)
            state.pop("time", None)

        if organization_id is not None and requested_employee:
            direct = _handle_requested_service_selection(
                payload=payload,
                state=state,
                client=client,
                session=session,
                app_settings=app_settings,
                organization_id=organization_id,
            )
            if direct is not None:
                return direct

    if selection is not None and selection.type == "employee":
        state["employee"] = selection.label
        state.pop("candidate_slots", None)
        if state.get("service") and not state.get("date"):
            return {
                "text": (
                    "На какой день вы хотите записаться?"
                    if payload.locale == "ru"
                    else "What day would you like to book?"
                ),
                "items": [],
                "state": state,
            }

    if state != payload.state:
        payload = payload.model_copy(update={"state": state})

    result = ai.chat(payload, client, session, app_settings)
    if isinstance(result, dict):
        result = _attach_guard_state(result, state)
    return result


app.include_router(auth.router)
app.include_router(domain.router)
app.include_router(admin.router)
app.include_router(schedules.router)
app.include_router(appointment_api.router)
app.include_router(health_api.router)
app.include_router(version.router)
app.include_router(waitlist.router)
app.include_router(ai.router)
app.include_router(journeys.router)

STYLE = """
body{margin:0;background:#071019;color:#eef4fb;font:14px system-ui}*{box-sizing:border-box}
.wrap{max-width:1240px;margin:auto;padding:34px}.hero{display:flex;justify-content:space-between;gap:20px;align-items:flex-start}
h1{font-size:38px;margin:4px 0}p{color:#91a6bb}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}
.card{background:#0d1925;border:1px solid #203246;border-radius:16px;padding:18px}.n{font-size:32px;font-weight:800}
.two{display:grid;grid-template-columns:1.2fr .8fr;gap:14px}.row{display:flex;gap:12px;align-items:center;border-top:1px solid #1c2d3e;padding:11px 0}
.row:first-child{border:0}.prov{min-width:78px;text-align:center;border-radius:7px;padding:4px 7px;background:#182b3e;text-transform:uppercase;font-size:10px}
.mb{color:#61c8ff}.vg{color:#ffc36e}.gg{color:#72e89d}.danger{color:#ff7484}.ok{color:#66e19a}.muted{color:#8297ab}
table{width:100%;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #1c2d3e;text-align:left}
.badge{padding:6px 9px;border-radius:999px;border:1px solid #31506b;color:#9fc7e8}
@media(max-width:800px){.grid{grid-template-columns:1fr 1fr}.two{grid-template-columns:1fr}}
"""


def h(value: object) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def csv_download(rows: list[dict], filename: str) -> Response:
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(
            {
                key: f"'{value}" if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value
                for key, value in row.items()
            }
            for row in rows
        )
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def page() -> str:
    aps = db.list("appointments")
    conf = db.list("conflicts")
    jobs = db.list("sync_jobs")
    dead = db.list("dead_letters")
    feas = svc.feasibility()

    rows = "".join(
        f"<div class='row'><span class='prov {'mb' if a['provider']=='mindbody' else 'vg' if a['provider']=='vagaro' else 'gg'}'>{h(a['provider'])}</span>"
        f"<div><b>Appointment</b><div class='muted'>{h(a['start_at'])} → {h(a['end_at'])}</div></div>"
        f"<span style='margin-left:auto'>{h(a['status'])}</span></div>"
        for a in aps[:8]
    ) or "<p>No demo data yet. Run <code>python scripts/seed_demo.py</code>.</p>"

    caps = "".join(
        f"<tr><td>{h(x['provider'])}</td><td>{'✓' if x['webhook_ingress'] else '—'}</td>"
        f"<td>{'✓' if x['write_appointments'] else '—'}</td><td>{'✓' if x['live_configured'] else 'demo'}</td></tr>"
        for x in feas["providers"]
    )

    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>SlotBridge</title><style>{STYLE}</style></head><body><div class='wrap'>
    <div class='hero'><div><div class='ok'>● SYSTEM HEALTHY</div><h1>SlotBridge</h1><p>Appointment synchronization control plane for multi-booking systems.</p></div><span class='badge'>DEMO MODE</span></div>
    <div class='grid'><div class='card'><div class='muted'>Appointments</div><div class='n'>{len(aps)}</div></div><div class='card'><div class='muted'>Conflicts</div><div class='n'>{len(conf)}</div></div><div class='card'><div class='muted'>Sync jobs</div><div class='n'>{len(jobs)}</div></div><div class='card'><div class='muted'>Dead letters</div><div class='n'>{len(dead)}</div></div></div>
    <div class='two'><div class='card'><h2>Canonical schedule</h2>{rows}</div><div class='card'><h2>Capability matrix</h2><table><tr><th>Provider</th><th>Hook</th><th>Write</th><th>Live</th></tr>{caps}</table></div></div>
    <div class='two' style='margin-top:14px'><div class='card'><h2>Conflict radar</h2><p>{len(conf)} active overlap(s) detected across normalized schedules.</p><a style='color:#58b6ff' href='/api/conflicts'>Open JSON</a> · <a style='color:#58b6ff' href='/api/conflicts.csv'>Export CSV</a></div><div class='card'><h2>Phase-1 feasibility</h2><p>{len(feas['blockers'])} blocker(s) currently require attention.</p><a style='color:#58b6ff' href='/api/feasibility'>Open report</a></div></div>
    </div></body></html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return page()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "slotbridge"}


@app.get("/api/appointments")
def appointments(_admin: Annotated[User, Depends(require_admin)]):
    return {"items": sanitized_appointments()}


@app.get("/api/appointments.csv")
def appointments_csv(_admin: Annotated[User, Depends(require_admin)]):
    return csv_download(sanitized_appointments(), "slotbridge-appointments.csv")


@app.get("/api/conflicts")
def conflicts(_admin: Annotated[User, Depends(require_admin)]):
    return {"items": db.list("conflicts")}


@app.get("/api/conflicts.csv")
def conflicts_csv(_admin: Annotated[User, Depends(require_admin)]):
    return csv_download(db.list("conflicts"), "slotbridge-conflicts.csv")


@app.get("/api/feasibility")
def feasibility(_admin: Annotated[User, Depends(require_admin)]):
    return svc.feasibility()


@app.get("/api/sync-jobs")
def sync_jobs(_admin: Annotated[User, Depends(require_admin)]):
    return {"items": db.list("sync_jobs")}


@app.get("/api/dead-letters")
def dead_letters(_admin: Annotated[User, Depends(require_admin)]):
    return {"items": db.list("dead_letters")}


@app.post("/webhooks/{provider}")
async def webhook(
    provider: str,
    request: Request,
    app_settings: Annotated[Settings, Depends(get_settings)],
):
    if provider not in svc.adapters:
        raise HTTPException(404, "Unknown provider")
    body = await request.body()
    if len(body) > 1_000_000:
        raise HTTPException(413, "Webhook payload is too large")
    verify_webhook(
        provider,
        body,
        request.headers.get("X-SlotBridge-Signature"),
        app_settings,
    )
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(400, "Invalid JSON payload") from None
    if not isinstance(payload, dict):
        raise HTTPException(422, "Webhook payload must be a JSON object")
    return svc.ingest(provider, payload)


@app.post("/api/reconcile")
def reconcile(_admin: Annotated[User, Depends(require_admin)]):
    return {"conflicts": svc.reconcile()}


@app.post("/api/sync-plan/{appointment_id}")
def plan(
    appointment_id: int,
    _admin: Annotated[User, Depends(require_admin)],
    target: str = "google",
):
    if target not in svc.adapters:
        raise HTTPException(404, "Unknown target")
    if not db.get_appointment(appointment_id):
        raise HTTPException(404, "Appointment not found")
    return {"job_id": svc.plan(appointment_id, target), "target": target}


def sanitized_appointments() -> list[dict]:
    safe_columns = {
        "id",
        "provider",
        "external_id",
        "start_at",
        "end_at",
        "client_name",
        "staff_name",
        "status",
        "updated_at",
    }
    return [
        {key: value for key, value in row.items() if key in safe_columns}
        for row in db.list("appointments")
    ]
