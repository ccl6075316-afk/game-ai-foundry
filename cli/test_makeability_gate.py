"""Tests for makeability export gates and sidecar persistence."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from host_chat import (
    assert_makeability_exportable,
    draft_fingerprint,
    export_brief,
    makeability_sidecar_path,
    new_session,
    write_makeability_sidecar,
)
from test_fixtures import SMOKE_BRIEF

_EXPORT_DRAFT = SMOKE_BRIEF


def _detail_only_review(draft: dict) -> dict:
    return {
        "schema_version": 1,
        "reviewed_at": "2026-07-27T12:00:00+00:00",
        "draft_fingerprint": draft_fingerprint(draft),
        "intent_gaps": [],
        "detail_gaps": [
            {
                "id": "bite_rate",
                "topic": "bite chance and wait timing",
                "suggested_table_shape": "object",
                "example_keys": ["base_bite_chance", "wait_sec_min"],
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


def _ready_session(*, review: dict | None = None) -> dict:
    session = new_session("gate-test")
    draft = copy.deepcopy(_EXPORT_DRAFT)
    session["draft_brief"] = draft
    session["ready_to_export"] = True
    if review is not None:
        session["makeability_review"] = copy.deepcopy(review)
    return session


class MakeabilityGateTests(unittest.TestCase):
    def test_missing_review_allows_structural_export(self) -> None:
        session = _ready_session(review=None)
        brief = export_brief(session)
        self.assertEqual(brief["project"]["title"], _EXPORT_DRAFT["project"]["title"])

    def test_stale_fingerprint_allows_structural_export(self) -> None:
        session = _ready_session(review=_detail_only_review(_EXPORT_DRAFT))
        session["makeability_review"]["draft_fingerprint"] = "stale-fingerprint"
        brief = export_brief(session)
        self.assertIn("project", brief)

    def test_open_intent_gaps_allow_structural_export(self) -> None:
        review = _detail_only_review(_EXPORT_DRAFT)
        review["intent_gaps"] = [
            {
                "id": "win_condition",
                "question": "会话何时结束？",
                "why_blocking": "无明确胜负则无法验收",
            }
        ]
        session = _ready_session(review=review)
        brief = export_brief(session)
        self.assertIn("project", brief)

    def test_detail_gaps_allow_export_and_sidecar(self) -> None:
        session = _ready_session(review=_detail_only_review(_EXPORT_DRAFT))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "brief.json"
            brief = export_brief(session)
            output.write_text(json.dumps(brief, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            sidecar_path = makeability_sidecar_path(output)
            write_makeability_sidecar(sidecar_path, session["makeability_review"])

            self.assertTrue(output.is_file())
            self.assertTrue(sidecar_path.is_file())
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            self.assertEqual(sidecar.get("intent_gaps"), [])
            self.assertGreaterEqual(len(sidecar.get("detail_gaps") or []), 1)
            self.assertIn("brief_meta", brief)

    def test_bound_project_sidecar_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = makeability_sidecar_path("projects/fishing-2d/brief.json", repo_root=root)
            self.assertEqual(path, (root / "projects" / "fishing-2d" / "makeability.json").resolve())

    def test_external_bound_sidecar_path(self) -> None:
        from external_projects import add_external_project

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            ext_root = workspace / "ext-sidecar"
            ext_root.mkdir()
            (ext_root / "project.godot").write_text("", encoding="utf-8")
            entry = add_external_project(workspace, ext_root)
            key = f"external:{entry['id']}/brief.json"
            path = makeability_sidecar_path(key, repo_root=workspace)
            self.assertEqual(path, (ext_root / "makeability.json").resolve())

    def test_assert_makeability_exportable_returns_review(self) -> None:
        session = _ready_session(review=_detail_only_review(_EXPORT_DRAFT))
        review = assert_makeability_exportable(session)
        self.assertEqual(review["draft_fingerprint"], draft_fingerprint(_EXPORT_DRAFT))


if __name__ == "__main__":
    unittest.main()
