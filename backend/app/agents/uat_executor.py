import os, tempfile, subprocess, re, json, textwrap, traceback
from app.free_llm_client import call_llm
from app.config import load_config
from app import lexful_auth
from app.security import sanitize
from app.logger import get_logger

log = get_logger("uat_executor")


TEMPLATE = '''import os, json, sys, traceback
from playwright.sync_api import sync_playwright

def run_test(page):
{body}

def main():
    headless = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
    slow_mo = int(os.getenv("PLAYWRIGHT_SLOW_MO", "300"))
    cookies = json.loads(os.getenv("PLAYWRIGHT_COOKIES_JSON", "[]"))
    base_url = os.getenv("BASE_URL", "").rstrip("/")

    result = {{"status": "ERROR", "reason": "did not run", "boxes": []}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=slow_mo)
        try:
            ctx = browser.new_context(viewport={{"width": 1440, "height": 900}})
            if cookies:
                ctx.add_cookies(cookies)
            page = ctx.new_page()
            page.goto(base_url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1500)
            try:
                run_test(page)
                result = {{"status": "PASS", "reason": "ok", "boxes": []}}
            except AssertionError as e:
                result = {{"status": "FAIL", "reason": "Assertion: " + str(e)[:400], "boxes": []}}
            except Exception as e:
                tb = traceback.format_exc()
                result = {{"status": "FAIL", "reason": type(e).__name__ + ": " + str(e)[:400], "boxes": [], "trace": tb[-800:]}}
            try: page.screenshot(path="/tmp/uat-last-step.png")
            except Exception: pass
            if not headless: page.wait_for_timeout(3000)
        except Exception as e:
            tb = traceback.format_exc()
            result = {{"status": "ERROR", "reason": type(e).__name__ + ": " + str(e)[:400], "boxes": [], "trace": tb[-800:]}}
        finally:
            try: browser.close()
            except Exception: pass
    sys.stdout.write("__RESULT__" + json.dumps(result) + "\\n")
    sys.stdout.flush()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        tb = traceback.format_exc()
        sys.stdout.write("__RESULT__" + json.dumps({{"status":"ERROR","reason":str(e)[:400],"boxes":[],"trace":tb[-800:]}}) + "\\n")
'''


def _skill(name):
    p = os.path.join(os.path.dirname(__file__), "..", "skills", name)
    with open(p) as f: return f.read().split("---")[2].strip()


def _clean_body(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(python)?", "", raw).rstrip("`").strip()
    lines = []
    for line in raw.splitlines():
        s = line.strip()
        if re.match(r"^(import|from)\s", s): continue
        if "sync_playwright" in s: continue
        if re.match(r"^(browser|ctx|context|p)\s*=", s): continue
        if s.startswith("def run_test"): continue
        if s.startswith("def main"): continue
        if s == "browser.close()": continue
        lines.append(line)
    body = "\n".join(lines).rstrip()
    if body:
        body = textwrap.dedent(body)
        body = "\n".join(("    " + ln) if ln.strip() else "" for ln in body.splitlines())
    # syntax check
    test_src = "def run_test(page):\n" + (body or "    pass") + "\n"
    try:
        compile(test_src, "<test>", "exec")
    except SyntaxError as e:
        log.error("LLM body has SYNTAX ERROR: %s at line %s", e.msg, e.lineno)
        return f"    raise AssertionError('LLM generated invalid code: {e.msg} (line {e.lineno})')"
    return body or "    pass"


def execute_test_case(test_case: dict, base_url: str, persona: str = "admin") -> dict:
    sys_prompt = _skill("uat_exec_skill.md")
    prompt = (
        f"The runner has already launched Chromium, injected cookies, "
        f"and navigated to {base_url}.\n\n"
        f"Test case: {json.dumps(test_case)}\n\n"
        f"Write ONLY the body of run_test(page). 4-space indent. "
        f"No imports, no browser launch, no page.goto. Use assert after each step."
    )

    log.info("════════════════════════════════════════")
    log.info("TEST CASE %s", test_case.get("id"))
    log.info("════════════════════════════════════════")
    log.info("requesting body from LLM...")

    try:
        raw, prov, model = call_llm("uat_execute", sys_prompt, prompt, max_tokens=1200)
        log.info("LLM responded: %s/%s (%d chars)", prov, model, len(raw))
    except Exception as e:
        log.error("LLM call failed: %s", sanitize(str(e))[:200])
        return {"test_id": test_case.get("id", "?"), "status": "ERROR",
                "reason": f"LLM unavailable: {sanitize(str(e))[:150]}", "boxes": []}

    log.info("── RAW LLM OUTPUT (first 500 chars) ──")
    log.info("%s", raw[:500])

    body = _clean_body(raw)
    log.info("── CLEANED BODY ──")
    for ln in body.splitlines()[:40]:
        log.info("  %s", ln[:160])

    script = TEMPLATE.format(body=body)

    cookie_json = "[]"
    try:
        cookies = lexful_auth.detect_and_get_cookies(base_url, persona=persona)
        if cookies:
            cookie_json = json.dumps(cookies)
            log.info("injected %d cookies", len(cookies))
    except Exception as e:
        log.warning("cookie fetch failed: %s", sanitize(str(e))[:150])

    headless = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script); path = f.name

    log.info("running Playwright (headless=%s)", headless)
    try:
        env = {
            **os.environ,
            "BASE_URL": base_url,
            "PLAYWRIGHT_COOKIES_JSON": cookie_json,
            "PLAYWRIGHT_HEADLESS": "true" if headless else "false",
            "PLAYWRIGHT_SLOW_MO": "300" if not headless else "0",
        }
        r = subprocess.run(["python3", path], capture_output=True, text=True,
                           timeout=180, env=env)

        log.info("── PLAYWRIGHT STDOUT (%d chars) ──", len(r.stdout))
        for ln in r.stdout.splitlines()[-25:]:
            log.info("  OUT | %s", ln[:200])

        if r.stderr.strip():
            log.info("── PLAYWRIGHT STDERR (%d chars) ──", len(r.stderr))
            for ln in r.stderr.splitlines()[-25:]:
                log.info("  ERR | %s", ln[:200])

        # Find __RESULT__ marker
        result = None
        for line in reversed(r.stdout.splitlines()):
            if "__RESULT__" in line:
                try:
                    result = json.loads(line.split("__RESULT__", 1)[1])
                    break
                except Exception as e:
                    log.error("bad JSON after __RESULT__: %s", e)
                    continue

        if result is None:
            # No marker — script never got to main()
            reason = "Script crashed before main(). "
            if r.stderr.strip():
                reason += f"Python error: {r.stderr.strip().splitlines()[-1][:200]}"
            elif r.stdout.strip():
                reason += f"Output: {r.stdout.strip()[-200:]}"
            else:
                reason += "No output at all."
            result = {"status": "ERROR", "reason": reason, "boxes": []}

        log.info("═══ RESULT: %s ═══", result.get("status"))
        log.info("REASON: %s", result.get("reason", "")[:300])
        if result.get("trace"):
            for ln in result["trace"].splitlines():
                log.info("  TRACE | %s", ln[:200])

        return {
            "test_id": test_case.get("id", "?"),
            "status": result.get("status", "ERROR"),
            "reason": sanitize(result.get("reason", ""))[:500],
            "boxes": result.get("boxes", []),
        }
    except subprocess.TimeoutExpired:
        return {"test_id": test_case.get("id", "?"), "status": "TIMEOUT",
                "reason": "Script exceeded 180s", "boxes": []}
    finally:
        try: os.unlink(path)
        except Exception: pass
