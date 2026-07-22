"""Tests for style_group img2img brief fields and helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from asset_pipeline import build_prompt_scaffold
from brief import (
    AssetSpec,
    AssetType,
    ProjectContext,
    audit_brief_for_export,
    audit_style_groups,
    load_brief_full,
    resolve_style_img2img_path,
    should_use_style_img2img,
)
from display_size import DisplaySize
from pipeline_manifest import build_manifest, tasks_list
from test_fixtures import EXAMPLE_BRIEF, write_brief

STYLE_GROUP_EXAMPLE_BRIEF = (
    Path(__file__).resolve().parent.parent / "resources" / "style-group-img2img.example.json"
)


def _valid_project(**overrides: object) -> ProjectContext:
    base = {
        "title": "Style Test",
        "description": "platformer test",
        "art_direction": "flat 2D",
        "dimension": "2d",
        "genre": "2d_platformer",
        "gameplay_loop": "run and jump",
        "session_goal": "demo",
        "player_asset": "hero_a",
        "controls": {"move_left": ["A"], "move_right": ["D"]},
        "viewport": {"width": 640, "height": 360},
        "camera": {"mode": "follow_player"},
    }
    base.update(overrides)
    return ProjectContext.from_dict(base)


def _character(
    name: str,
    *,
    asset_id: str | None = None,
    **style_fields: object,
) -> AssetSpec:
    data: dict[str, object] = {
        "name": name,
        "id": asset_id or name,
        "type": "character",
        "usage": "player_idle" if name.endswith("_a") or name == "hero_a" else "prop",
        "usage_description": f"{name} desc",
        "description": name,
        "display_size": {"width": 128, "height": 128},
    }
    data.update(style_fields)
    return AssetSpec.from_dict(data)


class StyleGroupTests(unittest.TestCase):
    def test_legal_group_anchor_and_follower(self) -> None:
        project = _valid_project()
        anchor = _character("hero_a", style_group="cast_main")
        follower = _character(
            "hero_b",
            asset_id="hero_b",
            style_group="cast_main",
            style_anchor="hero_a",
        )
        assets = [anchor, follower]

        self.assertEqual(audit_style_groups(project, assets), [])
        self.assertFalse(should_use_style_img2img(anchor, project=project, assets=assets))
        self.assertTrue(should_use_style_img2img(follower, project=project, assets=assets))

    def test_use_style_img2img_false_opt_out(self) -> None:
        project = _valid_project()
        anchor = _character("hero_a", style_group="cast_main")
        follower = _character(
            "hero_b",
            asset_id="hero_b",
            style_group="cast_main",
            style_anchor="hero_a",
            use_style_img2img=False,
        )
        assets = [anchor, follower]

        self.assertFalse(should_use_style_img2img(follower, project=project, assets=assets))

    def test_bad_anchor_reports_error(self) -> None:
        project = _valid_project()
        follower = _character(
            "hero_b",
            asset_id="hero_b",
            style_group="cast_main",
            style_anchor="missing_hero",
        )
        errors = audit_style_groups(project, [follower])
        self.assertTrue(any("style_anchor 'missing_hero'" in e for e in errors))

    def test_no_style_fields_backward_compatible(self) -> None:
        project = _valid_project()
        asset = _character("hero_a")
        self.assertEqual(audit_style_groups(project, [asset]), [])
        gaps = audit_brief_for_export(project, [asset])
        self.assertFalse(any("style_" in g for g in gaps))

    def test_visual_reference_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ref_file = root / "north_star.png"
            ref_file.write_bytes(b"\x89PNG\r\n\x1a\n")
            brief_path = write_brief(
                {
                    "project": {
                        "title": "VT",
                        "description": "test",
                        "art_direction": "flat",
                        "dimension": "2d",
                        "genre": "2d_platformer",
                        "gameplay_loop": "run",
                        "session_goal": "demo",
                        "player_asset": "icon_a",
                        "controls": {"move_left": ["A"], "move_right": ["D"]},
                        "viewport": {"width": 640, "height": 360},
                        "camera": {"mode": "follow_player"},
                        "visual_reference": str(ref_file),
                    },
                    "assets": [
                        {
                            "name": "icon_a",
                            "id": "icon_a",
                            "type": "icon_kit",
                            "usage": "item_icon",
                            "usage_description": "icon",
                            "description": "icon",
                            "display_size": {"width": 32, "height": 32},
                            "items": ["heart"],
                            "grid": "1x1",
                            "style_group": "ui_icons",
                            "style_anchor_kind": "visual_reference",
                        }
                    ],
                },
                prefix="style-vt-",
            )
            try:
                from brief import load_brief_full

                project, assets, _ = load_brief_full(brief_path)
                spec = assets[0]
                self.assertEqual(audit_style_groups(project, assets, brief_path=brief_path), [])
                self.assertFalse(
                    should_use_style_img2img(spec, project=project, assets=assets)
                )
                resolved = resolve_style_img2img_path(
                    spec,
                    project=project,
                    assets=assets,
                    brief_path=brief_path,
                )
                self.assertIsNone(resolved)
            finally:
                brief_path.unlink(missing_ok=True)

    def test_visual_reference_missing_project_ref(self) -> None:
        project = _valid_project()
        spec = _character(
            "hero_b",
            asset_id="hero_b",
            style_group="cast_main",
            style_anchor_kind="visual_reference",
        )
        errors = audit_style_groups(project, [spec])
        self.assertTrue(any("visual_reference requires" in e for e in errors))

    def test_unknown_style_anchor_kind(self) -> None:
        project = _valid_project()
        spec = _character(
            "hero_b",
            asset_id="hero_b",
            style_group="cast_main",
            style_anchor_kind="north_star",
        )
        errors = audit_style_groups(project, [spec])
        self.assertTrue(any("style_anchor_kind must be" in e for e in errors))

    def test_character_pose_skips_style_img2img(self) -> None:
        project = _valid_project()
        anchor = _character("hero_a", style_group="cast_main")
        pose = AssetSpec.from_dict(
            {
                "name": "hero_a_pose",
                "id": "hero_a_pose",
                "type": "character_pose",
                "usage": "player_action",
                "usage_description": "pose",
                "description": "pose",
                "display_size": {"width": 128, "height": 128},
                "reference_asset": "hero_a",
                "action": "kick",
                "style_group": "cast_main",
                "style_anchor": "hero_a",
            }
        )
        assets = [anchor, pose]
        self.assertFalse(should_use_style_img2img(pose, project=project, assets=assets))

    def test_resolve_asset_anchor_path(self) -> None:
        project = _valid_project()
        anchor = _character("hero_a", style_group="cast_main")
        follower = _character(
            "hero_b",
            asset_id="hero_b",
            style_group="cast_main",
            style_anchor="hero_a",
        )
        brief_path = write_brief(
            {
                "project": {
                    "title": "Style Test",
                    "description": "platformer test",
                    "art_direction": "flat 2D",
                    "dimension": "2d",
                    "genre": "2d_platformer",
                    "gameplay_loop": "run and jump",
                    "session_goal": "demo",
                    "player_asset": "hero_a",
                    "controls": {"move_left": ["A"], "move_right": ["D"]},
                    "viewport": {"width": 640, "height": 360},
                    "camera": {"mode": "follow_player"},
                },
                "assets": [
                    {
                        "name": "hero_a",
                        "id": "hero_a",
                        "type": "character",
                        "usage": "player_idle",
                        "usage_description": "anchor",
                        "description": "anchor",
                        "display_size": {"width": 128, "height": 128},
                        "style_group": "cast_main",
                    },
                    {
                        "name": "hero_b",
                        "id": "hero_b",
                        "type": "character",
                        "usage": "prop",
                        "usage_description": "follower",
                        "description": "follower",
                        "display_size": {"width": 128, "height": 128},
                        "style_group": "cast_main",
                        "style_anchor": "hero_a",
                    },
                ],
            },
            prefix="style-path-",
        )
        try:
            path = resolve_style_img2img_path(
                follower,
                project=project,
                assets=[anchor, follower],
                brief_path=brief_path,
            )
            self.assertIsNotNone(path)
            self.assertIn("hero_a_raw.png", path.replace("\\", "/"))
        finally:
            brief_path.unlink(missing_ok=True)

    def test_asset_to_dict_omits_defaults(self) -> None:
        from shared_context import asset_to_dict

        spec = _character("hero_a")
        data = asset_to_dict(spec)
        self.assertNotIn("style_group", data)
        self.assertNotIn("use_style_img2img", data)

        follower = _character(
            "hero_b",
            asset_id="hero_b",
            style_group="cast_main",
            style_anchor="hero_a",
            use_style_img2img=False,
        )
        out = asset_to_dict(follower)
        self.assertEqual(out["style_group"], "cast_main")
        self.assertEqual(out["style_anchor"], "hero_a")
        self.assertFalse(out["use_style_img2img"])

    def test_identity_preferred_over_style_anchor(self) -> None:
        project = _valid_project()
        style_anchor = _character("hero_a", style_group="cast_main")
        identity = _character("hero_id", asset_id="hero_id", style_group="cast_main")
        follower = _character(
            "hero_b",
            asset_id="hero_b",
            style_group="cast_main",
            style_anchor="hero_a",
            identity_anchor="hero_id",
        )
        assets = [style_anchor, identity, follower]
        brief_path = write_brief(
            {
                "project": {
                    "title": "Style Test",
                    "description": "platformer test",
                    "art_direction": "flat 2D",
                    "dimension": "2d",
                    "genre": "2d_platformer",
                    "gameplay_loop": "run and jump",
                    "session_goal": "demo",
                    "player_asset": "hero_a",
                    "controls": {"move_left": ["A"], "move_right": ["D"]},
                    "viewport": {"width": 640, "height": 360},
                    "camera": {"mode": "follow_player"},
                },
                "assets": [
                    {
                        "name": "hero_a",
                        "id": "hero_a",
                        "type": "character",
                        "usage": "player_idle",
                        "usage_description": "style anchor",
                        "description": "style anchor",
                        "display_size": {"width": 128, "height": 128},
                        "style_group": "cast_main",
                    },
                    {
                        "name": "hero_id",
                        "id": "hero_id",
                        "type": "character",
                        "usage": "prop",
                        "usage_description": "identity anchor",
                        "description": "identity anchor",
                        "display_size": {"width": 128, "height": 128},
                        "style_group": "cast_main",
                    },
                    {
                        "name": "hero_b",
                        "id": "hero_b",
                        "type": "character",
                        "usage": "prop",
                        "usage_description": "follower",
                        "description": "follower",
                        "display_size": {"width": 128, "height": 128},
                        "style_group": "cast_main",
                        "style_anchor": "hero_a",
                        "identity_anchor": "hero_id",
                    },
                ],
            },
            prefix="style-identity-",
        )
        try:
            path = resolve_style_img2img_path(
                follower,
                project=project,
                assets=assets,
                brief_path=brief_path,
            )
            self.assertIsNotNone(path)
            normalized = path.replace("\\", "/")
            self.assertIn("hero_id_raw.png", normalized)
            self.assertNotIn("hero_a_raw.png", normalized)
        finally:
            brief_path.unlink(missing_ok=True)

    def test_unknown_identity_audit_error(self) -> None:
        project = _valid_project()
        spec = _character(
            "hero_b",
            asset_id="hero_b",
            style_group="cast_main",
            style_anchor="hero_a",
            identity_anchor="missing_identity",
        )
        errors = audit_style_groups(project, [spec])
        self.assertTrue(any("identity_anchor 'missing_identity'" in e for e in errors))

    def test_icon_kit_style_group_not_allowed(self) -> None:
        project = _valid_project()
        spec = AssetSpec.from_dict(
            {
                "name": "ui_icons",
                "id": "ui_icons",
                "type": "icon_kit",
                "usage": "item_icon",
                "usage_description": "icons",
                "description": "icons",
                "display_size": {"width": 32, "height": 32},
                "items": ["heart"],
                "grid": "1x1",
                "style_group": "ui_pack",
                "style_anchor": "hero_a",
            }
        )
        anchor = _character("hero_a", style_group="ui_pack")
        assets = [anchor, spec]
        self.assertFalse(should_use_style_img2img(spec, project=project, assets=assets))


def _style_group_brief_data(*, opt_out: bool = False) -> dict[str, object]:
    follower: dict[str, object] = {
        "name": "hero_b",
        "id": "hero_b",
        "type": "character",
        "usage": "prop",
        "usage_description": "follower",
        "description": "follower",
        "display_size": {"width": 128, "height": 128},
        "style_group": "cast_main",
        "style_anchor": "hero_a",
    }
    if opt_out:
        follower["use_style_img2img"] = False
    return {
        "project": {
            "title": "Style Pipeline",
            "description": "platformer test",
            "art_direction": "flat 2D",
            "dimension": "2d",
            "genre": "2d_platformer",
            "gameplay_loop": "run and jump",
            "session_goal": "demo",
            "player_asset": "hero_a",
            "controls": {"move_left": ["A"], "move_right": ["D"]},
            "viewport": {"width": 640, "height": 360},
            "camera": {"mode": "follow_player"},
        },
        "assets": [
            {
                "name": "hero_a",
                "id": "hero_a",
                "type": "character",
                "usage": "player_idle",
                "usage_description": "anchor",
                "description": "anchor",
                "display_size": {"width": 128, "height": 128},
                "style_group": "cast_main",
            },
            follower,
        ],
    }


class StyleGroupPipelineTests(unittest.TestCase):
    def test_follower_still_includes_reference_image(self) -> None:
        brief_path = write_brief(_style_group_brief_data(), prefix="style-pipe-")
        try:
            manifest = build_manifest(brief_path)
            gen = next(t for t in tasks_list(manifest) if t["id"] == "hero_b.image.generate")
            self.assertIn("--reference-image", gen["command"])
            self.assertIn("hero_a_raw.png", gen["command"].replace("\\", "/"))
            self.assertIn("hero_a.image.generate", gen["depends_on"])
        finally:
            brief_path.unlink(missing_ok=True)

    def test_opt_out_excludes_reference_image(self) -> None:
        brief_path = write_brief(_style_group_brief_data(opt_out=True), prefix="style-opt-")
        try:
            manifest = build_manifest(brief_path)
            gen = next(t for t in tasks_list(manifest) if t["id"] == "hero_b.image.generate")
            self.assertNotIn("--reference-image", gen["command"])
            self.assertNotIn("hero_a.image.generate", gen["depends_on"])
        finally:
            brief_path.unlink(missing_ok=True)

    def test_follower_plan_requires_reference_image(self) -> None:
        brief_path = write_brief(_style_group_brief_data(), prefix="style-plan-")
        try:
            project, assets, _ = load_brief_full(brief_path)
            follower = next(a for a in assets if a.name == "hero_b")
            plan = build_prompt_scaffold(project, follower, assets=assets)
            self.assertTrue(plan.requires_reference_image)
        finally:
            brief_path.unlink(missing_ok=True)

    def test_video_still_uses_reference_asset_not_style_anchor(self) -> None:
        manifest = build_manifest(EXAMPLE_BRIEF)
        video = next(t for t in tasks_list(manifest) if t["id"] == "knight_walk.video.generate")
        self.assertIn("knight.image.generate", video["depends_on"])
        self.assertIn("--reference-image", video["command"])
        self.assertIn("knight_raw.png", video["command"].replace("\\", "/"))

    def test_example_brief_manifest_reference_image(self) -> None:
        self.assertTrue(STYLE_GROUP_EXAMPLE_BRIEF.is_file())
        project, assets, _ = load_brief_full(STYLE_GROUP_EXAMPLE_BRIEF)
        self.assertEqual(
            audit_style_groups(project, assets, brief_path=STYLE_GROUP_EXAMPLE_BRIEF),
            [],
        )
        manifest = build_manifest(STYLE_GROUP_EXAMPLE_BRIEF)
        follower = next(t for t in tasks_list(manifest) if t["id"] == "hero_b.image.generate")
        self.assertIn("--reference-image", follower["command"])
        self.assertIn("hero_a_raw.png", follower["command"].replace("\\", "/"))
        self.assertIn("hero_a.image.generate", follower["depends_on"])

        opt_out = next(t for t in tasks_list(manifest) if t["id"] == "hero_c.image.generate")
        self.assertNotIn("--reference-image", opt_out["command"])
        self.assertNotIn("hero_a.image.generate", opt_out["depends_on"])

        video = next(t for t in tasks_list(manifest) if t["id"] == "hero_a_walk.video.generate")
        self.assertIn("hero_a.image.generate", video["depends_on"])
        self.assertIn("--reference-image", video["command"])
        self.assertIn("hero_a_raw.png", video["command"].replace("\\", "/"))

    def test_follower_identity_anchor_wires_reference_and_dep(self) -> None:
        """identity_anchor overrides style_anchor for --reference-image and depends_on."""
        brief_path = write_brief(
            {
                "project": _style_group_brief_data()["project"],
                "assets": [
                    _style_group_brief_data()["assets"][0],
                    {
                        "name": "hero_id",
                        "id": "hero_id",
                        "type": "character",
                        "usage": "prop",
                        "usage_description": "identity anchor",
                        "description": "identity anchor",
                        "display_size": {"width": 128, "height": 128},
                        "style_group": "cast_main",
                    },
                    {
                        "name": "hero_b",
                        "id": "hero_b",
                        "type": "character",
                        "usage": "prop",
                        "usage_description": "follower",
                        "description": "follower",
                        "display_size": {"width": 128, "height": 128},
                        "style_group": "cast_main",
                        "style_anchor": "hero_a",
                        "identity_anchor": "hero_id",
                    },
                ],
            },
            prefix="style-identity-pipe-",
        )
        try:
            manifest = build_manifest(brief_path)
            gen = next(t for t in tasks_list(manifest) if t["id"] == "hero_b.image.generate")
            cmd = gen["command"].replace("\\", "/")
            self.assertIn("--reference-image", cmd)
            self.assertIn("hero_id_raw.png", cmd)
            self.assertNotIn("hero_a_raw.png", cmd)
            self.assertIn("hero_id.image.generate", gen["depends_on"])
            self.assertNotIn("hero_a.image.generate", gen["depends_on"])
        finally:
            brief_path.unlink(missing_ok=True)

    def test_character_pose_uses_reference_asset_not_style_group(self) -> None:
        brief_path = write_brief(
            {
                "project": _style_group_brief_data()["project"],
                "assets": [
                    _style_group_brief_data()["assets"][0],
                    {
                        "name": "hero_a_kick",
                        "id": "hero_a_kick",
                        "type": "character_pose",
                        "usage": "player_action",
                        "usage_description": "kick",
                        "description": "kick",
                        "display_size": {"width": 128, "height": 128},
                        "reference_asset": "hero_a",
                        "action": "kick",
                        "style_group": "cast_main",
                        "style_anchor": "hero_a",
                    },
                ],
            },
            prefix="style-pose-",
        )
        try:
            manifest = build_manifest(brief_path)
            gen = next(t for t in tasks_list(manifest) if t["id"] == "hero_a_kick.image.generate")
            self.assertIn("--reference-image", gen["command"])
            self.assertIn("hero_a_raw.png", gen["command"].replace("\\", "/"))
            self.assertIn("hero_a.image.generate", gen["depends_on"])
        finally:
            brief_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
