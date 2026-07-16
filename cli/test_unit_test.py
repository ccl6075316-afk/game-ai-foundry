"""Tests for L1 unit-test harness helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from unit_test import ensure_unit_test_project, find_test_projects, run_unit_tests


class UnitTestHarnessTest(unittest.TestCase):
    def test_ensure_creates_xunit_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project.godot").write_text(
                '[dotnet]\nproject/assembly_name="ForestPlatformer"\n',
                encoding="utf-8",
            )
            csproj = ensure_unit_test_project(root, health=3)
            self.assertTrue(csproj.is_file())
            self.assertTrue((root / "scripts" / "PlayerStats.cs").is_file())
            self.assertTrue((root / "tests" / "PlayerStatsTests.cs").is_file())
            found = find_test_projects(root)
            self.assertEqual(found, [csproj.resolve()])

    def test_run_unit_tests_invokes_dotnet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project.godot").write_text(
                '[dotnet]\nproject/assembly_name="Demo"\n',
                encoding="utf-8",
            )
            ensure_unit_test_project(root)
            fake = mock.Mock(returncode=0, stdout="Passed!", stderr="")
            with mock.patch("unit_test.subprocess.run", return_value=fake) as run:
                with mock.patch("unit_test.resolve_dotnet", return_value="dotnet"):
                    with mock.patch("unit_test.toolchain_env", return_value={}):
                        report = run_unit_tests(root, scaffold_if_missing=False)
            self.assertTrue(report["ok"])
            self.assertEqual(run.call_count, 1)
            args = run.call_args[0][0]
            self.assertEqual(args[0], "dotnet")
            self.assertEqual(args[1], "test")


if __name__ == "__main__":
    unittest.main()
