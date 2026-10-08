from fastapi import APIRouter
from pydantic import BaseModel
from app import lexful_auth, audit
from app.security import sanitize, has_real

router = APIRouter()


@router.get("/personas")
def list_personas():
    import os
    cfg = lexful_auth.load_cfg()
    out = []
    for name, p in cfg["personas"].items():
        env_var = p["password_env"]
        has_pw = has_real(os.getenv(env_var, ""))
        out.append({
            "name": name,
            "email": p["email"],
            "env_var": env_var,
            "password_set": has_pw,
        })
    return {
        "personas": out,
        "api_url": cfg["api_url"],
        "app_url": cfg["app_url"],
        "domain": cfg["domain"],
    }


class TestPersonaRequest(BaseModel):
    persona: str


@router.post("/personas/test")
def test_persona(req: TestPersonaRequest):
    try:
        result = lexful_auth.run_persona(
            req.persona, headless=True,
            screenshot=f"/tmp/lexful-{req.persona}-test.png",
        )
        audit.log(f"Persona {req.persona} verified",
                  category="execution", status="success",
                  detail={"url": result["url"]})
        return {"ok": True, "persona": req.persona,
                "url": result["url"], "screenshot": result["screenshot"]}
    except Exception as e:
        msg = sanitize(str(e))[:300]
        audit.log(f"Persona {req.persona} test failed",
                  category="execution", status="error",
                  detail={"error": msg})
        return {"ok": False, "persona": req.persona, "error": msg}
