"""prop_stateful states[] expands in manifest; follow-on states use img2img."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline_manifest import build_manifest, tasks_list


def _stateful_brief(*, asset_id: str = "door") -> dict:
    return {
        "project": {
            "title": "T",
            "genre": "platformer",
            "gameplay_loop": "loop",
            "description": "d",
            "art_direction": "pixel",
            "dimension": "2d",
            "session_goal": "demo",
            "controls": {"move": ["A", "D"], "jump": ["Space"]},
            "viewport": {"width": 1280, "height": 720},
        },
        "assets": [
            {
                "name": "door",
                "id": asset_id,
                "type": "texture",
                "usage": "prop",
                "usage_description": "stateful door",
                "description": "door",
                "display_size": {"width": 64, "height": 96},
                "content_class": "prop_stateful",
                "states": ["closed", "open"],
            }
        ],
    }


class StatefulExpandManifestTests(unittest.TestCase):
    def test_follow_on_state_depends_on_state0_raw(self) -> None:
        brief = _stateful_brief()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brief_path = root / "brief.json"
            brief_path.write_text(json.dumps(brief), encoding="utf-8")
            out = root / "output"
            plans = root / "plans"
            with patch(
                "gamefactory.load_config",
                return_value={"image": {"model": "main-m", "bulk_model": "cheap-m"}},
            ):
                manifest = build_manifest(
                    brief_path,
                    output_dir=out,
                    plans_dir=plans,
                    include_godot=False,
                    include_game_dev=False,
                )

        closed_gen = next(
            t for t in tasks_list(manifest) if t["id"] == "door__closed.image.generate"
        )
        open_gen = next(
            t for t in tasks_list(manifest) if t["id"] == "door__open.image.generate"
        )

        self.assertNotIn("--reference-image", closed_gen["command"])

        self.assertIn("door__closed.image.generate", open_gen["depends_on"])
        self.assertIn("--reference-image", open_gen["command"])
        self.assertIn("door__closed_raw.png", open_gen["command"].replace("\\", "/"))

        gens = [t for t in tasks_list(manifest) if t["step"] == "image.generate"]
        self.assertEqual(len(gens), 2)


if __name__ == "__main__":
    unittest.main()
