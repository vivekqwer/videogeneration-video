# Build Log

## 2026-11-20: ReelGen engine
- Built `reelgen/`: script parser, edge-tts voiceover with word timings, ASS subtitles (word highlight + pop), Ken Burns photos / animated gradients, ffmpeg pipe renderer, CLI `main.py`.
- Fixes: multilingual voice returned no audio (switched default + fallback voice); ffmpeg relative path bug (absolute paths).
- Verified: `examples/sample_en.txt` -> 1080x1920, 30fps, 19.7s, AAC audio, subtitles OK. Render ~105s for 20s video.

## 2026-11-21: Git setup
- `git init -b main`, remote `origin` -> vivekqwer/videogeneration-video (public, empty), `.gitignore`.

## 2026-11-21: AI Video Studio dashboard
- FastAPI backend (`dashboard/`), SQLite job store, one worker per provider.
- Providers: ReelGen (local), LTX-Video, LTX-2.3, Wan 2.2 5B, HunyuanVideo 1.5, CogVideoX 5B, Self-Forcing (HF ZeroGPU). I2V models get FLUX.1-schnell start image.
- Discover + auto-connect: scans HF Spaces, inspects API, saves generic provider to `data/custom_providers.json`.
- UI: Generate (multi-model), Gallery (search/filter/download/delete), AI Models, Discover.

### Test results
- LTX-Video direct call: OK, 3s clip in 21s (anonymous).
- ReelGen via dashboard (Hindi): OK, 26s, Devanagari subtitles render correctly.
- Discover: 40 Spaces with runtime status. Connect `zerogpu-aoti/wan2-2-fp8da-aoti-faster`: OK. `prithivMLmods/Wan2.2-Fast`: correctly rejected (custom API).
- LTX / Wan 2.2 / Self-Forcing via dashboard: blocked by anonymous ZeroGPU quota (exhausted during testing) -> error shown in UI correctly. **Not yet verified end-to-end with HF_TOKEN.** LTX-2.3, Hunyuan 1.5, CogVideoX not yet run.

### Pending
- User to add free `HF_TOKEN` in `.env`, then re-test all HF providers.
- First commit/push (repo is public) awaiting user OK.
- Paid API providers (fal.ai etc.) when needed.
