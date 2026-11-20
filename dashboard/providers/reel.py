"""Local, unlimited provider: script -> voiceover + subtitles reel (reelgen)."""
from pathlib import Path

from reelgen.config import Config
from reelgen.pipeline import make_reel

from ..settings import ASPECTS
from .base import GenRequest, Provider, ProviderError


class ReelProvider(Provider):
    id, name, kind = "reelgen", "ReelGen (voice + subtitles)", "reel"
    free = True
    source = "local"
    max_duration = 600
    notes = "Unlimited, local. Prompt = script; har sentence ek scene. Hindi/English auto."

    def generate(self, req: GenRequest, out: Path, log) -> Path:
        aw, ah = ASPECTS.get(req.aspect, (9, 16))
        w, h = (1080, 1920) if ah > aw else (1920, 1080) if aw > ah else (1080, 1080)
        cfg = Config(width=w, height=h, voice=req.extra.get("voice") or None,
                     pexels_query=req.extra.get("query") or None,
                     subtitle_margin_v=int(h * 0.32), font_size=int(min(w, h) * 0.085))
        log("Voiceover + subtitles + render (1-3 min)...")
        try:
            return make_reel(req.prompt, out, cfg)
        except Exception as e:
            raise ProviderError(str(e)[:400]) from e
