import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = DATA_DIR / "jobs.db"
CUSTOM_PROVIDERS = DATA_DIR / "custom_providers.json"
for d in (DATA_DIR, MEDIA_DIR):
    d.mkdir(parents=True, exist_ok=True)

HOST = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
PORT = int(os.environ.get("DASHBOARD_PORT", "8000"))

ASPECTS = {"9:16": (9, 16), "16:9": (16, 9), "1:1": (1, 1)}


def hf_token() -> str | None:
    return os.environ.get("HF_TOKEN") or None


def dims(aspect: str, long_side: int, multiple: int = 32) -> tuple[int, int]:
    """(width, height) for an aspect ratio, long side fixed, rounded to multiple."""
    aw, ah = ASPECTS.get(aspect, (9, 16))
    if ah >= aw:
        h = long_side
        w = long_side * aw / ah
    else:
        w = long_side
        h = long_side * ah / aw
    r = lambda v: max(multiple, int(round(v / multiple)) * multiple)
    return r(w), r(h)
