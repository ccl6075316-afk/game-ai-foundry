from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import click
from click.testing import CliRunner

from asset_review import (
    get_review,
    iter_review_rows,
    replace_local_file,
    resolve_canonical_path,
    set_review,
)
from assets_cmds import (
    _pick_regenerate_task_id,
    build_regenerate_plan,
    register_assets_commands,
)
from assets_manifest import load_assets_manifest, save_assets_manifest


def _cli_runner() -> tuple[CliRunner, click.Group]:
    @click.group()
    def root() -> None:
        pass

    register_assets_commands(root)
    return CliRunner(), root


def _manifest():
    return {
        "manifest_version": 1,
        "assets": {
            "knight": {
                "brief": {
                    "name": "knight",
                    "type": "character",
                    "usage": "player",
                    "usage_description": "hero",
                },
                "stages": [
                    {
                        "stage": "image.raw",
                        "path_repo": "output/demo/knight_raw.png",
                        "role": "pipeline_intermediate",
                    },
                    {
                        "stage": "image.nobg",
                        "path_repo": "output/demo/knight_nobg.png",
                        "role": "gameplay_ready",
                    },
                ],
            },
            "item_icons": {
                "brief": {
                    "name": "item_icons",
                    "type": "icon_kit",
                    "usage": "item_icon",
                    "items": [
                        {"id": "sword", "slug": "sword", "usage": "item_icon"},
                        {"id": "potion", "slug": "potion", "usage": "pickup"},
                    ],
                },
                "stages": [
                    {
                        "stage": "image.nobg",
                        "path_repo": "output/demo/item_icons__sword_nobg.png",
                        "kit_item_slug": "sword",
                        "kit_item_id": "sword",
                        "role": "gameplay_ready",
                    },
                    {
                        "stage": "image.nobg",
                        "path_repo": "output/demo/item_icons__potion_nobg.png",
                        "kit_item_slug": "potion",
                        "kit_item_id": "potion",
                        "role": "gameplay_ready",
                    },
                ],
                "item_reviews": {},
            },
        },
    }


class AssetReviewTests(unittest.TestCase):
    def test_iter_rows_expands_kit(self) -> None:
        rows = iter_review_rows(_manifest())
        ids = {r["row_id"] for r in rows}
        self.assertIn("knight", ids)
        self.assertIn("item_icons__sword", ids)
        self.assertIn("item_icons__potion", ids)

    def test_canonical_prefers_nobg(self) -> None:
        m = _manifest()
        path = resolve_canonical_path(m["assets"]["knight"])
        self.assertEqual(path, "output/demo/knight_nobg.png")

    def test_set_review_accept(self) -> None:
        m = _manifest()
        rev = set_review(m, asset_name="knight", status="accepted")
        self.assertEqual(rev["status"], "accepted")
        self.assertEqual(get_review(m, asset_name="knight")["status"], "accepted")

    def test_kit_item_review_isolated(self) -> None:
        m = _manifest()
        set_review(
            m,
            asset_name="item_icons",
            kit_item_slug="sword",
            status="replaced",
            source="local_file",
        )
        self.assertEqual(
            get_review(m, asset_name="item_icons", kit_item_slug="sword")["status"],
            "replaced",
        )
        self.assertEqual(
            get_review(m, asset_name="item_icons", kit_item_slug="potion")["status"],
            "pending",
        )

    def test_replace_local_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            manifest_path = repo / "assets-manifest.json"
            dest_rel = "output/demo/knight_nobg.png"
            dest = repo / dest_rel
            dest.parent.mkdir(parents=True)
            dest.write_bytes(b"old")
            source = root / "new.png"
            source.write_bytes(b"new-bytes")
            manifest = _manifest()
            save_assets_manifest(manifest_path, manifest)

            result = replace_local_file(
                manifest_path,
                asset_name="knight",
                source_abs=source,
                repo_root=repo,
            )
            self.assertTrue(result["ok"])
            self.assertEqual(dest.read_bytes(), b"new-bytes")
            self.assertEqual(result["review"]["status"], "replaced")
            self.assertEqual(result["review"]["source"], "local_file")

    def test_pick_regenerate_kit_item_prefers_generate(self) -> None:
        tasks = [
            {
                "id": "item_icons__sword.prompt.craft",
                "asset": "item_icons",
                "asset_id": "item_icons__sword",
                "step": "prompt.craft",
                "status": "done",
                "artifacts": {"kit_item_slug": "sword"},
            },
            {
                "id": "item_icons__sword.image.generate",
                "asset": "item_icons",
                "asset_id": "item_icons__sword",
                "step": "image.generate",
                "status": "done",
                "artifacts": {"kit_item_slug": "sword"},
            },
            {
                "id": "item_icons__potion.image.generate",
                "asset": "item_icons",
                "asset_id": "item_icons__potion",
                "step": "image.generate",
                "status": "done",
                "artifacts": {"kit_item_slug": "potion"},
            },
        ]
        tid = _pick_regenerate_task_id(tasks, "item_icons", item="sword")
        self.assertEqual(tid, "item_icons__sword.image.generate")

    def test_build_regenerate_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "pipe.json"
            manifest.write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "knight.image.generate",
                                "asset": "knight",
                                "status": "failed",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            plan = build_regenerate_plan(manifest, "knight", jobs=2)
            self.assertEqual(plan["reset_task_id"], "knight.image.generate")
            self.assertTrue(any("pipeline reset" in c for c in plan["commands"]))
            self.assertTrue(any("pipeline run" in c and "--jobs 2" in c for c in plan["commands"]))

    def test_build_regenerate_plan_missing_task_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "pipe.json"
            manifest.write_text(json.dumps({"tasks": []}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                build_regenerate_plan(manifest, "knight", jobs=2)
            self.assertIn("no reset_task_id", str(ctx.exception))
            self.assertNotIn("pipeline run", str(ctx.exception))

    def test_mark_replaced_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "assets-manifest.json"
            save_assets_manifest(manifest_path, _manifest())
            runner, root = _cli_runner()
            result = runner.invoke(
                root,
                [
                    "assets",
                    "review",
                    "mark-replaced",
                    "--manifest",
                    str(manifest_path),
                    "--asset",
                    "knight",
                    "--source",
                    "regenerate",
                    "--json",
                ],
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)
            payload = json.loads(result.output)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["row_id"], "knight")
            self.assertEqual(payload["review"]["status"], "replaced")
            self.assertEqual(payload["review"]["source"], "regenerate")
            self.assertTrue(payload["review"]["updated_at"])

            saved = load_assets_manifest(manifest_path)
            rev = get_review(saved, asset_name="knight")
            self.assertEqual(rev["status"], "replaced")
            self.assertEqual(rev["source"], "regenerate")

    def test_mark_replaced_cli_kit_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "assets-manifest.json"
            save_assets_manifest(manifest_path, _manifest())
            runner, root = _cli_runner()
            result = runner.invoke(
                root,
                [
                    "assets",
                    "review",
                    "mark-replaced",
                    "--manifest",
                    str(manifest_path),
                    "--asset",
                    "item_icons",
                    "--item",
                    "sword",
                    "--source",
                    "regenerate",
                    "--json",
                ],
            )
            self.assertEqual(result.exit_code, 0, msg=result.output)
            payload = json.loads(result.output)
            self.assertEqual(payload["row_id"], "item_icons__sword")
            self.assertEqual(payload["review"]["status"], "replaced")
            self.assertEqual(payload["review"]["source"], "regenerate")
            saved = load_assets_manifest(manifest_path)
            self.assertEqual(
                get_review(saved, asset_name="item_icons", kit_item_slug="sword")["source"],
                "regenerate",
            )
            self.assertEqual(
                get_review(saved, asset_name="item_icons", kit_item_slug="potion")["status"],
                "pending",
            )


if __name__ == "__main__":
    unittest.main()
