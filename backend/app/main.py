from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import base64, os

from app.config import apply_settings_to_env
from app.agents.ux_auditor import audit_ux
from app.agents.mockup_builder import build_mockup
from app.utils import capture_screenshot, run_async
from app.routers import tickets, skills, linear_webhook
from app.routers import settings as settings_router
from app.routers import audit as audit_router
from app.routers import personas as personas_router
from app.routers import history_api as history_router
from app.routers import crawl as crawl_router

app = FastAPI(title="AI Review Hub")


@app.on_event("startup")
def _startup():
    apply_settings_to_env()
    from app import audit
    audit.log("Backend started", category="system", status="success")


app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
app.include_router(settings_router.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(linear_webhook.router, prefix="/api")
app.include_router(audit_router.router, prefix="/api")
app.include_router(personas_router.router, prefix="/api")
app.include_router(history_router.router, prefix="/api")
app.include_router(crawl_router.router, prefix="/api")


class UXRequest(BaseModel):
    url: Optional[str] = None
    image_base64: Optional[str] = None
    generate_mockup: bool = True
    persona: Optional[str] = None


@app.post("/api/ux/analyze")
def ux_pipeline(request: UXRequest):
    debug = {"url": request.url, "persona_requested": request.persona}

    try:
        if request.image_base64:
            img = base64.b64decode(request.image_base64.split(",")[1])
            final_url = None
        elif request.url:
            cookies = None
            persona_used = None
            auth_error = None

            # Try to authenticate via Lexful persona
            try:
                from app import lexful_auth, audit
                p = request.persona or "admin"
                debug["attempting_persona"] = p
                cookies = lexful_auth.detect_and_get_cookies(request.url, persona=p)
                debug["cookies_count"] = len(cookies) if cookies else 0
                if cookies:
                    persona_used = p
                    audit.log(f"UX audit authenticated as {p}",
                              category="execution", status="success",
                              target=request.url, detail={"persona": p})
                    debug["auth"] = "ok"
                else:
                    debug["auth"] = "not_lexful_url"
            except Exception as e:
                from app.security import sanitize
                auth_error = sanitize(str(e))[:300]
                debug["auth"] = "failed"
                debug["auth_error"] = auth_error
                try:
                    from app import audit
                    audit.log("UX auth failed", category="execution",
                              status="error", detail={"error": auth_error})
                except Exception:
                    pass

            img, final_url = run_async(
                capture_screenshot(request.url, cookies=cookies))
            debug["final_url"] = final_url
            debug["redirected_to_login"] = "/login" in (final_url or "")
        else:
            raise HTTPException(400, "Provide URL or image.")

        # Screenshot too small usually means blank/login page
        debug["screenshot_bytes"] = len(img)

        audit_report = audit_ux(img)
        out = {
            "audit_report": audit_report,
            "status": "success",
            "final_url": final_url,
            "debug": debug,
        }
        if "persona_used" in dir() and persona_used:
            out["persona_used"] = persona_used

        if request.generate_mockup:
            out["mockup_html"] = build_mockup(img, audit_report)

        try:
            from app import history
            history.save("ux", {
                "url": request.url or "(uploaded image)",
                "final_url": final_url,
                "persona": out.get("persona_used"),
                "status": "success",
                "audit_report": audit_report,
                "mockup_html": out.get("mockup_html"),
            })
        except Exception as e:
            from app.security import sanitize
            print(f"[history] UX save failed: {sanitize(str(e))}")

        return out
    except HTTPException:
        raise
    except Exception as e:
        from app.security import sanitize
        return {"status": "error", "detail": sanitize(str(e))[:300], "debug": debug}


@app.get("/api/health")
def health():
    return {"status": "ok", "agents": 5,
            "linear": bool(os.getenv("LINEAR_API_KEY"))}
