"""Job store (SQLite) + worker pool. One worker per provider so free quotas
aren't hammered; different providers run in parallel."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

from .providers import GenRequest, ProviderError, all_providers
from .settings import DB_PATH, MEDIA_DIR

_lock = threading.Lock()
_executors: dict[str, ThreadPoolExecutor] = {}

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, provider TEXT, provider_name TEXT, prompt TEXT, params TEXT,
  status TEXT, message TEXT, output TEXT, created REAL, started REAL, finished REAL
)"""


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def init() -> None:
    with _db() as con:
        con.execute(SCHEMA)
        # jobs that were running when the server stopped will never finish
        con.execute("UPDATE jobs SET status='error', message='Server restart se ruk gaya' "
                    "WHERE status IN ('queued','running')")


def _update(job_id: str, **fields) -> None:
    keys = ", ".join(f"{k}=?" for k in fields)
    with _lock, _db() as con:
        con.execute(f"UPDATE jobs SET {keys} WHERE id=?", (*fields.values(), job_id))


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["params"] = json.loads(d["params"] or "{}")
    d["url"] = f"/media/{d['output']}" if d.get("output") else None
    end = d.get("finished") or time.time()
    d["elapsed"] = round(end - d["started"], 1) if d.get("started") else None
    return d


def list_jobs(limit: int = 200) -> list[dict]:
    with _db() as con:
        rows = con.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
    return [_row(r) for r in rows]


def get_job(job_id: str) -> dict | None:
    with _db() as con:
        r = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return _row(r) if r else None


def delete_job(job_id: str) -> None:
    job = get_job(job_id)
    if job and job["status"] in ("queued", "running"):
        raise ValueError("Chalti job delete nahi ho sakti")
    for f in MEDIA_DIR.glob(f"{job_id}*"):
        f.unlink(missing_ok=True)
    with _lock, _db() as con:
        con.execute("DELETE FROM jobs WHERE id=?", (job_id,))


def submit(provider_id: str, req: GenRequest) -> dict:
    providers = all_providers()
    p = providers.get(provider_id)
    if not p:
        raise ValueError(f"Unknown provider {provider_id}")
    ok, status = p.available()
    if not ok:
        raise ValueError(f"{p.name}: {status}")
    job_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    with _lock, _db() as con:
        con.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (job_id, p.id, p.name, req.prompt, json.dumps(asdict(req)),
                     "queued", "Queue mein hai", None, time.time(), None, None))
    ex = _executors.setdefault(p.id, ThreadPoolExecutor(max_workers=1, thread_name_prefix=p.id))
    ex.submit(_run, job_id, p, req)
    return get_job(job_id)


def _run(job_id: str, provider, req: GenRequest) -> None:
    _update(job_id, status="running", started=time.time(), message="Start...")
    out = MEDIA_DIR / f"{job_id}.mp4"
    try:
        provider.generate(req, out, lambda m: _update(job_id, message=str(m)[:300]))
        if not out.exists():
            raise ProviderError("Output video nahi bani")
        _update(job_id, status="done", output=out.name, message="Ready", finished=time.time())
    except ProviderError as e:
        _update(job_id, status="error", message=str(e), finished=time.time())
    except Exception as e:
        traceback.print_exc()
        _update(job_id, status="error", message=f"{type(e).__name__}: {str(e)[:300]}",
                finished=time.time())
