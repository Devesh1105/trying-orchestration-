"""Vision-Language tagging service (LLaVA via Ollama, with GPT-4V fallback)."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import httpx
from loguru import logger
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from models.schemas import AnchorPoint, AssetMetadata, StyleTag

_OLLAMA_URL = "http://localhost:11434"
_LLAVA_MODEL = "llava:13b"

_TAG_SYSTEM_PROMPT = """\
You are a 3D asset cataloguer for a spatial AI engine.
Given an image of a 3D object or scene prop, output ONLY valid JSON (no markdown)
with these keys:
  name         : short human name (string)
  description  : one sentence (string)
  category     : one of [furniture, prop, architecture, vegetation, lighting, vehicle, character, other]
  anchor_point : one of [floor, wall, ceiling, surface, floating]
  indoor       : boolean
  style_tags   : array of 0-3 items from [cozy, industrial, cyberpunk, minimalist, rustic, futuristic, fantasy, realistic]
"""


class TaggerService:
    def __init__(
        self,
        use_ollama: bool = True,
        openai_api_key: str | None = None,
        openai_model: str = "gpt-4o",
    ) -> None:
        self._use_ollama = use_ollama
        self._openai_model = openai_model
        self._openai: AsyncOpenAI | None = (
            AsyncOpenAI(api_key=openai_api_key) if openai_api_key else None
        )

    async def tag_asset(
        self, image_path: Path, source_prompt: str = ""
    ) -> dict:
        """Return raw tag dict; caller merges into AssetMetadata."""
        encoded = self._encode_image(image_path)
        if self._use_ollama:
            try:
                return await self._tag_ollama(encoded)
            except Exception as exc:
                logger.warning("Ollama tagger failed ({}); trying OpenAI", exc)

        if self._openai:
            return await self._tag_openai(encoded)

        logger.warning("No tagger available; returning defaults")
        return self._defaults(source_prompt)

    # ── Ollama / LLaVA ────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def _tag_ollama(self, b64_image: str) -> dict:
        payload = {
            "model": _LLAVA_MODEL,
            "prompt": "Analyse this 3D asset image and output the JSON as instructed.",
            "system": _TAG_SYSTEM_PROMPT,
            "images": [b64_image],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{_OLLAMA_URL}/api/generate", json=payload)
            resp.raise_for_status()
        raw = resp.json()["response"]
        return self._parse_json(raw)

    # ── OpenAI / GPT-4V ───────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=16))
    async def _tag_openai(self, b64_image: str) -> dict:
        if not self._openai:
            raise RuntimeError("OpenAI client not configured")
        response = await self._openai.chat.completions.create(
            model=self._openai_model,
            messages=[
                {"role": "system", "content": _TAG_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}"
                            },
                        },
                        {
                            "type": "text",
                            "text": "Analyse this 3D asset image and output the JSON.",
                        },
                    ],
                },
            ],
            max_tokens=512,
        )
        raw = response.choices[0].message.content or ""
        return self._parse_json(raw)

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _encode_image(path: Path) -> str:
        return base64.b64encode(path.read_bytes()).decode()

    @staticmethod
    def _parse_json(text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"No JSON object found in tagger response: {text!r}")
        return json.loads(text[start:end])

    @staticmethod
    def _defaults(source_prompt: str) -> dict:
        return {
            "name": source_prompt[:40] or "unnamed asset",
            "description": "Auto-generated asset",
            "category": "prop",
            "anchor_point": AnchorPoint.FLOOR,
            "indoor": True,
            "style_tags": [],
        }
