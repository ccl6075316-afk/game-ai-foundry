"""Volume gates: provenance, immutable inputs, subprocess failures and real GLB checks."""
from __future__ import annotations

import copy
import io
import json
import math
import shlex
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from click.testing import CliRunner
from PIL import Image

from gamefactory import cli
import volume_fish as volume
from workflow.contract import RESPONSE_FIELDS


def make_glb(path: Path, source: Path, *, loop=True, nearest=True, closed=True, weights=True, metallic=False, root_move=False, front_source=None, use_front=True):
    blob = bytearray()
    views, accessors = [], []
    def add(rows, component, kind, fmt):
        while len(blob) % 4:
            blob.append(0)
        data = b''.join(struct.pack('<' + fmt * len(row), *row) for row in rows)
        view = len(views)
        views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(data)})
        blob.extend(data)
        accessors.append({'bufferView': view, 'componentType': component, 'count': len(rows), 'type': kind})
        return len(accessors) - 1
    pos = add([(0,0,0), (1,0,0), (0,1,0), (0,0,1)], 5126, 'VEC3', 'f')
    weight = add([(1 if weights else .5,0,0,0)] * 4, 5126, 'VEC4', 'f')
    joint = add([(1,0,0,0)] * 4, 5123, 'VEC4', 'H')
    indices = [0,2,1,0,1,3,1,2,3,2,0,3]
    index = add([(i,) for i in (indices if closed else indices[:-3])], 5123, 'SCALAR', 'H')
    times = add([(0,), (.5,), (1,)], 5126, 'SCALAR', 'f')
    rotations = add([(0,0,0,1), (0,.2,0,.98), (0,0,0,1) if loop else (0,.3,0,.95)], 5126, 'VEC4', 'f')
    image = source.read_bytes()
    while len(blob) % 4:
        blob.append(0)
    image_view = len(views)
    views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(image)})
    blob.extend(image)
    doc = {'asset': {'version': '2.0'}, 'buffers': [{'byteLength': len(blob)}], 'bufferViews': views,
           'accessors': accessors, 'meshes': [{'primitives': [{'attributes': {'POSITION': pos, 'WEIGHTS_0': weight, 'JOINTS_0': joint}, 'indices': index, 'material': 0}]}],
           'nodes': [{'mesh': 0, 'skin': 0}, {'children':[2]}, {}], 'skins': [{'joints': [1,2]}],
           'animations': [{'samplers': [{'input': times, 'output': rotations}], 'channels': [{'sampler': 0, 'target': {'node': 1 if root_move else 2, 'path': 'rotation'}}]}],
           'images': [{'bufferView': image_view, 'mimeType': 'image/png'}], 'textures': [{'sampler': 0, 'source': 0}],
           'samplers': [{'magFilter': 9728 if nearest else 9729, 'minFilter': 9728}],
           'materials': [{'pbrMetallicRoughness': {'roughnessFactor': 1, 'metallicFactor': 1 if metallic else 0, 'baseColorTexture': {'index': 0}}}]}
    if front_source:
        while len(blob) % 4:
            blob.append(0)
        view = len(views)
        front = front_source.read_bytes()
        views.append({'buffer':0,'byteOffset':len(blob),'byteLength':len(front)})
        blob.extend(front)
        doc['images'].append({'bufferView':view,'mimeType':'image/png'})
        doc['textures'].append({'sampler':0,'source':1})
        mat = copy.deepcopy(doc['materials'][0])
        mat['pbrMetallicRoughness']['baseColorTexture']['index'] = 1
        doc['materials'].append(mat)
        if use_front:
            # Two open material regions together form the closed tetrahedron.
            primitive = doc['meshes'][0]['primitives'][0]
            primitive['indices'] = add([(i,) for i in indices[:6]],5123,'SCALAR','H')
            second = copy.deepcopy(primitive)
            second.update(indices=add([(i,) for i in indices[6:]],5123,'SCALAR','H'),material=1)
            doc['meshes'][0]['primitives'].append(second)
        doc['buffers'][0]['byteLength'] = len(blob)
    payload = json.dumps(doc).encode()
    payload += b' ' * (-len(payload) % 4)
    blob.extend(b'\0' * (-len(blob) % 4))
    result = struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(payload) + 8 + len(blob))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(result + struct.pack('<I4s', len(payload), b'JSON') + payload + struct.pack('<I4s', len(blob), b'BIN\0') + blob)


class VolumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.brief, self.manifest, self.profile, self.handoff = (self.root / name for name in ['brief.json','assets-manifest.json','profile.json','handoff.json'])
        self.source, self.raw, self.reference = (self.root / name for name in ['fish_nobg.png','fish_raw.png','style.png'])
        image = Image.new('RGBA', (8,4), (0,0,0,0))
        for x in range(1,7):
            image.putpixel((x,2), (23,81,123,255))
        image.save(self.source)
        Image.new('RGB',(8,4),'white').save(self.raw)
        image.save(self.reference)
        self.profile_data = json.loads((volume.REPO_ROOT / 'resources/volume-fish/profile.schema.example.json').read_text(encoding='utf-8'))
        self.profile_data.update(profile_review_status='approved')
        self.profile_data['style']['reference_image'] = str(self.reference)
        self.brief_data = {'brief_meta':{'contract_version':1,'frozen_at':'2026-10-13T00:00:00Z'},'project': {'art_direction': 'pixel art, limited palette', 'art_tokens': {'texture_filter':'nearest'}}, 'assets': [{'name':'fish','id':'fish_id','type':'character','real_length_cm':30}]}
        self.manifest_data = {'manifest_version':1,'brief':str(self.brief),'assets': {'fish': {'review':{'status':'accepted','source':'pipeline'},'stages':[
            {'task_id':'fish.image.generate','stage':'image.raw','status':'done','role':'pipeline_intermediate','path_repo':str(self.raw)},
            {'task_id':'fish.image.remove-bg','stage':'image.nobg','status':'done','role':'gameplay_ready','path_repo':str(self.source)}]}}}
        self.save_inputs()

    def tearDown(self):
        self.tmp.cleanup()

    def test_native_root_attachment_requires_paired_authored_roots(self):
        data=copy.deepcopy(self.profile_data)
        data['rest_shape_revision']={'source_handoff':'old.json','source_handoff_sha256':'a'*64,
            'source_blend':'base.blend','source_glb':'base.glb','blend_sha256':'b'*64,'glb_sha256':'c'*64,
            'stations':[[0,.1,.1],[1,.1,.1]]}
        data['fins']=[{'name':'Pectoral','polygon':[[.4,.5],[.6,.5],[.5,.7]],
            'anchor':[.5,.5],'tip':[.5,.7],'paired':True,'root_depth':.03,'tip_depth':.1,
            'thickness':.001,'amplitude':.01,'phase':0,'axis':[1,0,0],
            'root_attachment':{'mode':'body_surface','root_band':.05,'blend_end':.35,'inset':.0008}}]
        volume.validate_profile(data,self.profile)
        data['fins'][0]['paired']=False
        with self.assertRaisesRegex(volume.VolumeError,'paired fin roots'):
            volume.validate_profile(data,self.profile)

    def test_static_mouth_with_single_skin_keeps_multisource_atlas_requirement(self):
        data=copy.deepcopy(self.profile_data)
        data['oral_jaws']={'corner':[.7,.5],'front':[.85,.5],'gap':.001,'upper_retraction':0,'lower_projection':0,'lip_bevel':0,'front_pigment_band':[.3,.7]}
        volume.validate_profile(data,self.profile)
        data['head_projection']=self.projection()
        with self.assertRaisesRegex(volume.VolumeError,'multi-source'):
            volume.validate_profile(data,self.profile)
        data['head_projection']['continuous_atlas']=True
        volume.validate_profile(data,self.profile)

    def test_lateral_head_and_fin_geometry_reject_invalid_parameters(self):
        self.profile_data['cephalofoil'] = {'center_v': .55, 'sections': [[-.2,.90,.97,.01],[-.1,.89,.98,.02],[0,.88,.97,.02],[.1,.89,.98,.02],[.2,.90,.97,.01]]}
        volume.validate_profile(self.profile_data,self.profile)
        for field,value in [('center_v',float('nan')),('sections',[[0,.9,.8,.02]]*5)]:
            invalid=copy.deepcopy(self.profile_data);invalid['cephalofoil'][field]=value
            with self.subTest(field=field), self.assertRaises(volume.VolumeError):volume.validate_profile(invalid,self.profile)
        for value in [-.1,1.1]:
            invalid=copy.deepcopy(self.profile_data)
            invalid['fins']=[{'name':'Pectoral','polygon':[[.4,.5],[.6,.5],[.5,.7]],'anchor':[.5,.5],'tip':[.5,.7],'paired':True,'root_depth':.03,'tip_depth':.1,'thickness':.001,'amplitude':.01,'phase':0,'axis':[1,0,0],'vertical_scale':value}]
            with self.subTest(scale=value), self.assertRaises(volume.VolumeError):volume.validate_profile(invalid,self.profile)

    def test_lateral_head_requires_clay_review_evidence(self):
        self.profile_data['cephalofoil'] = {'center_v': .55, 'sections': [[-.2,.90,.97,.01],[-.1,.89,.98,.02],[0,.88,.97,.02],[.1,.89,.98,.02],[.2,.90,.97,.01]]}
        self.save_inputs();self.plan()
        with patch('volume_fish.subprocess.run',side_effect=self.successful_builder):
            self.invoke('build','--handoff',self.handoff,'--blender',sys.executable)
            result,data=self.invoke('render','--handoff',self.handoff,'--blender',sys.executable)
        self.assertEqual(result.exit_code,1)
        self.assertIn('clay', str(data['failures']))
        self.assertEqual(self.invoke('accept','--handoff',self.handoff,'--note','Test')[0].exit_code,1)

    def save_inputs(self):
        for path,data in [(self.brief,self.brief_data),(self.manifest,self.manifest_data),(self.profile,self.profile_data)]:
            path.write_text(json.dumps(data))

    def invoke(self, *args):
        result = CliRunner().invoke(cli, ['volume', *map(str,args), '--json'])
        data = json.loads(result.output)
        self.assertEqual(set(data), set(RESPONSE_FIELDS))
        return result,data

    def plan(self):
        return self.invoke('plan','--brief',self.brief,'--assets-manifest',self.manifest,'--asset','fish','--profile',self.profile,'--output',self.handoff)

    def successful_builder(self, argv, **kwargs):
        self.assertNotIn('shell', kwargs)
        self.assertEqual(argv[1:4], ['--background','--python',str(volume.BUILDER)])
        handoff = volume.read_json(self.handoff)
        output = handoff['outputs']
        render = '--render-only' in argv
        if not render:
            make_glb(Path(output['glb']), self.source)
            Path(output['blend']).write_bytes(b'fixture blend')
        report = {'ok':True,'status':'done','next_action':'human_review','run_id':handoff['run_id'],
                  'source_sha256':handoff['source']['sha256'], 'profile_sha256':handoff['profile_snapshot']['sha256'],
                  'style_reference_sha256':handoff['style_contract']['style_reference_sha256'],
                  'glb_sha256':volume.sha(Path(output['glb'])), 'blend_sha256':volume.sha(Path(output['blend'])), 'checks': {key:True for key in volume.CHECKS}, 'style_visual_review':'pending','failures':[]}
        if render:
            report['review'] = {}
            for view in ['side','front','oblique','style_comparison']:
                path = Path(output['review_dir']) / (view + '.png')
                path.parent.mkdir(parents=True,exist_ok=True)
                Image.new('RGB',(8,4)).save(path)
                report['review'][view] = str(path)
        volume.write_json(Path(output['render_report' if render else 'validation_report']),report)
        return subprocess.CompletedProcess(argv,0,'','')

    def test_success_plan_build_validate_render_contract_and_human_gate(self):
        result,data = self.plan()
        self.assertEqual(result.exit_code,0,result.output)
        self.assertEqual((data['status'],data['next_action']),('pending','run'))
        with patch('volume_fish.subprocess.run',side_effect=self.successful_builder):
            result,data = self.invoke('build','--handoff',self.handoff,'--blender',sys.executable)
            self.assertEqual(result.exit_code,0,result.output)
            self.assertEqual((data['status'],data['next_action']),('done','human_review'))
            self.assertEqual(data['summary']['style_visual_review'],'pending')
            before = self.handoff.read_bytes()
            result,data = self.invoke('validate','--handoff',self.handoff)
            self.assertEqual(result.exit_code,0,result.output)
            self.assertEqual(before,self.handoff.read_bytes())
            result,data = self.invoke('render','--handoff',self.handoff,'--blender',sys.executable)
            self.assertEqual(result.exit_code,0,result.output)
        self.assertEqual(len(data['summary']['review']),4)
        result,data = self.invoke('validate','--handoff',self.handoff)
        self.assertEqual(result.exit_code,0,result.output)

    def projection(self):
        return {'start_u':1,'end_u':0,'normal_threshold':.95,'side_limit':.1,
                'source_rect':[0,0,1,1], 'model_depth_range':[-.5,.5], 'model_v_range':[0,1]}

    def test_continuous_atlas_rejects_invalid_blend_intervals(self):
        data=copy.deepcopy(self.profile_data)
        data['head_projection']=dict(self.projection(),continuous_atlas=True,blend_end_u=.80)
        volume.validate_profile(data,self.profile)
        for end in (float('nan'),.0,.99):
            invalid=copy.deepcopy(data);invalid['head_projection']['blend_end_u']=end
            with self.subTest(end=end),self.assertRaises(volume.VolumeError):volume.validate_profile(invalid,self.profile)
        invalid=copy.deepcopy(data);invalid['head_projection']['continuous_atlas']='true'
        with self.assertRaises(volume.VolumeError):volume.validate_profile(invalid,self.profile)

    def test_head_vertical_offsets_require_ordered_finite_stations(self):
        data=copy.deepcopy(self.profile_data)
        data['head_projection']=dict(self.projection(),vertical_offsets=[[.6,-.03],[.8,.05]])
        volume.validate_profile(data,self.profile)
        for rows in ([[.6,0]],[[.8,0],[.6,0]],[[.6,0],[.6,.1]],[[.6,0],[.8,float('nan')]],[[.6,0],[.8,.3]]):
            invalid=copy.deepcopy(data);invalid['head_projection']['vertical_offsets']=rows
            with self.subTest(rows=rows),self.assertRaises(volume.VolumeError):volume.validate_profile(invalid,self.profile)

    def test_derived_texture_must_be_declared_and_pixel_identical(self):
        derived=self.root/'derived.png';Image.new('RGBA',(8,4),(30,70,90,255)).save(derived)
        glb=self.root/'derived.glb';make_glb(glb,self.source,front_source=derived)
        with self.assertRaises(volume.VolumeError):volume.glb_checks(glb,self.source)
        volume.glb_checks(glb,self.source,derived_source_paths=(derived,))
        Image.new('RGBA',(8,4),(31,70,90,255)).save(derived)
        with self.assertRaises(volume.VolumeError):volume.glb_checks(glb,self.source,derived_source_paths=(derived,))

    def test_head_projection_valid_boundaries_and_invalid_donors(self):
        valid = self.projection()
        data = copy.deepcopy(self.profile_data)
        data['head_projection'] = valid
        volume.validate_profile(data,self.profile)
        invalid = [dict(valid,start_u=0),dict(valid,source_rect=[0,0,1.01,1]),dict(valid,model_v_range=[.8,.2]),
                   dict(valid,normal_threshold=.96),dict(valid,normal_threshold=-1.01),dict(valid,side_limit=0),dict(valid,start_u=float('nan')),
                   dict(valid,python='arbitrary code')]
        for head in invalid:
            with self.subTest(head=head), self.assertRaises(volume.VolumeError):
                volume.validate_profile({**data,'head_projection':head},self.profile)
        with self.assertRaises(volume.VolumeError):
            volume.validate_profile({**self.profile_data,'head_uv':{}},self.profile)

    def eye_patch(self):
        return {'center':[.8,.4], 'radius':.01, 'depth':.03, 'mode':'surface_patch',
                'source_rect':[.7,.3,.9,.5], 'thickness':.001, 'surface_offset':.0005}

    def test_eye_patch_and_legacy_profiles_are_compatible_without_mutation(self):
        for eyes in [None, {'center':[.8,.4], 'radius':.01, 'depth':.03},
                     dict(self.eye_patch(),source_rect=[0,0,1,1],thickness=.0001,surface_offset=0),
                     dict(self.eye_patch(),thickness=.01,surface_offset=.003),
                     dict(self.eye_patch(),radius=.05,source_rect=[0,0,.5,1])]:
            with self.subTest(eyes=eyes):
                data = {**self.profile_data,'eyes':eyes}
                before = copy.deepcopy(data)
                volume.validate_profile(data,self.profile)
                self.assertEqual(data,before)

    def test_eye_patch_rejects_derived_height_overflow_and_geometry_budget(self):
        for rect in [[0,0,1e-320,1],[0,0,5e-324,1],[0,0,.01,1]]:
            with self.subTest(rect=rect), self.assertRaisesRegex(volume.VolumeError,'Derived eye patch half height'):
                volume.validate_profile({**self.profile_data,'eyes':dict(self.eye_patch(),source_rect=rect)},self.profile)
        # Normalized rectangles also depend on the native image aspect ratio.
        with self.assertRaisesRegex(volume.VolumeError,'Derived eye patch half height'):
            volume.validate_profile({**self.profile_data,'source_aspect_ratio':.1,
                                     'eyes':dict(self.eye_patch(),source_rect=[0,0,1,1])},self.profile)

    def test_eye_patch_rejects_missing_unknown_and_ignored_fields(self):
        valid = self.eye_patch()
        cases = [{k:v for k,v in valid.items() if k!=missing} for missing in valid]
        cases += [dict(valid,unknown=True), dict(valid,mode='side_sphere'), dict(valid,mode='legacy'),
                  dict(valid,mode=None), dict(valid,mode=True)]
        base = {key:valid[key] for key in ['center','radius','depth']}
        cases += [{**base,key:valid[key]} for key in ['source_rect','thickness','surface_offset']]
        for eyes in cases:
            with self.subTest(eyes=eyes), self.assertRaises(volume.VolumeError):
                volume.validate_profile({**self.profile_data,'eyes':eyes},self.profile)

    def test_eye_patch_rejects_nonfinite_invalid_rectangles_and_offsets(self):
        cases = [('source_rect',v) for v in [[0,0,0,1],[.8,0,.2,1],[0,.8,1,.2],[-.01,0,1,1],
                                            [0,0,1.01,1],[0,0,1],[0,0,True,1],[0,0,float('nan'),1]]]
        cases += [(key,value) for key,values in {
            'thickness':[0,.000099,.01001,float('inf'),float('nan'),True],
            'surface_offset':[-.0001,.00301,float('-inf'),float('nan'),False],
            'radius':[float('nan')], 'depth':[float('inf')], 'center':[[.5,float('nan')]],
        }.items() for value in values]
        for key,value in cases:
            with self.subTest(key=key,value=value), self.assertRaises(volume.VolumeError):
                volume.validate_profile({**self.profile_data,'eyes':dict(self.eye_patch(),**{key:value})},self.profile)

    def test_head_uv_patch_accepts_budget_limits_and_exact_donor_edges(self):
        polygon = [[.3+.1*math.cos(i*math.tau/128), .3+.1*math.sin(i*math.tau/128)] for i in range(128)]
        for patches in [[], [{'polygon':[[0,0],[.5,0],[.5,.5]],'offset':[.5,.5]}],
                        [{'polygon':polygon,'offset':[.2,.2]}]*16]:
            with self.subTest(count=len(patches)):
                data = {**self.profile_data,'head_projection':dict(self.projection(),uv_patches=patches)}
                before = copy.deepcopy(data)
                volume.validate_profile(data,self.profile)
                self.assertEqual(data,before)

    def test_head_uv_patch_rejects_invalid_shapes_budgets_and_donor_escape(self):
        patch = {'polygon':[[.2,.2],[.4,.2],[.4,.4]],'offset':[0,0]}
        cases = [None,{},[patch]*17,[dict(patch,unknown=True)],
                 [{'polygon':patch['polygon']}],[{'offset':[0,0]}],
                 [dict(patch,polygon=[[.2,.2]]*2)],[dict(patch,polygon=[[.2,.2]]*129)],
                 [dict(patch,polygon=[[0,0],[1.01,0],[0,1]])],
                 [dict(patch,polygon=[[0,0],[1,0],[0,float('nan')]])]]
        cases += [[dict(patch,offset=offset)] for offset in [[0],[0,0,0],[1.01,0],[float('nan'),0],
                                                            [0,float('inf')],[False,0],[.7,0],[-.3,0]]]
        for patches in cases:
            with self.subTest(patches=patches), self.assertRaises(volume.VolumeError):
                volume.validate_profile({**self.profile_data,'head_projection':dict(self.projection(),uv_patches=patches)},self.profile)

    def add_plan(self, content):
        plan = self.root/'prompt-plan.json'
        volume.write_json(plan, {'plan':content})
        self.manifest_data['assets']['fish']['stages'].insert(0, {'stage':'prompt.plan','status':'done','path_repo':str(plan)})
        self.save_inputs()
        return plan

    def test_generation_reference_explicit_and_changed_reference(self):
        generation_ref = self.root/'generation-reference.png'
        Image.new('RGB',(3,5),'blue').save(generation_ref)
        self.add_plan({'requires_reference_image':True,'reference_image':str(generation_ref)})
        result,data = self.plan()
        self.assertEqual(result.exit_code,0,result.output)
        source = data['summary']['source']
        self.assertEqual(source['generation_reference_image'],str(generation_ref))
        self.assertNotEqual(source['generation_reference_sha256'],volume.sha(self.reference))
        Image.new('RGB',(3,5),'red').save(generation_ref)
        with patch('volume_fish.subprocess.run') as run:
            result,_ = self.invoke('build','--handoff',self.handoff,'--blender',sys.executable)
            self.assertEqual(result.exit_code,1)
            run.assert_not_called()

    def test_required_generation_reference_requires_successful_matching_argv(self):
        plan = self.add_plan({'requires_reference_image':True,'reference_image':None})
        ledger = self.root/'pipeline.json'
        command = shlex.join(['python','gamefactory.py','image','generate','--plan-file',str(plan),'--output',str(self.raw),'--reference-image',str(self.reference)])
        task = {'id':'fish.image.generate','asset':'fish','step':'image.generate','status':'done','result':{'exit_code':0},'command':command}
        with patch('volume_fish.default_paths_for_brief',return_value={'manifest':ledger}):
            result,_ = self.plan()
            self.assertEqual(result.exit_code,1)
            for invalid in [dict(task,status='failed'),dict(task,asset='other'),dict(task,command=command.replace(str(self.raw),str(self.source)))]:
                volume.write_json(ledger,{'tasks':[invalid]})
                result,_ = self.plan()
                self.assertEqual(result.exit_code,1)
            volume.write_json(ledger,{'tasks':[task]})
            result,data = self.plan()
            self.assertEqual(result.exit_code,0,result.output)
            self.assertEqual(data['summary']['source']['generation_reference_evidence']['kind'],'pipeline_task')
            Image.new('RGB',(8,4),'red').save(self.reference)
            with self.assertRaises(volume.VolumeError):
                volume.fresh_handoff(self.handoff)
        with self.assertRaises(volume.VolumeError):
            volume.generation_path('../../outside.png')

    def test_surface_sections_reject_disordered_and_degenerate_donors(self):
        self.profile_data['dorsal_projection'] = {
            'start_u':.1,'end_u':.9,'normal_threshold':.5,
            'source_rect':[.1,.2,.9,.8],'model_depth_range':[-.1,.1],
            'sections':[[.1,.1,.4,.6,.02],[.3,.3,.3,.7,.06],
                        [.6,.6,.3,.7,.05],[.9,.9,.45,.55,.01]]}
        volume.validate_profile(self.profile_data,self.profile)
        for column,value in [(0,.1),(2,.8),(4,0),(4,float('nan'))]:
            invalid=copy.deepcopy(self.profile_data)
            invalid['dorsal_projection']['sections'][1][column]=value
            with self.subTest(column=column,value=value),self.assertRaises(volume.VolumeError):
                volume.validate_profile(invalid,self.profile)

    def test_two_original_textures_on_one_closed_mesh_and_unused_front_rejected(self):
        front = self.root/'front.png'
        Image.new('RGBA',(3,7),(120,20,45,255)).save(front)
        glb = self.root/'two-source.glb'
        make_glb(glb,self.source,front_source=front)
        self.assertTrue(all(volume.glb_checks(glb,self.source,front).values()))
        with self.assertRaises(volume.VolumeError):
            volume.glb_checks(glb,self.source)
        make_glb(glb,self.source,front_source=front,use_front=False)
        with self.assertRaises(volume.VolumeError):
            volume.glb_checks(glb,self.source,front)
        Image.new('RGBA',(3,7),(80,20,45,255)).save(front)
        with self.assertRaises(volume.VolumeError):
            volume.glb_checks(glb,self.source,front)

    def test_front_flags_review_and_freshness(self):
        args = ['plan','--brief',self.brief,'--assets-manifest',self.manifest,'--asset','fish','--profile',self.profile,'--output',self.handoff]
        result,_ = self.invoke(*args,'--front-asset','fish')
        self.assertEqual(result.exit_code,1)
        self.profile_data['head_projection'] = self.projection()
        self.save_inputs()
        result,_ = self.invoke(*args)
        self.assertEqual(result.exit_code,1)
        front = self.root/'front-ledger.json'
        ledger = copy.deepcopy(self.manifest_data)
        front_brief = self.root/'front-brief.json'
        front_brief_data = copy.deepcopy(self.brief_data)
        front_brief_data['project']['view'] = 'front'
        volume.write_json(front_brief, front_brief_data)
        ledger['brief'] = str(front_brief)
        ledger['assets']['fish']['review']['status'] = 'pending'
        volume.write_json(front,ledger)
        front_args = ['--front-assets-manifest',front,'--front-asset','fish']
        result,_ = self.invoke(*args,*front_args)
        self.assertEqual(result.exit_code,1)
        ledger['assets']['fish']['review']['status'] = 'accepted'
        volume.write_json(front,ledger)
        result,_ = self.invoke(*args,*front_args)
        self.assertEqual(result.exit_code,0,result.output)
        data = volume.fresh_handoff(self.handoff)
        self.assertEqual(data['front_source_image'],str(self.source))
        ledger['assets']['fish']['review']['status'] = 'pending'
        volume.write_json(front,ledger)
        with self.assertRaises(volume.VolumeError):
            volume.fresh_handoff(self.handoff)

    def test_front_source_rejects_side_and_three_quarter_briefs(self):
        self.profile_data['head_projection'] = self.projection()
        for view in ('side', 'three_quarter'):
            with self.subTest(view=view):
                self.brief_data['project']['view'] = view
                self.save_inputs()
                result, data = self.invoke('plan', '--brief', self.brief,
                    '--assets-manifest', self.manifest, '--asset', 'fish',
                    '--profile', self.profile, '--output', self.handoff,
                    '--front-assets-manifest', self.manifest, '--front-asset', 'fish')
                self.assertEqual(result.exit_code, 1)
                self.assertEqual(data['status'], 'blocked')
                self.assertIn('project.view=front', data['failures'][0]['message'])
                self.assertFalse(self.handoff.exists())

    def test_accept_requires_fresh_render_records_operator_and_rebuild_resets(self):
        self.plan()
        with patch('volume_fish.subprocess.run',side_effect=self.successful_builder):
            self.invoke('build','--handoff',self.handoff,'--blender',sys.executable)
            result,_ = self.invoke('accept','--handoff',self.handoff,'--note','reviewed')
            self.assertEqual(result.exit_code,1)
            self.invoke('render','--handoff',self.handoff,'--blender',sys.executable)
            result,_ = self.invoke('accept','--handoff',self.handoff,'--note','  ')
            self.assertEqual(result.exit_code,1)
            handoff = volume.read_json(self.handoff)
            front = Path(handoff['outputs']['review_dir'])/'front.png'
            original = front.read_bytes()
            front.unlink()
            result,_ = self.invoke('accept','--handoff',self.handoff,'--note','reviewed')
            self.assertEqual(result.exit_code,1)
            front.write_bytes(original)
            result,data = self.invoke('accept','--handoff',self.handoff,'--note','Reviewed source, reference and all angles')
            self.assertEqual(result.exit_code,0,result.output)
            self.assertEqual(data['next_action'],'none')
            self.assertEqual(data['summary']['style_review']['reviewer'],'command_operator')
            self.assertEqual(volume.read_json(Path(handoff['outputs']['validation_report']))['style_visual_review'],'pending')
            result,data = self.invoke('validate','--handoff',self.handoff)
            self.assertEqual(result.exit_code,0,result.output)
            self.assertEqual(data['next_action'],'none')
            Image.new('RGB',(8,4),'red').save(front)
            result,_ = self.invoke('validate','--handoff',self.handoff)
            self.assertEqual(result.exit_code,1)
            # A rerender can repair changed images, while clearing earlier approval.
            result,data = self.invoke('render','--handoff',self.handoff,'--blender',sys.executable)
            self.assertEqual(result.exit_code,0,result.output)
            self.assertEqual(data['next_action'],'human_review')
            self.assertNotIn('style_review',volume.read_json(self.handoff))
            self.invoke('accept','--handoff',self.handoff,'--note','Reviewed again')
            result,data = self.invoke('build','--handoff',self.handoff,'--blender',sys.executable)
            self.assertEqual(result.exit_code,0,result.output)
            self.assertEqual(data['next_action'],'human_review')

    def test_unfrozen_brief_is_rejected(self):
        self.brief_data.pop('brief_meta')
        self.save_inputs()
        result,data = self.plan()
        self.assertEqual(result.exit_code,1)
        self.assertIn('frozen Brief',data['failures'][0]['message'])

    def test_shard_length_and_identity_are_resolved_and_frozen(self):
        shard = self.root/'assets/fish/spec.json'
        shard.parent.mkdir(parents=True)
        spec = self.brief_data['assets'][0]
        shard.write_text(json.dumps(spec))
        self.brief_data['assets'] = [{'id':'fish_id','name':'fish','path':'assets/fish/spec.json'}]
        self.save_inputs()
        result,data = self.invoke('plan','--brief',self.brief,'--assets-manifest',self.manifest,'--asset','fish_id','--profile',self.profile,'--output',self.handoff)
        self.assertEqual(result.exit_code,0,result.output)
        spec['real_length_cm'] = 60
        shard.write_text(json.dumps(spec))
        with patch('volume_fish.subprocess.run') as run:
            result,data = self.invoke('build','--handoff',self.handoff,'--blender',sys.executable)
            self.assertEqual(result.exit_code,1)
            self.assertIn('shard changed',data['failures'][0]['message'])
            run.assert_not_called()
        self.handoff.unlink()
        result,data = self.plan()
        self.assertEqual(result.exit_code,1)
        self.assertIn('real_length_cm differs',data['failures'][0]['message'])

    def test_invalid_json_still_emits_contract(self):
        self.profile.write_text('{')
        result,data = self.plan()
        self.assertEqual(result.exit_code,1)
        self.assertEqual(data['status'],'blocked')

    def test_unreviewed_or_local_replacement_source_blocks(self):
        for status,source in [('pending','pipeline'),('accepted','local_file')]:
            with self.subTest(status=status,source=source):
                self.manifest_data['assets']['fish']['review'] = {'status':status,'source':source}
                self.save_inputs()
                result,data = self.plan()
                self.assertEqual(result.exit_code,1)
                self.assertEqual((data['status'],data['next_action']),('blocked','fix_input'))
                self.assertFalse(self.handoff.exists())

    def test_missing_generation_blocks(self):
        self.manifest_data['assets']['fish']['stages'] = self.manifest_data['assets']['fish']['stages'][1:]
        self.save_inputs()
        result,data = self.plan()
        self.assertEqual(result.exit_code,1)
        self.assertIn('image.generate',data['failures'][0]['message'])

    def test_source_profile_brief_reference_changes_block_before_subprocess(self):
        for field in ['source','profile','brief','reference']:
            with self.subTest(field=field):
                self.save_inputs()
                if self.handoff.exists(): self.handoff.unlink()
                original = getattr(self,field).read_bytes()
                result,_ = self.plan()
                self.assertEqual(result.exit_code,0,result.output)
                getattr(self,field).write_bytes(original+b' ')
                with patch('volume_fish.subprocess.run') as run:
                    result,data = self.invoke('build','--handoff',self.handoff,'--blender',sys.executable)
                    self.assertEqual(result.exit_code,1)
                    self.assertEqual(data['status'],'blocked')
                    run.assert_not_called()
                getattr(self,field).write_bytes(original)

    def test_revoked_review_blocks_build(self):
        self.plan()
        self.manifest_data['assets']['fish']['review']['status'] = 'pending'
        self.save_inputs()
        with patch('volume_fish.subprocess.run') as run:
            result,_ = self.invoke('build','--handoff',self.handoff,'--blender',sys.executable)
            self.assertEqual(result.exit_code,1)
            run.assert_not_called()

    def test_profile_code_unknown_fields_and_traversal_are_rejected(self):
        for mutation in [{'python':'import os'}, {'style':{**self.profile_data['style'],'reference_image':'../style.png'}},
                         {'style':{**self.profile_data['style'],'pixel_art':False}}, {'profile_review_status':'draft'}]:
            with self.subTest(mutation=mutation):
                data = {**self.profile_data,**mutation}
                self.profile.write_text(json.dumps(data))
                result,_ = self.plan()
                self.assertEqual(result.exit_code,1)
                self.assertFalse(self.handoff.exists())

    def test_output_traversal_and_symlink_are_rejected(self):
        self.plan()
        data = volume.read_json(self.handoff)
        data['outputs']['glb'] = str(self.root.parent/'escape.glb')
        volume.write_json(self.handoff,data)
        with patch('volume_fish.subprocess.run') as run:
            result,_ = self.invoke('build','--handoff',self.handoff,'--blender',sys.executable)
            self.assertEqual(result.exit_code,1)
            run.assert_not_called()
        data = volume.read_json(self.handoff)
        data['outputs'] = volume.expected_outputs(self.handoff)
        volume.write_json(self.handoff,data)
        target = self.root/'redirected'
        target.mkdir()
        Path(data['outputs']['directory']).symlink_to(target,target_is_directory=True)
        with patch('volume_fish.subprocess.run') as run:
            result,_ = self.invoke('build','--handoff',self.handoff,'--blender',sys.executable)
            self.assertEqual(result.exit_code,1)
            run.assert_not_called()

    def test_failure_and_stale_reports_never_become_done(self):
        self.plan()
        for result in [subprocess.CompletedProcess([],1,'','failure'),subprocess.CompletedProcess([],0,'','')]:
            with self.subTest(code=result.returncode), patch('volume_fish.subprocess.run',return_value=result):
                response,data = self.invoke('build','--handoff',self.handoff,'--blender',sys.executable)
                self.assertEqual(response.exit_code,1)
                self.assertNotEqual(data['status'],'done')
                self.assertNotEqual(volume.read_json(self.handoff)['status'],'done')

    def test_real_glb_checks_reject_open_skin_loop_and_blur(self):
        glb = self.root/'fish.glb'
        for option in ['loop','nearest','closed','weights']:
            with self.subTest(option=option):
                make_glb(glb,self.source,**{option:False})
                with self.assertRaises(volume.VolumeError):
                    volume.glb_checks(glb,self.source)
        for option in ['metallic','root_move']:
            with self.subTest(option=option):
                make_glb(glb,self.source,**{option:True})
                with self.assertRaises(volume.VolumeError):
                    volume.glb_checks(glb,self.source)
        make_glb(glb,self.source)
        self.assertTrue(all(volume.glb_checks(glb,self.source).values()))

    def test_modified_output_fails_validation(self):
        self.plan()
        with patch('volume_fish.subprocess.run',side_effect=self.successful_builder):
            result,_ = self.invoke('build','--handoff',self.handoff,'--blender',sys.executable)
            self.assertEqual(result.exit_code,0,result.output)
        data = volume.read_json(self.handoff)
        with Path(data['outputs']['glb']).open('ab') as f:f.write(b'changed')
        result,_ = self.invoke('validate','--handoff',self.handoff)
        self.assertEqual(result.exit_code,1)

    def test_windows_relative_separator_and_repo_reference(self):
        child=self.root/'nested';child.mkdir();(child/'x.png').write_bytes(self.reference.read_bytes())
        self.assertEqual(volume.resolve_file('nested\\x.png',self.root),child/'x.png')
        with patch('volume_fish.REPO_ROOT',self.root):
            self.assertEqual(volume.resolve_file('repo://nested/x.png',self.root),child/'x.png')
        with self.assertRaises(volume.VolumeError):
            volume.resolve_file('nested\\..\\style.png',self.root)


if __name__ == '__main__':
    unittest.main()
