"""Text -> 9:16 reel with voiceover + word-highlighted subtitles.

Examples:
  python main.py examples/sample_en.txt -o output/reel.mp4
  python main.py examples/sample_hi.txt --music bg.mp3 --images my_photos/
  python main.py --text "Hello world. This is a reel." -o output/quick.mp4
  python main.py --list-voices hi-IN
"""
import argparse
import sys
from pathlib import Path

from reelgen.config import Config


def main() -> int:
    ap = argparse.ArgumentParser(description="Text to 9:16 reel generator")
    ap.add_argument("script", nargs="?", help="path to script .txt")
    ap.add_argument("--text", help="script text inline (instead of file)")
    ap.add_argument("-o", "--out", help="output .mp4 (default: output/<script>.mp4)")
    ap.add_argument("--voice", help="edge-tts voice, e.g. hi-IN-SwaraNeural")
    ap.add_argument("--rate", default="+5%", help="speech rate, e.g. +10%%")
    ap.add_argument("--pitch", default="+0Hz")
    ap.add_argument("--images", type=Path, help="folder of images to use as backgrounds")
    ap.add_argument("--query", help="Pexels search query for all scenes (needs PEXELS_API_KEY)")
    ap.add_argument("--music", type=Path, help="background music file")
    ap.add_argument("--music-volume", type=float, default=0.12)
    ap.add_argument("--words-per-line", type=int, default=3)
    ap.add_argument("--font-size", type=int, default=92)
    ap.add_argument("--uppercase", action="store_true", help="uppercase subtitles (English)")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--keep-work", action="store_true", help="keep temp files for debugging")
    ap.add_argument("--list-voices", metavar="LOCALE", help="list voices for locale prefix, e.g. hi-IN")
    a = ap.parse_args()

    if a.list_voices is not None:
        from reelgen.tts import list_voices
        for v in list_voices(a.list_voices):
            print(f"{v['ShortName']:40} {v['Gender']}")
        return 0

    if a.text:
        text, stem = a.text, "reel"
    elif a.script:
        p = Path(a.script)
        text, stem = p.read_text(encoding="utf-8"), p.stem
    else:
        ap.error("give a script file or --text")

    cfg = Config(voice=a.voice, rate=a.rate, pitch=a.pitch, images_dir=a.images,
                 pexels_query=a.query, music=a.music, music_volume=a.music_volume,
                 words_per_line=a.words_per_line, font_size=a.font_size,
                 uppercase=a.uppercase, fps=a.fps, keep_work=a.keep_work)
    if cfg.music and not Path(cfg.music).exists():
        ap.error(f"music file not found: {cfg.music}")

    from reelgen.pipeline import make_reel
    out = Path(a.out) if a.out else Path("output") / f"{stem}.mp4"
    make_reel(text, out, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
