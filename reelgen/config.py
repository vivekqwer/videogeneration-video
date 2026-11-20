from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    width: int = 1080
    height: int = 1920
    fps: int = 30

    # Voice (edge-tts). None -> picked automatically from script language.
    voice: str | None = None
    rate: str = "+5%"
    pitch: str = "+0Hz"
    scene_gap: float = 0.25   # silence between scenes (s)
    tail: float = 0.6         # silence at the end (s)

    # Subtitles
    words_per_line: int = 3
    max_chars_per_line: int = 18
    font_size: int = 92
    uppercase: bool = False
    subtitle_margin_v: int = 620   # px from bottom
    highlight_color: str = "&H0000E5FF&"  # ASS BGR -> yellow

    # Visuals
    images_dir: Path | None = None
    pexels_query: str | None = None
    darken: float = 0.72      # brightness multiplier for photos
    crossfade: float = 0.3    # seconds

    # Audio
    music: Path | None = None
    music_volume: float = 0.12

    # Encoding
    crf: int = 20
    preset: str = "veryfast"

    keep_work: bool = False
    extra: dict = field(default_factory=dict)


DEFAULT_VOICES = {
    "hi": "hi-IN-MadhurNeural",
    "en": "en-US-AndrewNeural",
}

# Used if the chosen voice returns no audio for a sentence.
FALLBACK_VOICES = {
    "hi": "hi-IN-SwaraNeural",
    "en": "en-US-GuyNeural",
}

FONTS = {
    # family name used in ASS, file in C:\Windows\Fonts
    "hi": ("Nirmala UI", "NirmalaB.ttf"),
    "en": ("Arial", "arialbd.ttf"),
}
