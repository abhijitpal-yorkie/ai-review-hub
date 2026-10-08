"""
Credential masking for all diagnostic/log output.
Every print in the diagnostic layer passes through sanitize().
"""
import re, os

PATTERNS = [
    # Linear keys
    (r'lin_api_[A-Za-z0-9]+', 'lin_api_****'),
    (r'lin_wh_[A-Za-z0-9]+', 'lin_wh_****'),
    # Groq keys
    (r'gsk_[A-Za-z0-9]+', 'gsk_****'),
    # Google AI keys
    (r'AIza[A-Za-z0-9_\-]+', 'AIza****'),
    # Cerebras / NVIDIA / OpenRouter (generic long tokens)
    (r'csk-[A-Za-z0-9]+', 'csk-****'),
    (r'nvapi-[A-Za-z0-9_\-]+', 'nvapi-****'),
    (r'sk-or-v1-[A-Za-z0-9]+', 'sk-or-v1-****'),
    # JSON password fields (double and single quotes)
    (r'"password"\s*:\s*"[^"]*"', '"password":"****"'),
    (r"'password'\s*:\s*'[^']*'", "'password':'****'"),
    (r'"api_key"\s*:\s*"[^"]*"', '"api_key":"****"'),
    # Cookies
    (r'stytch_session=[^;\s]+', 'stytch_session=****'),
    (r'stytch_session_jwt=[^;\s]+', 'stytch_session_jwt=****'),
    # Auth headers
    (r'Bearer\s+[A-Za-z0-9._\-]+', 'Bearer ****'),
    (r'Basic\s+[A-Za-z0-9+/=]+', 'Basic ****'),
    # Generic long base64-looking secrets in URLs
    (r'(?<=key=)[A-Za-z0-9_\-]{20,}', '****'),
]

def sanitize(text) -> str:
    if not isinstance(text, str):
        text = str(text)
    for pat, rep in PATTERNS:
        text = re.sub(pat, rep, text)
    return text

def safe_print(msg):
    print(sanitize(msg))

def masked(value: str) -> str:
    """Show first 6 and last 4 chars of a credential, asterisks in the middle."""
    if not value:
        return "(not set)"
    if len(value) <= 12:
        return "*" * len(value)
    return f"{value[:6]}…{value[-4:]}"

def has_real(value: str) -> bool:
    return bool(value) and not value.startswith("your_") and len(value) > 8
