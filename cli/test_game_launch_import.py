"""A freshly pulled project must import assets before entering play mode."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from godot_cmds import launch_game_project


class LaunchImportTests(unittest.TestCase):
    def launch(self, result):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            with patch('godot_cmds._get_godot_exe', return_value='godot'), \
                 patch('godot_cmds._load_config', return_value={}), \
                 patch('godot_cmds.toolchain_env', return_value={}), \
                 patch('godot_cmds.subprocess.run', return_value=result) as run, \
                 patch('godot_cmds.subprocess.Popen') as start:
                start.side_effect = lambda *args, **kwargs: self.assertEqual(run.call_count, 1)
                try:
                    launch_game_project(project, skip_build=True)
                except SystemExit as exc:
                    return exc.code, run.call_args_list, start.call_args_list
                return 0, run.call_args_list, start.call_args_list

    def test_skip_build_still_imports_assets(self):
        code, runs, starts = self.launch(subprocess.CompletedProcess([], 0, '', ''))
        self.assertEqual(code, 0)
        self.assertEqual(len(runs), 1)
        self.assertIn('--import', runs[0].args[0])
        self.assertIn('--quit', runs[0].args[0])
        self.assertEqual(len(starts), 1)

    def test_import_process_failure_prevents_launch(self):
        code, runs, starts = self.launch(subprocess.CompletedProcess([], 1, '', 'broken PNG'))
        self.assertEqual(code, 1)
        self.assertEqual(starts, [])

    def test_godot_zero_exit_with_import_error_prevents_launch(self):
        code, runs, starts = self.launch(subprocess.CompletedProcess([], 0, 'ERROR: missing source', ''))
        self.assertEqual(code, 1)
        self.assertEqual(starts, [])

    def test_stderr_import_error_prevents_launch(self):
        code, runs, starts = self.launch(subprocess.CompletedProcess([], 0, '', 'SCRIPT ERROR: broken shader'))
        self.assertEqual(code, 1)
        self.assertEqual(starts, [])


if __name__ == '__main__':
    unittest.main()
