from __future__ import annotations
import hashlib, json, sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

@dataclass
class Event:
    provider: str
    event_key: str
    external_id: str
    action: str
    start_at: str | None
    end_at: str | None
    client_name: str
    staff_name: str
    status: str
    origin_token: str
    raw: dict[str, Any]

class DB:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def con(self):
        c = sqlite3.connect(self.path, check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c

    def init(self):
        with self.con() as c:
            c.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS webhooks(
              id INTEGER PRIMARY KEY, provider TEXT, event_key TEXT, received_at TEXT, payload TEXT,
              UNIQUE(provider,event_key)
            );
            CREATE TABLE IF NOT EXISTS appointments(
              id INTEGER PRIMARY KEY, provider TEXT, external_id TEXT, start_at TEXT, end_at TEXT,
              client_name TEXT, staff_name TEXT, status TEXT, origin_token TEXT, raw TEXT, updated_at TEXT,
              UNIQUE(provider,external_id)
            );
            CREATE TABLE IF NOT EXISTS conflicts(
              id INTEGER PRIMARY KEY, a_id INTEGER, b_id INTEGER, start_at TEXT, end_at TEXT,
              severity TEXT, status TEXT DEFAULT 'open', UNIQUE(a_id,b_id)
            );
            CREATE TABLE IF NOT EXISTS sync_jobs(
              id INTEGER PRIMARY KEY, appointment_id INTEGER, source_provider TEXT, target_provider TEXT,
              operation TEXT, status TEXT, attempts INTEGER DEFAULT 0, payload TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS dead_letters(
              id INTEGER PRIMARY KEY, sync_job_id INTEGER, provider TEXT, reason TEXT, payload TEXT, created_at TEXT
            );
            """)
            c.commit()

    def record_webhook(self, provider, key, payload):
        try:
            with self.con() as c:
                c.execute("INSERT INTO webhooks(provider,event_key,received_at,payload) VALUES(?,?,?,?)",
                          (provider,key,now(),json.dumps(payload)))
                c.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def upsert(self, e: Event):
        with self.con() as c:
            row = c.execute("SELECT id FROM appointments WHERE provider=? AND external_id=?",
                            (e.provider,e.external_id)).fetchone()
            vals=(e.start_at,e.end_at,e.client_name,e.staff_name,e.status,e.origin_token,json.dumps(e.raw),now())
            if row:
                c.execute("""UPDATE appointments SET start_at=?,end_at=?,client_name=?,staff_name=?,status=?,origin_token=?,raw=?,updated_at=?
                             WHERE id=?""", vals+(row["id"],))
                aid=row["id"]
            else:
                cur=c.execute("""INSERT INTO appointments(provider,external_id,start_at,end_at,client_name,staff_name,status,origin_token,raw,updated_at)
                                 VALUES(?,?,?,?,?,?,?,?,?,?)""",
                              (e.provider,e.external_id)+vals)
                aid=cur.lastrowid
            c.commit()
            return int(aid)

    def list(self, table):
        with self.con() as c:
            return [dict(r) for r in c.execute(f"SELECT * FROM {table} ORDER BY id DESC").fetchall()]

    def get_appointment(self, aid):
        with self.con() as c:
            r=c.execute("SELECT * FROM appointments WHERE id=?",(aid,)).fetchone()
            return dict(r) if r else None

    def replace_conflicts(self, items):
        with self.con() as c:
            c.execute("DELETE FROM conflicts")
            for x in items:
                c.execute("""INSERT OR IGNORE INTO conflicts(a_id,b_id,start_at,end_at,severity,status)
                             VALUES(?,?,?,?,?,'open')""",
                          (x["a_id"],x["b_id"],x["start_at"],x["end_at"],x["severity"]))
            c.commit()

    def create_job(self, aid, source, target, op, status, payload):
        with self.con() as c:
            cur=c.execute("""INSERT INTO sync_jobs(appointment_id,source_provider,target_provider,operation,status,attempts,payload,created_at)
                             VALUES(?,?,?,?,?,0,?,?)""",
                          (aid,source,target,op,status,json.dumps(payload),now()))
            jid=cur.lastrowid
            c.commit()
            return int(jid)

    def dead_letter(self, jid, provider, reason, payload):
        with self.con() as c:
            c.execute("""INSERT INTO dead_letters(sync_job_id,provider,reason,payload,created_at)
                         VALUES(?,?,?,?,?)""",(jid,provider,reason,json.dumps(payload),now()))
            c.commit()

def parse_dt(v):
    if not v: return None
    try: return datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError: return None

def detect_conflicts(rows):
    active=[r for r in rows if r.get("status") not in {"cancelled","canceled"} and parse_dt(r.get("start_at")) and parse_dt(r.get("end_at"))]
    out=[]
    for i,a in enumerate(active):
        for b in active[i+1:]:
            s=max(parse_dt(a["start_at"]),parse_dt(b["start_at"]))
            e=min(parse_dt(a["end_at"]),parse_dt(b["end_at"]))
            if s<e:
                out.append({
                    "a_id":min(a["id"],b["id"]),"b_id":max(a["id"],b["id"]),
                    "start_at":s.isoformat(),"end_at":e.isoformat(),
                    "severity":"critical" if a["provider"]!=b["provider"] else "major"
                })
    return out

class Mindbody:
    name="mindbody"
    def normalize(self,p):
        d=p.get("eventData") or {}
        eid=str(p.get("eventId") or "")
        cancelled=eid.endswith(".cancelled")
        client=" ".join(x for x in [d.get("clientFirstName",""),d.get("clientLastName","")] if x)
        staff=" ".join(x for x in [d.get("staffFirstName",""),d.get("staffLastName","")] if x)
        return Event(self.name,str(p.get("messageId") or digest(p)),str(d.get("appointmentId") or digest(p)[:16]),
                     "cancel" if cancelled else "upsert",d.get("startDateTime"),d.get("endDateTime"),
                     client,staff,"cancelled" if cancelled else str(d.get("status") or "scheduled").lower(),
                     str(p.get("transactionKey") or ""),p)
    def capability(self,configured=False):
        return {"provider":self.name,"webhook_ingress":True,"read_appointments":True,"write_appointments":True,
                "calendar_blocks":True,"live_configured":configured,
                "notes":"Appointment operations are capability-gated; live use still needs approved credentials and mapping."}

class Vagaro:
    name="vagaro"
    def normalize(self,p):
        d=p.get("data") or p.get("appointment") or p
        et=str(p.get("eventType") or p.get("type") or "appointment.modified").lower()
        cancelled="cancel" in et or str(d.get("status") or "").lower() in {"cancelled","canceled"}
        return Event(self.name,str(p.get("eventId") or p.get("id") or digest(p)),
                     str(d.get("appointmentId") or d.get("appointment_id") or d.get("id") or digest(p)[:16]),
                     "cancel" if cancelled else "upsert",
                     d.get("startDateTime") or d.get("start"), d.get("endDateTime") or d.get("end"),
                     str(d.get("customerName") or d.get("clientName") or ""),
                     str(d.get("employeeName") or d.get("staffName") or ""),
                     "cancelled" if cancelled else str(d.get("status") or "scheduled").lower(),"",p)
    def capability(self,configured=False):
        return {"provider":self.name,"webhook_ingress":True,"read_appointments":False,"write_appointments":False,
                "calendar_blocks":False,"live_configured":configured,
                "notes":"Webhook ingress is enabled; no undocumented appointment-write endpoint is assumed."}

class Google:
    name="google"
    def normalize(self,p):
        start=p.get("start") or {}; end=p.get("end") or {}
        blocked=p.get("slotbridgeBlock",False) or str(p.get("transparency") or "opaque")!="transparent"
        cancelled=str(p.get("status") or "").lower()=="cancelled"
        return Event(self.name,str(p.get("eventKey") or p.get("etag") or digest(p)),str(p.get("id") or digest(p)[:16]),
                     "cancel" if cancelled else ("block" if blocked else "upsert"),
                     start.get("dateTime") or start.get("date"),end.get("dateTime") or end.get("date"),
                     str(p.get("summary") or "Calendar block"),"",
                     "cancelled" if cancelled else ("blocked" if blocked else "scheduled"),
                     str(((p.get("extendedProperties") or {}).get("private") or {}).get("slotbridgeOrigin") or ""),p)
    def capability(self,configured=False):
        return {"provider":self.name,"webhook_ingress":True,"read_appointments":True,"write_appointments":True,
                "calendar_blocks":True,"live_configured":configured,
                "notes":"Demo mode simulates writes; a live connector can use Google Calendar OAuth."}

class Service:
    def __init__(self,db,configured=None):
        self.db=db
        self.adapters={"mindbody":Mindbody(),"vagaro":Vagaro(),"google":Google()}
        self.configured=configured or {}

    def ingest(self,provider,payload):
        a=self.adapters[provider]
        e=a.normalize(payload)
        if not self.db.record_webhook(provider,e.event_key,payload):
            return {"accepted":True,"deduplicated":True,"event_key":e.event_key}
        aid=self.db.upsert(e)
        n=self.reconcile()
        if provider in {"mindbody","vagaro"}:
            self.plan(aid,"google")
        return {"accepted":True,"deduplicated":False,"appointment_id":aid,"conflicts":n}

    def reconcile(self):
        items=detect_conflicts(self.db.list("appointments"))
        self.db.replace_conflicts(items)
        return len(items)

    def feasibility(self):
        providers=[a.capability(bool(self.configured.get(name))) for name,a in self.adapters.items()]
        blockers=[]
        for p in providers:
            if not p["live_configured"]: blockers.append(f"{p['provider']}: live credentials not configured.")
            if p["provider"]=="vagaro" and not p["write_appointments"]:
                blockers.append("vagaro: two-way appointment writes require a verified supported integration path.")
        return {"providers":providers,"blockers":blockers,
                "phase_1":[
                    "Verify API/webhook access for each business account.",
                    "Verify appointment create/update/cancel permissions.",
                    "Map staff, services, locations and time zones.",
                    "Define conflict ownership and cancellation propagation.",
                    "Define loop prevention and manual fallback behavior."
                ]}

    def plan(self,aid,target):
        a=self.db.get_appointment(aid)
        cap=self.adapters[target].capability(bool(self.configured.get(target)))
        op="delete" if a["status"] in {"cancelled","canceled"} else "upsert"
        status="pending" if cap["write_appointments"] else "unsupported"
        payload={"appointment_id":aid,"start_at":a["start_at"],"end_at":a["end_at"],
                 "summary":a["client_name"],"origin":f"slotbridge:{a['provider']}:{a['external_id']}"}
        jid=self.db.create_job(aid,a["provider"],target,op,status,payload)
        if status=="unsupported":
            self.db.dead_letter(jid,target,"Target connector does not expose appointment writes",payload)
        return jid
