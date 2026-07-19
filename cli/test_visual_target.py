"""Tests for visual target candidate generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from visual_target import (
    apply_visual_target_pick,
    build_candidate_prompts,
    build_visual_target_plan,
    default_output_dir,
    generate_visual_targets,
    load_visual_target_manifest,
)


@pytest.fixture
def example_brief(tmp_path: Path) -> Path:
    brief = {
        "project": {
            "title": "Dino Scavenger",
            "description": "Side-scrolling scavenger with raptor companion.",
            "art_direction": "Pixel art, warm desert palette.",
            "genre": "side_scroller",
            "gameplay_loop": "Collect scraps while avoiding hazards.",
            "session_goal": "Fill the scrap meter before sunset.",
            "viewport": {"width": 1280, "height": 720},
        },
        "assets": [
            {
                "id": "player",
                "type": "character",
                "usage": "player_idle",
                "generate_method": "image",
            }
        ],
    }
    path = tmp_path / "dino-brief.json"
    path.write_text(json.dumps(brief), encoding="utf-8")
    return path


def test_build_candidate_prompts_count(example_brief: Path) -> None:
    prompts = build_candidate_prompts(example_brief, count=3)
    assert len(prompts) == 3
    assert prompts[0]["id"] == "a"
    text = prompts[0]["prompt"].lower()
    assert "screenshot" in text or "framebuffer" in text
    assert "use case:" in text
    assert "art direction" in text or "style lock" in text or "pixel" in text


def test_default_output_dir(example_brief: Path) -> None:
    out = default_output_dir(example_brief)
    assert "dino-scavenger" in str(out)
    assert out.name == "visual-target"


def test_build_visual_target_plan_scaffold(example_brief: Path) -> None:
    plan = build_visual_target_plan(
        example_brief,
        {"id": "a", "label": "opening_moment", "focus": "Opening scene."},
        craft=False,
        config={},
    )
    assert plan["kind"] == "visual_target"
    assert plan["prompt_source"] == "scaffold"
    assert plan["validation"]["skip_validate"] is True
    assert "screenshot" in plan["prompt"].lower()
    assert "Use case:" in plan["prompt"]


def test_generate_dry_run_writes_handoffs(example_brief: Path, tmp_path: Path) -> None:
    out = tmp_path / "visual-target"
    plans = tmp_path / "plans"
    manifest = generate_visual_targets(
        example_brief,
        out,
        count=2,
        config={},
        dry_run=True,
        craft=False,
        plans_dir=plans,
    )
    assert len(manifest["candidates"]) == 2
    assert manifest["craft"] is False
    for c in manifest["candidates"]:
        assert Path(c["handoff_path"]).is_file()
        handoff = json.loads(Path(c["handoff_path"]).read_text(encoding="utf-8"))
        assert handoff["consumer_role"] == "image-generator"
        assert handoff["plan"]["kind"] == "visual_target"


def test_image_size_from_handoff() -> None:
    from plan_io import image_size_from_handoff

    handoff = {"plan": {"image_size": "1280x720", "asset_type": "visual_target"}}
    assert image_size_from_handoff(handoff) == "1280x720"
    assert image_size_from_handoff({"plan": {}}) is None


def test_apply_pick_updates_brief(example_brief: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "visual-target"
    out_dir.mkdir()
    fake_png = out_dir / "candidate_b.png"
    fake_png.write_bytes(b"\x89PNG\r\n")

    manifest = {
        "viewport_size": "1280x720",
        "candidates": [
            {"id": "a", "label": "opening", "path": str(out_dir / "candidate_a.png")},
            {"id": "b", "label": "action", "path": str(fake_png), "prompt_summary": "action"},
        ]
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = apply_visual_target_pick(example_brief, "b", manifest_path)
    assert result["selected_id"] == "b"

    data = json.loads(example_brief.read_text(encoding="utf-8"))
    assert data["project"]["visual_reference"]
    assert data["project"]["visual_target"]["selected_id"] == "b"
    assert data["project"]["visual_target"]["image_size"] == "1280x720"

    assert len(data["project"]["visual_target"]["candidates"]) == 2

    updated = load_visual_target_manifest(manifest_path)
    assert updated["selected_id"] == "b"
    assert (out_dir / "selected.png").is_file()
