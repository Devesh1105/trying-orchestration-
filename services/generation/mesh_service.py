"""Image-to-3D mesh service using TripoSR."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from uuid import uuid4

import numpy as np
import rembg
import trimesh
from loguru import logger
from PIL import Image


class MeshService:
    """Converts a 2-D PNG to a GLB mesh via TripoSR (spawned subprocess)."""

    _OUTPUT_DIR = Path("./storage/generated/meshes")
    # TripoSR run script path (populated after install_triposr.sh runs)
    _TRIPOSR_RUN = Path("./vendor/TripoSR/run.py")

    def __init__(self) -> None:
        self._OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────

    async def image_to_glb(self, image_path: Path) -> Path:
        """Remove background, run TripoSR, return path to .glb file."""
        clean_path = await asyncio.to_thread(self._remove_background, image_path)
        glb_path = await asyncio.to_thread(self._run_triposr, clean_path)
        return glb_path

    # ── Internal ───────────────────────────────────────────────────────────

    def _remove_background(self, image_path: Path) -> Path:
        logger.info("Removing background from '{}'", image_path.name)
        img = Image.open(image_path).convert("RGBA")
        out = rembg.remove(img)
        clean_path = image_path.with_suffix(".nobg.png")
        out.save(clean_path)
        return clean_path

    def _run_triposr(self, image_path: Path) -> Path:
        out_dir = self._OUTPUT_DIR / uuid4().hex
        out_dir.mkdir(parents=True, exist_ok=True)

        if not self._TRIPOSR_RUN.exists():
            raise FileNotFoundError(
                f"TripoSR not found at {self._TRIPOSR_RUN}. "
                "Run scripts/install_triposr.sh first."
            )

        cmd = [
            "python",
            str(self._TRIPOSR_RUN),
            str(image_path),
            "--output-dir",
            str(out_dir),
            "--chunk-size",
            "8192",
        ]
        logger.info("Running TripoSR: {}", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise RuntimeError(f"TripoSR failed:\n{result.stderr}")

        obj_files = list(out_dir.glob("**/*.obj"))
        if not obj_files:
            raise RuntimeError("TripoSR produced no .obj output")

        glb_path = out_dir / "mesh.glb"
        mesh = trimesh.load(str(obj_files[0]))
        mesh.export(str(glb_path))
        logger.info("Mesh exported → {}", glb_path)
        return glb_path
