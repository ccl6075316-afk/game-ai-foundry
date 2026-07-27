"""Tests for production derive merging makeability sidecar."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from production import (
    derive_production,
    load_makeability_sidecar,
    validate_production,
)
from test_fixtures import EXAMPLE_BRIEF, write_brief


SAMPLE_SIDECAR = {
    "schema_version": 1,
    "reviewed_at": "2026-07-27T08:00:00+00:00",
    "draft_fingerprint": "abc123",
    "intent_gaps": [],
    "detail_gaps": [
        {
            "id": "bite_rate",
            "topic": "bite chance / wait time",
            "suggested_table_shape": "object",
            "example_keys": ["base_bite_chance", "wait_sec_min"],
        },
        {
            "id": "fish_prices",
            "topic": "economy table",
            "suggested_table_shape": "object",
            "example_keys": ["common", "rare"],
        },
    ],
    "suggested_defaults": [
        {
            "gap_id": "bite_rate",
            "value": {"base_bite_chance": 0.35, "wait_sec_min": 2},
            "confidence": "low",
            "note": "provisional placeholder",
        },
    ],
}


def _write_sidecar(brief_path: Path, sidecar: dict) -> Path:
    sidecar_path = brief_path.parent / "makeability.json"
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return sidecar_path


class LoadMakeabilitySidecarTest(unittest.TestCase):
    def test_missing_sidecar_returns_none(self) -> None:
        brief = write_brief({"project": {"title": "NoSidecar", "genre": "generic"}, "assets": []})
        self.addCleanup(lambda: brief.unlink(missing_ok=True))
        self.assertIsNone(load_makeability_sidecar(brief))

    def test_existing_sidecar_parsed(self) -> None:
        brief = write_brief({"project": {"title": "HasSidecar", "genre": "generic"}, "assets": []})
        self.addCleanup(lambda: brief.unlink(missing_ok=True))
        sidecar_path = _write_sidecar(brief, SAMPLE_SIDECAR)
        self.addCleanup(lambda: sidecar_path.unlink(missing_ok=True))
        loaded = load_makeability_sidecar(brief)
        self.assertIsInstance(loaded, dict)
        self.assertEqual(len(loaded.get("detail_gaps") or []), 2)


class DeriveMakeabilityMergeTest(unittest.TestCase):
    def test_no_sidecar_derive_unchanged(self) -> None:
        data = derive_production(EXAMPLE_BRIEF)
        doc = data["production_doc"]
        self.assertNotIn("makeability", doc)
        errors = validate_production(data, brief_path=EXAMPLE_BRIEF)
        self.assertEqual(errors, [])

    def test_with_sidecar_merges_makeability_and_tuning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = Path(tmp) / "brief.json"
            brief_path.write_text(EXAMPLE_BRIEF.read_text(encoding="utf-8"), encoding="utf-8")
            _write_sidecar(brief_path, SAMPLE_SIDECAR)

            data = derive_production(brief_path)
            doc = data["production_doc"]

            makeability = doc.get("makeability")
            self.assertIsInstance(makeability, dict)
            self.assertEqual(makeability["status"], "pending")
            self.assertIn("source", makeability)

            items = makeability.get("detail_items")
            self.assertIsInstance(items, list)
            self.assertEqual(len(items), 2)

            bite = next(i for i in items if i["id"] == "bite_rate")
            self.assertEqual(bite["status"], "provisional")
            self.assertEqual(bite["owner"], "pm")
            self.assertEqual(
                bite["provisional_values"],
                {"base_bite_chance": 0.35, "wait_sec_min": 2},
            )

            fish = next(i for i in items if i["id"] == "fish_prices")
            self.assertEqual(fish["status"], "open")
            self.assertNotIn("provisional_values", fish)

            tuning = doc.get("tuning")
            self.assertIsInstance(tuning, dict)
            self.assertEqual(tuning.get("bite_rate"), {"base_bite_chance": 0.35, "wait_sec_min": 2})

            errors = validate_production(data, brief_path=brief_path)
            self.assertEqual(errors, [])

    def test_all_defaults_yields_partial_status(self) -> None:
        sidecar = {
            **SAMPLE_SIDECAR,
            "suggested_defaults": [
                *SAMPLE_SIDECAR["suggested_defaults"],
                {
                    "gap_id": "fish_prices",
                    "value": {"common": 10, "rare": 50},
                    "confidence": "low",
                    "note": "provisional",
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = Path(tmp) / "brief.json"
            brief_path.write_text(EXAMPLE_BRIEF.read_text(encoding="utf-8"), encoding="utf-8")
            _write_sidecar(brief_path, sidecar)

            data = derive_production(brief_path)
            makeability = data["production_doc"]["makeability"]
            self.assertEqual(makeability["status"], "partial")
            self.assertTrue(all(i["status"] == "provisional" for i in makeability["detail_items"]))

    def test_all_open_details_yields_pending_status(self) -> None:
        sidecar = {
            **SAMPLE_SIDECAR,
            "suggested_defaults": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = Path(tmp) / "brief.json"
            brief_path.write_text(EXAMPLE_BRIEF.read_text(encoding="utf-8"), encoding="utf-8")
            _write_sidecar(brief_path, sidecar)

            data = derive_production(brief_path)
            makeability = data["production_doc"]["makeability"]
            self.assertEqual(makeability["status"], "pending")
            self.assertTrue(all(i["status"] == "open" for i in makeability["detail_items"]))
            self.assertNotIn("tuning", data["production_doc"])


class ValidateMakeabilityBackwardCompatTest(unittest.TestCase):
    def test_validate_without_makeability_still_passes(self) -> None:
        data = derive_production(EXAMPLE_BRIEF)
        self.assertNotIn("makeability", data["production_doc"])
        errors = validate_production(data, brief_path=EXAMPLE_BRIEF)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
