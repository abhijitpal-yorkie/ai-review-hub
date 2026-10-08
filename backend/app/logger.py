import sys, os, logging
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "app.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

class ColorFmt(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",   # cyan
        "INFO": "\033[32m",    # green
        "WARNING": "\033[33m", # yellow
        "ERROR": "\033[31m",   # red
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, r):
        ts = datetime.fromtimestamp(r.created).strftime("%H:%M:%S")
        c = self.COLORS.get(r.levelname, "")
        msg = r.getMessage()
        try: msg = msg % r.args if r.args else msg
        except Exception: pass
        return f"{ts} {c}{r.levelname:<7}{self.RESET} {r.name:<20} {msg}"

_log = logging.getLogger("airh")
_log.setLevel(logging.INFO)
_log.handlers.clear()

# stdout handler
h1 = logging.StreamHandler(sys.stdout)
h1.setFormatter(ColorFmt())
_log.addHandler(h1)

# file handler (no colors)
h2 = logging.FileHandler(LOG_FILE)
h2.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
_log.addHandler(h2)

def get_logger(name=""):
    return _log.getChild(name) if name else _log

# Public helpers
def info(msg, *a, name="app"):    _log.getChild(name).info(msg, *a)
def warn(msg, *a, name="app"):    _log.getChild(name).warning(msg, *a)
def error(msg, *a, name="app"):   _log.getChild(name).error(msg, *a)
def debug(msg, *a, name="app"):   _log.getChild(name).debug(msg, *a)

def step(label: str):
    """Print a visual step marker."""
    print(f"\n\033[1;36m▶ {label}\033[0m", flush=True)
