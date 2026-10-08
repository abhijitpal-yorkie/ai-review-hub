from fastapi import APIRouter, Query
from app import audit
router = APIRouter()

@router.get("/audit")
def get_audit(limit: int = Query(200, ge=1, le=1000),
              category: str = None, status: str = None):
    return {"events": audit.tail(limit=limit, category=category, status=status),
            "stats": audit.stats()}

@router.delete("/audit")
def clear_audit():
    import os
    from app.audit import AUDIT_PATH
    if os.path.exists(AUDIT_PATH): os.remove(AUDIT_PATH)
    audit.log("Audit log cleared", category="system", status="warn")
    return {"ok": True}
