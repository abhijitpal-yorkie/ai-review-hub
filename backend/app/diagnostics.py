"""
One-shot diagnostic: tests Linear API, Stytch/Lexful auth, and Playwright.
Every output line is sanitized — safe to paste into chat.
"""
import os, sys, json, argparse, requests
from app.security import sanitize, masked, has_real
from app import lexful_auth

LINEAR_API = "https://api.linear.app/graphql"

def _gql(query, variables=None, key=None):
    r = requests.post(LINEAR_API,
        json={"query": query, "variables": variables or {}},
        headers={"Authorization": key, "Content-Type": "application/json"},
        timeout=20)
    return r.status_code, r.text

def test_linear():
    print("════════════════════════════════════════════════")
    print("  LINEAR API DIAGNOSTIC")
    print("════════════════════════════════════════════════")
    print()

    key = os.getenv("LINEAR_API_KEY")
    if not has_real(key):
        # try settings.json
        try:
            s = json.load(open(os.path.expanduser("~/ai-review-hub/backend/data/settings.json")))
            key = s.get("linear", {}).get("api_key", "")
        except Exception:
            pass
    if not has_real(key):
        print("  ✗ Linear API key not set (checked env + settings.json)")
        print("    Add it in Settings → Linear connection, or export LINEAR_API_KEY")
        return False

    print(f"  Key: {masked(key)}")
    print()

    # ── Test 1: viewer (auth check) ──
    print("  ── Test 1: viewer query (auth check) ──")
    code, body = _gql("{viewer{id name email}}", key=key)
    print(f"    HTTP {code}")
    if code == 200:
        try:
            d = json.loads(body)
            if "errors" in d:
                print(f"    GraphQL errors: {sanitize(str(d['errors'])[:200])}")
            else:
                v = d["data"]["viewer"]
                print(f"    ✓ connected as {v.get('name')} ({v.get('email')})")
        except Exception:
            print(f"    raw: {sanitize(body[:200])}")
    else:
        print(f"    body: {sanitize(body[:250])}")
    print()

    # ── Test 2: incremental field test ──
    print("  ── Test 2: incremental field test ──")
    variations = [
        ("minimal",           "{issues(first:1){nodes{id identifier title}}}"),
        ("+ description",     "{issues(first:1){nodes{id identifier title description}}}"),
        ("+ state",           "{issues(first:1){nodes{id identifier title state{name}}}}"),
        ("+ priority",        "{issues(first:1){nodes{id identifier title priority}}}"),
        ("+ priorityLabel",   "{issues(first:1){nodes{id identifier title priorityLabel}}}"),
        ("+ assignee",        "{issues(first:1){nodes{id identifier title assignee{name}}}}"),
        ("+ team",            "{issues(first:1){nodes{id identifier title team{name}}}}"),
        ("+ url",             "{issues(first:1){nodes{id identifier title url}}}"),
        ("+ createdAt",       "{issues(first:1){nodes{id identifier title createdAt}}}"),
        ("+ updatedAt",       "{issues(first:1){nodes{id identifier title updatedAt}}}"),
        ("+ orderBy",         "{issues(first:1, orderBy:updatedAt){nodes{id identifier title}}}"),
        ("full (current)",    "{issues(first:1, orderBy:updatedAt){nodes{id identifier title description state{name} priority priorityLabel assignee{name} team{name} url createdAt updatedAt}}}"),
    ]
    failing_field = None
    for label, q in variations:
        code, body = _gql(q, key=key)
        if code == 200:
            try:
                d = json.loads(body)
                if "errors" in d:
                    err = d["errors"][0].get("message", "")[:100]
                    print(f"    ✗ {label:20} → GraphQL error: {sanitize(err)}")
                    if failing_field is None and label not in ("minimal",):
                        failing_field = label
                else:
                    print(f"    ✓ {label:20} → OK")
            except Exception:
                print(f"    ? {label:20} → parse error")
        else:
            print(f"    ✗ {label:20} → HTTP {code}: {sanitize(body[:120])}")
            if failing_field is None and label != "minimal":
                failing_field = label
    print()

    if failing_field:
        print(f"  ⚠ First field that fails: {failing_field}")
        print(f"    Fix: remove or replace the field in linear_client.py list_issues query")
    else:
        print("  ✓ All field variations passed — Linear API is healthy")
    print()
    return failing_field is None

def test_stytch():
    print("════════════════════════════════════════════════")
    print("  STYTCH / LEXFUL AUTH DIAGNOSTIC")
    print("════════════════════════════════════════════════")
    print()
    cfg = lexful_auth.load_cfg()
    print(f"  API URL:  {cfg['api_url']}")
    print(f"  App URL:  {cfg['app_url']}")
    print(f"  Domain:   {cfg['domain']}")
    print(f"  Org ID:   {masked(cfg['org_id'])}")
    print()

    any_passed = False
    for persona, p in cfg["personas"].items():
        env_var = p["password_env"]
        pw = os.getenv(env_var)
        print(f"  ── Persona: {persona} ({p['email']}) ──")
        if not has_real(pw):
            print(f"    ⚠ password not set — export {env_var}='...' first")
            print()
            continue
        try:
            cookies, _ = lexful_auth.get_cookies(persona)
            print(f"    ✓ authenticated — cookies: {', '.join(cookies.keys())}")
            any_passed = True

            # Playwright injection test
            try:
                result = lexful_auth.run_persona(persona, headless=True,
                                                  screenshot=f"/tmp/lexful-{persona}-diag.png")
                print(f"    ✓ Playwright injection works — landed at {result['url']}")
            except Exception as e:
                print(f"    ✗ Playwright: {sanitize(str(e))}")
        except Exception as e:
            print(f"    ✗ Auth failed: {sanitize(str(e))}")
        print()

    if not any_passed:
        print("  ⚠ No personas were testable — set at least one password env var:")
        print("     export LEXFUL_ADMIN_PASSWORD='...'")
        print("     export LEXFUL_SUPPORT_PASSWORD='...'")
        print("     export LEXFUL_VIEWER_PASSWORD='...'")
        print()
    return any_passed

def test_backend():
    print("════════════════════════════════════════════════")
    print("  BACKEND HEALTH")
    print("════════════════════════════════════════════════")
    print()
    try:
        r = requests.get("http://localhost:8000/api/health", timeout=5)
        print(f"  ✓ backend: {r.json()}")
    except Exception as e:
        print(f"  ✗ backend down: {sanitize(str(e))}")
    try:
        r = requests.get("http://localhost:8000/api/settings", timeout=5)
        d = r.json()
        print(f"  ✓ linear key: {'SET' if d['linear']['has_api_key'] else 'not set'}")
        print(f"  ✓ webhook URL: {d['linear']['suggested_webhook_url']}")
        for k, v in d['providers'].items():
            print(f"  ✓ {k}: {'SET' if v['has_key'] else '—'}")
    except Exception as e:
        print(f"  ✗ settings: {sanitize(str(e))}")
    print()

def cli():
    ap = argparse.ArgumentParser(description="AI Review Hub diagnostics")
    ap.add_argument("what", nargs="?", default="all",
                    choices=["all", "linear", "stytch", "backend"])
    args = ap.parse_args()
    if args.what in ("all", "backend"): test_backend()
    if args.what in ("all", "linear"):  test_linear()
    if args.what in ("all", "stytch"):  test_stytch()
    print("════════════════════════════════════════════════")
    print("  DIAGNOSTIC COMPLETE")
    print("════════════════════════════════════════════════")

if __name__ == "__main__":
    cli()
