"""Schema validation tests."""

import pytest
from pydantic import ValidationError

from models.schemas import (
    AnchorPoint,
    AssetMetadata,
    AssetPlacement,
    GenerationRequest,
    SceneGraph,
    StyleTag,
    Vec3,
)


def test_generation_request_valid():
    req = GenerationRequest(prompt="A cozy reading nook")
    assert req.prompt == "A cozy reading nook"
    assert req.max_assets == 12


def test_generation_request_strips_whitespace():
    req = GenerationRequest(prompt="  cyberpunk office  ")
    assert req.prompt == "cyberpunk office"


def test_generation_request_too_short():
    with pytest.raises(ValidationError):
        GenerationRequest(prompt="hi")


def test_asset_metadata_defaults():
    asset = AssetMetadata(name="Chair", description="A wooden chair")
    assert asset.anchor_point == AnchorPoint.FLOOR
    assert asset.indoor is True
    assert asset.generated is True


def test_scene_graph_roundtrip():
    from uuid import uuid4

    asset_id = uuid4()
    placement = AssetPlacement(
        asset_id=asset_id,
        asset_name="Desk",
        position=Vec3(x=1.0, y=0.0, z=2.5),
        rotation=Vec3(x=0.0, y=45.0, z=0.0),
    )
    scene = SceneGraph(
        title="My Office",
        description="A cozy home office",
        style=StyleTag.COZY,
        assets=[placement],
    )
    data = scene.model_dump()
    restored = SceneGraph(**data)
    assert restored.title == "My Office"
    assert len(restored.assets) == 1
    assert restored.assets[0].position.x == 1.0
