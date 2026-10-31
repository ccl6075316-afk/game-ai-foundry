"""Accepted archive reuse must not turn missing upstream files into new provenance."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import volume_fish as v
from volume_archive import plan_archive
from test_volume_fish import VolumeTests


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.fixture = VolumeTests()
        f = self.fixture
        f.setUp()
        self.addCleanup(f.tearDown)
        f.add_sop_fixture_fin()
        f.plan()
        with patch('volume_fish.subprocess.run', side_effect=f.successful_builder):
            self.assertEqual(f.invoke('build', '--handoff', f.handoff, '--blender', __import__('sys').executable)[0].exit_code, 0)
            self.assertEqual(f.invoke('render', '--handoff', f.handoff, '--blender', __import__('sys').executable)[0].exit_code, 0)
        from test_volume_sop import attach_complete_fixture
        attach_complete_fixture(f.handoff)
        self.assertEqual(f.invoke('accept', '--handoff', f.handoff, '--note', 'Fixture operator inspected all review images.')[0].exit_code, 0)
        old = v.read_json(f.handoff)
        self.spec = {'accepted_handoff': str(f.handoff), 'profile': str(f.profile),
                     'blend': old['outputs']['blend'], 'glb': old['outputs']['glb'],
                     'source': str(f.source), 'reference': str(f.reference),
                     'review_images': v.read_json(Path(old['outputs']['render_report']))['review']}
        self.archive = f.root/'archive.json'
        self.target = f.root/'candidate.json'
        self.save()

    def save(self):
        v.write_json(self.archive, self.spec)

    def plan(self):
        return plan_archive(self.archive, self.fixture.profile, self.target)

    def test_reuse_is_pending_and_does_not_require_or_recreate_upstream_files(self):
        f = self.fixture
        old_bytes = f.handoff.read_bytes()
        f.raw.unlink()
        f.brief.unlink()
        f.manifest.unlink()
        h = self.plan()
        self.assertEqual(h['style_visual_review'], 'pending')
        ledger=v.read_json(Path(h['production']['review']))
        self.assertEqual(ledger['task_type'],'rebuild')
        self.assertEqual(ledger['evidence'],{})
        self.assertTrue(all(row['result']=='pending' for row in ledger['stages'].values()))
        self.assertEqual(h['next_action'], 'run')
        self.assertEqual(v.fresh_handoff(self.target)['source']['sha256'], v.sha(f.source))
        self.assertEqual(old_bytes, f.handoff.read_bytes())
        self.assertFalse(f.manifest.exists())

    def test_changed_source_or_review_image_is_rejected(self):
        for key in ('source', 'glb'):
            p = Path(self.spec[key]); original = p.read_bytes()
            p.write_bytes(original+b'changed')
            with self.subTest(key=key), self.assertRaises(v.VolumeError):
                self.plan()
            p.write_bytes(original)
        p = Path(self.spec['review_images']['side'])
        p.write_bytes(p.read_bytes()+b'changed')
        with self.assertRaises(v.VolumeError): self.plan()

    def test_missing_review_and_unaccepted_history_are_rejected(self):
        self.spec['review_images'].pop('front'); self.save()
        with self.assertRaises(v.VolumeError): self.plan()
        f = self.fixture
        old = v.read_json(f.handoff); old['style_visual_review'] = 'pending'; v.write_json(f.handoff, old)
        with self.assertRaises(v.VolumeError): self.plan()

    def test_changed_historical_receipt_after_plan_is_rejected(self):
        self.plan()
        old = v.read_json(self.fixture.handoff)
        old['style_review']['note'] += ' changed'
        v.write_json(self.fixture.handoff, old)
        with self.assertRaises(v.VolumeError): v.fresh_handoff(self.target)

    def test_handoff_and_model_outputs_cannot_overwrite_archive_inputs(self):
        with self.assertRaises(v.VolumeError):
            plan_archive(self.archive, self.fixture.profile, self.fixture.handoff)
        self.plan()
        h = v.read_json(self.target); h['outputs']['glb'] = self.spec['glb']; v.write_json(self.target, h)
        with self.assertRaises(v.VolumeError): v.fresh_handoff(self.target)

    def test_archive_mapping_change_and_fake_generation_are_rejected(self):
        self.plan()
        self.spec['reference'] = str(self.fixture.source); self.save()
        with self.assertRaises(v.VolumeError): v.fresh_handoff(self.target)
        self.target.unlink()
        old = v.read_json(self.fixture.handoff); old['source']['generation_stage'] = 'local_file'
        v.write_json(self.fixture.handoff, old)
        with self.assertRaises(v.VolumeError): self.plan()


if __name__ == '__main__':
    unittest.main()
