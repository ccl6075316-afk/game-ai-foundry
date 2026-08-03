"""P0-5: unknown asset_type must not fall back to CHARACTER on validate."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from gamefactory import cli
from plan_io import HANDOFF_VERSION, IMAGE_GENERATOR_ROLE


class UnknownAssetTypeValidateTest(unittest.TestCase):
    def test_generate_validate_rejects_unknown_asset_type(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            out = Path("out.png")
            plan = Path("plan.json")
            handoff = {
                "handoff_version": HANDOFF_VERSION,
                "consumer_role": IMAGE_GENERATOR_ROLE,
                "plan": {
                    "prompt": "a rock",
                    "asset_type": "not_a_real_type",
                    "validation": {"min_alpha_ratio": 0.1},
                },
            }
            plan.write_text(json.dumps(handoff), encoding="utf-8")
            creds = MagicMock(
                model="test-model",
                api_key="sk-test-key-not-real",
                api_base="https://example.invalid/v1",
            )
            with (
                patch("gamefactory.generate_image"),
                patch(
                    "image_model_route.resolve_image_credentials",
                    return_value=creds,
                ),
                patch(
                    "image_model_route.effective_generate_tier",
                    return_value="quality",
                ),
            ):
                result = runner.invoke(
                    cli,
                    [
                        "image",
                        "generate",
                        "--plan-file",
                        str(plan),
                        "--output",
                        str(out),
                        "--validate",
                    ],
                    obj={"config": {"image": {"size": "1024x1024"}}},
                )
        combined = (result.output or "") + str(result.exception or "")
        self.assertEqual(result.exit_code, 1, msg=combined)
        self.assertIn("unknown asset_type", combined.lower())


if __name__ == "__main__":
    unittest.main()
