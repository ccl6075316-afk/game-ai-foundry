"""Scan active role skills for removed operational entry points."""

from __future__ import annotations

import re
import unittest

from skill_loader import ROLE_SKILLS, skills_root


_REMOVED_ENTRY_RE = re.compile(
    r"agents show|agent turn|host chat|brief chat|brief brainstorm|"
    r"setup executor|hermes paths|start-gui",
    re.IGNORECASE,
)


class ActiveSkillScanTests(unittest.TestCase):
    def test_active_skills_have_no_removed_entries(self) -> None:
        failures: list[str] = []
        for role, names in ROLE_SKILLS.items():
            for name in names:
                path = skills_root() / role / f"{name}.md"
                self.assertTrue(path.is_file(), f"Missing active skill: {path}")
                for line_number, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(),
                    start=1,
                ):
                    match = _REMOVED_ENTRY_RE.search(line)
                    if match:
                        failures.append(
                            f"{path}:{line_number}: {match.group(0)}"
                        )
        self.assertEqual([], failures, "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
