import os, requests
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional
from app.config import load_settings, save_settings, apply_settings_to_env
from app import linear_client, audit
router = APIRouter()

class Profile(BaseModel):
    name: str = ""; role: str = ""; email: str = ""

class Providers(BaseModel):
    gemini: Optional[str] = None; groq: Optional[str] = None; cerebras: Optional[str] = None
    nvidia: Optional[str] = None; openrouter: Optional[str] = None

class LinearCfg(BaseModel):
    api_key: Optional[str] = None; webhook_secret: Optional[str] = None; auto_report: Optional[bool] = None

class Defaults(BaseModel):
    uat_url: Optional[str] = None; max_parallel_cases: Optional[int] = None

class SettingsIn(BaseModel):
    profile: Optional[Profile] = None
    providers: Optional[Providers] = None
    linear: Optional[LinearCfg] = None
    defaults: Optional[Defaults] = None

class TestPayload(BaseModel):
    key: Optional[str] = None      # test THIS value, not saved
    secret: Optional[str] = None

def _mask(v): return ("*" * 8 + v[-4:]) if v and len(v) > 4 else ("*" * len(v) if v else "")

@router.get("/settings")
def get_settings(request: Request):
    s = load_settings()
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost:8000"
    scheme = request.headers.get("x-forwarded-proto") or "http"
    return {
        "profile": s["profile"],
        "linear": {
            "api_key_masked": _mask(s["linear"].get("api_key","")),
            "webhook_secret_masked": _mask(s["linear"].get("webhook_secret","")),
            "auto_report": s["linear"].get("auto_report", True),
            "has_api_key": bool(s["linear"].get("api_key")),
            "has_webhook_secret": bool(s["linear"].get("webhook_secret")),
            "suggested_webhook_url": f"{scheme}://{host}/api/webhooks/linear",
        },
        "providers": {k: {"masked": _mask(v), "has_key": bool(v)} for k,v in s["providers"].items()},
        "defaults": s["defaults"],
    }

@router.post("/settings")
def update_settings(payload: SettingsIn):
    s = load_settings()
    changes = []
    if payload.profile and payload.profile.dict() != s["profile"]:
        s["profile"].update(payload.profile.dict()); changes.append("profile")
    if payload.defaults:
        s["defaults"].update({k:v for k,v in payload.defaults.dict().items() if v is not None})
        changes.append("defaults")
    if payload.linear:
        for k,v in payload.linear.dict().items():
            if v is not None and v != "":
                s["linear"][k] = v
        changes.append("linear")
    if payload.providers:
        for k,v in payload.providers.dict().items():
            if v is not None and v != "":
                s["providers"][k] = v
                changes.append(f"provider:{k}")
    save_settings(s)
    apply_settings_to_env()
    audit.log("Settings updated", category="settings", status="success",
              detail={"fields": changes})
    return {"ok": True}

@router.post("/settings/test/linear")
def test_linear(payload: TestPayload = TestPayload()):
    # If payload has a key, test THAT. Otherwise test saved.
    key = payload.key
    if not key:
        apply_settings_to_env()
        key = os.getenv("LINEAR_API_KEY")
    if not key or key.startswith("your_"):
        audit.log("Linear test skipped — no key", category="linear", status="warn")
        return {"ok": False, "error": "Enter a Linear API key first"}
    q = {"query": "{viewer{id name email}}"}
    try:
        r = requests.post("https://api.linear.app/graphql", json=q,
                          headers={"Authorization": key, "Content-Type": "application/json"},
                          timeout=15)
        if r.status_code == 401:
            audit.log("Linear test failed — 401", category="linear", status="error")
            return {"ok": False, "error": "Key rejected by Linear (401). Check it's copied fully."}
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            audit.log("Linear test failed — API errors", category="linear", status="error",
                      detail={"errors": str(data["errors"])[:200]})
            return {"ok": False, "error": str(data["errors"][0].get("message", "API error"))}
        viewer = data["data"]["viewer"]
        # Auto-save the tested key so it persists
        if payload.key:
            s = load_settings()
            s["linear"]["api_key"] = payload.key
            save_settings(s)
            apply_settings_to_env()
        audit.log("Linear test OK (key auto-saved)", category="linear", status="success",
                  detail={"viewer": viewer.get("name")})
        return {"ok": True, "viewer": viewer, "saved": bool(payload.key)}
    except Exception as e:
        audit.log("Linear test error", category="linear", status="error",
                  detail={"error": str(e)[:200]})
        return {"ok": False, "error": str(e)}

@router.post("/settings/test/{provider}")
def test_provider(provider: str, payload: TestPayload = TestPayload()):
    keys = {"gemini":"GEMINI_API_KEY","groq":"GROQ_API_KEY","cerebras":"CEREBRAS_API_KEY",
            "openrouter":"OPENROUTER_API_KEY"}
    env = keys.get(provider)
    if not env: return {"ok": False, "error": "Unknown provider"}

    key = payload.key
    if not key:
        apply_settings_to_env()
        key = os.getenv(env)
    if not key or key.startswith("your_"):
        audit.log(f"{provider} test skipped", category="provider", status="warn")
        return {"ok": False, "error": f"Enter a {provider} API key first"}

    try:
        if provider == "gemini":
            # Real test: hit generateContent with the actual model we use
            from app.free_llm_client import PROVIDERS
            model = PROVIDERS["gemini"]["models"]["flash-lite"]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            r = requests.post(url, json={"contents":[{"parts":[{"text":"ok"}]}],
                                          "generationConfig":{"maxOutputTokens":5}},
                              timeout=20)
            if r.status_code == 200:
                # Auto-save on success
                if payload.key:
                    s = load_settings(); s["providers"]["gemini"] = payload.key
                    save_settings(s); apply_settings_to_env()
                audit.log("gemini test OK (key auto-saved)", category="provider", status="success",
                          detail={"model": model})
                return {"ok": True, "status": 200, "model": model}
            err = r.json().get("error", {}).get("message", r.text[:200]) if r.headers.get("content-type","").startswith("application/json") else r.text[:200]
            audit.log("gemini test failed", category="provider", status="error",
                      detail={"http": r.status_code, "msg": err[:150]})
            return {"ok": False, "status": r.status_code, "error": err}
        else:
            urls = {
                "groq": "https://api.groq.com/openai/v1/models",
                "cerebras": "https://api.cerebras.ai/v1/models",
                "openrouter": "https://openrouter.ai/api/v1/models",
            }
            r = requests.get(urls[provider], headers={"Authorization": f"Bearer {key}"}, timeout=15)
            ok = r.status_code == 200
            if ok and payload.key:
                s = load_settings(); s["providers"][provider] = payload.key
                save_settings(s); apply_settings_to_env()
            audit.log(f"{provider} test {'OK (saved)' if ok and payload.key else 'OK' if ok else 'failed'}",
                      category="provider", status="success" if ok else "error",
                      detail={"provider": provider, "http": r.status_code})
            return {"ok": ok, "status": r.status_code, "saved": bool(ok and payload.key),
                    "error": None if ok else f"HTTP {r.status_code}"}
    except Exception as e:
        audit.log(f"{provider} test error", category="provider", status="error",
                  detail={"error": str(e)[:200]})
        return {"ok": False, "error": str(e)}
