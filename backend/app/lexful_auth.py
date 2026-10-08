"""
Lexful UAT Stytch auth + Playwright cookie injection.
Loads .env.lexful at import so passwords are always available.
"""
import os, sys, json, argparse
from pathlib import Path
import requests

# ── Load .env.lexful once at import ──
_creds = Path(__file__).parent.parent / ".env.lexful"
if _creds.exists():
    for line in _creds.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)

CFG_PATH = Path(__file__).parent.parent / "data" / "lexful_personas.json"

DEFAULT_CFG = {
    "api_url": "https://api.uat.lexful.net",
    "app_url": "https://e2e-test.uat.lexful.net/docs/assets",
    "domain": ".lexful.net",
    "org_id": "organization-live-2928086d-1015-4fc0-a3eb-898cade37abd",
    "personas": {
        "admin":   {"email": "e2e-test+admin@lexful.ai",   "password_env": "LEXFUL_ADMIN_PASSWORD"},
        "support": {"email": "e2e-test+support@lexful.ai", "password_env": "LEXFUL_SUPPORT_PASSWORD"},
        "viewer":  {"email": "e2e-test+viewer@lexful.ai",  "password_env": "LEXFUL_VIEWER_PASSWORD"},
    },
}


def load_cfg():
    if not CFG_PATH.exists():
        CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CFG_PATH.write_text(json.dumps(DEFAULT_CFG, indent=2))
        return DEFAULT_CFG
    return {**DEFAULT_CFG, **json.loads(CFG_PATH.read_text())}


def get_cookies(persona: str):
    cfg = load_cfg()
    if persona not in cfg["personas"]:
        raise ValueError(f"Unknown persona '{persona}'. Options: {list(cfg['personas'].keys())}")
    p = cfg["personas"][persona]
    password = os.getenv(p["password_env"])
    if not password or password.startswith("your_"):
        raise RuntimeError(
            f"{p['password_env']} is not set. "
            f"Run: cd ~/ai-review-hub/backend && source venv/bin/activate && python3 setup_creds.py"
        )

    url = cfg["api_url"].rstrip("/") + "/auth/password"
    r = requests.post(url, json={
        "account_external_id": cfg["org_id"],
        "email": p["email"],
        "password": password,
    }, timeout=20)

    if r.status_code not in (200, 204):
        raise RuntimeError(f"Auth HTTP {r.status_code}: {r.text[:200]}")
    cookies = r.cookies.get_dict()
    if not cookies:
        raise RuntimeError("Auth succeeded but no cookies returned")
    return cookies, cfg


def playwright_cookies(cookies: dict, app_url: str):
    """
    Return Playwright cookie dicts. Uses url= form (not domain=) — Playwright
    matches url-based cookies more reliably across subdomains.
    """
    from urllib.parse import urlparse
    host = urlparse(app_url).hostname or "e2e-test.uat.lexful.net"
    # Extract root domain (last two labels)
    parts = host.split(".")
    root = ".".join(parts[-2:])  # e.g. lexful.net
    return [
        {
            "name": n, "value": v,
            "domain": f".{root}", "path": "/",
            "httpOnly": True, "secure": True, "sameSite": "Lax",
        }
        for n, v in cookies.items()
    ]


def detect_and_get_cookies(url: str, persona: str = "admin"):
    """Return playwright cookies if URL is on our configured root domain."""
    if not url:
        return None
    cfg = load_cfg()
    root = cfg["domain"].lstrip(".")
    if root not in url:
        return None
    cookies, _ = get_cookies(persona)
    return playwright_cookies(cookies, url)


def run_persona(persona: str, url=None, headless=False, screenshot=None):
    cookies, cfg = get_cookies(persona)
    target = url or cfg["app_url"]
    print(f"  ✓ authenticated as {persona} ({cfg['personas'][persona]['email']})")
    print(f"  ✓ got cookies: {', '.join(cookies.keys())}")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_cookies(playwright_cookies(cookies, target))
        page = ctx.new_page()
        page.goto(target, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
        final_url = page.url
        shot = screenshot or f"/tmp/lexful-{persona}.png"
        page.screenshot(path=shot)
        if "/login" in final_url:
            browser.close()
            raise RuntimeError(f"Redirected to login: {final_url}. Screenshot: {shot}")
        print(f"  ✓ landed at {final_url}")
        print(f"  ✓ screenshot: {shot}")
        if not headless:
            page.wait_for_timeout(3000)
        browser.close()
    return {"persona": persona, "url": final_url, "screenshot": shot}


def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True, choices=["admin", "support", "viewer"])
    ap.add_argument("--url", default=None)
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--screenshot", default=None)
    args = ap.parse_args()
    try:
        run_persona(args.persona, args.url, args.headless, args.screenshot)
    except Exception as e:
        print(f"  ✗ {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
