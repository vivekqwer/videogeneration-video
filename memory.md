# Project Memory: AI Video Studio

## Goal (user)
- One dashboard to generate videos from ~10 AI video models, **free**.
- Auto-connect new AI models as they appear.
- 9:16 reels from text with voiceover + subtitles (Hindi/English).
- More requirements pending ("aage aur bhi hai").

## Decisions
- **No ID/password auto-login** to AI websites (ToS, captcha/OTP, Claude cannot enter passwords). Use APIs / HF Spaces instead.
- Free route = Hugging Face ZeroGPU Spaces via `gradio_client`. Paid APIs (fal.ai, Runway, Veo, Kling) can be added later as providers with env keys.
- User PC: Intel HD 620, 8 GB RAM, no NVIDIA GPU -> no local video models.
- Stack: Python 3.13, FastAPI + vanilla JS dashboard, SQLite jobs, ffmpeg from `imageio-ffmpeg` (has libass/harfbuzz).
- Subtitles via ASS + libass (PIL has no raqm -> Hindi shaping breaks in PIL).
- Fonts: Arial Bold (en), Nirmala UI Bold (hi) copied from C:\Windows\Fonts.
- TTS: edge-tts. Default voices `en-US-AndrewNeural`, `hi-IN-MadhurNeural`; fallbacks Guy/Swara.

## Known issues / gotchas
- `en-US-AndrewMultilingualNeural` sometimes returns no audio -> not used.
- edge-tts intermittently fails on a sentence -> retry with backoff + fallback voice.
- ffmpeg runs with cwd=work dir (relative ass/fonts paths); all other paths must be absolute.
- Windows console cp1252 -> run server with `PYTHONUTF8=1`.
- Anonymous ZeroGPU quota is tiny (~2 runs); need free `HF_TOKEN` in `.env`.
- Generic auto-connect rejects Spaces with unknown required inputs (e.g. base64 custom APIs).

## Git
- Repo: https://github.com/vivekqwer/videogeneration-video (PUBLIC), branch `main`.
- Local identity: vivekqwer / GitHub noreply email (repo-local config).

## How to run
- Dashboard: `python -m dashboard` -> http://127.0.0.1:8000
- CLI reel: `python main.py examples/sample_hi.txt`

## FAQ
- Unlimited free AI video? No. Free = daily GPU quota per HF account.
- New AI model? Discover tab -> Connect (HF Spaces). Paid APIs need code provider + key.
