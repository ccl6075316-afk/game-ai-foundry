"""Small runner regressions using saved Godot metadata and disposable local logs."""
from __future__ import annotations
import argparse
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / "projects/fishing-2d/plans/reviews/fish-school-v1"
OUTPUT_REVIEW = ROOT / "projects/fishing-2d/plans/reviews/fish-school-motion-v2"
WORK = ROOT / "work/fish-school-tests"
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("fish_school_runner", Path(__file__).with_name("run_fish_school_experiment.py"))
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class RunnerRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved_path = REVIEW / "sim-full-50/benchmark.validation.json"
        cls.saved = RUNNER.read(cls.saved_path)
        cls.settings = {key: value for key, value in cls.saved["inputs"].items()
                        if key not in ("bindings_sha256", "changed_during_run")}
        cls.settings["fixed_simulation_delta_seconds"] = 1 / 60
        cls.bindings = cls.saved["inputs"]["bindings_sha256"]
        if not cls.bindings or not cls.saved.get("ok"):
            raise RuntimeError("A successful source-bound Godot simulation report is required")

    def test_saved_godot_precision_is_valid_for_resume(self):
        self.assertEqual(self.saved["inputs"]["mode"], "simulation")
        self.assertEqual(self.saved["inputs"]["count"], 50)
        self.assertTrue(RUNNER.valid(self.saved, self.settings, self.bindings))

    def test_settings_changes_reject_resume(self):
        for key, value in (("count", 51), ("mode", "motion"),
                           ("fixed_simulation_delta_seconds", 1 / 60 + 1e-9)):
            with self.subTest(key=key):
                changed = dict(self.settings, **{key: value})
                self.assertFalse(RUNNER.valid(self.saved, changed, self.bindings))

    def test_current_source_hash_change_rejects_resume(self):
        current = dict(self.bindings)
        current[next(iter(current))] = "0" * 64
        self.assertFalse(RUNNER.valid(self.saved, self.settings, current))
        current = dict(self.bindings, **{"res://new-bound-source.gd": "1" * 64})
        self.assertFalse(RUNNER.valid(self.saved, self.settings, current))

    def test_changed_or_failed_source_report_rejects_resume(self):
        changed = copy.deepcopy(self.saved)
        changed["inputs"]["changed_during_run"] = [next(iter(self.bindings))]
        self.assertFalse(RUNNER.valid(changed, self.settings, self.bindings))
        changed = copy.deepcopy(self.saved)
        changed.update(ok=False, status="failed")
        self.assertFalse(RUNNER.valid(changed, self.settings, self.bindings))

    def test_exact_review_roots_only(self):
        game = ROOT / "projects/fishing-2d/game"
        for name in ("fish-school-v1", "fish-school-motion-v2"):
            self.assertTrue(RUNNER.allowed_review_root(game, game.parent / "plans/reviews" / name))
        for suffix in ("fish-school-motion-v3", "fish-school-motion-v2/nested", "elsewhere"):
            self.assertFalse(RUNNER.allowed_review_root(game, game.parent / "plans/reviews" / suffix))

    def test_simulation_bindings_include_adapter_and_reject_changes(self):
        with tempfile.TemporaryDirectory(prefix="binding-", dir=WORK) as directory:
            game = Path(directory)
            for file in ("project.godot", "scenes/fish_school_review.tscn", "scripts/aquarium/fish_school/FishSchoolReview.gd", "scripts/aquarium/fish_school/FishSchoolSimulation.gd", "scripts/aquarium/fish_school/FishSchoolMotionAdapter.gd"):
                path = game / file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("source", encoding="utf-8")
            current = RUNNER.bindings(game, "simulation")
            adapter = "res://scripts/aquarium/fish_school/FishSchoolMotionAdapter.gd"
            self.assertIn(adapter, current)
            report = copy.deepcopy(self.saved)
            report["inputs"]["bindings_sha256"] = current
            self.assertTrue(RUNNER.valid(report, self.settings, current))
            (game / adapter.removeprefix("res://")).write_text("changed", encoding="utf-8")
            self.assertFalse(RUNNER.valid(report, self.settings, RUNNER.bindings(game, "simulation")))

    def test_changed_sources_protect_v1_even_before_rerun(self):
        with tempfile.TemporaryDirectory(prefix="historical-", dir=WORK) as directory:
            review = Path(directory) / "fish-school-v1"
            folder = review / "sim-full-50"
            folder.mkdir(parents=True)
            original = {"res://old.gd": "a" * 64}
            RUNNER.write(folder / "benchmark.validation.json", {"ok":True,"status":"done","inputs":{"mode":"simulation","bindings_sha256":original}})
            with patch.object(RUNNER, "bindings", return_value=original):
                RUNNER.protect_historical_v1(Path(directory) / "game", review)
            with patch.object(RUNNER, "bindings", return_value={"res://old.gd":"b" * 64}):
                with self.assertRaisesRegex(ValueError, "Historical fish-school-v1 evidence is frozen"):
                    RUNNER.protect_historical_v1(Path(directory) / "game", review)
            self.assertEqual(RUNNER.read(folder / "benchmark.validation.json")["inputs"]["bindings_sha256"], original)

    def classify(self, content):
        with tempfile.TemporaryDirectory(prefix="runner-", dir=WORK) as directory:
            log = Path(directory) / "engine.log"
            log.write_text(content, encoding="utf-8")
            result = RUNNER.log_errors([log])
        self.assertFalse(Path(directory).exists(), "Disposable logs must be removed immediately")
        return result

    def test_only_exact_known_ca_warning_is_allowed(self):
        errors, warnings = self.classify('ERROR: Condition "ret != noErr" is true. Returning: ""\n'
                                       '   at: get_system_ca_certificates (platform/macos/os_macos.mm:1035)\n')
        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["macOS system CA certificate lookup warning"])
        errors, warnings = self.classify('ERROR: Different certificate failure\n'
                                       '   at: get_system_ca_certificates (platform/macos/os_macos.mm:1035)\n')
        self.assertEqual(len(errors), 1)
        self.assertEqual(warnings, [])

    def test_shader_assertion_resource_and_script_errors_block_results(self):
        errors, warnings = self.classify('SHADER ERROR: sampler limit exceeded\n'
                                       'Shader compilation failed\n'
                                       'Assertion failed: accepted_source_mesh\n'
                                       'Failed to load resource: res://missing.scn\n'
                                       'SCRIPT ERROR: Invalid call\n'
                                       'ERROR: unrelated runtime fault\n')
        self.assertEqual(len(errors), 6)
        self.assertEqual(warnings, [])

    def test_ca_warning_does_not_hide_following_real_error(self):
        errors, warnings = self.classify('ERROR: Condition "ret != noErr" is true. Returning: ""\n'
                                       '   at: get_system_ca_certificates (platform/macos/os_macos.mm:1035)\n'
                                       'SCRIPT ERROR: independent failure\n')
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(warnings), 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, default=OUTPUT_REVIEW)
    args = parser.parse_args()
    game = ROOT / "projects/fishing-2d/game"
    if not args.review.is_absolute() or not RUNNER.allowed_review_root(game, args.review) or args.review.resolve() == REVIEW.resolve():
        parser.error("Unit evidence must use exact fish-school-motion-v2 root; preserve historical v1 report")
    args.review.mkdir(parents=True, exist_ok=True)
    if WORK.resolve() != WORK or not WORK.is_relative_to(ROOT / "work"):
        raise ValueError("Temporary test root must be the non-symlink repository work/fish-school-tests")
    existed = WORK.exists()
    WORK.mkdir(parents=True, exist_ok=True)
    if WORK.resolve() != WORK:
        raise ValueError("Temporary test root changed during creation")
    output = io.StringIO()
    try:
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RunnerRegression))
    finally:
        if not existed:
            WORK.rmdir()
    report = {"schema_version": 1, "command": "fish.school.runner-unit-test", "ok": result.wasSuccessful(),
              "status": "done" if result.wasSuccessful() else "failed", "next_action": "human_review" if result.wasSuccessful() else "fix_input",
              "tests": result.testsRun, "failures": [str(error) for _, error in result.failures + result.errors],
              "saved_metadata": str(RunnerRegression.saved_path), "temporary_output": "Disposable log directories removed immediately",
              "runner_sha256": RUNNER.hashlib.sha256(Path(RUNNER.__file__).read_bytes()).hexdigest(),
              "scope": "No GPU execution, model hashing, source edits or performance measurements"}
    RUNNER.write(args.review / "unit-test.validation.json", report)
    print(output.getvalue(), end="")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
