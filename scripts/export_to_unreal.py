"""
Export a Rada AI scene graph to Unreal Engine 5 via the Python Editor API.

Usage (run inside UE5's embedded Python interpreter via Editor Utility Script):
    import sys
    sys.path.insert(0, "/path/to/rada-ai")
    from scripts.export_to_unreal import export_scene
    export_scene("path/to/scene_graph.json", "/Game/RadaAI/Scenes/MyScene")

Or from the CLI (dry-run, no UE required):
    python scripts/export_to_unreal.py scene_graph.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


# ── Unreal import guard ───────────────────────────────────────────────────────

try:
    import unreal  # type: ignore[import]
    _IN_UNREAL = True
except ImportError:
    _IN_UNREAL = False


# ── Core export logic ─────────────────────────────────────────────────────────


def export_scene(
    scene_graph_path: str,
    unreal_destination: str = "/Game/RadaAI/Scenes",
    dry_run: bool = False,
) -> None:
    """
    Parse a Rada AI scene-graph JSON and place assets in an Unreal level.

    Args:
        scene_graph_path:  Path to the .json file produced by the backend.
        unreal_destination: UE content-browser path where imported assets live.
        dry_run:           Print placement commands without executing them.
    """
    scene = _load_scene(scene_graph_path)
    placements = scene.get("assets", [])
    print(f"[RadaAI] Exporting scene '{scene['title']}' — {len(placements)} assets")

    if dry_run or not _IN_UNREAL:
        _print_dry_run(scene, placements)
        return

    _execute_in_unreal(scene, placements, unreal_destination)


# ── Unreal execution ──────────────────────────────────────────────────────────


def _execute_in_unreal(
    scene: dict,
    placements: list[dict],
    destination: str,
) -> None:
    editor = unreal.EditorLevelLibrary  # type: ignore[attr-defined]
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()  # type: ignore[attr-defined]

    with unreal.ScopedEditorTransaction("Rada AI Scene Import") as _:  # type: ignore[attr-defined]
        for item in placements:
            glb_path = item.get("glb_url") or item.get("glb_path")
            asset_name = item["asset_name"]

            # Import GLB → UE static mesh
            ue_asset_path = _import_glb(
                glb_path, asset_name, destination, asset_tools
            )
            if ue_asset_path is None:
                print(f"  [WARN] Skipping '{asset_name}' — no GLB available")
                continue

            # Spawn actor
            location = _to_ue_vector(item["position"])
            rotation = _to_ue_rotator(item["rotation"])
            scale = _to_ue_vector(item["scale"], default=1.0)

            actor = editor.spawn_actor_from_object(
                unreal.load_asset(ue_asset_path),
                location,
            )
            if actor:
                actor.set_actor_rotation(rotation, teleport_physics=True)
                actor.set_actor_scale3d(scale)
                actor.set_actor_label(asset_name)
                print(f"  [OK] Placed '{asset_name}' at {location}")

    print("[RadaAI] Scene export complete.")


def _import_glb(
    glb_path: str | None,
    asset_name: str,
    destination: str,
    asset_tools: Any,
) -> str | None:
    if not glb_path or not Path(glb_path).exists():
        return None

    import_task = unreal.AssetImportTask()  # type: ignore[attr-defined]
    import_task.filename = str(Path(glb_path).resolve())
    import_task.destination_path = destination
    import_task.destination_name = _sanitise_name(asset_name)
    import_task.replace_existing = True
    import_task.automated = True
    import_task.save = True

    asset_tools.import_asset_tasks([import_task])
    return f"{destination}/{import_task.destination_name}"


# ── Coordinate conversion (Rada → Unreal) ────────────────────────────────────
# Rada AI:  right-handed, Y-up, metres
# Unreal:   left-handed, Z-up, centimetres


def _to_ue_vector(
    v: dict, default: float = 0.0
) -> "unreal.Vector":  # type: ignore[name-defined]
    x = float(v.get("x", default)) * 100  # m → cm
    y = float(v.get("z", default)) * 100  # swap Y/Z axis
    z = float(v.get("y", default)) * 100
    return unreal.Vector(x, y, z)  # type: ignore[attr-defined]


def _to_ue_rotator(v: dict) -> "unreal.Rotator":  # type: ignore[name-defined]
    # Rada rotation is Euler XYZ degrees; Unreal Rotator is pitch/yaw/roll
    pitch = float(v.get("x", 0.0))
    yaw   = float(v.get("y", 0.0))
    roll  = float(v.get("z", 0.0))
    return unreal.Rotator(pitch, yaw, roll)  # type: ignore[attr-defined]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _load_scene(path: str) -> dict:
    data = Path(path).read_text(encoding="utf-8")
    return json.loads(data)


def _sanitise_name(name: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name)[:60]


def _print_dry_run(scene: dict, placements: list[dict]) -> None:
    print(f"\n{'─'*60}")
    print(f"  DRY RUN — Scene: {scene['title']}")
    print(f"  Room: {scene['room_dimensions']}")
    print(f"{'─'*60}")
    for item in placements:
        pos = item["position"]
        rot = item["rotation"]
        print(
            f"  {item['asset_name']:<30}  "
            f"pos=({pos['x']:.2f}, {pos['y']:.2f}, {pos['z']:.2f})  "
            f"rot=({rot['x']:.0f}°, {rot['y']:.0f}°, {rot['z']:.0f}°)"
        )
    print(f"{'─'*60}\n")


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Rada AI scene to Unreal Engine 5")
    parser.add_argument("scene_json", help="Path to scene_graph.json")
    parser.add_argument(
        "--destination",
        default="/Game/RadaAI/Scenes",
        help="UE content-browser destination path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print placements without executing (no UE required)",
    )
    args = parser.parse_args()
    export_scene(args.scene_json, args.destination, dry_run=args.dry_run)
