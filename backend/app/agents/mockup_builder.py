import os, re
from app.free_llm_client import call_llm
from app.config import load_config
def _skill(name):
    p=os.path.join(os.path.dirname(__file__),"..","skills",name)
    with open(p) as f: return f.read().split("---")[2].strip()
def build_mockup(image_data: bytes, audit: str) -> str:
    cfg=load_config(); sys=""
    for s in cfg["active_skills"]["mockup"]:
        try: sys += _skill(s) + "\n\n"
        except: pass
    html,_,_ = call_llm("mockup_build", sys, f"UX Audit Report:\n{audit}\n\nGenerate the improved HTML mockup.", image_data=image_data, max_tokens=4000)
    html=html.strip()
    if html.startswith("```"): html=html.split("\n",1)[1].rsplit("```",1)[0]
    return html.strip()
