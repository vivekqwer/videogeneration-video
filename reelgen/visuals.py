"""Backgrounds: Pexels photos / local images (Ken Burns) or animated gradients."""
import math
import os
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageOps

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
OVERSCAN = 1.18  # source is this much larger than frame -> room for zoom/pan

PALETTES = [
    ((20, 30, 70), (120, 40, 140)),
    ((10, 60, 70), (20, 140, 120)),
    ((70, 20, 40), (210, 90, 60)),
    ((15, 15, 35), (60, 70, 160)),
    ((40, 10, 70), (200, 60, 120)),
]


def _ease(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0.0), 1.0))


class PhotoBackground:
    def __init__(self, path: Path, w: int, h: int, darken: float, variant: int):
        self.w, self.h = w, h
        bw, bh = int(w * OVERSCAN), int(h * OVERSCAN)
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        img = ImageOps.fit(img, (bw, bh), Image.LANCZOS)
        if darken < 1:
            img = Image.fromarray((np.asarray(img, dtype=np.float32) * darken).astype(np.uint8))
        self.img = img
        self.bw, self.bh = bw, bh
        zoom_in = variant % 2 == 0
        self.z0, self.z1 = (1.0, OVERSCAN) if zoom_in else (OVERSCAN, 1.0)
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        self.pan = dirs[variant % len(dirs)]

    def frame(self, p: float) -> Image.Image:
        e = _ease(p)
        zoom = self.z0 + (self.z1 - self.z0) * e
        cw, ch = self.bw / zoom, self.bh / zoom
        free_x, free_y = self.bw - cw, self.bh - ch
        px = 0.5 + 0.5 * self.pan[0] * (e - 0.5)
        py = 0.5 + 0.5 * self.pan[1] * (e - 0.5)
        x0, y0 = free_x * px, free_y * py
        return self.img.resize((self.w, self.h), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))


class GradientBackground:
    def __init__(self, w: int, h: int, variant: int, duration: float):
        self.w, self.h, self.duration = w, h, max(duration, 0.1)
        self.c1 = np.array(PALETTES[variant % len(PALETTES)][0], dtype=np.float32)
        self.c2 = np.array(PALETTES[variant % len(PALETTES)][1], dtype=np.float32)
        sw, sh = 54, 96
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        self.xx, self.yy = xx / sw, yy / sh
        self.phase = variant * 1.7

    def frame(self, p: float) -> Image.Image:
        t = p * self.duration * 0.35 + self.phase
        ang = t * 0.6
        g = (self.xx - 0.5) * math.cos(ang) + (self.yy - 0.5) * math.sin(ang) + 0.5
        bx, by = 0.5 + 0.3 * math.sin(t), 0.5 + 0.3 * math.cos(t * 0.8)
        blob = np.exp(-(((self.xx - bx) * 1.8) ** 2 + ((self.yy - by)) ** 2) * 6)
        mix = np.clip(g * 0.75 + blob * 0.45, 0, 1)[..., None]
        arr = self.c1 * (1 - mix) + self.c2 * mix
        small = Image.fromarray(arr.astype(np.uint8))
        return small.resize((self.w, self.h), Image.BICUBIC)


def local_images(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMG_EXT)


def fetch_pexels(query: str, count: int, dest: Path, start_index: int = 0) -> list[Path]:
    """Download portrait photos from Pexels (needs PEXELS_API_KEY)."""
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    dest.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "orientation": "portrait", "per_page": max(count, 1) + start_index},
            headers={"Authorization": key}, timeout=20)
        r.raise_for_status()
        photos = r.json().get("photos", [])[start_index:start_index + count]
    except Exception as e:
        print(f"  [pexels] search failed for {query!r}: {e}")
        return []
    out = []
    for ph in photos:
        path = dest / f"pexels_{ph['id']}.jpg"
        if not path.exists():
            try:
                data = requests.get(ph["src"]["large2x"], timeout=30)
                data.raise_for_status()
                path.write_bytes(data.content)
            except Exception as e:
                print(f"  [pexels] download failed: {e}")
                continue
        out.append(path)
    return out


def build_backgrounds(scenes, durations, cfg, work: Path) -> list:
    """One background object per scene."""
    w, h = cfg.width, cfg.height
    pool: list[Path] = []
    if cfg.images_dir:
        pool = local_images(Path(cfg.images_dir))
        if not pool:
            print(f"  [visuals] no images in {cfg.images_dir}, using gradients")

    per_scene: list[Path | None] = [None] * len(scenes)
    if pool:
        per_scene = [pool[i % len(pool)] for i in range(len(scenes))]
    elif os.environ.get("PEXELS_API_KEY"):
        used: dict[str, int] = {}
        for i, sc in enumerate(scenes):
            q = sc.query or cfg.pexels_query
            if not q:
                continue
            got = fetch_pexels(q, 1, work / "images", used.get(q, 0))
            used[q] = used.get(q, 0) + 1
            per_scene[i] = got[0] if got else None

    bgs = []
    for i, (path, dur) in enumerate(zip(per_scene, durations)):
        if path:
            try:
                bgs.append(PhotoBackground(path, w, h, cfg.darken, i))
                continue
            except Exception as e:
                print(f"  [visuals] bad image {path}: {e}")
        bgs.append(GradientBackground(w, h, i, dur))
    return bgs
