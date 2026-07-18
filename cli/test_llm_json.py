"""Tests for robust LLM JSON extraction."""

from __future__ import annotations

import unittest

from llm_json import LlmJsonError, parse_llm_json_object
from host_chat import _parse_llm_json


class LlmJsonTests(unittest.TestCase):
    def test_nested_object_inside_fence(self) -> None:
        """Old non-greedy \{.*?\} cut at the first closing brace — must not regress."""
        raw = """Here is the reply:
```json
{
  "assistant_message": "ok",
  "artifact": {
    "draft_brief": {
      "project": {"title": "Magic Prince"},
      "assets": [{"name": "hero"}]
    }
  },
  "ready_to_export": false
}
```
"""
        parsed = parse_llm_json_object(raw)
        self.assertEqual(parsed["assistant_message"], "ok")
        self.assertEqual(parsed["artifact"]["draft_brief"]["project"]["title"], "Magic Prince")
        self.assertEqual(parsed["artifact"]["draft_brief"]["assets"][0]["name"], "hero")

    def test_trailing_comma_and_smart_quotes(self) -> None:
        raw = '{\n  "assistant_message": \u201cok\u201d,\n  "choices": ["A",],\n}'
        parsed = parse_llm_json_object(raw)
        self.assertEqual(parsed["assistant_message"], "ok")
        self.assertEqual(parsed["choices"], ["A"])

    def test_preamble_then_json(self) -> None:
        raw = 'Sure.\n{"assistant_message": "hi", "ready_to_export": false}'
        parsed = parse_llm_json_object(raw)
        self.assertEqual(parsed["assistant_message"], "hi")

    def test_truncated_object_closed(self) -> None:
        raw = '{"assistant_message": "partial", "artifact": {"draft_brief": {"project": {"title": "X"'
        parsed = parse_llm_json_object(raw)
        self.assertEqual(parsed["assistant_message"], "partial")
        self.assertEqual(parsed["artifact"]["draft_brief"]["project"]["title"], "X")

    def test_soft_prose_fallback(self) -> None:
        parsed = parse_llm_json_object("先聊聊横版手感吧。", soft_prose_fallback=True)
        self.assertIn("横版", parsed["assistant_message"])
        self.assertFalse(parsed["ready_to_export"])

    def test_soft_fallback_off_raises(self) -> None:
        with self.assertRaises(LlmJsonError):
            parse_llm_json_object("先聊聊横版手感吧。", soft_prose_fallback=False)

    def test_host_chat_wrapper_uses_soft_fallback(self) -> None:
        parsed = _parse_llm_json("只是普通一句话，没有 JSON")
        self.assertTrue(parsed["assistant_message"])

    def test_unescaped_newlines_inside_string(self) -> None:
        raw = '{\n  "assistant_message": "第一行\n第二行",\n  "ready_to_export": false\n}'
        parsed = parse_llm_json_object(raw)
        self.assertIn("第一行", parsed["assistant_message"])
        self.assertIn("第二行", parsed["assistant_message"])

    def test_broken_json_soft_recovery(self) -> None:
        # Truncation may be closed into valid JSON; completely mangled text must soft-recover.
        raw = '{"assistant_message": "还在扩写", "artifact": {"draft_brief": {"project": {"title": "X"'
        parsed = parse_llm_json_object(raw, soft_prose_fallback=True)
        self.assertTrue(parsed["assistant_message"])

        mangled = '{assistant_message: 还在扩写, draft_brief: <<<broken>>>'
        soft = parse_llm_json_object(mangled, soft_prose_fallback=True)
        self.assertTrue(soft["assistant_message"])
        self.assertIn("recovered", soft.get("notes_for_host", ""))


if __name__ == "__main__":
    unittest.main()
