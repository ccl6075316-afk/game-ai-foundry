"""Tests for brief-driven animation naming (no hardcoded action presets)."""

from __future__ import annotations

import unittest

from brief import AssetSpec, AssetType, resolve_animation_loop, resolve_animation_name


def _spec(**kwargs: object) -> AssetSpec:
    data = {"name": "hero", "type": "character", **kwargs}
    return AssetSpec.from_dict(data)


class BriefAnimationTests(unittest.TestCase):
    def test_explicit_animation_name(self) -> None:
        spec = _spec(name="hero_cannon", reference_asset="hero", animation_name="fire_cannon")
        self.assertEqual(resolve_animation_name(spec), "fire_cannon")

    def test_derive_from_reference_prefix(self) -> None:
        spec = _spec(
            name="magic_prince_walk",
            reference_asset="magic_prince",
            action="walking",
        )
        self.assertEqual(resolve_animation_name(spec), "walk")

    def test_derive_cannon_without_code_change(self) -> None:
        spec = _spec(
            name="magic_prince_cannon_fire",
            reference_asset="magic_prince",
            action="firing cannon",
        )
        self.assertEqual(resolve_animation_name(spec), "cannon_fire")

    def test_reference_still_is_idle(self) -> None:
        spec = _spec(name="magic_prince", reference_asset="")
        self.assertEqual(resolve_animation_name(spec), "idle")

    def test_animation_loop_from_brief(self) -> None:
        one_shot = _spec(name="hero_attack", reference_asset="hero", animation_loop=False)
        self.assertFalse(resolve_animation_loop(one_shot))
        self.assertTrue(resolve_animation_loop(_spec(name="hero_walk", reference_asset="hero")))


if __name__ == "__main__":
    unittest.main()
