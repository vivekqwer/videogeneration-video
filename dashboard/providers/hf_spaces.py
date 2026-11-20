"""Built-in free providers running on Hugging Face ZeroGPU Spaces."""
from __future__ import annotations

from pathlib import Path

from ..settings import dims
from .base import GenRequest, Provider
from .hf_common import client, extract_file, file_arg, friendly, keyframe, save_video

NEG = "worst quality, inconsistent motion, blurry, jittery, distorted, watermark, text"


class HFSpaceProvider(Provider):
    space = ""
    free = True

    @property
    def source(self):  # type: ignore[override]
        return f"https://huggingface.co/spaces/{self.space}"

    def call(self, req: GenRequest, out: Path, log):
        raise NotImplementedError

    def generate(self, req: GenRequest, out: Path, log) -> Path:
        log(f"Connecting to {self.space} ...")
        try:
            res = self.call(req, out, log)
        except Exception as e:
            raise friendly(e) from e
        log("Video download ho rahi hai...")
        return save_video(extract_file(res), out)

    def start_image(self, req: GenRequest, w: int, h: int, out: Path, log) -> str:
        if req.image:
            return req.image
        return keyframe(req.prompt, w, h, out.with_name(out.stem + "_key.png"), log)


class LTXVideo(HFSpaceProvider):
    id, name, kind = "ltx-video", "LTX-Video 0.9.8 (distilled)", "t2v"
    space = "Lightricks/ltx-video-distilled"
    max_duration = 8
    notes = "Fast (~20s). Text ya image se video."

    def call(self, req, out, log):
        w, h = dims(req.aspect, 832, 32)
        common = dict(negative_prompt=req.negative_prompt or NEG, input_video_filepath=None,
                      height_ui=h, width_ui=w, duration_ui=min(req.duration, self.max_duration),
                      ui_frames_to_use=9, seed_ui=max(req.seed, 0), randomize_seed=req.seed < 0,
                      ui_guidance_scale=1, improve_texture_flag=True)
        c = client(self.space)
        log("GPU par generate ho raha hai...")
        if req.image:
            return c.predict(prompt=req.prompt, input_image_filepath=file_arg(req.image),
                             mode="image-to-video", api_name="/image_to_video", **common)
        return c.predict(prompt=req.prompt, input_image_filepath=None, mode="text-to-video",
                         api_name="/text_to_video", **common)


class LTX23(HFSpaceProvider):
    id, name, kind = "ltx-2.3", "LTX-2.3 (video + audio)", "i2v"
    space = "Lightricks/LTX-2-3"
    max_duration = 5
    notes = "Pehle FLUX se start image, phir video. Audio bhi banata hai."

    def call(self, req, out, log):
        w, h = dims(req.aspect, 1024, 64)
        img = self.start_image(req, w, h, out, log)
        log("GPU par generate ho raha hai...")
        return client(self.space).predict(
            input_image=file_arg(img), prompt=req.prompt, duration=min(req.duration, self.max_duration),
            enhance_prompt=True, seed=max(req.seed, 0), randomize_seed=req.seed < 0,
            height=h, width=w, api_name="/generate_video")


class Wan22Fast(HFSpaceProvider):
    id, name, kind = "wan-2.2-5b", "Wan 2.2 5B (fast)", "i2v"
    space = "AlekseyCalvin/FastWan2.2_5B_TI2V"
    max_duration = 4
    notes = "FLUX start image + Wan 2.2 motion."

    def call(self, req, out, log):
        w, h = dims(req.aspect, 832, 32)
        img = self.start_image(req, w, h, out, log)
        log("GPU par generate ho raha hai...")
        return client(self.space).predict(
            input_image=file_arg(img), prompt=req.prompt, height=h, width=w,
            negative_prompt=req.negative_prompt or NEG,
            duration_seconds=min(req.duration, self.max_duration), api_name="/generate_video")


class Hunyuan15(HFSpaceProvider):
    id, name, kind = "hunyuan-1.5", "HunyuanVideo 1.5", "i2v"
    space = "multimodalart/Hunyuan-Video-1-5"
    max_duration = 5
    notes = "FLUX start image + Hunyuan motion. Slow but high quality."

    def call(self, req, out, log):
        w, h = dims(req.aspect, 832, 32)
        img = self.start_image(req, w, h, out, log)
        frames = int(min(req.duration, self.max_duration) * 24) // 4 * 4 + 1
        log("GPU par generate ho raha hai...")
        return client(self.space).predict(
            input_image=file_arg(img), prompt=req.prompt, length=frames, api_name="/generate")


class CogVideoX(HFSpaceProvider):
    id, name, kind = "cogvideox-5b", "CogVideoX 5B", "t2v"
    space = "zai-org/CogVideoX-5B-Space"
    max_duration = 6
    aspects = ("16:9",)
    notes = "Sirf 720x480 landscape, ~6s. Slow."

    def call(self, req, out, log):
        log("GPU par generate ho raha hai (1-3 min)...")
        return client(self.space).predict(
            prompt=req.prompt, image_input=None, video_input=None, video_strength=0.8,
            seed_value=req.seed, scale_status=False, rife_status=False, api_name="/generate")


class SelfForcing(HFSpaceProvider):
    id, name, kind = "self-forcing", "Self-Forcing (Wan 1.3B realtime)", "t2v"
    space = "multimodalart/self-forcing"
    max_duration = 5
    aspects = ("16:9",)
    notes = "Bahut fast, low resolution landscape."

    def call(self, req, out, log):
        log("GPU par generate ho raha hai...")
        job = client(self.space).submit(prompt=req.prompt, seed=req.seed, fps=15,
                                        api_name="/video_generation_handler_streaming")
        return job.result(timeout=600)


BUILTIN_HF = [LTXVideo(), LTX23(), Wan22Fast(), Hunyuan15(), CogVideoX(), SelfForcing()]
