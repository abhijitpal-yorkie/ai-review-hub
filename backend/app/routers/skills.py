import os, shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.config import load_config, save_config
router = APIRouter()
SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "skills")

@router.get("/skills")
def list_skills():
    files = [f for f in os.listdir(SKILLS_DIR) if f.endswith(".md")]
    return {"skills": files, "config": load_config()}

@router.post("/skills/upload")
async def upload_skill(file: UploadFile = File(...)):
    if not file.filename.endswith(".md"): raise HTTPException(400, "Only .md files")
    dest = os.path.join(SKILLS_DIR, file.filename)
    with open(dest, "wb") as f: shutil.copyfileobj(file.file, f)
    return {"ok": True, "filename": file.filename}

class SkillSelect(BaseModel):
    active_skills: dict
@router.post("/skills/select")
def select_skills(req: SkillSelect):
    cfg = load_config()
    cfg["active_skills"] = req.active_skills
    save_config(cfg)
    return {"ok": True, "config": cfg}

class PlaywrightConfig(BaseModel):
    wait_until: str = "load"
    networkidle_cap_ms: int = 5000
@router.post("/config/playwright")
def set_playwright(req: PlaywrightConfig):
    cfg = load_config()
    cfg["playwright"]["wait_until"] = req.wait_until
    cfg["playwright"]["networkidle_cap_ms"] = req.networkidle_cap_ms
    save_config(cfg)
    return {"ok": True, "config": cfg}
