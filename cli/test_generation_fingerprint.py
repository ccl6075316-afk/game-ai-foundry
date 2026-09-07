"""Tests for generation input fingerprint / staleness."""

from __future__ import annotations

import json
import unittest

from asset_sizing import resolve_generation_image_size
from brief import AssetSpec, AssetType, ProjectContext
from display_size import DisplaySize
from generation_fingerprint import (
    build_generation_input,
    embed_generation_fingerprint,
    extract_generation_input_from_handoff,
    generation_input_fingerprint,
    is_handoff_generation_stale,
)
from plan_io import build_handoff


class GenerationFingerprintTest(unittest.TestCase):
    def _fish_spec(self, description: str) -> AssetSpec:
        return AssetSpec(
            name="fish",
            type=AssetType.CHARACTER,
            id="char_fish",
            description=description,
            aspect_ratio="16:9",
            real_length_cm=150,
            generation_size=DisplaySize(1920, 1080),
        )

    def test_description_change_detected_as_stale(self) -> None:
        project = ProjectContext(title="t")
        spec = self._fish_spec("old description")
        plan = embed_generation_fingerprint(
            {"prompt": "crafted", "asset_name": "fish", "asset_type": "character"},
            spec=spec,
            project=project,
        )
        handoff = build_handoff(plan, context={"asset": {"id": "char_fish", "description": "old description"}})
        current = build_generation_input(
            self._fish_spec("new description with generation_size 1920x1080"),
            project,
        )
        self.assertTrue(is_handoff_generation_stale(handoff, current))

    def test_legacy_handoff_without_fingerprint_field(self) -> None:
        project = ProjectContext(title="t")
        spec = self._fish_spec("非洲鲶。按 1920×1080 横构图生成")
        handoff = build_handoff(
            {
                "prompt": "p",
                "asset_name": spec.name,
                "asset_type": "character",
                "image_size": resolve_generation_image_size(spec, project),
                "display_size": {"width": 1920, "height": 1080},
            },
            context={
                "asset": {
                    "id": spec.id,
                    "name": spec.name,
                    "type": "character",
                    "description": "非洲鲶。按 1920×1080 横构图生成",
                    "display_size": {"width": 1920, "height": 1080},
                    "aspect_ratio": "16:9",
                },
            },
        )
        current = build_generation_input(
            AssetSpec(
                name=spec.name,
                type=AssetType.CHARACTER,
                id=spec.id,
                description="非洲鲶。按 16:9 横构图生成（generation_size 1920×1080）",
                aspect_ratio="16:9",
                real_length_cm=150,
                generation_size=DisplaySize(1920, 1080),
            ),
            project,
        )
        self.assertTrue(is_handoff_generation_stale(handoff, current))

    def test_fingerprint_stable_json(self) -> None:
        data = {"id": "a", "description": "x", "image_size": "1920x1080"}
        self.assertEqual(
            generation_input_fingerprint(data),
            generation_input_fingerprint(dict(data)),
        )

    def test_size_baseline_in_fingerprint(self) -> None:
        base_project = ProjectContext(title="t")
        spec = AssetSpec(
            name="fish",
            type=AssetType.CHARACTER,
            id="char_fish",
            description="same",
            real_length_cm=50,
        )
        with_baseline = ProjectContext(
            title="t",
            size_baseline={
                "asset_id": "char_ref",
                "real_length_cm": 180,
                "display_size": {"width": 1920, "height": 1080},
            },
        )
        fp_none = generation_input_fingerprint(build_generation_input(spec, base_project))
        fp_base = generation_input_fingerprint(build_generation_input(spec, with_baseline))
        self.assertNotEqual(fp_none, fp_base)

    def test_embed_with_raw_shard_matches_reconcile_current(self) -> None:
        """Craft must fingerprint the same raw_shard reconcile uses, or board wipe is pending."""
        project = ProjectContext(
            title="t",
            size_baseline={
                "asset_id": "char_ref",
                "real_length_cm": 80,
                "display_size": {"width": 213, "height": 120},
            },
        )
        raw_shard = {
            "id": "pose_x",
            "name": "fish_swim",
            "type": "character_pose",
            "description": "swim clip",
            "aspect_ratio": "16:9",
            "action": "swim",
            "animation_method": "video",
            "duration_seconds": 4,
            "animation_loop": True,
            "generate_method": "video",
            "usage": "animation_clip",
            "real_length_cm": 60,
            "size_source": "manual",
            "generation_size": {"width": 1920, "height": 1080},
            "grid": "2x2",
            "reference_asset": "fish_char",
        }
        spec = AssetSpec.from_dict(raw_shard)
        plan = embed_generation_fingerprint(
            {"video_prompt": "swim", "asset_name": spec.name, "asset_type": "character_pose"},
            spec=spec,
            project=project,
            raw_shard=raw_shard,
        )
        handoff = build_handoff(plan, context={"asset": dict(raw_shard), "project": {}})
        current = build_generation_input(spec, project, raw_shard=raw_shard)
        self.assertFalse(is_handoff_generation_stale(handoff, current))
        # Without raw_shard at embed time, reconcile (with shard) falsely marks stale.
        bad = embed_generation_fingerprint(
            {"video_prompt": "swim", "asset_name": spec.name, "asset_type": "character_pose"},
            spec=spec,
            project=project,
        )
        bad_handoff = build_handoff(bad, context={"asset": dict(raw_shard), "project": {}})
        self.assertTrue(is_handoff_generation_stale(bad_handoff, current))


if __name__ == "__main__":
    unittest.main()
