"""Compatibility checks without creating projects, caches or touching assets."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from audit_workspace import inventory, linked_directory


class AuditWorkspaceTests(unittest.TestCase):
    def test_python311_path_without_junction_api(self):
        path = SimpleNamespace(is_symlink=lambda: False,
                               lstat=lambda: SimpleNamespace(st_file_attributes=0))
        self.assertFalse(linked_directory(path))

    def test_python311_reparse_point_is_still_excluded(self):
        path = SimpleNamespace(is_symlink=lambda: False,
                               lstat=lambda: SimpleNamespace(st_file_attributes=0x400))
        self.assertTrue(linked_directory(path))

    def test_symlink_is_excluded_on_all_python_versions(self):
        self.assertTrue(linked_directory(SimpleNamespace(is_symlink=lambda: True)))

    def test_junction_is_excluded_when_api_is_available(self):
        path = SimpleNamespace(is_symlink=lambda: False, is_junction=lambda: True)
        self.assertTrue(linked_directory(path))

    def test_regular_directory_is_included(self):
        path = SimpleNamespace(is_symlink=lambda: False, is_junction=lambda: False)
        self.assertFalse(linked_directory(path))

    def test_missing_optional_repositories_do_not_run_git_in_parent(self):
        with patch.object(Path, "exists", return_value=False), \
                patch("audit_workspace.os.walk", return_value=[]), \
                patch("audit_workspace.subprocess.check_output") as git:
            report = inventory(Path("standalone-checkout"))
        git.assert_not_called()
        self.assertTrue(report["ok"])
        self.assertEqual(2, len(report["repositories"]))
        self.assertTrue(all(not row["available"] for row in report["repositories"]))


if __name__ == "__main__":
    unittest.main()
