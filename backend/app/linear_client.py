
import os, time, requests
from app.config import load_settings, apply_settings_to_env
from app import audit
from app.security import sanitize

LINEAR_API = "https://api.linear.app/graphql"


def _key():
    apply_settings_to_env()
    k = os.getenv("LINEAR_API_KEY")
    if not k or k.startswith("your_"):
        raise RuntimeError("Linear API key not configured. Go to Settings.")
    return k


def _gql(query: str, variables: dict = None, retries: int = 3) -> dict:
    headers = {"Authorization": _key(), "Content-Type": "application/json"}
    payload = {"query": query, "variables": variables or {}}
    for attempt in range(retries):
        r = requests.post(LINEAR_API, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if "errors" in data:
                first = data["errors"][0]
                code = first.get("extensions", {}).get("code", "")
                if code == "RATELIMITED" and attempt < retries - 1:
                    wait = int(r.headers.get("Retry-After", 60))
                    time.sleep(min(wait, 30)); continue
                raise RuntimeError(f"Linear GraphQL error: {sanitize(first.get('message', ''))}")
            return data["data"]
        if r.status_code == 400 and attempt < retries - 1:
            try:
                errors = r.json().get("errors", [])
                if errors and errors[0].get("extensions", {}).get("code") == "RATELIMITED":
                    time.sleep(min(int(r.headers.get("Retry-After", 60)), 30)); continue
            except Exception: pass
        if r.status_code in (429, 503) and attempt < retries - 1:
            time.sleep(min(5 * (attempt + 1), 30)); continue
        r.raise_for_status()
    raise RuntimeError("Linear API exhausted after retries")


def list_issues(first: int = 30) -> list:
    q = """query($first:Int!){
      issues(first:$first, orderBy:updatedAt){
        nodes{
          id identifier title description
          state{name} priority priorityLabel
          assignee{name} team{id name} url createdAt updatedAt
        }
      }
    }"""
    return _gql(q, {"first": first})["issues"]["nodes"]


def get_issue(issue_id: str) -> dict:
    q = """query($id:String!){
      issue(id:$id){
        id identifier title description
        state{name} priority assignee{name} team{id name} url
        comments{nodes{id body createdAt user{name}}}
      }
    }"""
    return _gql(q, {"id": issue_id})["issue"]


def create_comment(issue_id: str, body: str) -> dict:
    q = """mutation($input:CommentCreateInput!){
      commentCreate(input:$input){ success comment{id url} }
    }"""
    return _gql(q, {"input": {"issueId": issue_id, "body": body}})["commentCreate"]


def create_issue(title: str, description: str, team_id: str,
                 parent_id: str = None, priority: int = 2) -> dict:
    """Create a Linear issue. If parent_id is given, it becomes a sub-issue."""
    if parent_id:
        q = """mutation($input:IssueCreateInput!){
          issueCreate(input:$input){ success issue{id identifier url title} }
        }"""
        inp = {"title": title, "description": description, "teamId": team_id,
               "parentId": parent_id, "priority": priority}
    else:
        q = """mutation($input:IssueCreateInput!){
          issueCreate(input:$input){ success issue{id identifier url title} }
        }"""
        inp = {"title": title, "description": description, "teamId": team_id,
               "priority": priority}
    return _gql(q, {"input": inp})["issueCreate"]


def upload_file(filename: str, content: bytes, content_type: str = "image/png") -> str:
    q = """mutation($ct:String!,$fn:String!,$size:Int!){
      fileUpload(contentType:$ct, filename:$fn, size:$size){
        success uploadFile{ uploadUrl assetUrl headers{key value} }
      }
    }"""
    data = _gql(q, {"ct": content_type, "fn": filename, "size": len(content)})["fileUpload"]
    if not data["success"]: raise RuntimeError("Linear fileUpload failed")
    upload = data["uploadFile"]
    hdrs = {h["key"]: h["value"] for h in upload.get("headers", [])} or {"Content-Type": content_type}
    r = requests.put(upload["uploadUrl"], data=content, headers=hdrs, timeout=60)
    r.raise_for_status()
    return upload["assetUrl"]


def post_report_to_issue(issue_id: str, report_md: str, screenshots: list = None) -> dict:
    body = report_md
    if screenshots:
        body += "\n\n### Screenshots\n"
        for s in screenshots:
            try:
                url = upload_file(s["filename"], s["content"], "image/png")
                body += f"\n![{s['filename']}]({url})\n"
            except Exception as e:
                body += f"\n_(upload failed {s['filename']}: {e})_\n"
    return create_comment(issue_id, body)


def test_connection() -> dict:
    try:
        d = _gql("{viewer{id name email}}")
        return {"ok": True, "viewer": d["viewer"]}
    except Exception as e:
        return {"ok": False, "error": sanitize(str(e))}
