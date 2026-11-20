# AI Video Studio

One dashboard to generate videos from many free AI models + a local text-to-reel engine.

## Features
- **Dashboard** (`http://127.0.0.1:8000`): prompt → pick one or many AI models → generate → preview, download, gallery.
- **Free AI models** via Hugging Face ZeroGPU Spaces: LTX-Video, LTX-2.3 (with audio), Wan 2.2 5B, HunyuanVideo 1.5, CogVideoX 5B, Self-Forcing.
  Image→video models get an auto start image from FLUX.1-schnell.
- **Discover new AI**: scans Hugging Face for video Spaces; **Connect** auto-maps the Space API into a new provider.
- **ReelGen** (local, unlimited): script → 9:16 reel with edge-tts voiceover + word-highlighted subtitles (Hindi/English).

## Setup
```powershell
pip install -r requirements.txt
copy .env.example .env   # add free HF_TOKEN for more GPU quota
python -m dashboard
```

ReelGen CLI:
```powershell
python main.py examples/sample_hi.txt -o output/reel.mp4
python main.py --list-voices hi-IN
```

## Limits (free)
- Hugging Face free GPU quota is per account per day (a few minutes of GPU). Without `HF_TOKEN` it is very small.
- edge-tts and HF Spaces need internet; prompts/scripts are sent to those services.
- Community Spaces can go offline or change their API; the dashboard shows the error.

## Structure
```
dashboard/        FastAPI app, job queue (SQLite), providers, static UI
  providers/      reel.py, hf_spaces.py (built-in), custom.py (auto-connect)
reelgen/          text -> reel engine (tts, subtitles, visuals, render)
main.py           ReelGen CLI
data/             jobs.db, media/ (generated, git-ignored)
```
