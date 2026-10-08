import os
from app.free_llm_client import call_llm
from app.config import load_config
def _skill(name):
    p=os.path.join(os.path.dirname(__file__),"..","skills",name)
    with open(p) as f: return f.read().split("---")[2].strip()
def generate_test_cases(ticket_text: str) -> str:
    cfg=load_config()
    sys=""
    for s in cfg["active_skills"]["qa"]:
        try: sys += _skill(s) + "\n\n"
        except: pass
    text,_,_ = call_llm("qa_generate", sys, f"Ticket:\n\n{ticket_text}", max_tokens=2500)
    return text
