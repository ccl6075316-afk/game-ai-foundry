"""Portable Hermes skill packaging — no machine paths in shipped SKILL.md."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hermes_pack import (
    _PLACEHOLDER_ROOT,
    build_skill_markdown,
    stamp_local_paths,
    sync_hermes_skills,
)


class HermesPortabilityTests(unittest.TestCase):
    def test_terminal_section_uses_placeholder(self) -> None:
        md = build_skill_markdown(
            "game-factory-codex",
            {
                "role": None,
                "description": "test",
                "tags": [],
                "related": [],
                "extra_skill": "codex-delegate.md",
            },
        )
        self.assertIn(_PLACEHOLDER_ROOT, md)
        self.assertNotRegex(md, r"[A-Za-z]:\\")
        self.assertNotRegex(md, r"/Users/[A-Za-z]")

    def test_stamp_rewrites_for_local_install(self) -> None:
        text = f'workdir="{_PLACEHOLDER_ROOT}"\ncd {_PLACEHOLDER_ROOT}/cli'
        root = Path("/tmp/foundry-root")
        cli = root / "cli"
        out = stamp_local_paths(text, root=root, cli=cli)
        self.assertIn(str(root.resolve()), out)
        self.assertNotIn(_PLACEHOLDER_ROOT, out)

    def test_sync_writes_portable_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            written = sync_hermes_skills(Path(tmp))
            self.assertGreaterEqual(len(written), 1)
            for path in written:
                text = path.read_text(encoding="utf-8")
                self.assertIn(_PLACEHOLDER_ROOT, text)
                self.assertNotRegex(text, r"[A-Za-z]:\\")


if __name__ == "__main__":
    unittest.main()
