#!/usr/bin/env python3
"""
Interactive credential setup for Lexful UAT personas.
Prompts for each password (hidden input), writes to a locked file.
"""
import os, sys, getpass, stat
from pathlib import Path

CREDS_FILE = Path(__file__).parent / ".env.lexful"

PERSONAS = [
    ("LEXFUL_ADMIN_PASSWORD",   "admin persona (e2e-test+admin@lexful.ai)"),
    ("LEXFUL_SUPPORT_PASSWORD", "support persona (e2e-test+support@lexful.ai)"),
    ("LEXFUL_VIEWER_PASSWORD",  "viewer persona (e2e-test+viewer@lexful.ai)"),
]

def load_existing():
    data = {}
    if CREDS_FILE.exists():
        for line in CREDS_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"): continue
            if "=" in line:
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip().strip('"').strip("'")
    return data

def save_all(data):
    lines = ["# Lexful UAT persona passwords", "# Auto-generated. Do not commit.", ""]
    for k, v in data.items():
        if v:
            # Escape any quotes/backslashes
            escaped = v.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k}="{escaped}"')
    CREDS_FILE.write_text("\n".join(lines) + "\n")
    # Lock to owner-only read/write
    os.chmod(CREDS_FILE, stat.S_IRUSR | stat.S_IWUSR)

def main():
    print()
    print("════════════════════════════════════════════════")
    print("  LEXFUL UAT — CREDENTIAL SETUP")
    print("════════════════════════════════════════════════")
    print()
    print(f"  Saving to: {CREDS_FILE}")
    print()

    existing = load_existing()
    updated = dict(existing)

    for env_var, label in PERSONAS:
        already = "yes" if existing.get(env_var) else "no"
        print(f"  ── {label} ──")
        if existing.get(env_var):
            print(f"     (already set — press Enter to keep, or paste new password)")
        try:
            pw = getpass.getpass("     Password: ")
        except (KeyboardInterrupt, EOFError):
            print("\n     (skipped)")
            continue
        if pw.strip() == "":
            if existing.get(env_var):
                print(f"     ✓ kept existing")
                continue
            else:
                print(f"     ⚠ skipped (no value)")
                continue
        updated[env_var] = pw
        print(f"     ✓ saved ({len(pw)} chars)")

    save_all(updated)
    print()
    print("════════════════════════════════════════════════")
    print("  ✅  SAVED")
    print("════════════════════════════════════════════════")
    print()
    print(f"  File: {CREDS_FILE}")
    print(f"  Permissions: 600 (owner only)")
    print()
    print("  Verify:")
    print("    python3 -c \"import os; from pathlib import Path;")
    print("      [print(f'  ✓ {k} set') if os.getenv(k) else None for k in ['LEXFUL_ADMIN_PASSWORD','LEXFUL_SUPPORT_PASSWORD','LEXFUL_VIEWER_PASSWORD']]\"")
    print()
    print("  Test a persona:")
    print("    python3 -m app.lexful_auth --persona admin --headless")
    print()

if __name__ == "__main__":
    main()
