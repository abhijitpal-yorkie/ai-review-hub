import os, time, hashlib, base64, requests

PROVIDERS = {
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        "key_env": "GEMINI_API_KEY",
        "models": {
            "flash-lite": "gemini-3.1-flash-lite",   # text gen — high quota
            "flash":      "gemini-3.8-flash",        # vision — recommended by Google
            "flash-alt":  "gemini-3.5-flash",        # vision backup
            "flash-lite-alt": "gemini-3.5-flash-lite"
        },
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "models": {"fast": "llama-3.1-8b-instant", "large": "llama-3.3-70b-versatile"},
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "key_env": "CEREBRAS_API_KEY",
        "models": {"large": "gpt-oss-120b"},
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
        "models": {"free": "meta-llama/llama-3.3-70b-instruct:free"},
    },
}

# Only chains using providers the user has configured:
#   Gemini (text + vision) + Groq (text failover)
FALLBACK_CHAINS = {
    "qa_generate":  [("gemini","flash-lite"), ("groq","large")],
    "qa_validate":  [("gemini","flash-lite"), ("groq","fast")],
    "uat_execute":  [("gemini","flash-lite"), ("groq","large")],
    "ux_audit":     [("gemini","flash"), ("gemini","flash-alt")],
    "mockup_build": [("groq","large"), ("gemini","flash")],
}

_cache = {}
def _ckey(p,m,s): return hashlib.sha256(f"{p}|{m}|{s}".encode()).hexdigest()

def _call(provider, model_key, sys, usr, image_data=None, max_tokens=2048):
    cfg = PROVIDERS[provider]
    key = os.getenv(cfg["key_env"])
    if not key or key.startswith("your_"):
        raise RuntimeError(f"Missing {cfg['key_env']}")
    model = cfg["models"][model_key]

    if provider == "gemini":
        url = cfg["url"].format(model=model, key=key)
        parts = [{"text": usr}]
        if image_data:
            parts.append({"inline_data": {"mime_type": "image/png",
                                          "data": base64.b64encode(image_data).decode()}})
        r = requests.post(url, json={
            "system_instruction": {"parts": [{"text": sys}]},
            "contents": [{"parts": parts}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2},
        }, timeout=120)
        if not r.ok:
            raise RuntimeError(f"gemini HTTP {r.status_code}: {r.text[:180]}")
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    msgs = [{"role":"system","content":sys},{"role":"user","content":usr}]
    if image_data:
        b64 = base64.b64encode(image_data).decode()
        msgs[-1] = {"role":"user","content":[
            {"type":"text","text":usr},
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64}"}}]}
    r = requests.post(cfg["url"], json={
        "model": model, "messages": msgs,
        "max_tokens": max_tokens, "temperature": 0.2,
    }, headers=headers, timeout=120)
    if not r.ok:
        raise RuntimeError(f"{provider} HTTP {r.status_code}: {r.text[:180]}")
    return r.json()["choices"][0]["message"]["content"]

def call_llm(chain_key, sys, usr, image_data=None, max_tokens=2048):
    errs = []
    for prov, mk in FALLBACK_CHAINS[chain_key]:
        ck = _ckey(prov, mk, sys + usr)
        if ck in _cache:
            ts, txt = _cache[ck]
            if time.time() - ts < 3600:
                return txt, prov, mk
        try:
            txt = _call(prov, mk, sys, usr, image_data, max_tokens)
            _cache[ck] = (time.time(), txt)
            return txt, prov, mk
        except Exception as e:
            errs.append(f"{prov}/{mk}: {str(e)[:150]}")
            continue
    raise RuntimeError(f"All providers exhausted for '{chain_key}'. Errors: {errs}")
