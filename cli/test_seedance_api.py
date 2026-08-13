"""Seedance task payload helpers."""

from __future__ import annotations

import unittest

from seedance_api import build_task_payload, resolve_model


class SeedancePayloadTests(unittest.TestCase):
    def test_mini_t2v_keeps_ratio(self) -> None:
        payload = build_task_payload(model="mini", prompt="swim", ratio="1:1")
        self.assertEqual(payload["model"], "doubao-seedance-2-0-mini-260615")
        self.assertEqual(payload["ratio"], "1:1")

    def test_25_i2v_omits_ratio(self) -> None:
        payload = build_task_payload(
            model="2.5",
            prompt="swim",
            ratio="1:1",
            reference_image_item={"type": "image_url", "image_url": {"url": "x"}},
        )
        self.assertEqual(payload["model"], "doubao-seedance-2-5-260628")
        self.assertNotIn("ratio", payload)

    def test_adaptive_ratio_omitted(self) -> None:
        payload = build_task_payload(model="mini", prompt="swim", ratio="adaptive")
        self.assertNotIn("ratio", payload)

    def test_resolve_25_alias(self) -> None:
        self.assertEqual(resolve_model("2.5"), "doubao-seedance-2-5-260628")
