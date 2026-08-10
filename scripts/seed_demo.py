from pathlib import Path
import json, os, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.core import DB, Service

db_path=os.getenv("SLOTBRIDGE_DB_PATH","data/slotbridge.db")
p=Path(db_path)
if p.exists(): p.unlink()
db=DB(db_path); svc=Service(db)

def load(n): return json.loads((ROOT/"examples"/n).read_text())

print(svc.ingest("mindbody",load("mindbody.json")))
print(svc.ingest("vagaro",load("vagaro.json")))
print(svc.ingest("google",load("google.json")))
print(svc.ingest("mindbody",load("mindbody.json")))  # duplicate
first=db.list("appointments")[-1]
print({"unsupported_job":svc.plan(first["id"],"vagaro")})
print({"appointments":len(db.list("appointments")),"conflicts":len(db.list("conflicts")),
       "sync_jobs":len(db.list("sync_jobs")),"dead_letters":len(db.list("dead_letters"))})
