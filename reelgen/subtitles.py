"""Reels-style ASS subtitles: short chunks, current word highlighted, pop-in."""
from pathlib import Path

from .tts import SceneAudio, Word

BASE_COLOR = "&H00FFFFFF&"
LINGER = 0.35  # seconds a chunk stays after its last word


def _ts(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def _chunk(words: list[Word], max_words: int, max_chars: int) -> list[list[Word]]:
    chunks, cur = [], []
    for w in words:
        length = sum(len(x.text) + 1 for x in cur) + len(w.text)
        long_pause = cur and (w.start - cur[-1].end) > 0.6
        if cur and (len(cur) >= max_words or length > max_chars or long_pause):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if w.text and w.text[-1] in ".!?,।;:":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(scenes: list[SceneAudio], out: Path, *, font: str, size: int, width: int,
              height: int, margin_v: int, max_words: int, max_chars: int,
              uppercase: bool, highlight: str) -> Path:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Reel,{font},{size},{BASE_COLOR},{BASE_COLOR},&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,7,3,2,70,70,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    all_chunks: list[list[Word]] = []
    for sc in scenes:
        all_chunks.extend(_chunk(sc.words, max_words, max_chars))

    for ci, chunk in enumerate(all_chunks):
        next_start = all_chunks[ci + 1][0].start if ci + 1 < len(all_chunks) else None
        texts = [_esc(w.text.upper() if uppercase else w.text) for w in chunk]
        for wi, w in enumerate(chunk):
            start = w.start
            if wi + 1 < len(chunk):
                end = chunk[wi + 1].start
            else:
                end = w.end + LINGER
                if next_start is not None:
                    end = min(end, next_start)
            if end <= start:
                continue
            parts = [
                f"{{\\c{highlight}}}{t}{{\\c{BASE_COLOR}}}" if j == wi else t
                for j, t in enumerate(texts)
            ]
            pop = "{\\fscx82\\fscy82\\t(0,90,\\fscx100\\fscy100)}" if wi == 0 else ""
            lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Reel,,0,0,0,,{pop}{' '.join(parts)}")

    out.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return out
