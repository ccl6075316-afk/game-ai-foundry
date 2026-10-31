"""Prevent a hall redeployment from restoring a stale monolithic/visitor-free host."""
import unittest
from pathlib import Path

from produce_hall_3d import NAMES

ROOT = Path(__file__).resolve().parents[3]
GAME = ROOT / "projects/fishing-2d/game"


class HallSourceSyncTests(unittest.TestCase):
    @unittest.skipUnless((GAME / "project.godot").is_file(), "Requires the optional fishing-2d checkout")
    def test_every_deployed_source_matches_the_game(self):
        for name in NAMES:
            with self.subTest(name=name):
                self.assertEqual((ROOT / "resources/runtime/godot/aquascape" / name).read_bytes(),
                                 (GAME / "scripts/aquarium" / name).read_bytes())

    def test_all_sources_exist_in_standalone_foundry(self):
        for name in NAMES:
            with self.subTest(name=name):
                self.assertTrue((ROOT / "resources/runtime/godot/aquascape" / name).is_file())

    def test_modules_and_visitor_dependencies_are_deployed_together(self):
        self.assertEqual(len(NAMES), len(set(NAMES)))
        for name in ["HallLayoutRules", "HallLayoutStore", "HallEditHistory", "HallEditorPanel",
                     "HallEditorInput", "HallWalkController", "HallLayoutDocument", "HallBuildCommands",
                     "HallSceneProjection"]:
            self.assertIn("hall/" + name + ".gd", NAMES)
        self.assertIn("visitors/HallVisitorCrowd.gd", NAMES)
        self.assertIn("visitors/HallVisitorNavigation.gd", NAMES)
        self.assertIn("visitors/VisitorMaterialV2.gdshader", NAMES)


if __name__ == "__main__":
    unittest.main()
