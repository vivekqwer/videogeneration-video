"""Parse a plain-text script into scenes.

Format:
  - One or more sentences per line; each sentence becomes a scene.
  - Optional per-line image search query: `[city night] Your sentence here.`
  - Lines starting with `#` are comments.
"""
import re
from dataclasses import dataclass

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
SENT_SPLIT = re.compile(r"(?<=[.!?।|])\s+")
QUERY_PREFIX = re.compile(r"^\[([^\]]+)\]\s*(.*)$")
MIN_SCENE_CHARS = 25


@dataclass
class Scene:
    text: str
    query: str | None = None


def detect_lang(text: str) -> str:
    return "hi" if DEVANAGARI.search(text) else "en"


def parse_script(raw: str) -> list[Scene]:
    scenes: list[Scene] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        query = None
        m = QUERY_PREFIX.match(line)
        if m:
            query, line = m.group(1).strip(), m.group(2).strip()
        if not line:
            continue
        merged: list[str] = []
        for part in (p.strip() for p in SENT_SPLIT.split(line)):
            if not part:
                continue
            if merged and len(merged[-1]) < MIN_SCENE_CHARS:
                merged[-1] += " " + part
            else:
                merged.append(part)
        scenes.extend(Scene(p, query) for p in merged)
    if not scenes:
        raise ValueError("Script is empty.")
    return scenes
