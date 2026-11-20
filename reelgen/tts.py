"""Voiceover via edge-tts (free Microsoft neural voices, needs internet).

Each scene is synthesized separately so scene boundaries are exact; audio is
decoded to PCM and concatenated with small gaps. Word timings come from
edge-tts WordBoundary events and are shifted onto the global timeline.
"""
import asyncio
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path

import edge_tts

from .ffmpeg import decode_to_pcm

SAMPLE_RATE = 24000
BYTES_PER_SAMPLE = 2


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class SceneAudio:
    start: float
    end: float
    words: list[Word] = field(default_factory=list)


async def _synth(text: str, voice: str, rate: str, pitch: str, mp3: Path) -> list[Word]:
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    words: list[Word] = []
    with open(mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / 1e7
                words.append(Word(chunk["text"], s, s + chunk["duration"] / 1e7))
    return words


def _synth_retry(text, voice, rate, pitch, mp3, tries=3, fallback=None) -> list[Word]:
    last = None
    for v in [voice] + ([fallback] if fallback and fallback != voice else []):
        for attempt in range(tries):
            try:
                words = asyncio.run(_synth(text, v, rate, pitch, mp3))
                if v != voice:
                    print(f"  [tts] used fallback voice {v}")
                return words
            except Exception as e:  # network hiccups / NoAudioReceived
                last = e
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"TTS failed for: {text[:60]!r}: {last}")


def _silence(seconds: float) -> bytes:
    return b"\x00\x00" * int(seconds * SAMPLE_RATE)


def synthesize(texts: list[str], voice: str, rate: str, pitch: str, work: Path,
               gap: float, tail: float, fallback: str | None = None
               ) -> tuple[Path, list[SceneAudio], float]:
    """Returns (voice.wav, per-scene timings, total duration)."""
    pcm = bytearray()
    scenes: list[SceneAudio] = []
    for i, text in enumerate(texts):
        mp3 = work / f"scene_{i:03d}.mp3"
        words = _synth_retry(text, voice, rate, pitch, mp3, fallback=fallback)
        start = len(pcm) / BYTES_PER_SAMPLE / SAMPLE_RATE
        data = decode_to_pcm(mp3, SAMPLE_RATE)
        pcm += data
        end = len(pcm) / BYTES_PER_SAMPLE / SAMPLE_RATE
        scenes.append(SceneAudio(start, end, [Word(w.text, w.start + start, w.end + start) for w in words]))
        pcm += _silence(gap if i < len(texts) - 1 else tail)
        print(f"  [tts] scene {i + 1}/{len(texts)}  {end - start:.2f}s  {len(words)} words")

    out = work / "voice.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(BYTES_PER_SAMPLE)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(bytes(pcm))
    total = len(pcm) / BYTES_PER_SAMPLE / SAMPLE_RATE
    return out, scenes, total


async def _list_voices(prefix: str) -> list[dict]:
    voices = await edge_tts.list_voices()
    return [v for v in voices if v["Locale"].lower().startswith(prefix.lower())]


def list_voices(prefix: str = "") -> list[dict]:
    return asyncio.run(_list_voices(prefix))
