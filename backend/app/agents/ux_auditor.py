import os
from app.free_llm_client import call_llm
from app.config import load_config
from app.logger import get_logger

log = get_logger("ux_auditor")


def _skill(name):
    p = os.path.join(os.path.dirname(__file__), "..", "skills", name)
    with open(p) as f:
        return f.read().split("---")[2].strip()


def audit_ux(image_data: bytes) -> str:
    cfg = load_config()
    sys = ""
    for s in cfg["active_skills"]["ux"]:
        try: sys += _skill(s) + "\n\n"
        except Exception: pass

    prompt = (
        "Analyze this UI screenshot. Return ALL sections. "
        "You MUST output every line below, do not stop early:\n"
        "### UX Score\n"
        "- **Clarity & Hierarchy:** X/5\n"
        "- **Visual Noise:** X/5\n"
        "- **Consistency & Standards:** X/5\n"
        "- **Feedback & Affordance:** X/5\n"
        "- **Accessibility:** X/5\n"
        "- **Overall:** X/25\n\n"
        "### Before & After\n"
        "- **Current Issue:** <one clear sentence>\n"
        "- **Proposed Fix:** <one clear sentence>\n"
        "- **Visual Description:** <2-3 sentences>\n"
    )
    text, prov, model = call_llm("ux_audit", sys, prompt,
                                 image_data=image_data, max_tokens=2500)
    log.info("raw response: provider=%s model=%s length=%d", prov, model, len(text))
    log.info("first 200 chars: %s", text[:200].replace("\n", " | "))

    # Guard: if response too short, retry once with a stronger instruction
    if len(text) < 400:
        log.warning("response too short (%d chars), retrying with strict prompt", len(text))
        strict_prompt = (
            "You skipped mandatory sections. You MUST output all of these:\n\n"
            "### UX Score\n"
            "- **Clarity & Hierarchy:** X/5\n"
            "- **Visual Noise:** X/5\n"
            "- **Consistency & Standards:** X/5\n"
            "- **Feedback & Affordance:** X/5\n"
            "- **Accessibility:** X/5\n"
            "- **Overall:** X/25\n\n"
            "### Before & After\n"
            "- **Current Issue:** ...\n"
            "- **Proposed Fix:** ...\n"
            "- **Visual Description:** ...\n\n"
            "Now write it out, all 9 lines."
        )
        text2, prov2, model2 = call_llm("ux_audit", sys, strict_prompt,
                                        image_data=image_data, max_tokens=2500)
        log.info("retry response: length=%d", len(text2))
        if len(text2) > len(text):
            return text2
    return text
