"""Tests for visual target candidate generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from visual_target import (
    apply_visual_target_pick,
    build_candidate_prompts,
    default_output_dir,
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
    assert "art direction" in prompts[0]["prompt"].lower() or "Art direction" in prompts[0]["prompt"]
    assert "in-game screenshot" in prompts[0]["prompt"].lower()


def test_default_output_dir(example_brief: Path) -> None:
    out = default_output_dir(example_brief)
    assert "dino-scavenger" in str(out)
    assert out.name == "visual-target"


def test_apply_pick_updates_brief(example_brief: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "visual-target"
    out_dir.mkdir()
    fake_png = out_dir / "candidate_b.png"
    fake_png.write_bytes(b"\x89PNG\r\n")

    manifest = {
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
    assert len(data["project"]["visual_target"]["candidates"]) == 2

    updated = load_visual_target_manifest(manifest_path)
    assert updated["selected_id"] == "b"
    assert (out_dir / "selected.png").is_file()
