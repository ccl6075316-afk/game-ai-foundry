"""Bounded viewer/evidence contracts, with no production model or native app dependency."""
import contextlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess

PORTABLE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORTABLE))
import view
import evidence


class ViewEvidenceTests(unittest.TestCase):
    def setUp(self):
        work = view.ROOT / 'work' / 'fish-portable-tools'
        work.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='unit-view-', dir=work)
        self.base = Path(self.temp.name)
        self.game = self.base / 'game'
        self.game.mkdir()
        (self.game / 'project.godot').write_text('config_version=5\n')
        self.model = self.base / 'synthetic.glb'
        doc = {'asset': {'version': '2.0'}, 'nodes': [{'mesh': 0}], 'meshes': [{'primitives': [{}]}], 'animations': [{'name': 'Synthetic'}]}
        data = json.dumps(doc).encode()
        data += b' ' * ((-len(data)) % 4)
        self.model.write_bytes(struct.pack('<4sII', b'glTF', 2, 20+len(data)) + struct.pack('<II', len(data), 0x4e4f534a) + data)
        self.spec = self.base / 'spec.json'
        self.data = {'kind': 'fish_asset_finalization_spec', 'version': 1, 'species': 'synthetic',
                     'model': {'path': str(self.model.relative_to(view.ROOT)), 'sha256': view.sha256(self.model)},
                     'game': str(self.game.relative_to(view.ROOT)),
                     'camera': {'focus': {'mode': 'bbox_relative', 'position': [.7,.5,.5]}},
                     'viewer': {'native_clip': 'Synthetic'}}
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        self.spec.write_text(json.dumps(self.data))

    def test_relative_paths_and_camera_are_explicit(self):
        config = view.prepare(self.spec)
        self.assertEqual(config['model'], str(self.model))
        self.assertEqual(config['model_scale'], [1,1,1])
        self.assertEqual(config['camera']['focus']['mode'], 'bbox_relative')
        self.assertFalse(config['capabilities']['part_diagnostics'])
        self.assertEqual(config['inventory']['mesh_count'], 1)

    def test_missing_reference(self):
        self.model.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing reference'):
            view.prepare(self.spec)

    def test_hash_mismatch(self):
        self.data['model']['sha256'] = '0' * 64
        self.save()
        with self.assertRaisesRegex(ValueError, 'hash'):
            view.prepare(self.spec)

    def test_focus_cannot_hide_species_constant(self):
        self.data['camera']['focus'] = {'mode':'bbox_relative','position':[1.4,.5,.5]}
        self.save()
        with self.assertRaisesRegex(ValueError, r'\[0,1\]'):
            view.prepare(self.spec)
        self.data['camera']['focus'] = {'mode':'model','position':[1.4,.5,.5]}
        self.save()
        self.assertEqual(view.prepare(self.spec)['camera']['focus']['position'][0], 1.4)

    def test_reference_is_not_silently_final(self):
        self.data['inputs'] = {'reference_glb': self.data.pop('model')}
        self.save()
        with self.assertRaisesRegex(ValueError, 'model reference required'):
            view.prepare(self.spec)
        self.data['viewer']['model_role'] = 'reference'
        self.save()
        self.assertEqual(view.prepare(self.spec)['model_role'], 'reference_model')

    def test_cli_rejects_output_escape_single_json_no_write(self):
        outside = view.ROOT / 'should-not-exist-view-output'
        result = io.StringIO()
        with contextlib.redirect_stdout(result):
            code = view.main(['--spec', str(self.spec), '--output', str(outside), '--dry-run', '--json'])
        report = json.loads(result.getvalue())
        self.assertEqual(code, 1)
        self.assertFalse(report['ok'])
        self.assertFalse(outside.exists())

    def test_shared_experiment_whitelist_and_fresh_output(self):
        target = view.ROOT / 'projects' / 'synthetic-view-test' / 'experiments' / 'fresh-output'
        self.assertEqual(view.output_path(target), target)
        self.assertFalse(target.exists())
        with self.assertRaisesRegex(ValueError, 'Fresh output'):
            view.output_path(self.base)
        with self.assertRaisesRegex(ValueError, 'aliases'):
            view.output_path(self.model.parent, [self.model])

    def test_dry_run_no_directory_or_native_launch(self):
        output = self.base / 'dry-run'
        result = io.StringIO()
        with contextlib.redirect_stdout(result):
            code = view.main(['--spec', str(self.spec), '--output', str(output), '--dry-run'])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(result.getvalue())['ok'])
        self.assertFalse(output.exists())

    def test_capture_name_traversal_and_backwards_time_rejected(self):
        for captures in ([{'name':'../escape'}], [{'name':'a','time_seconds':1},{'name':'b','time_seconds':0}]):
            self.data['viewer']['captures'] = captures
            self.save()
            with self.assertRaises(ValueError):
                view.prepare(self.spec)

    def test_motion_hash_required(self):
        self.data['motion'] = {'runtime': {'path':str(self.model), 'sha256':'0'*64}, 'profile':self.data['model']}
        self.save()
        with self.assertRaisesRegex(ValueError, 'hash'):
            view.prepare(self.spec)

    def test_zero_exit_and_ok_report_do_not_hide_godot_script_error(self):
        output = self.base / 'error-run'
        def fake_run(argv, stdout, **kwargs):
            stdout.write('SCRIPT ERROR: intentional synthetic negative\n')
            stdout.flush()
            (output / 'viewer.validation.json').write_text(json.dumps({'ok':True}))
            return subprocess.CompletedProcess(argv, 0)
        result = io.StringIO()
        with patch.object(view.subprocess, 'run', fake_run), contextlib.redirect_stdout(result):
            code = view.main(['--spec',str(self.spec),'--output',str(output),'--godot',sys.executable,'--smoke'])
        report = json.loads(result.getvalue())
        self.assertEqual(code, 1)
        self.assertFalse(report['ok'])
        self.assertIn('godot_runtime_error', [f['code'] for f in report['failures']])

    def test_all_godot_error_spellings_are_detected(self):
        for line in ['ERROR: shader', 'SCRIPT ERROR: broken', 'Parse Error: bad syntax', 'Assertion failed: false']:
            self.assertEqual(view.godot_errors(line), [line])
        self.assertEqual(view.godot_errors('Godot Engine v4\nAll checks complete'), [])

    def report(self, capture=True):
        image = self.base / 'capture.png'
        image.write_bytes(b'synthetic not decoded by inventory')
        report = self.base / 'viewer.validation.json'
        report.write_text(json.dumps({'kind':'fish_asset_viewer_validation', 'ok': True,
            'model':str(self.model), 'model_sha256':view.sha256(self.model), 'visual_review':'accepted',
            'captures':[{'path':str(image), 'sha256':view.sha256(image), 'visual_review':'accepted'}] if capture else []}))
        return report, image

    def test_inventory_never_copies_acceptance(self):
        report, image = self.report()
        result = evidence.inventory([report, report])
        self.assertEqual(result['visual_review'], 'pending')
        self.assertEqual(len(result['captures']), 1)
        self.assertEqual(result['captures'][0]['visual_review'], 'pending')
        self.assertEqual(result['captures'][0]['sha256'], view.sha256(image))

    def test_inventory_rejects_changed_capture_and_missing_model(self):
        report, image = self.report()
        image.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Capture hash mismatch'):
            evidence.inventory([report])
        self.model.unlink()
        with self.assertRaisesRegex(ValueError, 'model missing or changed'):
            evidence.inventory([report])

    def test_evidence_cli_safe_dry_run(self):
        report, image = self.report()
        output = self.base / 'evidence'
        result = io.StringIO()
        with contextlib.redirect_stdout(result):
            code = evidence.main(['--report',str(report),'--output',str(output),'--dry-run'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(result.getvalue())['summary']['capture_count'], 1)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
