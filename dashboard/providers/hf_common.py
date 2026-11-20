"""Shared helpers for Hugging Face Space (ZeroGPU) providers."""
from __future__ import annotations

import contextlib
import io
import shutil
import subprocess
from pathlib import Path

from gradio_client import Client, handle_file

from ..settings import hf_token
from .base import ProviderError

QUOTA_WORDS = ("quota", "exceeded your gpu", "zerogpu", "rate limit", "too many requests")


def client(space: str) -> Client:
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return Client(space, token=hf_token(), verbose=False)
    except Exception as e:
        raise ProviderError(f"Space '{space}' se connect nahi hua: {e}") from e


def friendly(e: Exception) -> ProviderError:
    if isinstance(e, ProviderError):
        return e
    msg = str(e)
    if any(w in msg.lower() for w in QUOTA_WORDS):
        tip = "" if hf_token() else " .env mein free HF_TOKEN daalne se quota badhega."
        return ProviderError(f"Free GPU quota khatam ho gaya, thodi der baad try karo.{tip} ({msg[:160]})")
    return ProviderError(msg[:400] or type(e).__name__)


def extract_file(res) -> str:
    """Find the first video/file path in a gradio result."""
    if isinstance(res, dict):
        for k in ("video", "path", "value", "url"):
            v = res.get(k)
            if isinstance(v, str):
                return v
            if isinstance(v, dict):
                return extract_file(v)
    if isinstance(res, str):
        return res
    if isinstance(res, (list, tuple)):
        for item in res:
            try:
                return extract_file(item)
            except ProviderError:
                continue
    raise ProviderError(f"Space ne video file nahi lauti: {str(res)[:200]}")


def save_video(src: str, out: Path) -> Path:
    src_p = Path(src)
    if not src_p.exists():
        raise ProviderError(f"Output file nahi mili: {src}")
    if src_p.suffix.lower() == ".mp4":
        shutil.copy(src_p, out)
        return out
    from reelgen.ffmpeg import ffmpeg_exe  # remux/convert other formats (webm, ts, gif)
    cmd = [ffmpeg_exe(), "-y", "-v", "error", "-i", str(src_p), "-c:v", "libx264",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise ProviderError(f"Video convert fail: {r.stderr.decode(errors='ignore')[:200]}")
    return out


FLUX_SPACE = "black-forest-labs/FLUX.1-schnell"


def keyframe(prompt: str, w: int, h: int, out_png: Path, log) -> str:
    """Text -> start image (free FLUX.1-schnell Space) for image-to-video models."""
    log("Start image bana raha hoon (FLUX.1-schnell)...")
    scale = 1024 / max(w, h)
    fw, fh = (int(round(w * scale / 32)) * 32, int(round(h * scale / 32)) * 32)
    try:
        res = client(FLUX_SPACE).predict(prompt=prompt, seed=0, randomize_seed=True,
                                         width=fw, height=fh, num_inference_steps=4,
                                         api_name="/infer")
    except Exception as e:
        raise friendly(e) from e
    path = extract_file(res)
    shutil.copy(path, out_png)
    return str(out_png)


def file_arg(path: str):
    return handle_file(path)
