"""Tests for Makeability Critic (host_chat.run_makeability_review)."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from host_chat import (
    HostChatError,
    _build_user_payload,
    _makeability_critic_system,
    draft_fingerprint,
    format_makeability_review_details,
    new_session,
    run_makeability_review,
    session_status,
)
from host_chat import _build_makeability_review

_FISHING_DRAFT = {
    "project": {
        "title": "River Cast",
        "description": "Relaxing 2D fishing game on a riverside.",
        "art_direction": "Soft watercolor riverside, gentle palette.",
        "dimension": "2d",
        "genre": "fishing",
        "gameplay_loop": (
            "Cast line into water, wait for bite signal, reel minigame, "
            "sell fish at market, spend earnings on gear upgrades, repeat until session goal."
        ),
        "session_goal": "Complete the rare fish collection and unlock the golden rod.",
        "player_asset": "player_fisher",
        "controls": {"move": "arrow keys", "cast": "space", "reel": "hold space"},
        "viewport": {"width": 1280, "height": 720},
        "camera": {"mode": "follow_player"},
        "view": "side",
    },
    "assets": [
        {
            "name": "player_fisher",
            "id": "player_fisher",
            "type": "character",
            "usage": "player",
            "content_class": "character",
            "usage_description": "Fisher avatar on the riverbank.",
            "display_size": {"width": 128, "height": 192},
            "generate_method": "image",
        },
    ],
}


def _v2_intent_gap(**overrides: object) -> dict:
    gap = {
        "id": "win_condition",
        "decision_key": "session.win_condition",
        "target_paths": ["project.session_goal"],
        "write_paths": ["project.session_goal"],
        "occurrences": [{"path": "project.session_goal", "relation": "canonical"}],
        "question": "会话何时算结束？",
        "why_blocking": "无明确胜负则无法验收",
        "choices": ["集齐图鉴", "达到金币目标"],
    }
    gap.update(overrides)
    return gap


def _detail_gaps_mock() -> dict:
    return {
        "intent_gaps": [],
        "detail_gaps": [
            {
                "id": "bite_rate",
                "topic": "bite chance and wait timing",
                "suggested_table_shape": "object",
                "example_keys": ["base_bite_chance", "wait_sec_min", "wait_sec_max"],
            },
            {
                "id": "fish_economy",
                "topic": "fish prices and sell values",
                "suggested_table_shape": "array",
                "example_keys": ["species_id", "base_price", "rarity"],
            },
            {
                "id": "reel_minigame",
                "topic": "reel tension and failure thresholds",
                "suggested_table_shape": "object",
                "example_keys": ["tension_gain", "snap_threshold", "cooldown_sec"],
            },
        ],
        "suggested_defaults": [
            {
                "gap_id": "bite_rate",
                "value": {"base_bite_chance": 0.35, "wait_sec_min": 2, "wait_sec_max": 8},
                "confidence": "low",
                "note": "provisional placeholder",
            },
        ],
    }


class MakeabilityCriticTests(unittest.TestCase):
    def test_draft_fingerprint_stable(self) -> None:
        fp1 = draft_fingerprint(_FISHING_DRAFT)
        fp2 = draft_fingerprint(copy.deepcopy(_FISHING_DRAFT))
        self.assertEqual(fp1, fp2)
        self.assertEqual(len(fp1), 64)

    def test_fishing_draft_detail_gaps_parsed_without_mutating_draft(self) -> None:
        session = new_session("fish-review")
        draft = copy.deepcopy(_FISHING_DRAFT)
        session["draft_brief"] = draft
        session["ready_to_export"] = True
        draft_ref_before = session["draft_brief"]

        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(_detail_gaps_mock()),
        ):
            result = run_makeability_review(session, config=config)

        self.assertTrue(result["ok"])
        self.assertEqual(result["intent_count"], 0)
        self.assertGreaterEqual(result["detail_count"], 3)
        self.assertIs(session["draft_brief"], draft_ref_before)
        self.assertEqual(session["draft_brief"], _FISHING_DRAFT)

        review = session.get("makeability_review")
        self.assertIsInstance(review, dict)
        self.assertEqual(review.get("schema_version"), 2)
        self.assertEqual(review.get("draft_fingerprint"), draft_fingerprint(_FISHING_DRAFT))
        self.assertGreaterEqual(len(review.get("detail_gaps") or []), 3)

        st = session_status(session)
        self.assertTrue(st["has_review"])
        self.assertEqual(st["intent_count"], 0)
        self.assertGreaterEqual(st["detail_count"], 3)
        self.assertTrue(st["makeability_fingerprint_match"])

    def test_bad_json_raises_and_preserves_old_review(self) -> None:
        session = new_session("fish-bad-json")
        session["draft_brief"] = copy.deepcopy(_FISHING_DRAFT)
        old_review = {
            "schema_version": 2,
            "reviewed_at": "2026-07-27T00:00:00+00:00",
            "draft_fingerprint": "old",
            "intent_gaps": [],
            "detail_gaps": [{"id": "keep_me"}],
            "suggested_defaults": [],
        }
        session["makeability_review"] = copy.deepcopy(old_review)

        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion", return_value="not json at all"):
            with self.assertRaises(HostChatError):
                run_makeability_review(session, config=config)

        self.assertEqual(session["makeability_review"], old_review)

    def test_intent_gaps_force_ready_to_export_false(self) -> None:
        session = new_session("fish-intent")
        session["draft_brief"] = copy.deepcopy(_FISHING_DRAFT)
        session["ready_to_export"] = True

        payload = _detail_gaps_mock()
        payload["intent_gaps"] = [_v2_intent_gap()]

        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion", return_value=json.dumps(payload)):
            result = run_makeability_review(session, config=config)

        self.assertEqual(result["intent_count"], 1)
        self.assertFalse(session["ready_to_export"])
        self.assertFalse(result["ready_to_export"])
        # Review must land in conversation + next-turn payload for the main agent.
        messages = session.get("messages") or []
        self.assertTrue(messages)
        self.assertEqual(messages[-1]["role"], "assistant")
        self.assertIn("意图缺口", messages[-1]["content"])
        self.assertIn("会话何时算结束", messages[-1]["content"])
        self.assertIn("意图缺口", result["assistant_message"])

        payload = _build_user_payload(session, "chat")
        latest = payload.get("latest_makeability_review")
        self.assertIsInstance(latest, dict)
        self.assertTrue(latest.get("fingerprint_match"))
        self.assertEqual(len(latest.get("intent_gaps") or []), 1)
        self.assertIn("win_condition", str(latest["intent_gaps"][0].get("id")))

    def test_repeat_makeability_review_does_not_repeat_detail_topics(self) -> None:
        session = new_session("detail-dedupe")
        session["draft_brief"] = copy.deepcopy(_FISHING_DRAFT)
        payload = _detail_gaps_mock()
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(payload, ensure_ascii=False),
        ):
            first = run_makeability_review(session, config=config)
        topic = payload["detail_gaps"][0]["topic"]
        self.assertIn(topic, first["assistant_message"])
        self.assertGreaterEqual(len(session["makeability_review"]["detail_gaps"]), 3)

        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(payload, ensure_ascii=False),
        ):
            second = run_makeability_review(session, config=config)

        self.assertNotIn(topic, second["assistant_message"])
        self.assertIn("不再重复", second["assistant_message"])
        self.assertGreaterEqual(len(session["makeability_review"]["detail_gaps"]), 3)

    def test_detail_dedupe_same_topic_different_id(self) -> None:
        from makeability_decisions import detail_gap_stable_key

        topic = "Bite Rate And Timing"
        session = new_session("topic-dedupe")
        session["draft_brief"] = copy.deepcopy(_FISHING_DRAFT)
        first_payload = {
            "intent_gaps": [],
            "detail_gaps": [{"id": "bite_rate", "topic": topic}],
            "suggested_defaults": [],
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(first_payload, ensure_ascii=False),
        ):
            first = run_makeability_review(session, config=config)
        self.assertIn(topic.lower(), first["assistant_message"].lower())

        second_payload = {
            "intent_gaps": [],
            "detail_gaps": [{"id": "bite_rate_v2", "topic": "  bite   rate and timing  "}],
            "suggested_defaults": [],
        }
        self.assertEqual(
            detail_gap_stable_key(first_payload["detail_gaps"][0]),
            detail_gap_stable_key(second_payload["detail_gaps"][0]),
        )
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(second_payload, ensure_ascii=False),
        ):
            second = run_makeability_review(session, config=config)
        self.assertNotIn("bite_rate_v2", second["assistant_message"])
        self.assertIn("不再重复", second["assistant_message"])

    def test_format_makeability_review_details_lists_gaps(self) -> None:
        text = format_makeability_review_details(
            {
                "intent_gaps": [
                    {
                        "id": "a",
                        "question": "Q?",
                        "why_blocking": "because",
                        "choices": ["x", "y"],
                    }
                ],
                "detail_gaps": [{"id": "b", "topic": "numbers"}],
            }
        )
        self.assertIn("意图缺口", text)
        self.assertIn("Q?", text)
        self.assertIn("选项：x / y", text)
        self.assertIn("施工细节", text)
        self.assertIn("numbers", text)

    def test_critic_skill_schema_lists_occurrences_write_paths_and_scan_areas(self) -> None:
        system = _makeability_critic_system()
        for token in (
            "occurrences",
            "write_paths",
            "target_paths",
            "description",
            "gameplay_loop",
            "scenes",
            "systems",
            "ui_panels",
            "canonical",
            "duplicate",
            "conflict",
        ):
            self.assertIn(token, system, msg=f"missing {token} in critic system prompt")

    def test_fresh_critic_rejects_illegal_occurrence_relation(self) -> None:
        from host_chat import _build_makeability_review

        session = new_session("bad-relation")
        session["draft_brief"] = copy.deepcopy(_FISHING_DRAFT)
        parsed = {
            "intent_gaps": [
                {
                    "id": "bad_gap",
                    "decision_key": "session.bad",
                    "write_paths": ["project.session_goal", "project.description"],
                    "occurrences": [
                        {"path": "project.session_goal", "relation": "canonical"},
                        {"path": "project.description", "relation": "similar"},
                    ],
                    "question": "Q?",
                    "why_blocking": "x",
                }
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        with self.assertRaises(HostChatError) as ctx:
            _build_makeability_review(
                parsed,
                fingerprint=draft_fingerprint(_FISHING_DRAFT),
                session=session,
            )
        self.assertIn("invalid relation", str(ctx.exception))

    def test_fresh_critic_rejects_intent_gap_without_occurrences(self) -> None:
        from host_chat import _build_makeability_review

        session = new_session("fresh-schema")
        session["draft_brief"] = copy.deepcopy(_FISHING_DRAFT)
        parsed = {
            "intent_gaps": [
                {
                    "id": "bad_gap",
                    "decision_key": "session.bad",
                    "target_paths": ["project.session_goal"],
                    "write_paths": ["project.session_goal"],
                    "question": "Q?",
                    "why_blocking": "x",
                }
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        with self.assertRaises(HostChatError):
            _build_makeability_review(
                parsed,
                fingerprint=draft_fingerprint(_FISHING_DRAFT),
                session=session,
            )


    def test_fresh_critic_heals_conflict_path_missing_from_write_paths(self) -> None:
        from host_chat import _build_makeability_review

        session = new_session("fresh-schema-wp")
        session["draft_brief"] = copy.deepcopy(_FISHING_DRAFT)
        parsed = {
            "intent_gaps": [
                {
                    "id": "bad_gap",
                    "decision_key": "session.bad",
                    "target_paths": ["project.systems[id=aquarium].notes"],
                    "write_paths": ["project.systems[id=aquarium].notes"],
                    "occurrences": [
                        {
                            "path": "project.systems[id=aquarium].notes",
                            "relation": "canonical",
                        },
                        {
                            "path": "project.scenes[id=hall].notes",
                            "relation": "conflict",
                        },
                    ],
                    "question": "Q?",
                    "why_blocking": "x",
                    "choices": ["A", "B"],
                }
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        review = _build_makeability_review(
            parsed,
            fingerprint=draft_fingerprint(_FISHING_DRAFT),
            session=session,
        )
        gaps = review.get("intent_gaps") or []
        self.assertEqual(len(gaps), 1)
        wp = {str(p).lower() for p in (gaps[0].get("write_paths") or [])}
        self.assertIn("project.scenes[id=hall].notes", wp)
        self.assertIn("project.systems[id=aquarium].notes", wp)

    def test_fresh_critic_accepts_duplicate_conflict_in_write_paths(self) -> None:
        from host_chat import _build_makeability_review

        session = new_session("fresh-schema-ok")
        session["draft_brief"] = copy.deepcopy(_FISHING_DRAFT)
        parsed = {
            "intent_gaps": [
                {
                    "id": "ok_gap",
                    "decision_key": "system.aquarium.rule",
                    "target_paths": ["project.systems[id=aquarium].notes"],
                    "write_paths": [
                        "project.description",
                        "project.scenes[id=hall].notes",
                        "project.systems[id=aquarium].notes",
                    ],
                    "occurrences": [
                        {"path": "project.systems[id=aquarium].notes", "relation": "canonical"},
                        {"path": "project.description", "relation": "duplicate"},
                        {"path": "project.scenes[id=hall].notes", "relation": "conflict"},
                    ],
                    "question": "Q?",
                    "why_blocking": "x",
                    "choices": ["A", "B"],
                }
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        review = _build_makeability_review(
            parsed,
            fingerprint=draft_fingerprint(_FISHING_DRAFT),
            session=session,
        )
        self.assertEqual(len(review.get("intent_gaps") or []), 1)

    def test_catalog_makeability_without_bind_raises(self) -> None:
        session = new_session("catalog-blind")
        session["draft_brief"] = {
            "project": {
                "title": "Fish",
                "description": "overview",
                "genre": "sim",
                "gameplay_loop": "cast",
                "session_goal": "endless",
                "scenes": [{"id": "hub", "title": "Hub", "path": "scenes/hub.json"}],
                "systems": [],
            },
            "assets": [],
        }
        config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
        with patch("host_chat.chat_text_completion") as mock_chat:
            with self.assertRaises(HostChatError) as ctx:
                run_makeability_review(session, config=config)
            mock_chat.assert_not_called()
        self.assertIn("绑定", str(ctx.exception))

    def test_catalog_makeability_with_bind_sees_shard_notes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "scenes").mkdir()
            (root / "scenes" / "hub.json").write_text(
                json.dumps(
                    {"id": "hub", "title": "Hub", "notes": "SHARD_BODY_VISIBLE"},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            brief_path = root / "brief.json"
            brief_path.write_text("{}", encoding="utf-8")
            session = new_session("catalog-bound")
            # Point bind at a path under repo via monkeypatch of project root resolver
            session["draft_brief"] = {
                "project": {
                    "title": "Fish",
                    "description": "overview",
                    "genre": "sim",
                    "gameplay_loop": "cast",
                    "session_goal": "endless",
                    "scenes": [{"id": "hub", "title": "Hub", "path": "scenes/hub.json"}],
                    "systems": [],
                },
                "assets": [],
            }
            session["bound_brief_rel"] = "projects/_tmp_catalog_test/brief.json"
            seen: dict[str, Any] = {}

            def fake_chat(**kwargs: Any) -> str:
                payload = json.loads(kwargs["messages"][1]["content"])
                scenes = (payload.get("draft_brief") or {}).get("project", {}).get("scenes") or []
                hub = next((s for s in scenes if s.get("id") == "hub"), None)
                seen["notes"] = (hub or {}).get("notes")
                seen["shards"] = list((payload.get("scene_shards") or {}).keys())
                return json.dumps(_detail_gaps_mock())

            config = {"host": {"api_key": "k", "api_base": "https://example/v1", "model": "m"}}
            with (
                patch(
                    "host_chat._project_root_for_session",
                    return_value=root,
                ),
                patch("host_chat.chat_text_completion", side_effect=fake_chat),
            ):
                result = run_makeability_review(session, config=config)
            self.assertTrue(result["ok"])
            self.assertEqual(seen.get("notes"), "SHARD_BODY_VISIBLE")
            self.assertIn("hub", seen.get("shards") or [])


if __name__ == "__main__":
    unittest.main()
