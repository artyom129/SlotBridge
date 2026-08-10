from __future__ import annotations

import csv
import io
import os
from html import escape

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from app.core import DB, Service

load_dotenv()

DB_PATH = os.getenv("SLOTBRIDGE_DB_PATH", "data/slotbridge.db")
db = DB(DB_PATH)
configured = {
    "mindbody": bool(os.getenv("MINDBODY_API_KEY") and os.getenv("MINDBODY_SITE_ID")),
    "vagaro": bool(os.getenv("VAGARO_VERIFICATION_TOKEN")),
    "google": bool(os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN")),
}
svc = Service(db, configured)

app = FastAPI(
    title="SlotBridge",
    version="1.0.0",
    description="Appointment synchronization control plane with webhook normalization, conflict detection and capability-aware planning.",
)

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
        writer.writerows(rows)
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
        f"<div><b>{h(a['client_name'] or 'Appointment')}</b><div class='muted'>{h(a['start_at'])} → {h(a['end_at'])}</div></div>"
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
def appointments():
    return {"items": db.list("appointments")}


@app.get("/api/appointments.csv")
def appointments_csv():
    return csv_download(db.list("appointments"), "slotbridge-appointments.csv")


@app.get("/api/conflicts")
def conflicts():
    return {"items": db.list("conflicts")}


@app.get("/api/conflicts.csv")
def conflicts_csv():
    return csv_download(db.list("conflicts"), "slotbridge-conflicts.csv")


@app.get("/api/feasibility")
def feasibility():
    return svc.feasibility()


@app.get("/api/sync-jobs")
def sync_jobs():
    return {"items": db.list("sync_jobs")}


@app.get("/api/dead-letters")
def dead_letters():
    return {"items": db.list("dead_letters")}


@app.post("/webhooks/{provider}")
async def webhook(provider: str, request: Request):
    if provider not in svc.adapters:
        raise HTTPException(404, "Unknown provider")
    return svc.ingest(provider, await request.json())


@app.post("/api/reconcile")
def reconcile():
    return {"conflicts": svc.reconcile()}


@app.post("/api/sync-plan/{appointment_id}")
def plan(appointment_id: int, target: str = "google"):
    if target not in svc.adapters:
        raise HTTPException(404, "Unknown target")
    if not db.get_appointment(appointment_id):
        raise HTTPException(404, "Appointment not found")
    return {"job_id": svc.plan(appointment_id, target), "target": target}
