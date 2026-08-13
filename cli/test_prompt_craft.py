"""CJK assemble guards for prompt craft."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from prompt_craft import (
    PromptCraftError,
    _cjk_ok_as_short_label,
    assemble_asset_prompt,
    assemble_visual_target_prompt,
    contains_cjk,
    craft_asset_prompt,
    craft_visual_target_prompt,
    structured_fields_from_project_scaffold,
)


class FakeProjectZhProse:
    """Chinese description/art_direction must not land in final VT prompt."""

    title = "黑哨"
    description = "这是一款关于裁判道德选择的体育模拟游戏，玩家需要在比赛中做出判罚。"
    art_direction = "Q版电视转播风格，明亮扁平上色，强调可读性。"
    dimension = "2d"
    genre = "sports sim"
    gameplay_loop = "观看比赛并处理犯规QTE"
    session_goal = "撑完一场比赛"
    player_asset = "裁判"
    camera = {"mode": "broadcast", "scope": "pitch"}
    hud = [{"asset": "decision_wheel", "anchor": "top_right"}]
    viewport = {"width": 1280, "height": 720}


class CjkAssembleGuardTests(unittest.TestCase):
    def test_contains_cjk(self):
        self.assertTrue(contains_cjk("红色小船"))
        self.assertFalse(contains_cjk("red boat"))

    def test_cjk_ok_as_short_label(self):
        self.assertTrue(_cjk_ok_as_short_label("裁判"))
        self.assertTrue(_cjk_ok_as_short_label("red boat"))
        self.assertTrue(
            _cjk_ok_as_short_label(
                "裁判, clearly readable focal character, about 15-20% of screen height"
            )
        )
        self.assertFalse(_cjk_ok_as_short_label("这是一个很长的中文角色描述超过十二个汉字了"))
        self.assertFalse(_cjk_ok_as_short_label("裁判登场。"))
        self.assertFalse(_cjk_ok_as_short_label("Hello!\n世界"))

    def test_assemble_rejects_cjk_description_fallback(self):
        project = {"view": "side", "art_direction": "像素风"}
        spec = {"description": "码头上的红色小船", "type": "character"}
        with self.assertRaises(PromptCraftError):
            assemble_asset_prompt({}, project=project, spec=spec)

    def test_assemble_accepts_english_subject(self):
        project = {"view": "side"}
        spec = {"description": "码头上的红色小船", "type": "character"}
        prompt = assemble_asset_prompt(
            {"subject": "A small red boat at a wooden pier"},
            project=project,
            spec=spec,
        )
        self.assertIn("red boat", prompt.lower())

    def test_vt_scaffold_rejects_chinese_description_art_direction(self):
        fields = structured_fields_from_project_scaffold(
            FakeProjectZhProse(),
            {"id": "b", "label": "action_beat", "focus": "Foul decision beat."},
        )
        with self.assertRaises(PromptCraftError) as ctx:
            assemble_visual_target_prompt(fields)
        self.assertIn("Chinese brief text", str(ctx.exception))

    def test_vt_assemble_rejects_cjk_prose_hero(self):
        with self.assertRaises(PromptCraftError):
            assemble_visual_target_prompt(
                {
                    "scene": "green pitch under lights",
                    "hero": "这是一个很长的中文角色描述超过十二个汉字了",
                }
            )

    def test_vt_assemble_rejects_punctuated_cjk_hero(self):
        with self.assertRaises(PromptCraftError):
            assemble_visual_target_prompt(
                {
                    "scene": "green pitch under lights",
                    "hero": "裁判登场。",
                }
            )

    def test_vt_assemble_allows_short_cjk_hero_hud(self):
        prompt = assemble_visual_target_prompt(
            {
                "scene": "green pitch under lights",
                "hero": "裁判",
                "hud": "判罚轮盘",
                "style_lock": "chibi flat shading",
            }
        )
        self.assertIn("裁判", prompt)
        self.assertIn("判罚轮盘", prompt)

    @patch("prompt_craft.chat_text_completion")
    def test_llm_prose_asset_rejects_cjk_prose(self, chat: object) -> None:
        chat.return_value = (
            '{"prompt": "码头上的红色小船停靠在木质栈桥旁，柔和像素风。"}'
        )
        with self.assertRaises(PromptCraftError) as ctx:
            craft_asset_prompt(
                context={
                    "project": {"view": "side"},
                    "asset": {"type": "prop", "content_class": "prop_static"},
                },
                model="test",
                api_key="k",
                api_base="https://example.com/v1",
            )
        self.assertIn("Chinese brief text", str(ctx.exception))

    @patch("prompt_craft.chat_text_completion")
    def test_llm_prose_asset_allows_english(self, chat: object) -> None:
        chat.return_value = '{"prompt": "Referee on a green pitch, side view prop"}'
        out = craft_asset_prompt(
            context={
                "project": {"view": "side"},
                "asset": {"type": "character", "content_class": "character"},
            },
            model="test",
            api_key="k",
            api_base="https://example.com/v1",
        )
        self.assertEqual(out["prompt_source"], "llm_prose")
        self.assertIn("Referee", out["prompt"])

    @patch("prompt_craft.chat_text_completion")
    def test_llm_prose_vt_rejects_cjk_prose(self, chat: object) -> None:
        chat.return_value = (
            '{"prompt": "这是一款体育模拟的全屏截图，裁判正在判罚犯规。"}'
        )
        with self.assertRaises(PromptCraftError) as ctx:
            craft_visual_target_prompt(
                context={"project": {}},
                model="test",
                api_key="k",
                api_base="https://example.com/v1",
            )
        self.assertIn("Chinese brief text", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
