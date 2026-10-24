"""Evidence gate rejects omissions and stale inputs without granting acceptance."""
import json
from pathlib import Path
import tempfile
import unittest

from click.testing import CliRunner
from PIL import Image
from volume_cmds import volume_group
from volume_sop import STAGES, INPUT_ROLES, initialize, check, sha, write


class SopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.review = self.root / 'review.json'
        self.data = initialize('fixture_only', self.review)

    def populated_fixture(self):
        # Synthetic artifacts exercise bookkeeping, never visual acceptance.
        for role in INPUT_ROLES:
            path = self.root / (role + '.dat')
            path.write_text(role)
            self.data['candidate_files'][role] = {'path': path.name, 'sha256': sha(path)}
        geometry = self.root/'lips.json'
        write(geometry, {'parts': [dict(name=name, vertices=[[0,0,0],[1,0,0],[0,1,0]],
                                      triangles=[0,1,2]) for name in ('upper','lower')]})
        self.data['candidate_files']['lip_geometry'] = {'path':geometry.name, 'sha256':sha(geometry)}
        self.data['stages']['mouth']['implementation'] = {
            'branch':'source_lip_bands', **{name:{'resource_role':'model',
                'geometry_role':'lip_geometry','part':name,'node':'Fixture_lips'} for name in ('upper','lower')}}
        paths = {'data': self.root/'notes.txt', 'image': self.root/'view.png',
                 'report': self.root/'gate.json', 'video': self.root/'video.mp4'}
        paths['data'].write_text('Synthetic fixture')
        Image.new('RGB', (2, 2)).save(paths['image'])
        write(paths['report'], {'ok': True})
        paths['video'].write_bytes(b'Fixture tests metadata only, not video decoding')
        frozen = {k: v['sha256'] for k, v in self.data['candidate_files'].items()}
        for stage, criteria in STAGES.items():
            entry = self.data['stages'][stage]
            entry.update(result='passed', method='Fixture method', reviewer='Test', observations='Fixture only')
            for criterion, kind in criteria.items():
                eid = stage + '.' + criterion
                entry['checks'][criterion] = [eid]
                self.data['evidence'][eid] = {'path': paths[kind].name, 'sha256': sha(paths[kind]),
                    'kind': kind, 'bound_inputs': dict(frozen), 'observation': 'Fixture only'}
        write(self.review, self.data)

    def test_empty_review_fails_via_cli_with_structured_reasons(self):
        result = CliRunner().invoke(volume_group, ['sop-check', '--review', str(self.review),
            '--output', str(self.root/'result.json'), '--json'])
        self.assertEqual(result.exit_code, 1, result.output)
        payload = json.loads(result.output)
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['next_action'], 'fix_input')
        self.assertTrue(any(f.get('check_code') == 'missing_evidence' for f in payload['failures']))

    def test_complete_bookkeeping_passes_without_asset_acceptance(self):
        self.populated_fixture()
        report = check(self.review)
        self.assertTrue(report['ok'], report['failures'])
        self.assertEqual(report['next_action'], 'human_review')
        self.assertNotIn('accepted', report)

    def test_missing_lip_cover_is_rejected(self):
        self.populated_fixture()
        self.data['stages']['mouth']['checks']['native_pixel_cover_and_actual_uv_joins'] = []
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'missing_evidence' for f in check(self.review)['failures']))

    def test_pictures_and_passed_flags_cannot_replace_actual_lip_exports(self):
        self.populated_fixture()
        del self.data['stages']['mouth']['implementation']
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'missing_mouth_implementation' for f in check(self.review)['failures']))

    def test_missing_lower_layer_and_duplicate_part_are_rejected(self):
        self.populated_fixture()
        impl = self.data['stages']['mouth']['implementation']
        impl['lower']['part'] = 'absent'
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'invalid_lip_geometry' for f in check(self.review)['failures']))
        impl['lower']['part'] = 'upper'
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'duplicate_lip_layer' for f in check(self.review)['failures']))

    def test_empty_or_collapsed_export_cannot_pass_with_fresh_hashes(self):
        self.populated_fixture()
        path = self.root/'lips.json'
        for vertices, triangles in [([], []), ([[0,0,0],[1,0,0],[2,0,0]], [0,1,2])]:
            write(path, {'parts':[dict(name=n,vertices=vertices,triangles=triangles) for n in ('upper','lower')]})
            self.data['candidate_files']['lip_geometry']['sha256'] = sha(path)
            frozen = {k:v['sha256'] for k,v in self.data['candidate_files'].items()}
            for row in self.data['evidence'].values():row['bound_inputs'] = dict(frozen)
            write(self.review, self.data)
            self.assertTrue(any(f['code'] == 'invalid_lip_geometry' for f in check(self.review)['failures']))

    def test_anatomical_branch_requires_explicit_basis(self):
        self.populated_fixture()
        impl = {'branch':'anatomical_alternative'}
        self.data['stages']['mouth']['implementation'] = impl
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'missing_anatomical_basis' for f in check(self.review)['failures']))
        impl.update(reason='Fixture only, not anatomical approval', method_reference='Fixture structural branch')
        write(self.review, self.data)
        self.assertTrue(check(self.review)['ok'])

    def test_fin_contact_does_not_replace_native_source_shape(self):
        self.populated_fixture()
        self.data['stages']['fins']['checks']['source_cutout_and_shape_comparison'] = []
        write(self.review, self.data)
        report = check(self.review)
        self.assertTrue(any(f['code'] == 'missing_evidence' and
            'source_cutout_and_shape_comparison' in f['message'] for f in report['failures']))

    def test_fin_cutout_does_not_replace_body_attachment_evidence(self):
        self.populated_fixture()
        self.data['stages']['skin']['checks']['body_owned_fin_base_marks'] = []
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'missing_evidence' and
            'body_owned_fin_base_marks' in f['message'] for f in check(self.review)['failures']))

    def test_changed_candidate_and_old_binding_are_rejected(self):
        self.populated_fixture()
        path = self.root/'model.dat'
        path.write_text('new model')
        self.assertTrue(any(f['code'] == 'stale_artifact' for f in check(self.review)['failures']))
        self.data['candidate_files']['model']['sha256'] = sha(path)
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'stale_binding' for f in check(self.review)['failures']))

    def test_failed_report_and_changed_evidence_are_rejected(self):
        self.populated_fixture()
        path = self.root/'gate.json'
        write(path, {'ok': False})
        self.assertFalse(check(self.review)['ok'])
        for row in self.data['evidence'].values():
            if row['kind'] == 'report': row['sha256'] = sha(path)
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'failed_report' for f in check(self.review)['failures']))

    def test_no_overwrite_of_review_inputs_or_evidence(self):
        self.populated_fixture()
        with self.assertRaises(ValueError): initialize('replacement', self.review)
        for target in [self.review, self.root/'model.dat', self.root/'view.png']:
            before = target.read_bytes()
            with self.assertRaises(ValueError): check(self.review, target)
            self.assertEqual(before, target.read_bytes())

    def test_malformed_observation_cannot_pass(self):
        self.populated_fixture()
        self.data['evidence']['head.clay_front']['observation'] = 7
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'missing_observation' for f in check(self.review)['failures']))


if __name__ == '__main__':
    unittest.main()
