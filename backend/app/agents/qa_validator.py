import os, json
from app.free_llm_client import call_llm
from app.config import load_config
def _skill(name):
    p=os.path.join(os.path.dirname(__file__),"..","skills",name)
    with open(p) as f: return f.read().split("---")[2].strip()
def validate_test_cases(cases_md: str, ticket: str) -> dict:
    cfg=load_config()
    sys=""
    for s in cfg["active_skills"]["validation"]:
        try: sys += _skill(s) + "\n\n"
        except: pass
    payload=f"Ticket (truncated): {ticket[:300]}\n\nTest cases:\n{cases_md[:2000]}"
    text,_,_ = call_llm("qa_validate", sys, payload, max_tokens=600)
    clean=text.strip().replace("```json","").replace("```","").strip()
    try: return json.loads(clean)
    except Exception: return {"overall_score":0,"passed":False,"gaps":["Parse error"],"recommendation":f"Raw: {clean[:200]}"}
