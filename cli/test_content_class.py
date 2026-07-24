"""Tests for project.view / assets[].content_class / states / expand_stateful_assets."""

from __future__ import annotations

import unittest

from brief import (
    AssetSpec,
    ProjectContext,
    audit_content_class,
    expand_stateful_assets,
    normalize_asset_states,
)
from shared_context import asset_to_dict, project_to_dict


def _minimal_asset(**overrides: object) -> AssetSpec:
    base = {
        "name": "door",
        "id": "door",
        "type": "texture",
        "usage": "prop",
        "usage_description": "stateful door",
        "description": "door",
        "display_size": {"width": 64, "height": 96},
    }
    base.update(overrides)
    return AssetSpec.from_dict(base)


class ContentClassTests(unittest.TestCase):
    def test_absent_fields_ok(self) -> None:
        project = ProjectContext.from_dict({"title": "Legacy"})
        asset = _minimal_asset()
        self.assertEqual(project.view, "")
        self.assertEqual(asset.content_class, "")
        self.assertEqual(asset.states, [])
        self.assertEqual(asset.state, "")
        self.assertEqual(audit_content_class(project, [asset]), [])

    def test_bad_view_audit_error(self) -> None:
        project = ProjectContext.from_dict({"view": "isometric"})
        errors = audit_content_class(project, [])
        self.assertTrue(any("project.view must be one of" in e for e in errors))

    def test_bad_class_audit_error(self) -> None:
        project = ProjectContext.from_dict({})
        asset = _minimal_asset(content_class="door")
        errors = audit_content_class(project, [asset])
        self.assertTrue(any("content_class must be one of" in e for e in errors))

    def test_states_without_prop_stateful_error(self) -> None:
        project = ProjectContext.from_dict({})
        asset = _minimal_asset(content_class="prop_static", states=["open", "closed"])
        errors = audit_content_class(project, [asset])
        self.assertTrue(any("states[] requires content_class 'prop_stateful'" in e for e in errors))

    def test_prop_stateful_single_state_error(self) -> None:
        project = ProjectContext.from_dict({})
        asset = _minimal_asset(content_class="prop_stateful", states=["closed"])
        errors = audit_content_class(project, [asset])
        self.assertTrue(any("requires at least 2 states" in e for e in errors))

    def test_expand_two_states(self) -> None:
        asset = _minimal_asset(
            content_class="prop_stateful",
            states=["closed", "open"],
        )
        expanded = expand_stateful_assets([asset])
        self.assertEqual(len(expanded), 2)
        self.assertEqual(expanded[0].id, "door__closed")
        self.assertEqual(expanded[0].state, "closed")
        self.assertEqual(expanded[0].states, [])
        self.assertEqual(expanded[1].id, "door__open")
        self.assertEqual(expanded[1].state, "open")
        self.assertEqual(expanded[1].states, [])

    def test_expand_does_not_mutate_original(self) -> None:
        asset = _minimal_asset(
            content_class="prop_stateful",
            states=["closed", "open"],
        )
        original_states = list(asset.states)
        expand_stateful_assets([asset])
        self.assertEqual(asset.states, original_states)
        self.assertEqual(asset.id, "door")

    def test_round_trip_project_view_and_content_class(self) -> None:
        project = ProjectContext.from_dict({"view": "side"})
        asset = AssetSpec.from_dict(
            {
                "name": "floor",
                "id": "floor_a",
                "type": "texture",
                "usage": "tile_texture",
                "usage_description": "floor",
                "description": "floor",
                "display_size": {"width": 32, "height": 32},
                "content_class": "floor_tile",
            }
        )
        project_out = project_to_dict(project)
        asset_out = asset_to_dict(asset)
        self.assertEqual(project_out["view"], "side")
        self.assertEqual(asset_out["content_class"], "floor_tile")

        reparsed_project = ProjectContext.from_dict(project_out)
        reparsed_asset = AssetSpec.from_dict(asset_out)
        self.assertEqual(reparsed_project.view, "side")
        self.assertEqual(reparsed_asset.content_class, "floor_tile")

    def test_round_trip_state_field(self) -> None:
        asset = AssetSpec.from_dict(
            {
                "name": "door closed",
                "id": "door__closed",
                "type": "texture",
                "usage": "prop",
                "usage_description": "closed",
                "description": "closed",
                "display_size": {"width": 64, "height": 96},
                "content_class": "prop_stateful",
                "state": "closed",
            }
        )
        out = asset_to_dict(asset)
        self.assertEqual(out["state"], "closed")
        self.assertNotIn("states", out)
        reparsed = AssetSpec.from_dict(out)
        self.assertEqual(reparsed.state, "closed")

    def test_normalize_asset_states_dedupes_and_strips(self) -> None:
        self.assertEqual(
            normalize_asset_states([" closed ", "", "open", "closed", "open"]),
            ["closed", "open"],
        )


if __name__ == "__main__":
    unittest.main()
