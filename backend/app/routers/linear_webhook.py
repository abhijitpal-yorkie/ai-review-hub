import os, hmac, hashlib, json
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from app import linear_client
from app.agents.qa_generator import generate_test_cases
from app.agents.qa_validator import validate_test_cases
router = APIRouter()
@router.post("/webhooks/linear")
async def linear_webhook(request: Request, background: BackgroundTasks):
    raw = await request.body()
    secret = os.getenv("LINEAR_WEBHOOK_SECRET")
    sig = request.headers.get("Linear-Signature", "")
    if secret and sig:
        expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise HTTPException(401, "Invalid signature")
    try: payload = json.loads(raw)
    except Exception: raise HTTPException(400, "Invalid JSON")
    action = payload.get("action"); typ = payload.get("type")
    data = payload.get("data", {})
    if typ == "Issue" and action in ("create", "update"):
        background.add_task(_auto_generate, data)
    return {"ok": True, "received": f"{typ}.{action}"}
async def _auto_generate(issue_data: dict):
    try:
        iid = issue_data.get("id"); title = issue_data.get("title",""); desc = issue_data.get("description","")
        if not iid: return
        ticket = f"{title}\n\n{desc}"
        cases = generate_test_cases(ticket)
        val = validate_test_cases(cases, ticket)
        comment = f"### 🤖 Auto-generated Test Cases\n\n**Validation:** {val.get('overall_score','?')}/100 — {'PASS' if val.get('passed') else 'NEEDS WORK'}\n\n{val.get('recommendation','')}\n\n{cases}\n"
        linear_client.create_comment(iid, comment[:6000])
    except Exception as e:
        print(f"[auto_generate] {e}")
