"""Tests for makeability decision ledger (repeat-question fix)."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from host_chat import (
    HostChatError,
    _apply_parsed,
    _build_user_payload,
    _compute_ready_to_export,
    answer_makeability_gaps,
    assert_makeability_exportable,
    draft_fingerprint,
    new_session,
    run_makeability_review,
    save_session,
)
from makeability_decisions import (
    apply_whole_card_verifier_results,
    assert_critic_decision_checks_protocol,
    canonicalize_decision_checks,
    complete_critic_ledger_checks,
    decisions_for_verifier,
    effective_decision_check_status,
    ensure_decision_ledger,
    filter_intent_gaps_for_display,
    ledger_blocks_export,
    merge_critic_decision_checks,
    normalize_target_paths,
    record_gap_answers,
    reconcile_intent_gaps_with_ledger,
    required_write_paths_from_gap,
    decision_key_alias_map_from_checks,
    decision_key_alias_map_from_gaps,
    required_paths_by_key_from_ledger,
    resolve_decision_key,
    resolve_gaps_for_answers,
    sanitize_intent_gap,
    suppress_intent_gaps_by_ledger,
    validate_occurrences_strict,
    verifier_path_failure_detail,
    verifier_reported_all_keys,
)
from test_makeability_gate import _detail_only_review, _ready_session
from test_fixtures import SMOKE_BRIEF


def _minimal_draft() -> dict:
    return {
        "project": {
            "title": "Fish",
            "description": "d",
            "genre": "sim",
            "gameplay_loop": "cast",
            "session_goal": "endless",
            "systems": [
                {"id": "aquarium", "notes": "locked until purchased"},
                {"id": "market", "notes": "sell fish"},
            ],
        },
        "assets": [{"name": "rod", "type": "prop", "usage": "player"}],
    }


def _route_llm(*, closer: dict, verifier: dict, verifier_sequence: list[dict] | None = None):
    calls = {"n": 0}

    def side_effect(**kwargs):
        messages = kwargs["messages"]
        system = messages[0]["content"]
        if "Makeability Verifier" in system:
            if verifier_sequence is not None:
                idx = calls["n"]
                calls["n"] += 1
                payload = verifier_sequence[min(idx, len(verifier_sequence) - 1)]
            else:
                payload = verifier
            return json.dumps(payload, ensure_ascii=False)
        return json.dumps(closer, ensure_ascii=False)

    return side_effect


def _multi_path_gap() -> dict:
    return {
        "id": "aquarium_unlock_flow",
        "decision_key": "system.aquarium.unlock_rule",
        "question": "水族馆如何进入？",
        "target_paths": ["project.systems[id=aquarium].notes"],
        "write_paths": [
            "project.description",
            "project.scenes[id=aquarium_hall].notes",
            "project.systems[id=aquarium].notes",
        ],
        "occurrences": [
            {"path": "project.description", "relation": "duplicate"},
            {"path": "project.scenes[id=aquarium_hall].notes", "relation": "conflict"},
            {"path": "project.systems[id=aquarium].notes", "relation": "canonical"},
        ],
        "choices": ["A", "B"],
    }


def _v2_aquarium_intent(**overrides: object) -> dict:
    gap = {
        "id": "aquarium_unlock_flow",
        "decision_key": "system.aquarium.unlock_rule",
        "target_paths": ["project.systems[id=aquarium].notes"],
        "write_paths": ["project.systems[id=aquarium].notes"],
        "occurrences": [
            {"path": "project.systems[id=aquarium].notes", "relation": "canonical"},
        ],
        "question": "Q",
        "choices": ["A", "B"],
    }
    gap.update(overrides)
    return gap


class EarlyPersistTests(unittest.TestCase):
    def test_persist_after_record_called_before_api(self) -> None:
        session = new_session("persist-cb")
        session["draft_brief"] = _minimal_draft()
        session["makeability_review"] = {
            "schema_version": 2,
            "intent_gaps": [
                {
                    "id": "g1",
                    "decision_key": "system.a",
                    "question": "Q",
                    "choices": ["A"],
                }
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        calls: list[str] = []

        def persist(sess: dict) -> None:
            calls.append("persist")
            self.assertEqual(
                ensure_decision_ledger(sess)[0].get("status"),
                "pending",
            )

        with patch(
            "host_chat.resolve_host_api_settings",
            side_effect=lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("resolver boom")),
        ):
            answer_makeability_gaps(
                session,
                [{"gap_id": "g1", "choice": "A"}],
                config={},
                persist_after_record=persist,
            )
        self.assertEqual(calls, ["persist"])
        self.assertIn("A", ensure_decision_ledger(session)[0]["answer_text"])

    def test_cli_resolver_error_session_file_has_answer(self) -> None:
        from gamefactory import cli as gf_cli

        session = new_session("cli-resolver")
        session["draft_brief"] = _minimal_draft()
        session["makeability_review"] = {
            "schema_version": 2,
            "intent_gaps": [
                {
                    "id": "aquarium_unlock_flow",
                    "decision_key": "system.aquarium.unlock_rule",
                    "question": "Q",
                    "choices": ["A", "B"],
                }
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sess.json"
            save_session(path, session)
            answers = json.dumps([{"gap_id": "aquarium_unlock_flow", "choice": "B"}])
            runner = CliRunner()
            with patch(
                "host_chat.resolve_host_api_settings",
                side_effect=RuntimeError("resolver boom"),
            ):
                result = runner.invoke(
                    gf_cli,
                    [
                        "brief",
                        "chat",
                        "makeability-answer",
                        "--session",
                        str(path),
                        "--answers",
                        answers,
                        "--json",
                    ],
                    obj={"config": {}},
                )
            self.assertEqual(result.exit_code, 2)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            ledger = loaded.get("decision_ledger") or []
            self.assertTrue(ledger)
            self.assertIn("B", ledger[0].get("answer_text", ""))
            self.assertIn(ledger[0].get("status"), ("pending", "repair_failed"))


class TargetPathReconcileTests(unittest.TestCase):
    def test_same_target_paths_different_key_suppressed(self) -> None:
        paths = ["project.systems[id=aquarium].notes"]
        session = new_session("path-reconcile")
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "old_gap",
                "answer_text": "B",
                "status": "verified",
                "gap_snapshot": {
                    "id": "old_gap",
                    "decision_key": "system.aquarium.unlock_rule",
                    "target_paths": paths,
                },
                "verified_draft_fingerprint": "fp1",
            }
        ]
        raw_gaps = [
            {
                "id": "brand_new_gap",
                "decision_key": "system.aquarium.entry_rule",
                "target_paths": paths,
                "question": "reworded?",
            }
        ]
        reconciled = reconcile_intent_gaps_with_ledger(session, raw_gaps)
        # Explicit different decision_key on same path must stay distinct (M2).
        self.assertEqual(reconciled[0]["decision_key"], "system.aquarium.entry_rule")
        self.assertNotIn("decision_key_alias", reconciled[0])
        filtered = suppress_intent_gaps_by_ledger(session, reconciled)
        self.assertEqual(len(filtered), 1)

    def test_gap_id_fallback_key_still_reconciles_by_path(self) -> None:
        paths = ["project.systems[id=aquarium].notes"]
        session = new_session("path-reconcile-gapkey")
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "old_gap",
                "answer_text": "B",
                "status": "verified",
                "gap_snapshot": {
                    "id": "old_gap",
                    "decision_key": "system.aquarium.unlock_rule",
                    "target_paths": paths,
                },
                "verified_draft_fingerprint": "fp1",
            }
        ]
        raw_gaps = [
            {
                "id": "brand_new_gap",
                "decision_key": "gap.brand_new_gap",
                "target_paths": paths,
                "question": "reworded?",
            }
        ]
        reconciled = reconcile_intent_gaps_with_ledger(session, raw_gaps)
        self.assertEqual(reconciled[0]["decision_key"], "system.aquarium.unlock_rule")
        filtered = suppress_intent_gaps_by_ledger(session, reconciled)
        self.assertEqual(filtered, [])

    def test_normalize_target_paths_order_insensitive(self) -> None:
        a = normalize_target_paths(["B.Path", "A.Path"])
        b = normalize_target_paths(["a.path", "b.path"])
        self.assertEqual(a, b)


class VerifiedFingerprintTests(unittest.TestCase):
    def test_verifier_writes_verified_draft_fingerprint(self) -> None:
        session = new_session("vfp")
        session["decision_ledger"] = [
            {
                "decision_key": "system.a",
                "gap_id": "ga",
                "answer_text": "x",
                "status": "applied",
            }
        ]
        fp = "abc123"
        checks = [
            {
                "decision_key": "system.a",
                "gap_id": "ga",
                "status": "satisfied",
                "evidence_paths": [],
            }
        ]
        apply_whole_card_verifier_results(
            session,
            ["system.a"],
            checks,
            gap_id_for_key={"system.a": "ga"},
            raw_complete=True,
            verified_draft_fingerprint=fp,
        )
        self.assertEqual(ensure_decision_ledger(session)[0]["verified_draft_fingerprint"], fp)

    def test_stale_verified_fingerprint_blocks_export(self) -> None:
        draft = _minimal_draft()
        fp_old = draft_fingerprint(draft)
        draft2 = copy.deepcopy(draft)
        draft2["project"]["systems"][0]["notes"] = "externally changed"
        fp_new = draft_fingerprint(draft2)
        session = new_session("stale-vfp")
        session["draft_brief"] = draft2
        session["decision_ledger"] = [
            {
                "decision_key": "system.a",
                "gap_id": "g",
                "answer_text": "x",
                "status": "verified",
                "verified_draft_fingerprint": fp_old,
            }
        ]
        self.assertTrue(ledger_blocks_export(session, current_draft_fingerprint=fp_new))
        self.assertFalse(ledger_blocks_export(session, current_draft_fingerprint=fp_old))

    def test_critic_empty_checks_fail_protocol_without_downgrade(self) -> None:
        from host_chat import _build_makeability_review

        draft = _minimal_draft()
        fp = draft_fingerprint(draft)
        session = new_session("critic-empty")
        session["draft_brief"] = copy.deepcopy(draft)
        session["draft_brief"]["project"]["systems"][0]["notes"] = "external edit"
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "g1",
                "answer_text": "B",
                "status": "verified",
                "verified_draft_fingerprint": fp,
                "gap_snapshot": {
                    "target_paths": ["project.systems[id=aquarium].notes"],
                },
            }
        ]
        parsed = {
            "intent_gaps": [],
            "detail_gaps": [],
            "suggested_defaults": [],
            "decision_checks": [],
        }
        with self.assertRaises(HostChatError) as ctx:
            _build_makeability_review(
                parsed,
                fingerprint=draft_fingerprint(session["draft_brief"]),
                session=session,
            )
        self.assertIn("decision_checks incomplete", str(ctx.exception))
        self.assertEqual(ensure_decision_ledger(session)[0]["status"], "verified")

    def test_critic_empty_checks_helper_still_completes_for_merge_unit(self) -> None:
        """complete_critic_ledger_checks remains available for unit merge tests."""
        draft = _minimal_draft()
        fp = draft_fingerprint(draft)
        session = new_session("critic-empty-helper")
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "g1",
                "answer_text": "B",
                "status": "verified",
                "verified_draft_fingerprint": fp,
                "gap_snapshot": {
                    "target_paths": ["project.systems[id=aquarium].notes"],
                },
            }
        ]
        completed = complete_critic_ledger_checks(session, [])
        merge_critic_decision_checks(session, completed)
        self.assertEqual(ensure_decision_ledger(session)[0]["status"], "repair_failed")
        with self.assertRaises(HostChatError):
            assert_makeability_exportable(session)

    def test_critic_satisfied_refreshes_fingerprint_allows_export(self) -> None:
        draft = copy.deepcopy(SMOKE_BRIEF)
        fp_old = draft_fingerprint(draft)
        draft2 = copy.deepcopy(draft)
        if isinstance(draft2.get("project"), dict):
            systems = draft2["project"].get("systems")
            if isinstance(systems, list) and systems:
                systems[0] = dict(systems[0])
                systems[0]["notes"] = "externally changed"
        fp_new = draft_fingerprint(draft2)
        session = new_session("refresh-vfp")
        session["draft_brief"] = draft2
        session["decision_ledger"] = [
            {
                "decision_key": "system.test.rule",
                "gap_id": "g1",
                "answer_text": "B",
                "status": "verified",
                "verified_draft_fingerprint": fp_old,
                "gap_snapshot": {
                    "target_paths": ["project.session_goal"],
                    "decision_key": "system.test.rule",
                },
            }
        ]
        session["makeability_review"] = {
            "schema_version": 2,
            "draft_fingerprint": fp_new,
            "intent_gaps": [],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        raw_checks = [
            {
                "decision_key": "system.test.rule",
                "status": "satisfied",
                "evidence_paths": ["project.session_goal"],
            }
        ]
        checks = complete_critic_ledger_checks(session, raw_checks)
        merge_critic_decision_checks(session, checks, current_draft_fingerprint=fp_new)
        entry = ensure_decision_ledger(session)[0]
        self.assertEqual(entry["verified_draft_fingerprint"], fp_new)
        self.assertEqual(entry["status"], "verified")
        self.assertFalse(ledger_blocks_export(session, current_draft_fingerprint=fp_new))
        self.assertTrue(_compute_ready_to_export(session))
        assert_makeability_exportable(session)

    def test_critic_satisfied_partial_evidence_stays_repair_failed(self) -> None:
        draft = copy.deepcopy(SMOKE_BRIEF)
        fp_new = draft_fingerprint(draft)
        required = [
            "project.description",
            "project.scenes[id=aquarium_hall].notes",
            "project.systems[id=aquarium].notes",
        ]
        session = new_session("critic-partial")
        session["draft_brief"] = draft
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "g1",
                "answer_text": "B",
                "status": "verified",
                "verified_draft_fingerprint": "fp-old",
                "gap_snapshot": {
                    "write_paths": required,
                    "target_paths": ["project.systems[id=aquarium].notes"],
                    "decision_key": "system.aquarium.unlock_rule",
                },
            }
        ]
        checks = complete_critic_ledger_checks(
            session,
            [
                {
                    "decision_key": "system.aquarium.unlock_rule",
                    "status": "satisfied",
                    "evidence_paths": ["project.systems[id=aquarium].notes"],
                }
            ],
        )
        merge_critic_decision_checks(session, checks, current_draft_fingerprint=fp_new)
        entry = ensure_decision_ledger(session)[0]
        self.assertEqual(entry["status"], "repair_failed")
        self.assertNotEqual(entry.get("verified_draft_fingerprint"), fp_new)
        with self.assertRaises(HostChatError):
            assert_makeability_exportable(session)


class CriticAliasCanonicalTests(unittest.TestCase):
    def test_new_check_key_canonicalized_keeps_verified(self) -> None:
        paths = ["project.systems[id=aquarium].notes"]
        session = new_session("alias-check")
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "old_gap",
                "answer_text": "B",
                "status": "verified",
                "verified_draft_fingerprint": "fp1",
                "gap_snapshot": {
                    "id": "old_gap",
                    "target_paths": paths,
                    "decision_key": "system.aquarium.unlock_rule",
                },
            }
        ]
        raw_gaps = [
            {
                "id": "brand_new_gap",
                "decision_key": "system.aquarium.entry_rule",
                "target_paths": paths,
                "question": "reworded",
            }
        ]
        reconciled = reconcile_intent_gaps_with_ledger(session, raw_gaps)
        alias_map = decision_key_alias_map_from_gaps(reconciled)
        # Explicit other key on same path: no alias merge (M2).
        self.assertEqual(alias_map, {})
        self.assertEqual(reconciled[0]["decision_key"], "system.aquarium.entry_rule")
        raw_checks = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "status": "satisfied",
                "evidence_paths": paths,
            }
        ]
        checks = canonicalize_decision_checks(raw_checks, alias_map)
        checks = complete_critic_ledger_checks(session, checks)
        merge_critic_decision_checks(session, checks, current_draft_fingerprint="fp2")
        self.assertEqual(ensure_decision_ledger(session)[0]["status"], "verified")
        self.assertEqual(
            ensure_decision_ledger(session)[0]["verified_draft_fingerprint"],
            "fp2",
        )

    def test_checks_with_canonical_key_refresh_fingerprint(self) -> None:
        from host_chat import _build_makeability_review

        paths = ["project.session_goal"]
        draft = copy.deepcopy(SMOKE_BRIEF)
        fp_old = draft_fingerprint(draft)
        draft2 = copy.deepcopy(draft)
        fp_new = draft_fingerprint(draft2)
        session = new_session("checks-only-alias")
        session["draft_brief"] = draft2
        session["decision_ledger"] = [
            {
                "decision_key": "system.test.rule",
                "gap_id": "old_gap",
                "answer_text": "B",
                "status": "verified",
                "verified_draft_fingerprint": fp_old,
                "gap_snapshot": {
                    "id": "old_gap",
                    "target_paths": paths,
                    "decision_key": "system.test.rule",
                },
            }
        ]
        session["makeability_review"] = {
            "schema_version": 2,
            "draft_fingerprint": fp_old,
            "intent_gaps": [],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        parsed = {
            "intent_gaps": [],
            "detail_gaps": [],
            "suggested_defaults": [],
            "decision_checks": [
                {
                    "decision_key": "system.test.rule",
                    "status": "satisfied",
                    "evidence_paths": paths,
                }
            ],
        }
        _build_makeability_review(parsed, fingerprint=fp_new, session=session)
        entry = ensure_decision_ledger(session)[0]
        self.assertEqual(entry["status"], "verified")
        self.assertEqual(entry["verified_draft_fingerprint"], fp_new)
        self.assertFalse(ledger_blocks_export(session, current_draft_fingerprint=fp_new))
        self.assertTrue(_compute_ready_to_export(session))
        assert_makeability_exportable(session)

    def test_path_subset_does_not_alias_unrelated_decision_keys(self) -> None:
        single = ["project.systems[id=aquarium].notes"]
        full = [
            "project.description",
            "project.scenes[id=aquarium_hall].notes",
            "project.systems[id=aquarium].notes",
        ]
        session = new_session("multi-alias")
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "old_gap",
                "answer_text": "B",
                "status": "verified",
                "verified_draft_fingerprint": "fp1",
                "gap_snapshot": {
                    "target_paths": single,
                    "write_paths": full,
                    "decision_key": "system.aquarium.unlock_rule",
                },
            }
        ]
        raw_checks = [
            {
                "decision_key": "system.aquarium.entry_rule",
                "status": "satisfied",
                "evidence_paths": full,
            }
        ]
        alias_map = decision_key_alias_map_from_checks(session, raw_checks)
        self.assertEqual(alias_map, {})
        with self.assertRaises(ValueError):
            assert_critic_decision_checks_protocol(session, raw_checks)
        entry = ensure_decision_ledger(session)[0]
        self.assertEqual(entry["status"], "verified")
        self.assertEqual(entry["verified_draft_fingerprint"], "fp1")


class DecisionKeyTests(unittest.TestCase):
    def test_resolve_decision_key_prefers_explicit(self) -> None:
        gap = {"id": "old_id", "decision_key": "system.aquarium.unlock_rule"}
        self.assertEqual(resolve_decision_key(gap), "system.aquarium.unlock_rule")

    def test_resolve_decision_key_falls_back_to_gap_id(self) -> None:
        self.assertEqual(resolve_decision_key({"id": "aquarium_unlock_flow"}), "gap.aquarium_unlock_flow")


class VerifierWholeCardTests(unittest.TestCase):
    def test_incomplete_verifier_report_whole_card_repair_failed(self) -> None:
        session = new_session("whole-card")
        session["decision_ledger"] = [
            {
                "decision_key": "system.a",
                "gap_id": "ga",
                "answer_text": "A",
                "status": "applied",
            },
            {
                "decision_key": "system.b",
                "gap_id": "gb",
                "answer_text": "B",
                "status": "applied",
            },
        ]
        raw_checks = [
            {
                "decision_key": "system.a",
                "gap_id": "ga",
                "status": "satisfied",
                "evidence_paths": [],
            }
        ]
        verified, failed = apply_whole_card_verifier_results(
            session,
            ["system.a", "system.b"],
            raw_checks,
            gap_id_for_key={"system.a": "ga", "system.b": "gb"},
            raw_complete=verifier_reported_all_keys(["system.a", "system.b"], raw_checks),
        )
        self.assertEqual(verified, [])
        self.assertEqual(set(failed), {"ga", "gb"})


class LedgerRecordTests(unittest.TestCase):
    def test_no_api_key_after_record_returns_structured(self) -> None:
        session = new_session("no-api")
        session["draft_brief"] = _minimal_draft()
        session["makeability_review"] = {
            "schema_version": 2,
            "intent_gaps": [
                {
                    "id": "aquarium_unlock_flow",
                    "decision_key": "system.aquarium.unlock_rule",
                    "question": "如何解锁？",
                    "target_paths": ["project.systems[id=aquarium].notes"],
                    "choices": ["A", "B"],
                }
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        answers = [{"gap_id": "aquarium_unlock_flow", "choice": "B 开局可进"}]
        with patch(
            "host_chat.resolve_host_api_settings",
            return_value={"api_key": "", "api_base": "https://x", "model": "m"},
        ):
            result = answer_makeability_gaps(session, answers, config={})
        self.assertFalse(result["ok"])
        ledger = ensure_decision_ledger(session)
        self.assertEqual(ledger[0]["answer_text"], "B 开局可进")
        self.assertEqual(ledger[0]["status"], "repair_failed")

    def test_closer_error_after_record_persists_answer(self) -> None:
        session = new_session("ledger-fail")
        session["draft_brief"] = _minimal_draft()
        session["makeability_review"] = {
            "schema_version": 2,
            "intent_gaps": [
                {
                    "id": "aquarium_unlock_flow",
                    "decision_key": "system.aquarium.unlock_rule",
                    "question": "如何解锁？",
                    "target_paths": ["project.systems[id=aquarium].notes"],
                    "choices": ["A", "B"],
                }
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        answers = [{"gap_id": "aquarium_unlock_flow", "choice": "B 开局可进"}]
        with patch(
            "host_chat.chat_text_completion",
            side_effect=RuntimeError("closer down"),
        ), patch(
            "host_chat.resolve_host_api_settings",
            return_value={"api_key": "k", "api_base": "https://x", "model": "m"},
        ):
            result = answer_makeability_gaps(session, answers, config={})
        self.assertFalse(result["ok"])
        ledger = ensure_decision_ledger(session)
        self.assertIn("B 开局可进", ledger[0]["answer_text"])


class VerifierIndependentTests(unittest.TestCase):
    def test_closer_satisfied_claim_verifier_missing_not_verified(self) -> None:
        session = new_session("verifier-wins")
        draft = _minimal_draft()
        session["draft_brief"] = draft
        session["makeability_review"] = {
            "schema_version": 2,
            "intent_gaps": [
                {
                    "id": "aquarium_unlock_flow",
                    "decision_key": "system.aquarium.unlock_rule",
                    "question": "Q",
                    "target_paths": ["project.systems[id=aquarium].notes"],
                    "choices": ["A", "B"],
                }
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        closer = {
            "assistant_message": "done",
            "brief_patches": [
                {
                    "op": "upsert_system",
                    "match": {"id": "aquarium"},
                    "set": {"notes": "unlocked from start"},
                }
            ],
            "decision_checks": [
                {
                    "decision_key": "system.aquarium.unlock_rule",
                    "status": "satisfied",
                }
            ],
        }
        verifier = {
            "decision_checks": [
                {
                    "decision_key": "system.aquarium.unlock_rule",
                    "gap_id": "aquarium_unlock_flow",
                    "status": "missing",
                    "evidence_paths": [],
                }
            ]
        }
        answers = [{"gap_id": "aquarium_unlock_flow", "choice": "B"}]
        with patch(
            "host_chat.chat_text_completion",
            side_effect=_route_llm(closer=closer, verifier=verifier),
        ), patch(
            "host_chat.resolve_host_api_settings",
            return_value={"api_key": "k", "api_base": "https://x", "model": "m"},
        ):
            result = answer_makeability_gaps(session, answers, config={})
        self.assertFalse(result["ok"])
        self.assertEqual(result.get("verified_ids"), [])
        self.assertIn("aquarium_unlock_flow", result.get("repair_failed_ids") or [])

    def test_verifier_missing_one_key_whole_card_repair_failed(self) -> None:
        session = new_session("partial")
        draft = _minimal_draft()
        session["draft_brief"] = draft
        session["makeability_review"] = {
            "schema_version": 2,
            "intent_gaps": [
                {
                    "id": "aquarium_unlock_flow",
                    "decision_key": "system.aquarium.unlock_rule",
                    "question": "水族馆？",
                    "target_paths": ["project.systems[id=aquarium].notes"],
                    "choices": ["A", "B"],
                },
                {
                    "id": "market_access",
                    "decision_key": "system.market.access_rule",
                    "question": "市场？",
                    "target_paths": ["project.systems[id=market].notes"],
                    "choices": ["A", "B"],
                },
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        closer = {
            "assistant_message": "写了",
            "brief_patches": [
                {
                    "op": "upsert_system",
                    "match": {"id": "aquarium"},
                    "set": {"notes": "unlocked from start"},
                },
                {
                    "op": "upsert_system",
                    "match": {"id": "market"},
                    "set": {"notes": "open"},
                },
            ],
        }
        verifier = {
            "decision_checks": [
                {
                    "decision_key": "system.aquarium.unlock_rule",
                    "gap_id": "aquarium_unlock_flow",
                    "status": "satisfied",
                    "evidence_paths": [],
                }
            ]
        }
        answers = [
            {"gap_id": "aquarium_unlock_flow", "choice": "B"},
            {"gap_id": "market_access", "choice": "B"},
        ]
        with patch(
            "host_chat.chat_text_completion",
            side_effect=_route_llm(closer=closer, verifier=verifier),
        ), patch(
            "host_chat.resolve_host_api_settings",
            return_value={"api_key": "k", "api_base": "https://x", "model": "m"},
        ):
            result = answer_makeability_gaps(session, answers, config={})
        self.assertTrue(result.get("repair_failed"))
        self.assertEqual(result.get("verified_ids"), [])
        self.assertEqual(len(result.get("repair_failed_ids") or []), 2)


class ExportLedgerGateTests(unittest.TestCase):
    def test_pending_applied_repair_failed_block_export_verified_allows(self) -> None:
        draft = copy.deepcopy(SMOKE_BRIEF)
        review = _detail_only_review(draft)
        fp = draft_fingerprint(draft)
        for status, should_block in (
            ("pending", True),
            ("applied", True),
            ("repair_failed", True),
            ("verified", False),
        ):
            session = _ready_session(review=review)
            session["decision_ledger"] = [
                {
                    "decision_key": "system.test.rule",
                    "gap_id": "g1",
                    "answer_text": "choice",
                    "status": status,
                    "evidence_paths": [],
                    "updated_at": "t",
                    **(
                        {"verified_draft_fingerprint": fp}
                        if status == "verified"
                        else {}
                    ),
                }
            ]
            if should_block:
                with self.assertRaises(HostChatError):
                    assert_makeability_exportable(session)
            else:
                assert_makeability_exportable(session)

    def test_verified_without_fingerprint_blocks_export(self) -> None:
        draft = copy.deepcopy(SMOKE_BRIEF)
        session = _ready_session(review=_detail_only_review(draft))
        session["decision_ledger"] = [
            {
                "decision_key": "k",
                "answer_text": "x",
                "status": "verified",
            }
        ]
        self.assertTrue(ledger_blocks_export(session, current_draft_fingerprint=draft_fingerprint(draft)))
        with self.assertRaises(HostChatError):
            assert_makeability_exportable(session)

    def test_unknown_ledger_status_blocks_export(self) -> None:
        session = new_session("unknown-status")
        session["decision_ledger"] = [
            {"decision_key": "k", "answer_text": "x", "status": ""},
        ]
        self.assertTrue(ledger_blocks_export(session))
        session["decision_ledger"][0]["status"] = "bogus"
        self.assertTrue(ledger_blocks_export(session))

    def test_helper_without_current_fp_ignores_fingerprint_match(self) -> None:
        session = new_session("helper-fp")
        session["decision_ledger"] = [
            {
                "decision_key": "k",
                "answer_text": "x",
                "status": "verified",
                "verified_draft_fingerprint": "old-fp",
            }
        ]
        self.assertFalse(ledger_blocks_export(session))

    def test_ledger_blocks_export_helper(self) -> None:
        session = new_session("blk")
        session["decision_ledger"] = [
            {"decision_key": "k", "answer_text": "x", "status": "pending"}
        ]
        self.assertTrue(ledger_blocks_export(session))


class RetrySuppressTests(unittest.TestCase):
    def test_retry_after_review_suppresses_gap_uses_ledger(self) -> None:
        session = new_session("retry")
        draft = _minimal_draft()
        session["draft_brief"] = draft
        session["makeability_review"] = {
            "schema_version": 2,
            "intent_gaps": [],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "aquarium_unlock_flow",
                "gap_snapshot": {
                    "id": "aquarium_unlock_flow",
                    "decision_key": "system.aquarium.unlock_rule",
                    "target_paths": ["project.systems[id=aquarium].notes"],
                    "question": "Q",
                },
                "answer_text": "B 开局可进",
                "status": "repair_failed",
                "updated_at": "t",
            }
        ]
        closer = {
            "assistant_message": "ok",
            "brief_patches": [
                {
                    "op": "upsert_system",
                    "match": {"id": "aquarium"},
                    "set": {"notes": "unlocked from start"},
                }
            ],
        }
        verifier = {
            "decision_checks": [
                {
                    "decision_key": "system.aquarium.unlock_rule",
                    "gap_id": "aquarium_unlock_flow",
                    "status": "satisfied",
                    "evidence_paths": ["project.systems[id=aquarium].notes"],
                }
            ]
        }
        answers = [{"gap_id": "aquarium_unlock_flow", "choice": "B 开局可进"}]
        with patch(
            "host_chat.chat_text_completion",
            side_effect=_route_llm(closer=closer, verifier=verifier),
        ), patch(
            "host_chat.resolve_host_api_settings",
            return_value={"api_key": "k", "api_base": "https://x", "model": "m"},
        ):
            result = answer_makeability_gaps(session, answers, config={})
        self.assertTrue(result["ok"])
        self.assertEqual(ensure_decision_ledger(session)[0]["status"], "verified")
        self.assertEqual(ensure_decision_ledger(session)[0]["answer_text"], "B 开局可进")

    def test_retry_empty_choice_preserves_answer_text(self) -> None:
        session = new_session("preserve-ans")
        gaps = {
            "g1": {
                "id": "g1",
                "decision_key": "system.x",
                "target_paths": [],
            }
        }
        session["decision_ledger"] = [
            {
                "decision_key": "system.x",
                "gap_id": "g1",
                "answer_text": "saved",
                "status": "repair_failed",
            }
        ]
        record_gap_answers(session, [{"gap_id": "g1"}], gaps)
        self.assertEqual(ensure_decision_ledger(session)[0]["answer_text"], "saved")


class SuppressRepeatTests(unittest.TestCase):
    def test_same_decision_key_new_gap_id_suppressed(self) -> None:
        session = new_session("suppress")
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "old_wording",
                "answer_text": "B 开局可进",
                "status": "verified",
                "evidence_paths": ["project.systems[id=aquarium].notes"],
                "updated_at": "2026-08-05T00:00:00+00:00",
            }
        ]
        gaps = [
            {
                "id": "aquarium_unlock_reworded",
                "decision_key": "system.aquarium.unlock_rule",
                "question": "水族馆还要解锁吗？",
            }
        ]
        filtered = suppress_intent_gaps_by_ledger(session, gaps)
        self.assertEqual(filtered, [])

    def test_verified_then_review_does_not_reask(self) -> None:
        session = new_session("no-reask")
        draft = _minimal_draft()
        session["draft_brief"] = draft
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "aquarium_unlock_flow",
                "answer_text": "B",
                "status": "verified",
                "evidence_paths": [],
                "updated_at": "2026-08-05T00:00:00+00:00",
            }
        ]
        critic_payload = {
            "intent_gaps": [
                _v2_aquarium_intent(
                    id="new_id_same_semantics",
                    question="还要解锁？",
                    why_blocking="x",
                )
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
            "decision_checks": [
                {"decision_key": "system.aquarium.unlock_rule", "status": "satisfied"}
            ],
        }
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(critic_payload, ensure_ascii=False),
        ):
            result = run_makeability_review(
                session,
                config={"host": {"api_key": "k", "api_base": "https://x", "model": "m"}},
            )
        self.assertEqual(result["intent_count"], 0)
        self.assertEqual(session["makeability_review"]["intent_gaps"], [])

    def test_two_critic_runs_same_decision_key_no_reask(self) -> None:
        session = new_session("double-critic")
        session["draft_brief"] = _minimal_draft()
        payload = {
            "intent_gaps": [_v2_aquarium_intent(id="id1", question="Q1")],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(payload, ensure_ascii=False),
        ):
            run_makeability_review(
                session,
                config={"host": {"api_key": "k", "api_base": "https://x", "model": "m"}},
            )
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "id1",
                "answer_text": "B",
                "status": "verified",
                "updated_at": "t",
            }
        ]
        payload2 = {
            "intent_gaps": [_v2_aquarium_intent(id="id2", question="Q2")],
            "detail_gaps": [],
            "suggested_defaults": [],
            "decision_checks": [
                {
                    "decision_key": "system.aquarium.unlock_rule",
                    "status": "satisfied",
                    "evidence_paths": ["project.systems[id=aquarium].notes"],
                }
            ],
        }
        with patch(
            "host_chat.chat_text_completion",
            return_value=json.dumps(payload2, ensure_ascii=False),
        ):
            result = run_makeability_review(
                session,
                config={"host": {"api_key": "k", "api_base": "https://x", "model": "m"}},
            )
        self.assertEqual(result["intent_count"], 0)


class PayloadLedgerPriorityTests(unittest.TestCase):
    def test_build_user_payload_ledger_over_summary(self) -> None:
        session = new_session("ledger-priority")
        session["summary"] = "用户说水族馆需要付费解锁"
        session["draft_brief"] = _minimal_draft()
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "answer_text": "开局可进，无付费解锁",
                "status": "verified",
                "updated_at": "2026-08-05T00:00:00+00:00",
            }
        ]
        payload = _build_user_payload(session, "chat")
        self.assertIn("decision_ledger", payload)
        note = str(payload.get("summary_note") or "") + str(payload.get("decision_ledger_note") or "")
        self.assertIn("ledger", note.lower())
        self.assertIn("优先", note)


class ChatPatchLedgerTests(unittest.TestCase):
    def test_apply_parsed_patches_downgrade_verified_ledger(self) -> None:
        session = new_session("chat-patch")
        session["draft_brief"] = _minimal_draft()
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "g",
                "answer_text": "B",
                "status": "verified",
                "evidence_paths": ["project.systems[id=aquarium].notes"],
            }
        ]
        parsed = {
            "assistant_message": "patch",
            "artifact": {
                "brief_patches": [
                    {
                        "op": "upsert_system",
                        "match": {"id": "aquarium"},
                        "set": {"notes": "changed again"},
                    }
                ]
            },
        }
        _apply_parsed(session, parsed, "chat")
        self.assertEqual(ensure_decision_ledger(session)[0]["status"], "repair_failed")
        self.assertFalse(session.get("ready_to_export"))


class FilterDisplayTests(unittest.TestCase):
    def test_filter_intent_for_gui_excludes_repair_failed(self) -> None:
        session = new_session("gui-filter")
        session["decision_ledger"] = [
            {
                "decision_key": "system.market.access_rule",
                "gap_id": "market_access",
                "status": "repair_failed",
                "answer_text": "B",
                "updated_at": "t",
            }
        ]
        gaps = [{"id": "market_access", "decision_key": "system.market.access_rule", "question": "Q"}]
        shown = filter_intent_gaps_for_display(session, gaps)
        self.assertEqual(shown, [])


class OccurrencesWritePathsTests(unittest.TestCase):
    def test_normalization_stores_occurrences_write_paths_in_gap_snapshot(self) -> None:
        session = new_session("snap-v2")
        gap = sanitize_intent_gap(_multi_path_gap())
        record_gap_answers(
            session,
            [{"gap_id": "aquarium_unlock_flow", "choice": "开局可进"}],
            {"aquarium_unlock_flow": gap},
        )
        snap = ensure_decision_ledger(session)[0]["gap_snapshot"]
        self.assertEqual(len(snap.get("occurrences") or []), 3)
        self.assertEqual(
            snap.get("write_paths"),
            [
                "project.description",
                "project.scenes[id=aquarium_hall].notes",
                "project.systems[id=aquarium].notes",
            ],
        )
        self.assertEqual(snap.get("target_paths"), ["project.systems[id=aquarium].notes"])

    def test_satisfied_partial_evidence_repair_failed(self) -> None:
        required = [
            "project.description",
            "project.scenes[id=aquarium_hall].notes",
            "project.systems[id=aquarium].notes",
        ]
        check = {
            "decision_key": "system.aquarium.unlock_rule",
            "status": "satisfied",
            "evidence_paths": ["project.systems[id=aquarium].notes"],
        }
        self.assertEqual(
            effective_decision_check_status(check, required),
            "missing",
        )
        session = new_session("partial-ev")
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "g",
                "answer_text": "x",
                "status": "applied",
            }
        ]
        verified, failed = apply_whole_card_verifier_results(
            session,
            ["system.aquarium.unlock_rule"],
            [check],
            gap_id_for_key={"system.aquarium.unlock_rule": "g"},
            raw_complete=True,
            required_paths_by_key={"system.aquarium.unlock_rule": required},
        )
        self.assertEqual(verified, [])
        self.assertEqual(failed, ["g"])
        self.assertEqual(ensure_decision_ledger(session)[0]["status"], "repair_failed")

    def test_unresolved_paths_forces_repair_failed(self) -> None:
        session = new_session("unresolved")
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "g",
                "answer_text": "x",
                "status": "applied",
            }
        ]
        check = {
            "decision_key": "system.aquarium.unlock_rule",
            "status": "satisfied",
            "evidence_paths": ["project.systems[id=aquarium].notes"],
            "unresolved_paths": ["project.description"],
        }
        verified, failed = apply_whole_card_verifier_results(
            session,
            ["system.aquarium.unlock_rule"],
            [check],
            gap_id_for_key={"system.aquarium.unlock_rule": "g"},
            raw_complete=True,
            required_paths_by_key={
                "system.aquarium.unlock_rule": ["project.systems[id=aquarium].notes"]
            },
        )
        self.assertEqual(verified, [])
        self.assertEqual(failed, ["g"])

    def test_backward_compat_target_paths_only_still_verifies(self) -> None:
        session = new_session("legacy-tp")
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "g",
                "answer_text": "x",
                "status": "applied",
            }
        ]
        paths = ["project.systems[id=aquarium].notes"]
        check = {
            "decision_key": "system.aquarium.unlock_rule",
            "status": "satisfied",
            "evidence_paths": paths,
        }
        verified, failed = apply_whole_card_verifier_results(
            session,
            ["system.aquarium.unlock_rule"],
            [check],
            gap_id_for_key={"system.aquarium.unlock_rule": "g"},
            raw_complete=True,
            required_paths_by_key={"system.aquarium.unlock_rule": paths},
        )
        self.assertEqual(failed, [])
        self.assertEqual(verified, ["g"])
        self.assertEqual(ensure_decision_ledger(session)[0]["status"], "verified")

    def test_required_write_paths_fallback_target_paths(self) -> None:
        gap = {"target_paths": ["project.systems[id=aquarium].notes"]}
        self.assertEqual(
            required_write_paths_from_gap(gap),
            ["project.systems[id=aquarium].notes"],
        )


class MultiPathCloserVerifierTests(unittest.TestCase):
    def test_repair_closer_patches_all_write_paths_then_verified(self) -> None:
        session = new_session("multi-repair")
        draft = _minimal_draft()
        draft["project"]["description"] = "Buy aquarium building to unlock hall."
        draft["project"]["scenes"] = [
            {"id": "aquarium_hall", "notes": "Locked until purchase."},
        ]
        session["draft_brief"] = draft
        gap = _multi_path_gap()
        session["makeability_review"] = {
            "schema_version": 2,
            "intent_gaps": [gap],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        closer_first = {
            "assistant_message": "system only",
            "brief_patches": [
                {
                    "op": "upsert_system",
                    "match": {"id": "aquarium"},
                    "set": {"notes": "Enter from start; no purchase lock."},
                }
            ],
        }
        closer_repair = {
            "assistant_message": "all paths",
            "brief_patches": [
                {
                    "op": "set",
                    "path": "project.description",
                    "value": "Aquarium hall open from start.",
                },
                {
                    "op": "upsert_scene",
                    "match": {"id": "aquarium_hall"},
                    "set": {"notes": "Open from start."},
                },
                {
                    "op": "upsert_system",
                    "match": {"id": "aquarium"},
                    "set": {"notes": "Enter from start; no purchase lock."},
                },
            ],
        }
        verifier_first = {
            "decision_checks": [
                {
                    "decision_key": "system.aquarium.unlock_rule",
                    "gap_id": "aquarium_unlock_flow",
                    "status": "satisfied",
                    "evidence_paths": ["project.systems[id=aquarium].notes"],
                }
            ]
        }
        verifier_second = {
            "decision_checks": [
                {
                    "decision_key": "system.aquarium.unlock_rule",
                    "gap_id": "aquarium_unlock_flow",
                    "status": "satisfied",
                    "evidence_paths": [
                        "project.description",
                        "project.scenes[id=aquarium_hall].notes",
                        "project.systems[id=aquarium].notes",
                    ],
                }
            ]
        }
        answers = [{"gap_id": "aquarium_unlock_flow", "choice": "开局可进"}]

        def route(**kwargs):
            messages = kwargs["messages"]
            system = messages[0]["content"]
            if "Makeability Verifier" in system:
                user = json.loads(messages[1]["content"])
                pending = user.get("pending_decisions") or []
                if any(
                    "project.description" in (p.get("write_paths") or [])
                    for p in pending
                    if isinstance(p, dict)
                ):
                    draft_brief = user.get("candidate_draft_brief") or {}
                    desc = str((draft_brief.get("project") or {}).get("description") or "")
                    if "open from start" in desc.lower():
                        return json.dumps(verifier_second, ensure_ascii=False)
                return json.dumps(verifier_first, ensure_ascii=False)
            user = json.loads(messages[1]["content"])
            note = str(user.get("instruction") or "")
            if "Repair pass" in note:
                return json.dumps(closer_repair, ensure_ascii=False)
            return json.dumps(closer_first, ensure_ascii=False)

        with patch("host_chat.chat_text_completion", side_effect=route), patch(
            "host_chat.resolve_host_api_settings",
            return_value={"api_key": "k", "api_base": "https://x", "model": "m"},
        ):
            result = answer_makeability_gaps(session, answers, config={})
        self.assertTrue(result["ok"])
        self.assertEqual(ensure_decision_ledger(session)[0]["status"], "verified")

    def test_fishing_like_conflict_all_write_paths_in_verifier_spec(self) -> None:
        session = new_session("fishing-spec")
        gap = sanitize_intent_gap(_multi_path_gap())
        gaps_by_id = {"aquarium_unlock_flow": gap}
        record_gap_answers(
            session,
            [{"gap_id": "aquarium_unlock_flow", "choice": "开局可进"}],
            gaps_by_id,
        )
        specs = decisions_for_verifier(
            session,
            gaps_by_id,
            [{"gap_id": "aquarium_unlock_flow", "choice": "开局可进"}],
        )
        self.assertEqual(len(specs), 1)
        wp = specs[0].get("write_paths") or []
        self.assertIn("project.description", wp)
        self.assertIn("project.scenes[id=aquarium_hall].notes", wp)
        self.assertIn("project.systems[id=aquarium].notes", wp)


class VerifierPathDetailTests(unittest.TestCase):
    def test_missing_verifier_row_lists_all_required_paths(self) -> None:
        required = {
            "system.a": [
                "project.description",
                "project.systems[id=aquarium].notes",
            ]
        }
        lines = verifier_path_failure_detail(
            [],
            required,
            expected_keys=["system.a", "system.b"],
        )
        joined = " ".join(lines)
        self.assertIn("system.a", joined)
        self.assertIn("project.description", joined)
        self.assertIn("system.b", joined)


class CliMakeabilitySyncTests(unittest.TestCase):
    def test_cli_makeability_syncs_bound_disk_draft_before_review(self) -> None:
        from gamefactory import cli as gf_cli
        from host_chat import attach_bound_project, draft_fingerprint, persist_project_draft
        from host_chat import sync_session_draft_from_disk

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "demo"
            proj.mkdir(parents=True)
            session = new_session("cli-sync-review")
            session["bound_brief_rel"] = "projects/demo/brief.json"
            session["draft_brief"] = {
                "project": {"title": "Stale Session Title"},
                "assets": [],
            }
            attach_bound_project(session, "projects/demo/brief.json", repo_root=root)
            persist_project_draft(session, repo_root=root)
            draft_path = proj / "brief.draft.json"
            disk_draft = {
                "project": {"title": "Fresh Disk Title"},
                "assets": [{"name": "rod", "type": "prop", "usage": "x"}],
            }
            draft_path.write_text(json.dumps(disk_draft, ensure_ascii=False), encoding="utf-8")
            sess_path = root / "sess.json"
            # Persist session JSON without CAS write — disk already diverged intentionally.
            session["updated_at"] = "2026-08-05T00:00:00+00:00"
            sess_path.write_text(
                json.dumps(session, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            seen: list[str] = []

            def fake_review(sess: dict, config: dict | None = None) -> dict:
                seen.append(draft_fingerprint(sess.get("draft_brief")))
                sess["makeability_review"] = {
                    "schema_version": 2,
                    "draft_fingerprint": draft_fingerprint(sess["draft_brief"]),
                    "intent_gaps": [],
                    "detail_gaps": [],
                    "suggested_defaults": [],
                }
                return {
                    "ok": True,
                    "intent_count": 0,
                    "detail_count": 0,
                    "ready_to_export": True,
                    "assistant_message": "ok",
                }

            runner = CliRunner()
            with patch(
                "brief_cmds.host_sync_session_draft_from_disk",
                side_effect=lambda s: sync_session_draft_from_disk(
                    s, repo_root=root, workspace=root
                ),
            ), patch("brief_cmds.host_run_makeability_review", side_effect=fake_review):
                result = runner.invoke(
                    gf_cli,
                    [
                        "brief",
                        "chat",
                        "makeability",
                        "--session",
                        str(sess_path),
                        "--json",
                    ],
                    obj={"config": {}},
                )
            self.assertEqual(result.exit_code, 0, msg=result.output)
            self.assertEqual(seen, [draft_fingerprint(disk_draft)])

    def test_cli_makeability_dual_edit_errors_without_overwriting_session(self) -> None:
        from gamefactory import cli as gf_cli
        from host_chat import attach_bound_project, draft_fingerprint, persist_project_draft
        from host_chat import sync_session_draft_from_disk

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "demo"
            proj.mkdir(parents=True)
            session = new_session("cli-dual-edit")
            session["bound_brief_rel"] = "projects/demo/brief.json"
            session["draft_brief"] = {"project": {"title": "Base"}, "assets": []}
            attach_bound_project(session, "projects/demo/brief.json", repo_root=root)
            persist_project_draft(session, repo_root=root)
            session["draft_brief"] = {"project": {"title": "Session Only Edit"}, "assets": []}
            session_title = session["draft_brief"]["project"]["title"]
            (proj / "brief.draft.json").write_text(
                json.dumps(
                    {"project": {"title": "Disk Only Edit"}, "assets": []},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            sess_path = root / "sess.json"
            from host_chat import _utc_now

            session["updated_at"] = _utc_now()
            sess_path.write_text(
                json.dumps(session, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            review_calls: list[int] = []

            def fake_review(sess: dict, config: dict | None = None) -> dict:
                review_calls.append(1)
                return {"ok": True, "intent_count": 0, "detail_count": 0}

            runner = CliRunner()
            with patch(
                "brief_cmds.host_sync_session_draft_from_disk",
                side_effect=lambda s: sync_session_draft_from_disk(
                    s, repo_root=root, workspace=root
                ),
            ), patch("brief_cmds.host_run_makeability_review", side_effect=fake_review):
                result = runner.invoke(
                    gf_cli,
                    [
                        "brief",
                        "chat",
                        "makeability",
                        "--session",
                        str(sess_path),
                        "--json",
                    ],
                    obj={"config": {}},
                )
            self.assertEqual(result.exit_code, 1, msg=result.output)
            self.assertEqual(review_calls, [])
            loaded = json.loads(sess_path.read_text(encoding="utf-8"))
            self.assertEqual(
                loaded["draft_brief"]["project"]["title"],
                session_title,
            )


class MakeabilityAnswerCliTests(unittest.TestCase):
    def test_cli_saves_session_on_no_api_after_record(self) -> None:
        from gamefactory import cli as gf_cli

        session = new_session("cli-no-api")
        session["draft_brief"] = _minimal_draft()
        session["makeability_review"] = {
            "schema_version": 2,
            "intent_gaps": [
                {
                    "id": "aquarium_unlock_flow",
                    "decision_key": "system.aquarium.unlock_rule",
                    "question": "Q",
                    "choices": ["A", "B"],
                }
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sess.json"
            save_session(path, session)
            answers = json.dumps([{"gap_id": "aquarium_unlock_flow", "choice": "B"}])
            runner = CliRunner()
            with patch(
                "host_chat.resolve_host_api_settings",
                return_value={"api_key": "", "api_base": "https://x", "model": "m"},
            ):
                result = runner.invoke(
                    gf_cli,
                    [
                        "brief",
                        "chat",
                        "makeability-answer",
                        "--session",
                        str(path),
                        "--answers",
                        answers,
                        "--json",
                    ],
                    obj={"config": {}},
                )
            self.assertEqual(result.exit_code, 2)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            ledger = loaded.get("decision_ledger") or []
            self.assertTrue(ledger)
            self.assertIn("B", ledger[0].get("answer_text", ""))


class ReviewFindingFixesTests(unittest.TestCase):
    def test_save_session_survives_draft_cas_conflict(self) -> None:
        """H1: decision answers must land in session JSON even when draft CAS fails."""
        from host_chat import persist_project_draft, save_session

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "p"
            proj.mkdir(parents=True)
            conv = root / "conv"
            conv.mkdir()
            session = new_session("cas-answer")
            session["bound_brief_rel"] = "projects/p/brief.json"
            session["draft_brief"] = {"project": {"title": "Base"}, "assets": []}
            persist_project_draft(session, repo_root=root)
            # External disk edit while session still at tracked content.
            (proj / "brief.draft.json").write_text(
                json.dumps({"project": {"title": "Disk"}, "assets": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            session["decision_ledger"] = [
                {
                    "decision_key": "system.a",
                    "gap_id": "g1",
                    "answer_text": "B saved before LLM",
                    "status": "pending",
                }
            ]
            sess_path = conv / "sess.json"
            # Patch repo root resolution used by save_session → persist_project_draft
            with patch("host_chat._repo_root", return_value=root):
                save_session(sess_path, session)
            loaded = json.loads(sess_path.read_text(encoding="utf-8"))
            self.assertEqual(
                loaded["decision_ledger"][0]["answer_text"],
                "B saved before LLM",
            )
            self.assertTrue(str(loaded.get("last_draft_persist_error") or ""))
            disk = json.loads((proj / "brief.draft.json").read_text(encoding="utf-8"))
            self.assertEqual(disk["project"]["title"], "Disk")

    def test_persist_after_record_keeps_answers_when_cas_blocks_draft(self) -> None:
        from host_chat import persist_project_draft, save_session

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proj = root / "projects" / "p"
            proj.mkdir(parents=True)
            conv = root / "conv"
            conv.mkdir()
            session = new_session("cas-persist-after")
            session["bound_brief_rel"] = "projects/p/brief.json"
            session["draft_brief"] = _minimal_draft()
            persist_project_draft(session, repo_root=root)
            (proj / "brief.draft.json").write_text(
                json.dumps(
                    {"project": {"title": "External"}, "assets": []},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            session["makeability_review"] = {
                "schema_version": 2,
                "intent_gaps": [
                    {
                        "id": "aquarium_unlock_flow",
                        "decision_key": "system.aquarium.unlock_rule",
                        "question": "Q",
                        "choices": ["A", "B"],
                        "target_paths": ["project.systems[id=aquarium].notes"],
                    }
                ],
                "detail_gaps": [],
                "suggested_defaults": [],
            }
            sess_path = conv / "sess.json"
            saved: list[str] = []

            def persist_after_record(sess: dict) -> None:
                with patch("host_chat._repo_root", return_value=root):
                    save_session(sess_path, sess)
                saved.append("ok")

            closer = {
                "assistant_message": "done",
                "brief_patches": [
                    {
                        "op": "upsert_system",
                        "match": {"id": "aquarium"},
                        "set": {"notes": "unlocked"},
                    }
                ],
            }
            verifier = {
                "decision_checks": [
                    {
                        "decision_key": "system.aquarium.unlock_rule",
                        "gap_id": "aquarium_unlock_flow",
                        "status": "satisfied",
                        "evidence_paths": ["project.systems[id=aquarium].notes"],
                    }
                ]
            }
            with patch(
                "host_chat.chat_text_completion",
                side_effect=_route_llm(closer=closer, verifier=verifier),
            ), patch(
                "host_chat.resolve_host_api_settings",
                return_value={"api_key": "k", "api_base": "https://x", "model": "m"},
            ), patch("host_chat._repo_root", return_value=root):
                # First persist_after_record runs mid-flow; draft CAS soft-fails.
                result = answer_makeability_gaps(
                    session,
                    [{"gap_id": "aquarium_unlock_flow", "choice": "B"}],
                    config={},
                    persist_after_record=persist_after_record,
                )
            self.assertEqual(saved, ["ok"])
            mid = json.loads(sess_path.read_text(encoding="utf-8"))
            self.assertIn("B", mid["decision_ledger"][0]["answer_text"])
            # Whole-card may repair_failed if draft wasn't updated due to CAS —
            # answers must still be durable either way.
            self.assertTrue(mid["decision_ledger"][0].get("answer_text"))
            self.assertIsNotNone(result)

    def test_illegal_occurrence_relation_rejected(self) -> None:
        from host_chat import _build_makeability_review

        with self.assertRaises(ValueError):
            validate_occurrences_strict(
                [{"path": "project.session_goal", "relation": "related"}],
                field="occurrences",
            )
        session = new_session("bad-occ")
        session["draft_brief"] = _minimal_draft()
        parsed = {
            "intent_gaps": [
                {
                    "id": "g1",
                    "decision_key": "session.goal",
                    "write_paths": ["project.session_goal"],
                    "occurrences": [
                        {"path": "project.session_goal", "relation": "canonical"},
                        {"path": "project.description", "relation": "kinda-dup"},
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
                fingerprint=draft_fingerprint(session["draft_brief"]),
                session=session,
            )
        self.assertIn("invalid relation", str(ctx.exception))

    def test_verifier_protocol_error_skips_closer_repair_rounds(self) -> None:
        session = new_session("proto-skip")
        draft = _minimal_draft()
        session["draft_brief"] = draft
        session["makeability_review"] = {
            "schema_version": 2,
            "intent_gaps": [
                {
                    "id": "aquarium_unlock_flow",
                    "decision_key": "system.aquarium.unlock_rule",
                    "question": "水族馆？",
                    "target_paths": ["project.systems[id=aquarium].notes"],
                    "choices": ["A", "B"],
                },
                {
                    "id": "market_access",
                    "decision_key": "system.market.access_rule",
                    "question": "市场？",
                    "target_paths": ["project.systems[id=market].notes"],
                    "choices": ["A", "B"],
                },
            ],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        closer = {
            "assistant_message": "写了",
            "brief_patches": [
                {
                    "op": "upsert_system",
                    "match": {"id": "aquarium"},
                    "set": {"notes": "unlocked from start"},
                },
                {
                    "op": "upsert_system",
                    "match": {"id": "market"},
                    "set": {"notes": "open"},
                },
            ],
        }
        verifier = {
            "decision_checks": [
                {
                    "decision_key": "system.aquarium.unlock_rule",
                    "gap_id": "aquarium_unlock_flow",
                    "status": "satisfied",
                    "evidence_paths": ["project.systems[id=aquarium].notes"],
                }
            ]
        }
        answers = [
            {"gap_id": "aquarium_unlock_flow", "choice": "B"},
            {"gap_id": "market_access", "choice": "B"},
        ]
        calls = {"closer": 0, "verifier": 0}

        def counting_route(**kwargs):
            messages = kwargs["messages"]
            system = messages[0]["content"]
            if "Makeability Verifier" in system:
                calls["verifier"] += 1
                return json.dumps(verifier, ensure_ascii=False)
            calls["closer"] += 1
            return json.dumps(closer, ensure_ascii=False)

        with patch(
            "host_chat.chat_text_completion",
            side_effect=counting_route,
        ), patch(
            "host_chat.resolve_host_api_settings",
            return_value={"api_key": "k", "api_base": "https://x", "model": "m"},
        ):
            result = answer_makeability_gaps(session, answers, config={})
        self.assertTrue(result.get("repair_failed"))
        self.assertEqual(calls["closer"], 1)
        self.assertEqual(calls["verifier"], 1)

    def test_legacy_ledger_without_snapshot_still_resolves_gap(self) -> None:
        session = new_session("legacy-snap")
        session["makeability_review"] = {
            "schema_version": 2,
            "intent_gaps": [],
            "detail_gaps": [],
            "suggested_defaults": [],
        }
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "aquarium_unlock_flow",
                "answer_text": "B 开局可进",
                "status": "repair_failed",
                "evidence_paths": ["project.systems[id=aquarium].notes"],
            }
        ]
        gaps = resolve_gaps_for_answers(
            session,
            [{"gap_id": "aquarium_unlock_flow", "choice": "B 开局可进"}],
        )
        self.assertIn("aquarium_unlock_flow", gaps)
        self.assertEqual(
            gaps["aquarium_unlock_flow"]["decision_key"],
            "system.aquarium.unlock_rule",
        )
        self.assertTrue(gaps["aquarium_unlock_flow"].get("write_paths"))

    def test_critic_conflict_exposes_repair_gaps_and_answers(self) -> None:
        from host_chat import _build_makeability_review
        from makeability_decisions import repair_answers_from_ledger, repair_failed_gaps_for_display

        draft = _minimal_draft()
        fp = draft_fingerprint(draft)
        session = new_session("repair-gaps")
        session["draft_brief"] = draft
        session["decision_ledger"] = [
            {
                "decision_key": "system.aquarium.unlock_rule",
                "gap_id": "aquarium_unlock_flow",
                "answer_text": "B 开局可进",
                "status": "verified",
                "verified_draft_fingerprint": fp,
                "gap_snapshot": {
                    "id": "aquarium_unlock_flow",
                    "decision_key": "system.aquarium.unlock_rule",
                    "question": "水族馆？",
                    "target_paths": ["project.systems[id=aquarium].notes"],
                    "choices": ["A", "B"],
                },
            }
        ]
        parsed = {
            "intent_gaps": [],
            "detail_gaps": [],
            "suggested_defaults": [],
            "decision_checks": [
                {
                    "decision_key": "system.aquarium.unlock_rule",
                    "status": "conflict",
                    "evidence_paths": ["project.systems[id=aquarium].notes"],
                }
            ],
        }
        review = _build_makeability_review(parsed, fingerprint=fp, session=session)
        self.assertEqual(ensure_decision_ledger(session)[0]["status"], "repair_failed")
        self.assertEqual(len(review.get("repair_gaps") or []), 1)
        self.assertEqual(review["repair_gaps"][0]["id"], "aquarium_unlock_flow")
        self.assertEqual(len(review.get("repair_answers") or []), 1)
        self.assertEqual(
            repair_failed_gaps_for_display(session)[0]["id"],
            "aquarium_unlock_flow",
        )
        self.assertEqual(
            repair_answers_from_ledger(session)[0]["choice"],
            "B 开局可进",
        )


if __name__ == "__main__":
    unittest.main()
