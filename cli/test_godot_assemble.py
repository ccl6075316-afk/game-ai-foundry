"""Tests for godot assemble plan resolution."""

from __future__ import annotations

import unittest

from godot_assemble import GodotAssembleError, _resolve_character_asset


class GodotAssemblePlanTests(unittest.TestCase):
    def test_explicit_character_asset(self) -> None:
        name = _resolve_character_asset(
            {"character_asset": "magic_prince"},
            idle_still=None,
            animations=[],
        )
        self.assertEqual(name, "magic_prince")

    def test_from_idle_still_path(self) -> None:
        name = _resolve_character_asset(
            {},
            idle_still="output/demo/magic_prince_nobg.png",
            animations=[],
        )
        self.assertEqual(name, "magic_prince")

    def test_from_animation_reference_asset(self) -> None:
        name = _resolve_character_asset(
            {},
            idle_still=None,
            animations=[{"asset": "magic_prince_cannon", "reference_asset": "magic_prince"}],
        )
        self.assertEqual(name, "magic_prince")

    def test_missing_character_asset_raises(self) -> None:
        with self.assertRaises(GodotAssembleError):
            _resolve_character_asset({}, idle_still=None, animations=[{"asset": "orphan_anim"}])


if __name__ == "__main__":
    unittest.main()
