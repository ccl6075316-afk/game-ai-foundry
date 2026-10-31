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
            if role=='species_profile':write(path,{'species':'fixture_only','fins':[{'name':'Fixture_fin','paired':False,'root_attachment':{'root_band':.065}}]})
            else:path.write_text(role)
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
        self.data['candidate_files']['material_author_model']=dict(self.data['candidate_files']['model'])
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
        self.fin_volume_path=self.root/'fin-volume.json'
        self.fin_volume={'ok':True,'kind':'actual_authored_fin_volume_and_tail_section','species':'fixture_only','model_sha256':frozen['model'],'profile_sha256':frozen['species_profile'],'original_basal_domains_preserved':True,
            'current':{'ok':True,'fin_inventory':['Fixture_fin'],'fins':[{'name':'Fixture_fin','ok':True,'proximal_to_distal_median_ratio':2,
                'final_geometry_correspondence':{'maximum_bidirectional_position_error_native':0},'zones':{z:{'samples':2}for z in ('proximal','middle','distal')},'source_root_band':.065,'attachment_contact':{'ok':True},'missing_opposing_ray_count':0}],
                'tail_cross_section':{'ok':True,'sections':[{'fixture':True}],'maximum_width_error_mm':.1,'tolerance_mm':.4}},'rejected_original':{'ok':False}}
        write(self.fin_volume_path,self.fin_volume)
        self.lip_path=self.root/'native-lip.json';self.lip={'ok':True,'kind':'complete_anterior_semantic_color_chart','species':'fixture_only','source_sha256':frozen['source_image'],'model_sha256':frozen['material_author_model'],'geometry_weights_triangles_unchanged':True,'actual_3d_rim_transport':{'upper_edges':2,'lower_edges':2},'complete_native_lip_ownership':{'protected_texels':20,'maximum_front_weight_inside_complete_lip':0,'maximum_central_weight_inside_complete_lip':0,'domain':{'upper_width_px':8,'lower_width_px':10,'outer_fade_px':3}}};write(self.lip_path,self.lip)
        for stage, criteria in STAGES.items():
            entry = self.data['stages'][stage]
            entry.update(result='passed', method='Fixture method', reviewer='Test', observations='Fixture only')
            for criterion, kind in criteria.items():
                eid = stage + '.' + criterion
                entry['checks'][criterion] = [eid]
                path = self.cold_path if criterion == 'final_asset_cold_load' else paths[kind]
                if criterion=='actual_normal_thickness_and_tail_section':path=self.fin_volume_path
                if criterion=='complete_native_lip_domain_and_front_exclusion':path=self.lip_path
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

    def test_generic_pass_flag_cannot_replace_actual_fin_volume(self):
        self.populated_fixture();write(self.fin_volume_path,{'ok':True})
        self.data['evidence']['fins.actual_normal_thickness_and_tail_section']['sha256']=sha(self.fin_volume_path);write(self.review,self.data)
        self.assertTrue(any(f['code']=='missing_actual_fin_volume'for f in check(self.review)['failures']))

    def test_generic_or_partially_generated_lip_cannot_pass(self):
        self.populated_fixture();self.lip['complete_native_lip_ownership']['maximum_front_weight_inside_complete_lip']=.01;write(self.lip_path,self.lip);self.data['evidence']['mouth.complete_native_lip_domain_and_front_exclusion']['sha256']=sha(self.lip_path);write(self.review,self.data)
        self.assertTrue(any(f['code']=='incomplete_native_lip_domain'for f in check(self.review)['failures']))

    def test_changed_root_domain_is_rejected(self):
        self.populated_fixture();self.fin_volume['current']['fins'][0]['source_root_band']=.9;write(self.fin_volume_path,self.fin_volume);self.data['evidence']['fins.actual_normal_thickness_and_tail_section']['sha256']=sha(self.fin_volume_path);write(self.review,self.data)
        self.assertTrue(any(f['code']=='unverified_fin_attachment_volume'for f in check(self.review)['failures']))

    def test_constant_shell_stale_model_and_nonfailing_negative_are_rejected(self):
        self.populated_fixture()
        self.fin_volume['model_sha256']='0'*64;self.fin_volume['rejected_original']['ok']=True;self.fin_volume['current']['fins'][0]['proximal_to_distal_median_ratio']=1
        write(self.fin_volume_path,self.fin_volume);self.data['evidence']['fins.actual_normal_thickness_and_tail_section']['sha256']=sha(self.fin_volume_path);write(self.review,self.data)
        codes={f['code']for f in check(self.review)['failures']}
        self.assertTrue({'wrong_fin_volume_binding','fin_volume_negative_not_rejected','insufficient_actual_fin_taper'}<=codes)

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


class ProductionExitTests(unittest.TestCase):
    setUp = SopTests.setUp
    populated_fixture = SopTests.populated_fixture
    def production(self):
        return {'review':str(self.review),'species':'fixture_only','task_type':'new'}

    def test_cached_success_and_passed_text_cannot_replace_missing_evidence(self):
        from volume_sop import production_status
        self.populated_fixture()
        self.assertTrue(production_status(self.production())['ok'])
        self.data['stages']['fins']['checks']['actual_normal_thickness_and_tail_section']=[]
        self.data['ok']=True
        self.data['status']='done'
        write(self.review,self.data)
        result=production_status(self.production())
        self.assertFalse(result['ok'])
        self.assertIn('missing_evidence',{f['code'] for f in result['failures']})

    def test_resume_detects_standard_model_and_identity_changes(self):
        from volume_sop import production_status
        self.populated_fixture()
        model=self.root/self.data['candidate_files']['model']['path']
        model.write_bytes(b'new candidate')
        self.assertFalse(production_status(self.production())['ok'])
        self.populated_fixture()
        self.data['standard']['version']='historical'
        write(self.review,self.data)
        self.assertIn('stale_standard',{f['code'] for f in production_status(self.production())['failures']})
        self.assertFalse(production_status(dict(self.production(),species='another_fish'))['ok'])
        other=self.root/'other.glb';other.write_bytes(b'other valid candidate')
        self.assertIn('wrong_current_candidate',{f['code'] for f in production_status(self.production(),{'model':other})['failures']})

    def test_declared_standard_cannot_remove_required_criterion(self):
        from volume_sop import production_status
        self.populated_fixture()
        self.data['standard']['criteria']['fins'].pop('actual_normal_thickness_and_tail_section')
        self.data['stages']['fins']['checks'].pop('actual_normal_thickness_and_tail_section')
        write(self.review,self.data)
        result=production_status(self.production())
        self.assertIn('actual_normal_thickness_and_tail_section', STAGES['fins'])
        self.assertIn('stale_standard',{f['code'] for f in result['failures']})
        self.assertIn('missing_evidence',{f['code'] for f in result['failures']})

    def test_delivery_exit_uses_live_complete_sop_after_technical_success(self):
        import sys, importlib.util
        portable=Path(__file__).resolve().parents[1]/'resources/scripts/volume-fish/portable'
        sys.path.insert(0,str(portable))
        spec=importlib.util.spec_from_file_location('delivery_exit_under_test',portable/'run_delivery_checks.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.populated_fixture()
        status={'stages':[{'name':'fin490','ok':True}], 'formal_acceptance':False}
        expected={'model':self.root/self.data['candidate_files']['model']['path']}
        module.finish_delivery(status,self.production(),expected)
        self.assertTrue(status['ok'])
        self.fin_volume_path.write_text('{"ok":true,"status":"done"}')
        module.finish_delivery(status,self.production(),expected)
        self.assertFalse(status['ok'])
        self.assertEqual(status['status'],'blocked')
        self.assertTrue(status['specialized_checks_ok'])
        self.assertFalse(status['formal_acceptance'])
        self.assertIn('stale_artifact',{f['code'] for f in status['failures']})


def attach_complete_fixture(handoff):
    """Synthetic evidence only. Exercise acceptance wiring without pretending art QA."""
    import volume_fish as v
    h=v.read_json(handoff)
    fixture=SopTests()
    fixture.root=handoff.parent
    fixture.review=Path(h['production']['review'])
    fixture.review.unlink()
    species=v.read_json(Path(h['profile']))['species']
    fixture.data=initialize(species,fixture.review,h['production']['task_type'])
    fixture.populated_fixture()
    d=fixture.data
    for role,path in {'model':h['outputs']['glb'],'editable_source':h['outputs']['blend'],
                      'source_image':h['source_image'],'species_profile':h['profile']}.items():
        d['candidate_files'][role]={'path':str(path),'sha256':sha(Path(path))}
    d['candidate_files']['material_author_model']=dict(d['candidate_files']['model'])
    frozen={k:r['sha256'] for k,r in d['candidate_files'].items()}
    fixture.cold.update(species=species,bound_inputs=frozen)
    write(fixture.cold_path,fixture.cold)
    fins=v.read_json(Path(h['profile']))['fins']
    rows=[]
    for fin in fins:
        for suffix in (['_left','_right'] if fin.get('paired') else ['']):
            row=dict(fixture.fin_volume['current']['fins'][0])
            row.update(name=fin['name']+suffix,source_root_band=fin.get('root_attachment',{}).get('root_band'))
            rows.append(row)
    fixture.fin_volume.update(species=species,model_sha256=frozen['model'],profile_sha256=frozen['species_profile'])
    fixture.fin_volume['current'].update(fins=rows,fin_inventory=[r['name'] for r in rows])
    write(fixture.fin_volume_path,fixture.fin_volume)
    fixture.lip.update(species=species,source_sha256=frozen['source_image'],model_sha256=frozen['model'])
    write(fixture.lip_path,fixture.lip)
    for evidence in d['evidence'].values():
        evidence['bound_inputs']=frozen
        evidence['sha256']=sha(fixture.root/evidence['path'])
    write(fixture.review,d)
