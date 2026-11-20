import shutil
import time
from pathlib import Path

from .config import DEFAULT_VOICES, FALLBACK_VOICES, FONTS, Config
from .render import render, scene_boundaries
from .script import detect_lang, parse_script
from .subtitles import build_ass
from .tts import synthesize
from .visuals import build_backgrounds

WIN_FONTS = Path(r"C:\Windows\Fonts")


def make_reel(script_text: str, out: Path, cfg: Config) -> Path:
    t0 = time.time()
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / f".work_{out.stem}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    scenes = parse_script(script_text)
    lang = detect_lang(script_text)
    voice = cfg.voice or DEFAULT_VOICES[lang]
    print(f"[1/4] {len(scenes)} scenes, lang={lang}, voice={voice}")

    voice_wav, scene_audio, total = synthesize(
        [s.text for s in scenes], voice, cfg.rate, cfg.pitch, work, cfg.scene_gap, cfg.tail,
        fallback=FALLBACK_VOICES[lang])
    print(f"      audio {total:.2f}s")

    print("[2/4] subtitles")
    family, font_file = FONTS[lang]
    fonts = work / "fonts"
    fonts.mkdir()
    src = WIN_FONTS / font_file
    if src.exists():
        shutil.copy(src, fonts / font_file)
    else:
        print(f"      warning: {src} not found, libass will fall back to a default font")
    build_ass(scene_audio, work / "subs.ass", font=family, size=cfg.font_size,
              width=cfg.width, height=cfg.height, margin_v=cfg.subtitle_margin_v,
              max_words=cfg.words_per_line, max_chars=cfg.max_chars_per_line,
              uppercase=cfg.uppercase and lang == "en", highlight=cfg.highlight_color)

    print("[3/4] backgrounds")
    bounds = scene_boundaries(scene_audio, total)
    durations = [b - a for a, b in zip(bounds, bounds[1:])]
    bgs = build_backgrounds(scenes, durations, cfg, work)

    print("[4/4] render")
    render(bgs, bounds, total, work, out, cfg, voice_wav, "subs.ass", "fonts")

    if not cfg.keep_work:
        shutil.rmtree(work, ignore_errors=True)
    print(f"Done: {out}  ({total:.1f}s video, {time.time() - t0:.1f}s build)")
    return out
