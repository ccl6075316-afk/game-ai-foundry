"""Tests for brief frozen contract validation."""

from __future__ import annotations

import unittest

from brief import (
    AssetSpec,
    AssetType,
    ProjectContext,
    audit_brief_for_export,
    finalize_brief_export,
    validate_brief_for_export,
)
from display_size import DisplaySize
from test_fixtures import EXAMPLE_BRIEF, SMOKE_BRIEF, write_brief


class BriefContractTests(unittest.TestCase):
    def test_example_brief_passes_audit(self) -> None:
        from brief import load_brief_full

        project, assets, graphs = load_brief_full(EXAMPLE_BRIEF)
        self.assertEqual(audit_brief_for_export(project, assets, animation_graphs=graphs), [])

    def test_project_requires_gameplay_fields(self) -> None:
        project = ProjectContext(
            title="T",
            description="game",
            art_direction="art",
            dimension="2d",
        )
        asset = AssetSpec(
            name="hero",
            id="hero",
            type=AssetType.CHARACTER,
            usage="player_idle",
            usage_description="idle",
            display_size=DisplaySize(128, 128),
            description="hero",
        )
        gaps = audit_brief_for_export(project, [asset])
        self.assertTrue(any("genre" in g for g in gaps))
        self.assertTrue(any("gameplay_loop" in g for g in gaps))
        self.assertTrue(any("session_goal" in g for g in gaps))
        self.assertTrue(any("viewport" in g for g in gaps))
        self.assertTrue(any("controls" in g for g in gaps))

    def test_video_requires_player_facing_asset(self) -> None:
        project = ProjectContext(
            title="T",
            description="platformer",
            art_direction="flat",
            dimension="2d",
        )
        walk = AssetSpec(
            name="hero_walk",
            id="hero_walk",
            type=AssetType.CHARACTER,
            usage="vfx",
            usage_description="walk without player tag",
            display_size=DisplaySize(128, 128),
            description="walk",
            reference_asset="hero_ref",
            action="walking",
            animation_method="video",
        )
        ref = AssetSpec(
            name="hero_ref",
            id="hero_ref",
            type=AssetType.CHARACTER,
            usage="vfx",
            usage_description="ref",
            display_size=DisplaySize(128, 128),
            description="ref",
        )
        gaps = audit_brief_for_export(project, [ref, walk])
        self.assertTrue(any("player-facing" in g for g in gaps))

    def test_finalize_stamps_brief_meta(self) -> None:
        out = finalize_brief_export(SMOKE_BRIEF, source="brainstorm")
        self.assertIn("brief_meta", out)
        self.assertEqual(out["brief_meta"]["contract_version"], 1)
        self.assertEqual(out["brief_meta"]["source"], "brainstorm")
        self.assertTrue(out["brief_meta"]["frozen_at"])

    def test_validate_brief_file(self) -> None:
        path = write_brief(SMOKE_BRIEF)
        try:
            from brief import load_brief

            project, assets = load_brief(path)
            validate_brief_for_export(project, assets)
        finally:
            path.unlink(missing_ok=True)

    def test_parallax_layer_requires_scroll_fields(self) -> None:
        project = ProjectContext(
            title="T",
            description="platformer",
            art_direction="flat",
            dimension="2d",
            genre="2d_platformer",
            gameplay_loop="run",
            session_goal="demo",
            controls={"move_left": ["A"], "move_right": ["D"]},
            viewport={"width": 640, "height": 360},
            camera={"mode": "follow_player"},
        )
        layer = AssetSpec(
            name="sky_layer",
            id="sky_layer",
            type=AssetType.BACKGROUND,
            usage="parallax_layer",
            usage_description="far sky",
            display_size=DisplaySize(1920, 1080),
            description="sky",
        )
        gaps = audit_brief_for_export(project, [layer])
        self.assertTrue(any("parallax_order" in g for g in gaps))
        self.assertTrue(any("scroll_factor" in g for g in gaps))

    def test_audio_music_requires_loop_flag(self) -> None:
        project = ProjectContext(
            title="T",
            description="game",
            art_direction="art",
            dimension="2d",
            genre="puzzle",
            gameplay_loop="play",
            session_goal="demo",
            controls={"confirm": ["Space"]},
            viewport={"width": 800, "height": 600},
        )
        bgm = AssetSpec(
            name="bgm",
            id="bgm",
            type=AssetType.AUDIO,
            usage="music",
            usage_description="loop",
            description="calm music",
        )
        gaps = audit_brief_for_export(project, [bgm])
        self.assertTrue(any("audio_loop" in g for g in gaps))

    def test_ui_element_requires_hud_entry(self) -> None:
        project = ProjectContext(
            title="T",
            description="game",
            art_direction="art",
            dimension="2d",
            genre="puzzle",
            gameplay_loop="play",
            session_goal="demo",
            controls={"confirm": ["Space"]},
            viewport={"width": 800, "height": 600},
        )
        icon = AssetSpec(
            name="health_icon",
            type=AssetType.ICON_KIT,
            usage="ui_element",
            usage_description="HP bar icon",
            display_size=DisplaySize(32, 32),
            description="heart",
            items=["heart"],
            grid="1x1",
        )
        gaps = audit_brief_for_export(project, [icon])
        self.assertTrue(any("project.hud" in g for g in gaps))

    def test_asset_id_required_and_paths_use_id(self) -> None:
        from brief import AssetSpec, AssetType, ProjectContext, audit_brief_for_export
        from display_size import DisplaySize
        from pipeline_manifest import build_manifest, tasks_list

        project = ProjectContext(
            title="T",
            description="platformer",
            art_direction="flat",
            dimension="2d",
            genre="2d_platformer",
            gameplay_loop="run",
            session_goal="demo",
            player_asset="英雄",
            controls={"move_left": ["A"], "move_right": ["D"]},
            viewport={"width": 640, "height": 360},
            camera={"mode": "follow_player"},
        )
        no_id = AssetSpec(
            name="英雄",
            type=AssetType.CHARACTER,
            usage="player_idle",
            usage_description="hero",
            display_size=DisplaySize(64, 64),
            description="hero",
        )
        gaps = audit_brief_for_export(project, [no_id])
        self.assertTrue(any("missing required field 'id'" in g for g in gaps))

        brief = {
            "project": {
                "title": "T",
                "description": "platformer",
                "art_direction": "flat",
                "dimension": "2d",
                "genre": "2d_platformer",
                "gameplay_loop": "run",
                "session_goal": "demo",
                "player_asset": "英雄",
                "controls": {"move_left": ["A"], "move_right": ["D"]},
                "viewport": {"width": 640, "height": 360},
                "camera": {"mode": "follow_player"},
            },
            "assets": [
                {
                    "name": "英雄",
                    "id": "hero",
                    "type": "character",
                    "usage": "player_idle",
                    "usage_description": "hero",
                    "generate_method": "image",
                    "description": "hero",
                    "display_size": {"width": 64, "height": 64},
                }
            ],
        }
        path = write_brief(brief)
        try:
            manifest = build_manifest(path, include_godot=False)
            ids = {t["id"] for t in tasks_list(manifest)}
            self.assertIn("hero.image.generate", ids)
            self.assertNotIn("英雄.image.generate", ids)
            gen = next(t for t in tasks_list(manifest) if t["id"] == "hero.image.generate")
            self.assertEqual(gen["asset"], "英雄")
            self.assertEqual(gen["asset_id"], "hero")
            self.assertIn("hero_raw.png", gen["artifacts"]["output"].replace("\\", "/"))
        finally:
            path.unlink(missing_ok=True)

        from pipeline_manifest import build_manifest, tasks_list

        brief = {
            "project": {
                "title": "Audio Test",
                "description": "test",
                "art_direction": "flat",
                "dimension": "2d",
                "genre": "puzzle",
                "gameplay_loop": "play",
                "session_goal": "demo",
                "controls": {"confirm": ["Space"]},
                "viewport": {"width": 640, "height": 360},
            },
            "assets": [
                {
                    "name": "bgm",
                    "id": "bgm",
                    "type": "audio",
                    "usage": "music",
                    "usage_description": "loop",
                    "audio_loop": True,
                    "description": "music",
                }
            ],
        }
        path = write_brief(brief)
        try:
            manifest = build_manifest(path, include_godot=False)
            task_assets = {t["asset"] for t in tasks_list(manifest)}
            self.assertNotIn("bgm", task_assets)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
