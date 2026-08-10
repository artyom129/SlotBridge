from app.core import DB, Service, detect_conflicts

def test_overlap():
    rows=[
      {"id":1,"provider":"mindbody","external_id":"a","status":"scheduled","start_at":"2026-01-01T10:00:00+00:00","end_at":"2026-01-01T11:00:00+00:00"},
      {"id":2,"provider":"vagaro","external_id":"b","status":"scheduled","start_at":"2026-01-01T10:30:00+00:00","end_at":"2026-01-01T11:30:00+00:00"},
    ]
    x=detect_conflicts(rows)
    assert len(x)==1 and x[0]["severity"]=="critical"

def test_idempotency(tmp_path):
    db=DB(str(tmp_path/"t.db")); svc=Service(db)
    p={"messageId":"m1","eventId":"appointmentBooking.created",
       "eventData":{"appointmentId":1,"startDateTime":"2026-01-01T10:00:00+00:00","endDateTime":"2026-01-01T11:00:00+00:00"}}
    assert svc.ingest("mindbody",p)["deduplicated"] is False
    assert svc.ingest("mindbody",p)["deduplicated"] is True
    assert len(db.list("appointments"))==1

def test_vagaro_outbound_is_capability_blocked(tmp_path):
    db=DB(str(tmp_path/"t.db")); svc=Service(db)
    p={"messageId":"m2","eventId":"appointmentBooking.created",
       "eventData":{"appointmentId":2,"startDateTime":"2026-01-01T10:00:00+00:00","endDateTime":"2026-01-01T11:00:00+00:00"}}
    aid=svc.ingest("mindbody",p)["appointment_id"]
    jid=svc.plan(aid,"vagaro")
    jobs=db.list("sync_jobs")
    assert [j for j in jobs if j["id"]==jid][0]["status"]=="unsupported"
    assert len(db.list("dead_letters"))==1
