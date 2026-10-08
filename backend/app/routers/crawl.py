from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import base64
from app.crawler import crawl_sync
from app.agents.ux_auditor import audit_ux
from app.agents.mockup_builder import build_mockup
from app import history, audit
from app.logger import step, get_logger
from app.security import sanitize

log = get_logger("crawl")
router = APIRouter()


class CrawlRequest(BaseModel):
    url: str
    persona: Optional[str] = None
    max_pages: int = 15
    per_page_audit: bool = False


@router.post("/ux/crawl")
def crawl(req: CrawlRequest):
    step(f"Crawl request: {req.url} (max {req.max_pages} pages)")
    cookies = None
    persona_used = None

    # Auth if Lexful
    try:
        from app import lexful_auth
        cookies = lexful_auth.detect_and_get_cookies(req.url, persona=req.persona or "admin")
        if cookies:
            persona_used = req.persona or "admin"
            log.info("authenticated as %s (%d cookies)", persona_used, len(cookies))
    except Exception as e:
        log.warning("auth skipped: %s", sanitize(str(e))[:120])

    # Crawl
    try:
        results = crawl_sync(req.url, cookies=cookies, max_pages=req.max_pages)
    except Exception as e:
        raise HTTPException(500, f"Crawl failed: {sanitize(str(e))[:300]}")

    log.info("crawled %d pages", len(results))

    # Per-page audit
    pages = []
    for r in results:
        entry = {
            "url": r["url"],
            "final_url": r["final_url"],
            "links_found": r["links_found"],
            "error": r["error"],
            "screenshot_b64": None,
            "audit_report": None,
            "mockup_html": None,
        }
        if r.get("png_bytes"):
            entry["screenshot_b64"] = base64.b64encode(r["png_bytes"]).decode()
            if req.per_page_audit and not r["error"]:
                try:
                    step(f"Auditing {r['url']}")
                    import time
                    last = ""
                    for attempt in range(3):
                        if attempt > 0: time.sleep(15)
                        last = audit_ux(r["png_bytes"])
                        if len(last) >= 500: break
                        log.warning("attempt %d: short audit (%d chars), retrying", attempt+1, len(last))
                    entry["audit_report"] = last
                    entry["mockup_html"] = build_mockup(r["png_bytes"], last)
                except Exception as e:
                    entry["audit_report"] = f"Audit failed: {sanitize(str(e))[:200]}"
                    log.error("audit fail: %s", sanitize(str(e))[:150])
        pages.append(entry)

    # Aggregate score
    scores = []
    for p in pages:
        rep = p.get("audit_report") or ""
        for line in rep.splitlines():
            if "Overall:" in line and "/25" in line:
                try: scores.append(int(line.split("Overall:")[1].split("/")[0].strip().replace("*","")))
                except Exception: pass
    avg = round(sum(scores) / len(scores), 1) if scores else None

    out = {
        "start_url": req.url,
        "persona_used": persona_used,
        "pages_crawled": len(pages),
        "avg_score": avg,
        "pages": pages,
        "status": "success",
    }

    try:
        history.save("crawl", {
            "start_url": req.url,
            "persona": persona_used,
            "pages_crawled": len(pages),
            "avg_score": avg,
            "status": "success",
            "pages": [{k: v for k, v in p.items() if k != "screenshot_b64"} for p in pages],
        })
    except Exception as e:
        log.warning("history save failed: %s", sanitize(str(e))[:120])

    return out
