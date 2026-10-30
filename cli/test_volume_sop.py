"""Evidence gate rejects omissions and stale inputs without granting acceptance."""
import json
from pathlib import Path
import tempfile
import unittest

from click.testing import CliRunner
from PIL import Image
from volume_cmds import volume_group
from volume_sop import STAGES, INPUT_ROLES, initialize, check, sha, write
from volume_finalization import COLD_CHECKS


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
            path = self.root / (role + ('.glb' if role == 'model' else '.dat'))
            path.write_text(role)
            self.data['candidate_files'][role] = {'path': path.name, 'sha256': sha(path)}
        self.data['stages']['mouth']['implementation'] = {
            'branch':'integrated_jaw_cut','body_resource_role':'model',
            'cut_line':'Fixture lower-lip boundary','upper_jaw':'Fixture upper volume',
            'lower_jaw':'Fixture lower volume','method_reference':'Fixture method'}
        paths = {'data': self.root/'notes.txt', 'image': self.root/'view.png',
                 'report': self.root/'gate.json', 'video': self.root/'video.mp4'}
        paths['data'].write_text('Synthetic fixture')
        Image.new('RGB', (2, 2)).save(paths['image'])
        write(paths['report'], {'ok': True})
        paths['video'].write_bytes(b'Fixture tests metadata only, not video decoding')
        source = self.root/'editable.blend'
        source.write_bytes(b'Synthetic authoring source, not a Blender file')
        self.data['candidate_files']['editable_source'] = {'path':source.name, 'sha256':sha(source)}
        self.data['stages']['runtime']['finalization'] = {
            'state':'exported', 'editable_source_role':'editable_source', 'model_role':'model',
            'entry_role':'model', 'static_parts':{name:{'geometry_uv_weights_role':'model',
                'observation':'Synthetic declared model part'} for name in ('body','eyes','mouth','fins')},
            'engine_resource_roles':[], 'runtime_behaviors':[]}
        frozen = {k: v['sha256'] for k, v in self.data['candidate_files'].items()}
        self.cold_path = self.root/'final-cold.json'
        self.cold = {'ok':True, 'kind':'fish_final_asset_cold_load', 'species':'fixture_only',
            'bound_inputs':dict(frozen), 'entry_role':'model', 'fresh_process':True,
            'static_builders_disabled':True, 'runtime_static_build_calls':0, 'errors':[],
            'checks':{k:True for k in COLD_CHECKS}}
        write(self.cold_path, self.cold)
        for stage, criteria in STAGES.items():
            entry = self.data['stages'][stage]
            entry.update(result='passed', method='Fixture method', reviewer='Test', observations='Fixture only')
            for criterion, kind in criteria.items():
                eid = stage + '.' + criterion
                entry['checks'][criterion] = [eid]
                path = self.cold_path if criterion == 'final_asset_cold_load' else paths[kind]
                self.data['evidence'][eid] = {'path': path.name, 'sha256': sha(path),
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

    def test_missing_native_mouth_cover_is_rejected(self):
        self.populated_fixture()
        self.data['stages']['mouth']['checks']['native_pixel_cover_and_actual_uv_joins'] = []
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'missing_evidence' for f in check(self.review)['failures']))

    def test_pictures_and_passed_flags_cannot_replace_mouth_implementation(self):
        self.populated_fixture()
        del self.data['stages']['mouth']['implementation']
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'missing_mouth_implementation' for f in check(self.review)['failures']))

    def test_missing_integrated_jaw_details_are_rejected(self):
        self.populated_fixture()
        impl = self.data['stages']['mouth']['implementation']
        impl['lower_jaw'] = ''
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'missing_integrated_jaw_detail' for f in check(self.review)['failures']))
        impl['lower_jaw'] = 'Fixture lower volume'
        impl['body_resource_role'] = 'missing'
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'missing_artifact' for f in check(self.review)['failures']))

    def test_retired_lip_layer_cannot_pass(self):
        self.populated_fixture()
        self.data['stages']['mouth']['implementation']['upper'] = {'node':'Source_lips139'}
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'retired_lip_layer' for f in check(self.review)['failures']))
        self.data['stages']['mouth']['implementation'] = {'branch':'source_lip_bands'}
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'retired_lip_layer' for f in check(self.review)['failures']))

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
        path = self.root/'model.glb'
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
        for target in [self.review, self.root/'model.glb', self.root/'view.png']:
            before = target.read_bytes()
            with self.assertRaises(ValueError): check(self.review, target)
            self.assertEqual(before, target.read_bytes())

    def test_malformed_observation_cannot_pass(self):
        self.populated_fixture()
        self.data['evidence']['head.clay_front']['observation'] = 7
        write(self.review, self.data)
        self.assertTrue(any(f['code'] == 'missing_observation' for f in check(self.review)['failures']))

    def test_old_review_without_final_export_is_blocked(self):
        self.populated_fixture()
        del self.data['stages']['runtime']['finalization']
        write(self.review,self.data)
        self.assertTrue(any(f['code']=='asset_not_finalized' for f in check(self.review)['failures']))

    def test_pending_export_and_static_eye_builder_cannot_be_final(self):
        self.populated_fixture()
        declaration=self.data['stages']['runtime']['finalization']
        declaration['state']='experiment'
        write(self.review,self.data)
        self.assertFalse(check(self.review)['ok'])
        declaration['state']='exported'
        declaration['static_parts']['eyes']['geometry_uv_weights_role']='runtime_manifest'
        write(self.review,self.data)
        self.assertTrue(any(f['code']=='static_part_not_in_model' for f in check(self.review)['failures']))

    def test_generic_passed_report_does_not_prove_cold_final_asset(self):
        self.populated_fixture()
        evidence=self.data['evidence']['runtime.final_asset_cold_load']
        evidence.update(path='gate.json',sha256=sha(self.root/'gate.json'))
        write(self.review,self.data)
        self.assertTrue(any(f['code']=='invalid_final_asset_cold_load' for f in check(self.review)['failures']))

    def test_warm_load_build_calls_wrong_species_binding_and_errors_block_final(self):
        self.populated_fixture()
        original=dict(self.cold)
        for changes in ({'fresh_process':False}, {'static_builders_disabled':False},
                        {'runtime_static_build_calls':1}, {'runtime_static_build_calls':False},
                        {'species':'another_fish'}, {'bound_inputs':{}},
                        {'entry_role':'runtime_manifest'}, {'errors':['shader failure']},
                        {'checks':{'independent_load':True}}):
            with self.subTest(changes=changes):
                write(self.cold_path,{**original,**changes})
                self.data['evidence']['runtime.final_asset_cold_load']['sha256']=sha(self.cold_path)
                write(self.review,self.data)
                self.assertTrue(any(f['code']=='invalid_final_asset_cold_load' for f in check(self.review)['failures']))

    def test_missing_editable_source_and_empty_export_are_blocked(self):
        self.populated_fixture()
        self.data['stages']['runtime']['finalization']['editable_source_role']='missing_source'
        write(self.review,self.data)
        self.assertTrue(any(f['code']=='missing_final_asset_role' for f in check(self.review)['failures']))
        (self.root/'model.glb').write_bytes(b'')
        self.data['candidate_files']['model']['sha256']=sha(self.root/'model.glb')
        write(self.review,self.data)
        self.assertTrue(any(f['code']=='empty_final_asset' for f in check(self.review)['failures']))

    def test_runtime_static_construction_is_not_an_allowed_behavior(self):
        self.populated_fixture()
        self.data['stages']['runtime']['finalization']['runtime_behaviors']=[
            {'resource_role':'runtime_manifest','purpose':'static_geometry_build','observation':'Build eye at entry'}]
        write(self.review,self.data)
        self.assertTrue(any(f['code']=='invalid_runtime_behavior' for f in check(self.review)['failures']))

    def test_copied_species_card_fails_even_with_current_hash_and_bindings(self):
        self.populated_fixture()
        folder=self.root/'species';folder.mkdir()
        card=folder/'bluegill.md';card.write_text('Other species research')
        row=self.data['evidence']['preparation.research_and_measurements']
        row.update(path=str(card),sha256=sha(card))
        write(self.review,self.data)
        self.assertTrue(any(f['code']=='wrong_species_research' for f in check(self.review)['failures']))
        own=folder/'fixture-only.md';card.rename(own)
        row.update(path=str(own),sha256=sha(own))
        write(self.review,self.data)
        self.assertTrue(check(self.review)['ok'])

    def test_shader_animation_resources_can_remain_in_engine(self):
        self.populated_fixture()
        shader=self.root/'pixel.gdshader';shader.write_text('shader_type spatial;')
        self.data['candidate_files']['pixel_shader']={'path':shader.name,'sha256':sha(shader)}
        declaration=self.data['stages']['runtime']['finalization']
        declaration['engine_resource_roles']=['pixel_shader']
        declaration['runtime_behaviors']=[{'resource_role':'motion_config',
            'purpose':'animation','observation':'Independent per-fish animation remains live'}]
        frozen={k:v['sha256'] for k,v in self.data['candidate_files'].items()}
        self.cold['bound_inputs']=frozen
        write(self.cold_path,self.cold)
        for row in self.data['evidence'].values():row['bound_inputs']=dict(frozen)
        self.data['evidence']['runtime.final_asset_cold_load']['sha256']=sha(self.cold_path)
        write(self.review,self.data)
        self.assertTrue(check(self.review)['ok'])


if __name__ == '__main__':
    unittest.main()
