
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app import linear_client, history, audit
from app.agents.qa_generator import generate_test_cases
from app.agents.qa_validator import validate_test_cases
from app.agents.uat_executor import execute_test_case
from app.utils import capture_screenshot_bytes as capture_screenshot, run_async
from app.config import load_config, load_settings
from app.security import sanitize
from app.logger import get_logger
router = APIRouter()
log = get_logger("tickets")


class RunRequest(BaseModel):
    ticket_text: str
    base_url: Optional[str] = None
    execute: bool = False
    test_ids: Optional[list] = None


class ExecuteCaseReq(BaseModel):
    test_case: dict
    base_url: str


class ExecuteAllReq(BaseModel):
    test_cases: list
    base_url: str
    ticket_text: str = ""
    issue_id: Optional[str] = None


class PostReportReq(BaseModel):
    test_cases: list
    executions: list
    base_url: str = ""
    validation: Optional[dict] = None


class CreateChildrenReq(BaseModel):
    test_cases: list
    executions: list
    base_url: str = ""


def _parse_cases(markdown: str) -> list:
    cases = []
    for line in markdown.split("\n"):
        line = line.strip()
        if not line.startswith("|"): continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if not parts or len(parts) < 2: continue
        if parts[0].lower() in ("id", "----", "---", ""): continue
        if set(parts[0]) <= {"-", ":", " "}: continue
        if not parts[0].upper().startswith("TC"): continue
        cases.append({
            "id": parts[0], "title": parts[1] if len(parts) > 1 else "",
            "preconditions": parts[2] if len(parts) > 2 else "",
            "steps": parts[3] if len(parts) > 3 else "",
            "expected": parts[4] if len(parts) > 4 else "",
            "priority": parts[5] if len(parts) > 5 else "Medium",
        })
    return cases


@router.get("/tickets")
def list_tickets():
    try: return {"tickets": linear_client.list_issues(50)}
    except Exception as e: raise HTTPException(500, str(e))


@router.get("/tickets/{issue_id}")
def get_ticket(issue_id: str):
    try: return linear_client.get_issue(issue_id)
    except Exception as e: raise HTTPException(500, str(e))


@router.post("/tickets/{issue_id}/generate")
def generate_for_ticket(issue_id: str):
    try:
        issue = linear_client.get_issue(issue_id)
        ticket = f"{issue['title']}\n\n{issue.get('description','')}"
        cases_md = generate_test_cases(ticket)
        val = validate_test_cases(cases_md, ticket)
        parsed = _parse_cases(cases_md)
        audit.log("Test cases generated", category="qa", status="success",
                  target=issue.get("identifier", ""),
                  detail={"count": len(parsed), "score": val.get("overall_score")})
        try:
            history.save("tickets", {
                "action": "generate", "issue_id": issue.get("id"),
                "identifier": issue.get("identifier"), "title": issue.get("title"),
                "status": "success", "validation": val,
                "test_cases": parsed, "test_cases_markdown": cases_md,
            })
        except Exception as e:
            log.warning("history save: %s", sanitize(str(e)))
        return {"test_cases": parsed, "test_cases_markdown": cases_md,
                "validation": val, "status": "success"}
    except Exception as e:
        audit.log("Generation failed", category="qa", status="error", detail={"error": sanitize(str(e))})
        raise HTTPException(500, sanitize(str(e)))


@router.post("/execute/case")
def execute_single(req: ExecuteCaseReq):
    try:
        persona = load_settings()["defaults"].get("uat_persona", "admin")
        result = execute_test_case(req.test_case, req.base_url, persona=persona)
        audit.log(f"Case {result['status']}", category="execution",
                  status="success" if result["status"] == "PASS" else "error",
                  target=req.test_case.get("id", "?"),
                  detail={"url": req.base_url, "reason": result.get("reason", "")[:150]})
        return {"result": result, "status": "success"}
    except Exception as e:
        raise HTTPException(500, sanitize(str(e)))


@router.post("/execute/all")
def execute_all(req: ExecuteAllReq):
    try:
        cfg = load_config()
        limit = load_settings()["defaults"].get("max_parallel_cases", 10)
        persona = load_settings()["defaults"].get("uat_persona", "admin")
        executions = []
        screenshots = []
        for tc in req.test_cases[:limit]:
            r = execute_test_case(tc, req.base_url, persona=persona)
            executions.append(r)
            if r["status"] != "PASS":
                try:
                    img = run_async(capture_screenshot(req.base_url, annotate_boxes=r.get("boxes", [])))
                    screenshots.append({"filename": f"{tc['id']}.png", "content": img})
                except Exception: pass
        report = None
        if req.issue_id:
            try:
                issue = linear_client.get_issue(req.issue_id)
                report = _build_report(issue, executions)
                if load_settings()["linear"].get("auto_report", True):
                    linear_client.post_report_to_issue(req.issue_id, report, screenshots)
            except Exception as e:
                log.warning("auto-report: %s", sanitize(str(e)))
        passed = sum(1 for e in executions if e["status"] == "PASS")
        try:
            history.save("tickets", {
                "action": "run_all", "issue_id": req.issue_id, "base_url": req.base_url,
                "status": "success", "total": len(executions), "passed": passed,
                "executions": executions, "report_markdown": report,
                "screenshots_count": len(screenshots),
            })
        except Exception as e:
            log.warning("history save: %s", sanitize(str(e)))
        return {"executions": executions, "report_markdown": report,
                "screenshots_count": len(screenshots), "status": "success"}
    except Exception as e:
        raise HTTPException(500, sanitize(str(e)))


def _build_report(issue, executions):
    passed = sum(1 for e in executions if e["status"] == "PASS")
    total = len(executions)
    lines = [f"## 🧪 Test Execution Report — {issue['identifier']}",
             f"**{passed}/{total} passed** — posted from AI Review Hub", ""]
    for e in executions:
        icon = "✅" if e["status"] == "PASS" else ("❌" if e["status"] == "FAIL" else "⚠️")
        lines.append(f"- {icon} **{e['test_id']}** — {e['status']} — {e.get('reason','')[:200]}")
    return "\n".join(lines)


class TextRequest(BaseModel):
    ticket_text: str


@router.post("/tickets/generate-from-text")
def generate_from_text(req: TextRequest):
    try:
        cases_md = generate_test_cases(req.ticket_text)
        val = validate_test_cases(cases_md, req.ticket_text)
        return {"test_cases": _parse_cases(cases_md), "test_cases_markdown": cases_md,
                "validation": val, "status": "success"}
    except Exception as e:
        raise HTTPException(500, sanitize(str(e)))


@router.post("/tickets/{issue_id}/post-report")
def post_report(issue_id: str, req: PostReportReq):
    """Post execution results back to the Linear ticket as a comment."""
    try:
        issue = linear_client.get_issue(issue_id)
        passed = sum(1 for e in req.executions if e.get("status") == "PASS")
        total = len(req.executions)
        lines = [
            f"## 🧪 Test Execution Report",
            f"**{passed}/{total} passed** · UAT: `{req.base_url}`",
            "",
        ]
        if req.validation:
            lines.append(f"**Validation score:** {req.validation.get('overall_score','—')}/100")
            lines.append("")
        lines.append("### Results")
        for e in req.executions:
            icon = "✅" if e["status"] == "PASS" else ("❌" if e["status"] == "FAIL" else "⚠️")
            lines.append(f"- {icon} **{e['test_id']}** — {e['status']} — {(e.get('reason') or '')[:200]}")
        lines.append("")
        lines.append("### Test Cases")
        for tc in req.test_cases:
            lines.append(f"- **{tc.get('id')}** — {tc.get('title','')}")
        body = "\n".join(lines)
        result = linear_client.create_comment(issue_id, body)
        audit.log("Report posted to Linear", category="linear", status="success",
                  target=issue.get("identifier", ""),
                  detail={"passed": passed, "total": total})
        return {"ok": True, "comment": result.get("comment", {})}
    except Exception as e:
        audit.log("Post report failed", category="linear", status="error",
                  detail={"error": sanitize(str(e))[:200]})
        raise HTTPException(500, sanitize(str(e)))


@router.post("/tickets/{issue_id}/create-children")
def create_children(issue_id: str, req: CreateChildrenReq):
    """Create a child ticket in Linear for each failed test case."""
    try:
        parent = linear_client.get_issue(issue_id)
        team = parent.get("team", {})
        team_id = team.get("id")
        if not team_id:
            raise HTTPException(400, "Parent ticket has no team; cannot create children")
        failures = [e for e in req.executions if e.get("status") != "PASS"]
        if not failures:
            return {"ok": True, "created": [], "message": "No failures to convert"}

        cases_by_id = {tc.get("id"): tc for tc in req.test_cases}
        created = []
        for e in failures:
            tc = cases_by_id.get(e["test_id"], {})
            title = f"❌ {e['test_id']}: {tc.get('title', 'Test failure')}"
            desc = "\n".join([
                f"**Parent:** {parent['identifier']} — {parent['title']}",
                f"**Status:** {e['status']}",
                f"**Reason:** {e.get('reason', 'no reason')}",
                f"**UAT:** {req.base_url}",
                "",
                "### Steps to reproduce",
                tc.get("steps", "—"),
                "",
                "### Expected",
                tc.get("expected", "—"),
            ])
            priority = {"High": 1, "Medium": 2, "Low": 3}.get(tc.get("priority"), 2)
            res = linear_client.create_issue(title=title, description=desc,
                                             team_id=team_id, parent_id=issue_id,
                                             priority=priority)
            if res.get("success"):
                created.append(res.get("issue"))
        audit.log("Child tickets created", category="linear", status="success",
                  target=parent.get("identifier", ""),
                  detail={"count": len(created)})
        return {"ok": True, "created": created}
    except HTTPException: raise
    except Exception as e:
        audit.log("Create children failed", category="linear", status="error",
                  detail={"error": sanitize(str(e))[:200]})
        raise HTTPException(500, sanitize(str(e)))
