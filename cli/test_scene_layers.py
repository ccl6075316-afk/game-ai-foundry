"""Plate-first scene layers keep a common reference and placement scale."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner
from PIL import Image

from asset_pipeline import build_prompt_scaffold, validate_image
from asset_review import resolve_canonical_path
from brief import AssetSpec, ProjectContext, audit_scene_layers
from image_cmds import scene_compose_cmd, scene_crop_cmd, scene_preview_cmd, scene_reproject_cmd
from pipeline_manifest import build_manifest, tasks_list
from plan_io import validation_from_handoff
from production import build_layout
from prompt_craft import assemble_asset_prompt
from skill_loader import resolve_class_skill_name


def _brief() -> dict:
    return {
        "project": {
            "title": "Plate-first fishing scene",
            "description": "A fishing scene assembled from one image plate",
            "art_direction": "Crisp pixel art",
            "dimension": "2d",
            "genre": "Simulation / Fishing",
            "gameplay_loop": "Cast and reel",
            "session_goal": "One playable spot",
            "player_asset": "",
            "controls": {"cast": ["Space"]},
            "view": "side",
            "viewport": {"width": 640, "height": 360},
            "scenes": [{"id": "fishing", "title": "Fishing"}],
        },
        "assets": [
            {
                "id": "shoreline",
                "name": "Shoreline layer",
                "type": "character",
                "usage": "prop",
                "description": "The shoreline from the scene plate",
                "content_class": "scene_layer",
                "scene_ids": ["fishing"],
                "scene_master": "lake_plate",
                "scene_box_norm": [0.2, 0.3, 0.25, 0.2],
                "scene_scale": 1.0,
                "display_size": {"width": 160, "height": 72},
            },
            {
                "id": "lake_plate",
                "name": "Complete lake plate",
                "type": "background",
                "usage": "world_background",
                "description": "Complete fishing scene with sky, shore and water",
                "content_class": "backdrop_full",
                "scene_ids": ["fishing"],
                "display_size": {"width": 640, "height": 360},
            },
        ],
    }


class SceneLayerTests(unittest.TestCase):
    def test_review_prefers_plate_locked_over_generated_cutout(self) -> None:
        entry = {"stages": [
            {"stage": "image.nobg", "role": "gameplay_ready", "path_repo": "layer_nobg.png"},
            {"stage": "image.plate_locked", "role": "gameplay_ready",
             "path_repo": "layer_plate_locked.png"},
        ]}
        self.assertEqual(resolve_canonical_path(entry), "layer_plate_locked.png")

    def test_scene_layer_edge_contact_keeps_white_backdrop_checks(self) -> None:
        data = _brief()
        project = ProjectContext.from_dict(data["project"])
        assets = [AssetSpec.from_dict(row) for row in data["assets"]]
        scaffold = build_prompt_scaffold(project, assets[0], assets=assets)
        self.assertTrue(scaffold.validation["allow_subject_at_edge"])

        legacy_handoff = {
            "context": {"asset": data["assets"][0]},
            "plan": {"validation": {
                "asset_type": "character",
                "require_pure_white_background": True,
                "max_subject_regions": 16,
            }},
        }
        rules = validation_from_handoff(legacy_handoff)
        self.assertTrue(rules["allow_subject_at_edge"])
        with tempfile.TemporaryDirectory() as temp:
            image_path = Path(temp) / "edge-layer.png"
            image = Image.new("RGB", (300, 300), "white")
            for x in range(245, 300):
                for y in range(60, 240):
                    image.putpixel((x, y), (60, 70, 80))
            image.save(image_path)
            self.assertFalse(validate_image(image_path, "character", {
                **rules, "allow_subject_at_edge": False,
            }).ok)
            self.assertTrue(validate_image(image_path, "character", rules).ok)

            for x in range(12):
                for y in range(12):
                    image.putpixel((x, y), (0, 0, 0))
            image.save(image_path)
            self.assertFalse(validate_image(image_path, "character", rules).ok)

    def test_plate_dependency_crop_reference_and_scale_layout(self) -> None:
        data = _brief()
        project = ProjectContext.from_dict(data["project"])
        assets = [AssetSpec.from_dict(row) for row in data["assets"]]
        self.assertEqual(audit_scene_layers(project, assets), [])
        self.assertTrue(build_prompt_scaffold(project, assets[0], assets=assets).requires_reference_image)
        self.assertEqual(resolve_class_skill_name(assets[0]), "class-scene-layer")
        placement = build_layout(project, assets)["placements"][0]
        self.assertEqual(placement["xy_norm"], [0.325, 0.4])
        self.assertEqual(placement["scale"], 1.0)

        with tempfile.TemporaryDirectory() as temp:
            brief = Path(temp) / "brief.json"
            brief.write_text(json.dumps(data), encoding="utf-8")
            manifest = build_manifest(
                brief,
                output_dir=Path(temp) / "output",
                plans_dir=Path(temp) / "plans",
                include_godot=False,
                include_game_dev=False,
            )
        tasks = {task["id"]: task for task in tasks_list(manifest)}
        crop = tasks["shoreline.image.scene-crop"]
        generation = tasks["shoreline.image.generate"]
        self.assertIn("lake_plate.image.generate", crop["depends_on"])
        self.assertIn("shoreline.image.scene-crop", generation["depends_on"])
        self.assertIn("--reference-image", generation["command"])
        self.assertIn("--box 0.2 0.3 0.25 0.2", crop["command"])
        preview = tasks["shoreline.image.scene-preview"]
        self.assertIn("--scale 1.0", preview["command"])
        self.assertNotIn("shoreline.image.trim", tasks)
        matte = tasks["shoreline.image.remove-bg"]
        self.assertIn("shoreline_raw.png", matte["command"])
        self.assertIn("--mode color", matte["command"])
        reproject = tasks["shoreline.image.scene-reproject"]
        self.assertIn("shoreline.image.remove-bg", reproject["depends_on"])
        self.assertIn("--mask", reproject["command"])
        self.assertIn("shoreline_plate_locked.png", reproject["command"])
        self.assertIn("shoreline.image.scene-reproject", preview["depends_on"])
        self.assertIn("shoreline_plate_locked.png", preview["command"])
        composite = tasks["lake_plate.image.scene-compose"]
        self.assertIn("shoreline.image.scene-preview", composite["depends_on"])
        self.assertIn("--layer", composite["command"])
        self.assertIn("shoreline_plate_locked.png", composite["command"])

    def test_bad_scale_and_missing_master_are_rejected(self) -> None:
        data = _brief()
        data["assets"][0]["display_size"] = {"width": 700, "height": 72}
        data["assets"][0]["scene_master"] = "unknown"
        project = ProjectContext.from_dict(data["project"])
        assets = [AssetSpec.from_dict(row) for row in data["assets"]]
        errors = audit_scene_layers(project, assets)
        self.assertTrue(any("scene_master 'unknown'" in error for error in errors))
        data["assets"][0]["scene_master"] = "lake_plate"
        errors = audit_scene_layers(project, [AssetSpec.from_dict(row) for row in data["assets"]])
        self.assertTrue(any("display_size must match" in error for error in errors))

    def test_parallax_layer_cannot_be_independent_generation(self) -> None:
        data = _brief()
        layer = data["assets"][0]
        layer["usage"] = "parallax_layer"
        layer["content_class"] = "backdrop_sparse"
        layer.pop("scene_master")
        layer.pop("scene_box_norm")
        errors = audit_scene_layers(
            ProjectContext.from_dict(data["project"]),
            [AssetSpec.from_dict(row) for row in data["assets"]],
        )
        self.assertTrue(any("content_class='scene_layer'" in error for error in errors))

    def test_occlusion_requires_shared_plate_overlap_and_front_z(self) -> None:
        data = _brief()
        front = dict(data["assets"][0])
        front.update({
            "id": "front_reeds", "name": "Front reeds",
            "scene_box_norm": [0.4, 0.4, 0.2, 0.2],
            "display_size": {"width": 128, "height": 72},
            "scene_z": 2, "scene_occludes": ["shoreline"],
        })
        data["assets"].append(front)
        project = ProjectContext.from_dict(data["project"])
        assets = [AssetSpec.from_dict(row) for row in data["assets"]]
        self.assertEqual(audit_scene_layers(project, assets), [])
        placement = next(p for p in build_layout(project, assets)["placements"] if p["asset"] == "front_reeds")
        self.assertEqual(placement["z_index"], 2)

        data["assets"][-1]["scene_z"] = 0
        errors = audit_scene_layers(project, [AssetSpec.from_dict(row) for row in data["assets"]])
        self.assertTrue(any("scene_z above" in error for error in errors))
        data["assets"][-1]["scene_z"] = 2
        data["assets"][-1]["scene_box_norm"] = [0.7, 0.4, 0.2, 0.2]
        errors = audit_scene_layers(project, [AssetSpec.from_dict(row) for row in data["assets"]])
        self.assertTrue(any("boxes do not overlap" in error for error in errors))

    def test_reference_crop_keeps_source_pixels_and_prompt_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "plate.png"
            target = Path(temp) / "crop.png"
            image = Image.new("RGB", (100, 50))
            image.putpixel((20, 15), (15, 80, 140))
            image.save(source)
            result = CliRunner().invoke(
                scene_crop_cmd,
                ["--input", str(source), "--output", str(target),
                 "--box", "0.2", "0.3", "0.25", "0.2"],
            )
            self.assertEqual(result.exit_code, 0, result.output)
            with Image.open(target) as crop:
                self.assertEqual(crop.size, (25, 10))
                self.assertEqual(crop.getpixel((0, 0)), (15, 80, 140))

        prompt = assemble_asset_prompt(
            {"subject": "The shoreline"},
            project={"art_direction": "Crisp pixel art"},
            spec=_brief()["assets"][0],
        )
        self.assertIn("complete scene plate 'lake_plate'", prompt)
        self.assertIn("apparent size", prompt)

    def test_recomposition_preview_places_layer_on_plate_box(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            master = Path(temp) / "master.png"
            layer = Path(temp) / "layer.png"
            preview = Path(temp) / "preview.png"
            Image.new("RGBA", (100, 50), (0, 0, 100, 255)).save(master)
            Image.new("RGBA", (25, 10), (240, 20, 20, 255)).save(layer)
            result = CliRunner().invoke(
                scene_preview_cmd,
                ["--master", str(master), "--layer", str(layer),
                 "--output", str(preview), "--box", "0.2", "0.3", "0.25", "0.2",
                 "--scale", "1", "--opaque"],
            )
            self.assertEqual(result.exit_code, 0, result.output)
            with Image.open(preview) as image:
                self.assertEqual(image.size, (200, 50))
                self.assertEqual(image.getpixel((30, 20)), (0, 0, 100))
                self.assertEqual(image.getpixel((130, 20)), (240, 20, 20))

    def test_scene_reproject_copies_exact_plate_pixels_under_mask(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            master, mask, output = (root / name for name in ("master.png", "mask.png", "output.png"))
            image = Image.new("RGB", (100, 50), (12, 45, 90))
            for x in range(20, 45):
                for y in range(15, 25):
                    image.putpixel((x, y), (x, y, 120))
            image.save(master)
            cutout = Image.new("RGBA", (25, 10), (240, 0, 0, 0))
            cutout.putpixel((5, 5), (240, 0, 0, 255))
            cutout.save(mask)
            result = CliRunner().invoke(scene_reproject_cmd, [
                "--master", str(master), "--mask", str(mask), "--output", str(output),
                "--box", "0.2", "0.3", "0.25", "0.2",
            ])
            self.assertEqual(result.exit_code, 0, result.output)
            with Image.open(output) as projected:
                self.assertEqual(projected.size, (25, 10))
                self.assertEqual(projected.getpixel((5, 5)), (25, 20, 120, 255))
                self.assertEqual(projected.getpixel((4, 5)), (0, 0, 0, 0))

    def test_plate_locked_layer_recomposes_without_rounding_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            master, layer, comparison = (root / name for name in
                                         ("master.png", "layer.png", "comparison.png"))
            plate = Image.new("RGB", (101, 53))
            for y in range(53):
                for x in range(101):
                    plate.putpixel((x, y), (x * 2, y * 4, (x + y) % 256))
            plate.save(master)
            box = (0.03, 0.30, 0.94, 0.23)
            extract = CliRunner().invoke(scene_reproject_cmd, [
                "--master", str(master), "--output", str(layer), "--box",
                *(str(v) for v in box),
            ])
            self.assertEqual(extract.exit_code, 0, extract.output)
            compose = CliRunner().invoke(scene_compose_cmd, [
                "--master", str(master), "--output", str(comparison),
                "--layer", str(layer), *(str(v) for v in box), "1", "1", "1",
                "--require-exact",
            ])
            self.assertEqual(compose.exit_code, 0, compose.output)
            with Image.open(comparison) as result:
                self.assertEqual(
                    result.crop((0, 0, 101, 53)).tobytes(),
                    result.crop((101, 0, 202, 53)).tobytes(),
                )
            with Image.open(layer) as source:
                wrong = source.copy()
            wrong.putpixel((4, 4), (255, 0, 0, 255))
            wrong.save(layer)
            rejected = CliRunner().invoke(scene_compose_cmd, [
                "--master", str(master), "--output", str(comparison),
                "--layer", str(layer), *(str(v) for v in box), "1", "1", "1",
                "--require-exact",
            ])
            self.assertNotEqual(rejected.exit_code, 0)
            self.assertIn("differs from the source plate", rejected.output)

    def test_full_composite_respects_occlusion_z(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            master, back, front, preview = (root / name for name in
                                            ("master.png", "back.png", "front.png", "preview.png"))
            Image.new("RGBA", (100, 50), (0, 0, 100, 255)).save(master)
            Image.new("RGBA", (40, 20), (240, 20, 20, 255)).save(back)
            Image.new("RGBA", (40, 20), (20, 240, 20, 255)).save(front)
            result = CliRunner().invoke(scene_compose_cmd, [
                "--master", str(master), "--output", str(preview),
                "--layer", str(front), "0.3", "0.4", "0.4", "0.4", "1", "2", "0",
                "--layer", str(back), "0.2", "0.3", "0.4", "0.4", "1", "1", "0",
            ])
            self.assertEqual(result.exit_code, 0, result.output)
            with Image.open(preview) as image:
                self.assertEqual(image.getpixel((135, 23)), (20, 240, 20))


if __name__ == "__main__":
    unittest.main()
