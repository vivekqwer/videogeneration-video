"""Auto-connect: discover new video Spaces on Hugging Face and wrap them generically.

`discover()` lists running ZeroGPU Spaces that look like video generators.
`analyze(space)` inspects the Space API and picks the endpoint with a prompt
input and a file/video output, mapping width/height/duration/image params.
The mapping is saved in data/custom_providers.json and loaded as a provider.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from ..settings import CUSTOM_PROVIDERS, dims
from .base import GenRequest, ProviderError
from .hf_common import client, extract_file, file_arg, friendly, keyframe, save_video
from .hf_spaces import NEG, HFSpaceProvider

VIDEO_WORDS = re.compile(r"video|t2v|i2v|wan|ltx|hunyuan|cogvideo|kling|animate|motion|mochi|svd", re.I)
SKIP_WORDS = re.compile(r"upscal|to-text|caption|whisper|audio|foley|lip|subtitle|interpolat|s2v|face|swap|tts", re.I)


def discover(limit: int = 40) -> list[dict]:
    seen, out = set(), []
    for q in ("text-to-video", "video generation", "wan", "ltx", "image-to-video"):
        try:
            r = requests.get("https://huggingface.co/api/spaces",
                             params={"search": q, "sort": "likes", "direction": -1,
                                     "limit": 40, "full": "true"}, timeout=20)
            r.raise_for_status()
        except Exception:
            continue
        for s in r.json():
            sid = s.get("id", "")
            if sid in seen or not VIDEO_WORDS.search(sid) or SKIP_WORDS.search(sid):
                continue
            seen.add(sid)
            out.append({"space": sid, "likes": s.get("likes", 0),
                        "url": f"https://huggingface.co/spaces/{sid}"})
    out.sort(key=lambda x: -x["likes"])
    out = out[:limit]

    def runtime(item):  # search API omits runtime; fetch per Space
        try:
            rt = requests.get(f"https://huggingface.co/api/spaces/{item['space']}", timeout=15).json().get("runtime") or {}
        except Exception:
            rt = {}
        hw = (rt.get("hardware") or {}).get("current") or ""
        item.update(stage=rt.get("stage"), hardware=hw, free_gpu=hw.startswith("zero"))
        return item

    with ThreadPoolExecutor(max_workers=12) as ex:
        out = list(ex.map(runtime, out))
    out.sort(key=lambda x: (x["stage"] != "RUNNING", not x["free_gpu"], -x["likes"]))
    return out


def _is_file(p: dict) -> bool:
    t = (p.get("python_type") or {}).get("type", "")
    return "path:" in t or "filepath" in t or "video:" in t


def analyze(space: str) -> dict:
    c = client(space)
    api = c.view_api(return_format="dict", print_info=False)
    best = None
    for name, ep in api.get("named_endpoints", {}).items():
        params = ep.get("parameters", [])
        names = [(p.get("parameter_name") or "").lower() for p in params]
        prompt = next((p["parameter_name"] for p in params
                       if "prompt" in (p.get("parameter_name") or "").lower()
                       and "neg" not in (p.get("parameter_name") or "").lower()), None)
        if not prompt:
            continue
        rets = ep.get("returns", [])
        if not any(_is_file(r) for r in rets):
            continue
        score = 0
        score += 3 if re.search(r"generat|infer|video|run|predict", name) else 0
        score += 2 if any("video" in json.dumps(r).lower() for r in rets) else 0
        score -= 5 if re.search(r"enhance|upload|dims|update|example", name) else 0
        if best is None or score > best[0]:
            best = (score, name, params, names)
    if not best:
        raise ProviderError("Is Space mein prompt -> video wala endpoint nahi mila.")
    _, api_name, params, names = best

    def find(*keys, file=False):
        for p in params:
            n = (p.get("parameter_name") or "").lower()
            if any(k in n for k in keys) and _is_file(p) == file:
                return p["parameter_name"]
        return None

    image = find("image", file=True)
    image_required = bool(image) and not next(
        p for p in params if p["parameter_name"] == image).get("parameter_has_default")
    mapped = {find("prompt"), find("width"), find("height"), find("duration", "seconds"), image,
              next((p["parameter_name"] for p in params
                    if "neg" in (p.get("parameter_name") or "").lower()), None)}
    unknown = [p["parameter_name"] for p in params
               if not p.get("parameter_has_default") and not _is_file(p)
               and p["parameter_name"] not in mapped]
    if unknown:
        raise ProviderError(f"Is Space ke required inputs auto-fill nahi ho sakte: {', '.join(unknown)}")
    return {
        "id": "hf-" + re.sub(r"[^a-z0-9]+", "-", space.lower()).strip("-"),
        "name": space.split("/")[-1],
        "space": space,
        "api_name": api_name,
        "prompt": find("prompt"),
        "negative": next((p["parameter_name"] for p in params
                          if "neg" in (p.get("parameter_name") or "").lower()), None),
        "image": image,
        "image_required": image_required,
        "width": find("width"),
        "height": find("height"),
        "duration": find("duration", "seconds"),
        "null_files": [p["parameter_name"] for p in params
                       if _is_file(p) and p["parameter_name"] != image
                       and not p.get("parameter_has_default")],
    }


class CustomSpaceProvider(HFSpaceProvider):
    custom = True
    max_duration = 5
    notes = "Auto-connected Space (generic adapter)."

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.id = cfg["id"]
        self.name = cfg.get("name") or cfg["space"]
        self.space = cfg["space"]
        self.kind = "i2v" if cfg.get("image_required") else "t2v"

    def call(self, req: GenRequest, out: Path, log):
        c = self.cfg
        kw: dict = {c["prompt"]: req.prompt}
        w, h = dims(req.aspect, 832, 32)
        if c.get("negative"):
            kw[c["negative"]] = req.negative_prompt or NEG
        if c.get("width") and c.get("height"):
            kw[c["width"]], kw[c["height"]] = w, h
        if c.get("duration"):
            kw[c["duration"]] = min(req.duration, self.max_duration)
        if c.get("image"):
            if req.image or c.get("image_required"):
                kw[c["image"]] = file_arg(self.start_image(req, w, h, out, log))
            else:
                kw[c["image"]] = None
        for n in c.get("null_files", []):
            kw[n] = None
        log("GPU par generate ho raha hai...")
        return client(self.space).predict(api_name=c["api_name"], **kw)


def load_custom() -> list[CustomSpaceProvider]:
    if not CUSTOM_PROVIDERS.exists():
        return []
    try:
        return [CustomSpaceProvider(c) for c in json.loads(CUSTOM_PROVIDERS.read_text("utf-8"))]
    except Exception:
        return []


def save_custom(cfgs: list[dict]) -> None:
    CUSTOM_PROVIDERS.write_text(json.dumps(cfgs, indent=2), encoding="utf-8")


def add_custom(space: str) -> dict:
    try:
        cfg = analyze(space)
    except Exception as e:
        raise friendly(e) from e
    cfgs = [p.cfg for p in load_custom() if p.cfg["space"] != space] + [cfg]
    save_custom(cfgs)
    return cfg


def remove_custom(pid: str) -> None:
    save_custom([p.cfg for p in load_custom() if p.id != pid])
