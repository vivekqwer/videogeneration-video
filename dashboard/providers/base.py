from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GenRequest:
    prompt: str
    aspect: str = "9:16"
    duration: float = 4.0
    negative_prompt: str = ""
    seed: int = -1
    image: str | None = None   # optional start image (local path)
    extra: dict = field(default_factory=dict)


class ProviderError(Exception):
    """Readable error shown on the dashboard."""


class Provider:
    id: str = ""
    name: str = ""
    kind: str = "t2v"          # t2v | i2v | reel
    free: bool = True
    source: str = ""           # link to model / space
    max_duration: float = 5.0
    aspects: tuple[str, ...] = ("9:16", "16:9", "1:1")
    env: tuple[str, ...] = ()  # env vars required (API keys)
    notes: str = ""

    def available(self) -> tuple[bool, str]:
        missing = [e for e in self.env if not os.environ.get(e)]
        if missing:
            return False, f"Missing in .env: {', '.join(missing)}"
        return True, "ready"

    def generate(self, req: GenRequest, out: Path, log) -> Path:
        """Create the video at `out` (mp4). `log(msg)` reports progress."""
        raise NotImplementedError

    def info(self) -> dict:
        ok, status = self.available()
        return {
            "id": self.id, "name": self.name, "kind": self.kind, "free": self.free,
            "source": self.source, "max_duration": self.max_duration,
            "aspects": list(self.aspects), "ready": ok, "status": status,
            "notes": self.notes, "custom": getattr(self, "custom", False),
        }
