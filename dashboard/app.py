"""FastAPI backend for the AI video dashboard.

Run:  python -m dashboard   (opens http://127.0.0.1:8000)
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import jobs
from .providers import GenRequest, all_providers
from .providers.custom import add_custom, discover, remove_custom
from .settings import MEDIA_DIR, hf_token

STATIC = Path(__file__).parent / "static"
UPLOADS = MEDIA_DIR / "uploads"
UPLOADS.mkdir(exist_ok=True)

app = FastAPI(title="AI Video Dashboard")
jobs.init()


class GenerateBody(BaseModel):
    prompt: str = Field(min_length=2, max_length=8000)
    providers: list[str] = Field(min_length=1)
    aspect: str = "9:16"
    duration: float = Field(4, ge=1, le=600)
    negative_prompt: str = ""
    seed: int = -1
    image: str | None = None   # upload id from /api/upload
    voice: str | None = None
    query: str | None = None


class ConnectBody(BaseModel):
    space: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")


@app.get("/api/status")
def status():
    return {"hf_token": bool(hf_token())}


@app.get("/api/providers")
def providers():
    return [p.info() for p in all_providers().values()]


@app.post("/api/generate")
def generate(body: GenerateBody):
    image = None
    if body.image:
        image = UPLOADS / Path(body.image).name
        if not image.exists():
            raise HTTPException(400, "Uploaded image nahi mili")
    created, errors = [], []
    for pid in dict.fromkeys(body.providers):
        req = GenRequest(prompt=body.prompt, aspect=body.aspect, duration=body.duration,
                         negative_prompt=body.negative_prompt, seed=body.seed,
                         image=str(image) if image else None,
                         extra={"voice": body.voice, "query": body.query})
        try:
            created.append(jobs.submit(pid, req))
        except ValueError as e:
            errors.append(str(e))
    if not created:
        raise HTTPException(400, "; ".join(errors) or "Koi job nahi bani")
    return {"jobs": created, "errors": errors}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(400, "Sirf png/jpg/webp image")
    name = uuid.uuid4().hex + ext
    with open(UPLOADS / name, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"id": name, "url": f"/media/uploads/{name}"}


@app.get("/api/jobs")
def list_jobs():
    return jobs.list_jobs()


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    try:
        jobs.delete_job(job_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.get("/api/discover")
def api_discover():
    connected = {getattr(p, "space", None) for p in all_providers().values()}
    items = discover()
    for it in items:
        it["connected"] = it["space"] in connected
    return items


@app.post("/api/connect")
def api_connect(body: ConnectBody):
    try:
        return add_custom(body.space)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.delete("/api/providers/{pid}")
def api_disconnect(pid: str):
    remove_custom(pid)
    return {"ok": True}


app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
