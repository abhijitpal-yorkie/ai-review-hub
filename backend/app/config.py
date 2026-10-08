import json, os
BASE = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE, "..", "data", "config.json")
SETTINGS_PATH = os.path.join(BASE, "..", "data", "settings.json")

DEFAULT_SETTINGS = {
    "profile": {"name": "Your Name", "role": "QA Engineer", "email": ""},
    "providers": {"gemini": "", "groq": "", "cerebras": "", "nvidia": "", "openrouter": ""},
    "linear": {"api_key": "", "webhook_secret": "", "auto_report": True, "webhook_url": ""},
    "defaults": {"uat_url": "", "max_parallel_cases": 3},
}

DEFAULT_CONFIG = {
    "active_skills": {"qa": ["qa_skill.md"], "validation": ["qa_validate_skill.md"],
                      "uat": ["uat_exec_skill.md"],
                      "ux": ["ux_skill.md"], "mockup": ["mockup_skill.md"]},
    "playwright": {"wait_until": "load", "networkidle_cap_ms": 5000,
                   "viewport": {"width": 1440, "height": 900}},
}

def _load(path, default):
    if not os.path.exists(path):
        _save(path, default); return json.loads(json.dumps(default))
    try:
        with open(path) as f: return {**default, **json.load(f)}
    except Exception:
        return json.loads(json.dumps(default))

def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f: json.dump(data, f, indent=2)

def load_config():   return _load(CONFIG_PATH, DEFAULT_CONFIG)
def save_config(c):  _save(CONFIG_PATH, c)
def load_settings(): return _load(SETTINGS_PATH, DEFAULT_SETTINGS)
def save_settings(s):_save(SETTINGS_PATH, s)

def apply_settings_to_env():
    """Load settings.json values into os.environ so existing clients pick them up."""
    s = load_settings()
    for prov, key in s.get("providers", {}).items():
        if key: os.environ[f"{prov.upper()}_API_KEY"] = key
    lk = s.get("linear", {}).get("api_key")
    if lk: os.environ["LINEAR_API_KEY"] = lk
    ws = s.get("linear", {}).get("webhook_secret")
    if ws: os.environ["LINEAR_WEBHOOK_SECRET"] = ws
