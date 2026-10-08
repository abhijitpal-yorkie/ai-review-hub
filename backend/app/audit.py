import json, os, threading
from datetime import datetime, timezone

AUDIT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "audit.jsonl")
_lock = threading.Lock()
_MAX_BYTES = 5_000_000  # rotate at 5MB

def log(event: str, category: str = "system", status: str = "info",
        actor: str = "user", target: str = "", detail: dict = None):
    """Append one event to the audit log (JSONL — one JSON per line)."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "category": category,
        "status": status,
        "actor": actor,
        "target": target,
        "detail": detail or {},
    }
    with _lock:
        # rotate if too big
        try:
            if os.path.exists(AUDIT_PATH) and os.path.getsize(AUDIT_PATH) > _MAX_BYTES:
                os.rename(AUDIT_PATH, AUDIT_PATH + ".1")
        except Exception:
            pass
        with open(AUDIT_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    return entry

def tail(limit: int = 200, category: str = None, status: str = None) -> list:
    if not os.path.exists(AUDIT_PATH):
        return []
    out = []
    with open(AUDIT_PATH) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if category and e.get("category") != category: continue
            if status and e.get("status") != status: continue
            out.append(e)
    return out[-limit:][::-1]  # newest first

def stats() -> dict:
    events = tail(limit=10000)
    by_cat = {}
    by_status = {"info": 0, "success": 0, "error": 0, "warn": 0}
    for e in events:
        c = e.get("category", "system")
        by_cat[c] = by_cat.get(c, 0) + 1
        s = e.get("status", "info")
        if s in by_status: by_status[s] += 1
    return {"total": len(events), "by_category": by_cat, "by_status": by_status}
