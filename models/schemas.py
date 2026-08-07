"""Core Pydantic schemas for Rada AI."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ── Enumerations ─────────────────────────────────────────────────────────────


class AnchorPoint(str, Enum):
    FLOOR = "floor"
    WALL = "wall"
    CEILING = "ceiling"
    SURFACE = "surface"   # placed on top of another asset
    FLOATING = "floating"


class StyleTag(str, Enum):
    COZY = "cozy"
    INDUSTRIAL = "industrial"
    CYBERPUNK = "cyberpunk"
    MINIMALIST = "minimalist"
    RUSTIC = "rustic"
    FUTURISTIC = "futuristic"
    FANTASY = "fantasy"
    REALISTIC = "realistic"


class GenerationStatus(str, Enum):
    PENDING = "pending"
    GENERATING_2D = "generating_2d"
    GENERATING_3D = "generating_3d"
    TAGGING = "tagging"
    INDEXING = "indexing"
    COMPLETE = "complete"
    FAILED = "failed"


# ── Spatial primitives ────────────────────────────────────────────────────────


class Vec3(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class BoundingBox(BaseModel):
    min: Vec3 = Field(default_factory=Vec3)
    max: Vec3 = Field(default_factory=Vec3)


# ── Asset Metadata ────────────────────────────────────────────────────────────


class AssetMetadata(BaseModel):
    """Represents a single 3-D asset stored in the vector database."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str

    # file locations (relative to /storage root)
    glb_path: str | None = None
    obj_path: str | None = None
    preview_image_path: str | None = None

    # semantic tags
    style_tags: list[StyleTag] = Field(default_factory=list)
    category: str = ""                 # e.g. "furniture", "prop", "architecture"
    anchor_point: AnchorPoint = AnchorPoint.FLOOR
    indoor: bool = True

    # physics / placement hints
    bounding_box: BoundingBox = Field(default_factory=BoundingBox)
    collision_radius: float = 0.5      # metres

    # provenance
    source_prompt: str = ""
    generated: bool = True             # False = manually imported asset
    embedding: list[float] = Field(default_factory=list, exclude=True)

    model_config = {"use_enum_values": True}


# ── Scene Graph ───────────────────────────────────────────────────────────────


class AssetPlacement(BaseModel):
    """One asset instance placed in world space."""

    asset_id: UUID
    asset_name: str                    # denormalised for readability
    position: Vec3 = Field(default_factory=Vec3)
    rotation: Vec3 = Field(default_factory=Vec3)   # Euler angles (degrees)
    scale: Vec3 = Field(default_factory=lambda: Vec3(x=1, y=1, z=1))
    glb_url: str | None = None         # resolved at render time
    metadata: dict[str, Any] = Field(default_factory=dict)


class SceneGraph(BaseModel):
    """Complete scene description ready for Three.js / Unreal export."""

    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    style: StyleTag | None = None
    ambient_light_intensity: float = Field(default=0.8, ge=0.0, le=10.0)
    background_color: str = "#1a1a2e"  # hex colour

    assets: list[AssetPlacement] = Field(default_factory=list)

    # room / environment bounds
    room_dimensions: Vec3 = Field(
        default_factory=lambda: Vec3(x=10.0, y=3.0, z=10.0)
    )

    model_config = {"use_enum_values": True}


# ── API Request / Response models ────────────────────────────────────────────


class GenerationRequest(BaseModel):
    """User-facing request to generate a full scene."""

    prompt: str = Field(..., min_length=3, max_length=2000)
    style: StyleTag | None = None
    room_width: float = Field(default=10.0, gt=0, le=100)
    room_depth: float = Field(default=10.0, gt=0, le=100)
    room_height: float = Field(default=3.0, gt=0, le=20)
    max_assets: int = Field(default=12, ge=1, le=50)
    force_regenerate: bool = False     # bypass vector-DB cache

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, v: str) -> str:
        return v.strip()

    model_config = {"use_enum_values": True}


class GenerationResponse(BaseModel):
    job_id: UUID
    status: GenerationStatus
    scene_graph: SceneGraph | None = None
    error: str | None = None
    duration_seconds: float | None = None


class AssetSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)
    style: StyleTag | None = None
    anchor: AnchorPoint | None = None
    indoor_only: bool = True


class AssetSearchResponse(BaseModel):
    results: list[AssetMetadata]
    total: int
