from __future__ import annotations
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.core import DB, Service

DB_PATH=os.getenv("SLOTBRIDGE_DB_PATH","data/slotbridge.db")
db=DB(DB_PATH)
configured={
    "mindbody":bool(os.getenv("MINDBODY_API_KEY") and os.getenv("MINDBODY_SITE_ID")),
    "vagaro":bool(os.getenv("VAGARO_VERIFICATION_TOKEN")),
    "google":bool(os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN")),
}
svc=Service(db,configured)

app=FastAPI(title="SlotBridge",version="1.0.0",
            description="Appointment synchronization control plane with webhook normalization, conflict detection and capability-aware planning.")

STYLE="""
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

def page():
    aps=db.list("appointments")
    conf=db.list("conflicts")
    jobs=db.list("sync_jobs")
    dead=db.list("dead_letters")
    feas=svc.feasibility()
    rows="".join(f"<div class='row'><span class='prov {'mb' if a['provider']=='mindbody' else 'vg' if a['provider']=='vagaro' else 'gg'}'>{a['provider']}</span><div><b>{a['client_name'] or 'Appointment'}</b><div class='muted'>{a['start_at']} → {a['end_at']}</div></div><span style='margin-left:auto'>{a['status']}</span></div>" for a in aps[:8]) or "<p>No demo data yet. Run scripts/seed_demo.py.</p>"
    caps="".join(f"<tr><td>{x['provider']}</td><td>{'✓' if x['webhook_ingress'] else '—'}</td><td>{'✓' if x['write_appointments'] else '—'}</td><td>{'✓' if x['live_configured'] else 'demo'}</td></tr>" for x in feas["providers"])
    return f"""<!doctype html><html><head><title>SlotBridge</title><style>{STYLE}</style></head><body><div class='wrap'>
    <div class='hero'><div><div class='ok'>● SYSTEM HEALTHY</div><h1>SlotBridge</h1><p>Appointment synchronization control plane for multi-booking systems.</p></div><span class='badge'>DEMO MODE</span></div>
    <div class='grid'><div class='card'><div class='muted'>Appointments</div><div class='n'>{len(aps)}</div></div><div class='card'><div class='muted'>Conflicts</div><div class='n'>{len(conf)}</div></div><div class='card'><div class='muted'>Sync jobs</div><div class='n'>{len(jobs)}</div></div><div class='card'><div class='muted'>Dead letters</div><div class='n'>{len(dead)}</div></div></div>
    <div class='two'><div class='card'><h2>Canonical schedule</h2>{rows}</div><div class='card'><h2>Capability matrix</h2><table><tr><th>Provider</th><th>Hook</th><th>Write</th><th>Live</th></tr>{caps}</table></div></div>
    <div class='two' style='margin-top:14px'><div class='card'><h2>Conflict radar</h2><p>{len(conf)} active overlap(s) detected across normalized schedules.</p><a style='color:#58b6ff' href='/api/conflicts'>Open JSON</a></div><div class='card'><h2>Phase-1 feasibility</h2><p>{len(feas['blockers'])} blocker(s) currently require attention.</p><a style='color:#58b6ff' href='/api/feasibility'>Open report</a></div></div>
    </div></body></html>"""

@app.get("/",response_class=HTMLResponse)
def dashboard(): return page()

@app.get("/api/health")
def health(): return {"status":"ok","service":"slotbridge"}

@app.get("/api/appointments")
def appointments(): return {"items":db.list("appointments")}

@app.get("/api/conflicts")
def conflicts(): return {"items":db.list("conflicts")}

@app.get("/api/feasibility")
def feasibility(): return svc.feasibility()

@app.get("/api/sync-jobs")
def sync_jobs(): return {"items":db.list("sync_jobs")}

@app.get("/api/dead-letters")
def dead_letters(): return {"items":db.list("dead_letters")}

@app.post("/webhooks/{provider}")
async def webhook(provider:str, request:Request):
    if provider not in svc.adapters: raise HTTPException(404,"Unknown provider")
    return svc.ingest(provider,await request.json())

@app.post("/api/reconcile")
def reconcile(): return {"conflicts":svc.reconcile()}

@app.post("/api/sync-plan/{appointment_id}")
def plan(appointment_id:int,target:str="google"):
    if target not in svc.adapters: raise HTTPException(404,"Unknown target")
    if not db.get_appointment(appointment_id): raise HTTPException(404,"Appointment not found")
    return {"job_id":svc.plan(appointment_id,target),"target":target}
