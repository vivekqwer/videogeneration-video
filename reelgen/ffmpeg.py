import os
import shutil
import subprocess


def ffmpeg_exe() -> str:
    """FFMPEG_BINARY env > bundled imageio-ffmpeg (has libass) > PATH."""
    env = os.environ.get("FFMPEG_BINARY")
    if env:
        return env
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        exe = shutil.which("ffmpeg")
        if exe:
            return exe
    raise RuntimeError("ffmpeg not found. Run: pip install imageio-ffmpeg")


def decode_to_pcm(path: str, sample_rate: int) -> bytes:
    """Decode any audio file to mono s16le PCM bytes."""
    cmd = [ffmpeg_exe(), "-v", "error", "-i", str(path),
           "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", "-"]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed: {res.stderr.decode(errors='ignore')}")
    return res.stdout
