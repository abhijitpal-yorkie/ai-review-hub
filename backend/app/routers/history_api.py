from fastapi import APIRouter, HTTPException, Query
from app import history

router = APIRouter()

@router.get("/history/ux")
def list_ux(limit: int = Query(50, ge=1, le=500)):
    return {"records": history.list_recent("ux", limit=limit),
            "stats": history.stats("ux")}

@router.get("/history/tickets")
def list_tickets(limit: int = Query(50, ge=1, le=500)):
    return {"records": history.list_recent("tickets", limit=limit),
            "stats": history.stats("tickets")}

@router.get("/history/{kind}/{record_id}")
def get_record(kind: str, record_id: str):
    if kind not in ("ux", "tickets"):
        raise HTTPException(400, "kind must be 'ux' or 'tickets'")
    r = history.get(kind, record_id)
    if not r: raise HTTPException(404, "Record not found")
    return r

@router.delete("/history/{kind}/{record_id}")
def delete_record(kind: str, record_id: str):
    if kind not in ("ux", "tickets"):
        raise HTTPException(400, "kind must be 'ux' or 'tickets'")
    ok = history.delete(kind, record_id)
    if not ok: raise HTTPException(404, "Not found")
    return {"ok": True}
