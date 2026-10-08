"""
Append-only JSONL report store. One file per report type.
Every UX audit and every ticket test run is recorded here with full
artifacts (audit report, mockup HTML, execution results, screenshots).
"""
import json, os, uuid, threading
from datetime import datetime, timezone

BASE = os.path.join(os.path.dirname(__file__), "..", "data", "history")
os.makedirs(BASE, exist_ok=True)

_lock = threading.Lock()

def _path(kind: str) -> str:
    return os.path.join(BASE, f"{kind}.jsonl")

def save(kind: str, record: dict) -> dict:
    """Append a record with auto-generated id + timestamp."""
    if "id" not in record:
        record["id"] = uuid.uuid4().hex[:12]
    if "ts" not in record:
        record["ts"] = datetime.now(timezone.utc).isoformat()
    record["kind"] = kind
    with _lock:
        with open(_path(kind), "a") as f:
            f.write(json.dumps(record) + "\n")
    return record

def list_recent(kind: str, limit: int = 50) -> list:
    p = _path(kind)
    if not os.path.exists(p): return []
    lines = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line: lines.append(line)
    out = []
    for line in lines[-limit:]:
        try: out.append(json.loads(line))
        except Exception: pass
    return out[::-1]  # newest first

def get(kind: str, record_id: str) -> dict:
    for r in list_recent(kind, limit=10000):
        if r.get("id") == record_id: return r
    return None

def delete(kind: str, record_id: str) -> bool:
    p = _path(kind)
    if not os.path.exists(p): return False
    kept = []
    found = False
    with _lock:
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try: r = json.loads(line)
                except Exception:
                    kept.append(line); continue
                if r.get("id") == record_id:
                    found = True
                    continue
                kept.append(line)
        with open(p, "w") as f:
            for k in kept: f.write(k + "\n")
    return found

def stats(kind: str) -> dict:
    recs = list_recent(kind, limit=10000)
    return {
        "total": len(recs),
        "last_ts": recs[0]["ts"] if recs else None,
        "by_status": _count_by(recs, "status"),
    }

def _count_by(recs, key):
    out = {}
    for r in recs:
        v = r.get(key, "unknown")
        out[v] = out.get(v, 0) + 1
    return out
