"""Stable Diffusion XL image generation service."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import torch
from diffusers import StableDiffusionXLPipeline
from loguru import logger
from PIL import Image


class DiffusionService:
    """Generates 2-D concept images from text prompts using SDXL."""

    _MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"
    _OUTPUT_DIR = Path("./storage/generated/images")

    def __init__(self, model_id: str | None = None) -> None:
        self._model_id = model_id or self._MODEL_ID
        self._pipe: StableDiffusionXLPipeline | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def load(self) -> None:
        if self._pipe is not None:
            return
        logger.info("Loading SDXL pipeline from '{}'…", self._model_id)
        await asyncio.to_thread(self._load_sync)
        self._OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("SDXL pipeline ready")

    def _load_sync(self) -> None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        self._pipe = StableDiffusionXLPipeline.from_pretrained(
            self._model_id,
            torch_dtype=dtype,
            use_safetensors=True,
            variant="fp16" if device == "cuda" else None,
        ).to(device)
        if device == "cuda":
            self._pipe.enable_xformers_memory_efficient_attention()

    async def unload(self) -> None:
        self._pipe = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # ── Generation ─────────────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "low quality, blurry, deformed",
        width: int = 1024,
        height: int = 1024,
        steps: int = 30,
        guidance_scale: float = 7.5,
    ) -> Path:
        if self._pipe is None:
            raise RuntimeError("DiffusionService not loaded; call load() first")

        logger.info("Generating image for prompt: '{}'", prompt[:80])
        image: Image.Image = await asyncio.to_thread(
            self._generate_sync,
            prompt,
            negative_prompt,
            width,
            height,
            steps,
            guidance_scale,
        )
        out_path = self._OUTPUT_DIR / f"{uuid4().hex}.png"
        image.save(out_path)
        logger.info("Saved generated image → {}", out_path)
        return out_path

    def _generate_sync(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        guidance_scale: float,
    ) -> Image.Image:
        result = self._pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
        )
        return result.images[0]
