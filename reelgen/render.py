"""Stream background frames into ffmpeg, burn ASS subtitles, mux audio."""
import bisect
import subprocess
import time
from pathlib import Path

from PIL import Image

from .ffmpeg import ffmpeg_exe


def scene_boundaries(scene_audio, total: float) -> list[float]:
    """Visual cut points: midway through the silence between scenes."""
    b = [0.0]
    for prev, cur in zip(scene_audio, scene_audio[1:]):
        b.append((prev.end + cur.start) / 2)
    b.append(total)
    return b


def render(bgs, bounds: list[float], total: float, work: Path, out: Path, cfg,
           voice_wav: Path, ass_file: str, fonts_dir: str) -> None:
    w, h, fps = cfg.width, cfg.height, cfg.fps
    n_frames = int(round(total * fps))
    fade = cfg.crossfade

    cmd = [ffmpeg_exe(), "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
           "-i", str(Path(voice_wav).resolve())]
    vf = f"[0:v]ass={ass_file}:fontsdir={fonts_dir}[v]"
    if cfg.music:
        cmd += ["-stream_loop", "-1", "-i", str(Path(cfg.music).resolve())]
        filt = (f"{vf};[2:a]volume={cfg.music_volume}[m];"
                f"[1:a][m]amix=inputs=2:duration=first:normalize=0[a]")
        amap = "[a]"
    else:
        filt, amap = vf, "1:a"
    cmd += ["-filter_complex", filt, "-map", "[v]", "-map", amap,
            "-c:v", "libx264", "-preset", cfg.preset, "-crf", str(cfg.crf),
            "-pix_fmt", "yuv420p", "-r", str(fps),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", "-t", f"{total:.3f}", str(out.resolve())]

    proc = subprocess.Popen(cmd, cwd=str(work), stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    starts = bounds[:-1]
    t0 = time.time()
    try:
        for i in range(n_frames):
            t = i / fps
            k = max(0, bisect.bisect_right(starts, t) - 1)
            span = bounds[k + 1] - bounds[k]
            frame = bgs[k].frame((t - bounds[k]) / span)
            # crossfade from previous scene around the cut point
            if k > 0 and t < bounds[k] + fade / 2:
                a = (t - (bounds[k] - fade / 2)) / fade
                prev_span = bounds[k] - bounds[k - 1]
                prev = bgs[k - 1].frame(min(1.0, (t - bounds[k - 1]) / prev_span))
                frame = Image.blend(prev, frame, max(0.0, min(1.0, a)))
            elif k + 1 < len(bgs) and t > bounds[k + 1] - fade / 2:
                a = (t - (bounds[k + 1] - fade / 2)) / fade
                nxt = bgs[k + 1].frame(0.0)
                frame = Image.blend(frame, nxt, max(0.0, min(1.0, a)))
            proc.stdin.write(frame.tobytes())
            if i % (fps * 5) == 0:
                print(f"  [render] {i}/{n_frames} frames  ({time.time() - t0:.1f}s)")
        proc.stdin.close()
    except OSError:  # BrokenPipe / EINVAL on Windows when ffmpeg exits early
        pass
    err = proc.stderr.read().decode(errors="ignore")
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed:\n{err}")
    print(f"  [render] done {n_frames} frames in {time.time() - t0:.1f}s")
