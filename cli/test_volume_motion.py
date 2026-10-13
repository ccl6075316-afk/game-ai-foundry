"""Existing-model motion gates: real skins, bounds, provenance and fixed outputs."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from click.testing import CliRunner
from PIL import Image

from gamefactory import cli
from test_volume_fish import make_glb
import volume_motion as motion
from volume_fish import VolumeError, glb_document, sha
from workflow.contract import RESPONSE_FIELDS


def edit_glb(path, mutate, mutate_blob=None):
    doc,blob = glb_document(path)
    mutate(doc)
    if mutate_blob:
        blob = bytearray(blob)
        mutate_blob(doc,blob)
    data = json.dumps(doc).encode()
    data += b' ' * (-len(data)%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(data)+len(blob))+
                     struct.pack('<I4s',len(data),b'JSON')+data+struct.pack('<I4s',len(blob),b'BIN\0')+blob)


class MotionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.models,self.reviews = self.root/'models',self.root/'reviews'
        self.models.mkdir();self.reviews.mkdir()
        self.runtime = self.root/'VolumeFishMotion.gd'
        self.runtime.write_text('extends RefCounted\n# fixed bundled test fixture\n')
        self.runtime_patch = patch('volume_motion.RUNTIME',self.runtime)
        self.runtime_patch.start()
        self.source = self.root/'native.png'
        Image.new('RGBA',(8,4),(120,140,160,255)).save(self.source)
        self.evidence = self.root/'existing-validation.json'
        self.evidence.write_text(json.dumps({'status':'done','ok':True,'review':'prior model review'}))
        self.handoff,self.profiles = self.root/'motion.handoff.json',[]
        for species in sorted(motion.SPECIES):
            model = self.models/(species+'.glb')
            make_glb(model,self.source)
            def skeleton(doc):
                doc['nodes'] = [{'mesh':0,'skin':0},{'name':'Head','children':[2]},
                                {'name':'Spine','children':[3]},{'name':'Mid','children':[4]},{'name':'Tail'}]
                doc['skins'][0]['joints'] = [1,2,3,4]
                doc['animations'][0]['name'] = 'Animation'
            edit_glb(model,skeleton)
            receipt = {'schema_version':1,'kind':'existing_volume_model_review','species':species,'model_sha256':sha(model),
                       'review_status':'accepted','reviewer':'command_operator','note':'Reviewed unchanged existing GLB.',
                       'evidence':[str(self.evidence)]}
            (self.reviews/(species+'.validation.json')).write_text(json.dumps(receipt))
            profile = self.root/(species+'.json')
            profile.write_text(json.dumps(self.profile(species)))
            self.profiles.append(profile)

    def tearDown(self):
        self.runtime_patch.stop()
        self.temp.cleanup()

    def profile(self,species='piranha'):
        actions = {name:{'radius_scale':.6 if name=='Turn' else 1,'bend_radians':.24 if name=='Turn' else .08,
                         'vertical_sign':{'Swim':0,'Turn':0,'Ascend':1,'Dive':-1}[name],'clip_speed':1}
                   for name in ['Swim','Turn','Ascend','Dive']}
        return {'schema_version':1,'species':species,'real_length_cm':100,'head_sign':1,'base_clip':'Animation',
                'body_bones':['Head','Spine','Mid','Tail'],'tank_size_m':[6,5.1,5.8],'path_radii_m':[.7,.5],
                'vertical_amplitude_m':.3,'envelope_radius_m':2.2,'period_seconds':12,'transition_seconds':.8,
                'body_delay_seconds':.3,'base_body_gain':.5,'actions':actions,'notes':['Calibrated fixture.']}

    def invoke(self,*args):
        result = CliRunner().invoke(cli,['volume',*map(str,args),'--json'])
        data = json.loads(result.output)
        self.assertEqual(set(data),set(RESPONSE_FIELDS))
        return result,data

    def plan(self):
        args = []
        for profile in self.profiles:
            args.extend(['--profile',profile])
        return self.invoke('motion-plan',*args,'--models-dir',self.models,'--reviews-dir',self.reviews,'--output',self.handoff)

    def test_plan_build_validate_preserves_models_and_keeps_operator_review_pending(self):
        original = {p:sha(p) for p in self.models.iterdir()}
        result,data = self.plan()
        self.assertEqual(result.exit_code,0,result.output)
        self.assertEqual((data['status'],data['next_action']),('pending','run'))
        result,data = self.invoke('motion-build','--handoff',self.handoff)
        self.assertEqual(result.exit_code,0,result.output)
        handoff = json.loads(self.handoff.read_text())
        self.assertEqual(Path(handoff['outputs']['runtime']).read_bytes(),self.runtime.read_bytes())
        config = json.loads(Path(handoff['outputs']['config']).read_text())
        self.assertEqual(set(config['profiles']),motion.SPECIES)
        before = self.handoff.read_bytes()
        result,data = self.invoke('motion-validate','--handoff',self.handoff)
        self.assertEqual(result.exit_code,0,result.output)
        self.assertEqual(data['next_action'],'human_review')
        self.assertEqual(data['summary']['motion_visual_review'],'pending')
        self.assertEqual(self.handoff.read_bytes(),before)
        self.assertEqual({p:sha(p) for p in self.models.iterdir()},original)

    def test_missing_unknown_duplicate_or_reversed_body_bones_rejected(self):
        model = motion.inspect_model(self.models/'piranha.glb','Animation')
        for bones in [[],['Head','Spine','Tail'],['Head','Spine','Mid','Missing'],
                      ['Head','Spine','Mid','Mid'],['Tail','Mid','Spine','Head']]:
            with self.subTest(bones=bones),self.assertRaises(VolumeError):
                motion.validate_motion_profile({**self.profile(),'body_bones':bones},model)

    def test_nonfinite_unknown_and_over_budget_parameters_rejected(self):
        model = motion.inspect_model(self.models/'piranha.glb','Animation')
        for key,value in [('python','execute'),('period_seconds',float('nan')),('vertical_amplitude_m',float('inf')),
                          ('head_sign',True),('path_radii_m',[.1,float('nan')]),('real_length_cm',1001),
                          ('period_seconds',3),('body_delay_seconds',2.01),('base_body_gain',1.01),
                          ('tank_size_m',[101,5,5]),('notes',['x']*17)]:
            with self.subTest(key=key,value=value),self.assertRaises(VolumeError):
                motion.validate_motion_profile({**self.profile(),key:value},model)
        for change in [{'radius_scale':.29},{'clip_speed':2.01},{'bend_radians':float('nan')},
                       {'vertical_sign':True},{'code':'anything'}]:
            data = self.profile();data['actions']['Swim'].update(change)
            with self.subTest(action=change),self.assertRaises(VolumeError):
                motion.validate_motion_profile(data,model)

    def test_travelling_wave_parameters_are_optional_and_bounded(self):
        model = motion.inspect_model(self.models/'piranha.glb','Animation')
        motion.validate_motion_profile(self.profile(),model)
        motion.validate_motion_profile({**self.profile(),'body_wave_radians':.78,'body_wave_cycles':.85,'bend_bias':0},model)
        for field,value in [('body_wave_radians',1.01),('body_wave_radians',-.01),
                            ('body_wave_cycles',0),('body_wave_cycles',float('nan')),
                            ('bend_bias',-1),('bend_bias',float('inf'))]:
            with self.subTest(field=field,value=value),self.assertRaises(VolumeError):
                motion.validate_motion_profile({**self.profile(),field:value},model)

    def test_tank_and_action_relationships_are_enforced(self):
        model = motion.inspect_model(self.models/'piranha.glb','Animation')
        changes = [{'envelope_radius_m':1.99},{'tank_size_m':[5,5.1,5.8]},
                   {'tank_size_m':[6,4.9,5.8]},{'tank_size_m':[6,5.1,5]}]
        for change in changes:
            with self.subTest(change=change),self.assertRaises(VolumeError):
                motion.validate_motion_profile({**self.profile(),**change},model)
        for action,change in [('Turn',{'radius_scale':.9}),('Turn',{'bend_radians':.1}),
                              ('Swim',{'radius_scale':.9}),('Ascend',{'vertical_sign':-1})]:
            data = self.profile();data['actions'][action].update(change)
            with self.subTest(action=action,change=change),self.assertRaises(VolumeError):
                motion.validate_motion_profile(data,model)
        data=self.profile();data['tank_size_m']=[2*(.7+2.2+.02),2*(.3+2.2+.02),2*(.5+2.2+.02)]
        motion.validate_motion_profile(data,model)

    def test_real_model_skin_clip_and_bone_identity_required(self):
        model = self.models/'piranha.glb';original=model.read_bytes()
        changes = [lambda d:d.update(skins=[]),lambda d:d.update(animations=[]),
                   lambda d:d['nodes'][3].update(name='Spine'),lambda d:d['nodes'][0].pop('skin'),
                   lambda d:d['animations'][0].update(name='Other')]
        for change in changes:
            model.write_bytes(original);edit_glb(model,change)
            with self.subTest(change=change),self.assertRaises(VolumeError):
                motion.inspect_model(model,'Animation')

    def test_base_swim_requires_real_normalized_rotation_and_fixed_rest_lengths(self):
        model=self.models/'piranha.glb';original=model.read_bytes()
        def replace_keys(doc,blob,rows,kind):
            channel=doc['animations'][0]['channels'][0]
            sampler=doc['animations'][0]['samplers'][channel['sampler']]
            accessor=doc['accessors'][sampler['output']]
            view=doc['bufferViews'][accessor['bufferView']]
            accessor['type']='VEC4' if kind=='rotation' else 'VEC3'
            channel['target']['path']=kind
            data=b''.join(struct.pack('<'+'f'*len(row),*row) for row in rows)
            offset=view.get('byteOffset',0)+accessor.get('byteOffset',0)
            blob[offset:offset+len(data)]=data
        cases=[('sign-only',[(0,0,0,1),(0,0,0,-1),(0,0,0,1)],'rotation'),
               ('unnormalized',[(0,0,0,1),(0,.4,0,1),(0,0,0,1)],'rotation'),
               ('moving-rest',[(0,0,0),(0,.2,0),(0,0,0)],'translation'),
               ('scaling-rest',[(1,1,1),(1,1.2,1),(1,1,1)],'scale')]
        for name,rows,kind in cases:
            model.write_bytes(original)
            edit_glb(model,lambda _:None,lambda d,b:replace_keys(d,b,rows,kind))
            with self.subTest(case=name),self.assertRaises(VolumeError):
                motion.inspect_model(model,'Animation')

    def test_stale_inputs_runtime_receipt_and_evidence_block_build(self):
        self.assertEqual(self.plan()[0].exit_code,0)
        candidates=[self.runtime,self.profiles[0],next(self.models.iterdir()),next(self.reviews.iterdir()),self.evidence]
        for path in candidates:
            original=path.read_bytes();path.write_bytes(original+b' ')
            with self.subTest(path=path):
                result,data=self.invoke('motion-build','--handoff',self.handoff)
                self.assertEqual(result.exit_code,1,result.output)
                self.assertEqual(data['next_action'],'fix_input')
            path.write_bytes(original)

    def test_wrong_receipt_identity_and_unaccepted_review_block_plan(self):
        path=next(self.reviews.iterdir());original=path.read_bytes();receipt=json.loads(original)
        for change in [{'model_sha256':'0'*64},{'review_status':'pending'},{'reviewer':'user'},{'evidence':[]}]:
            path.write_text(json.dumps({**receipt,**change}))
            with self.subTest(change=change):
                result,_=self.plan();self.assertEqual(result.exit_code,1,result.output)
        path.write_bytes(original)

    def test_symlink_artifact_and_modified_output_paths_are_rejected(self):
        self.assertEqual(self.plan()[0].exit_code,0)
        data=json.loads(self.handoff.read_text());artifact=Path(data['outputs']['runtime']).parent
        outside=self.root/'outside';outside.mkdir();artifact.symlink_to(outside,target_is_directory=True)
        result,_=self.invoke('motion-build','--handoff',self.handoff)
        self.assertEqual(result.exit_code,1,result.output);self.assertEqual(list(outside.iterdir()),[])
        artifact.unlink()
        artifact.mkdir();sentinel=outside/'untouched.gd';sentinel.write_text('keep')
        linked_runtime=Path(data['outputs']['runtime']);linked_runtime.symlink_to(sentinel)
        result,_=self.invoke('motion-build','--handoff',self.handoff)
        self.assertEqual(result.exit_code,1,result.output);self.assertEqual(sentinel.read_text(),'keep')
        linked_runtime.unlink()
        data['outputs']['config']=str(outside/'escape.json');self.handoff.write_text(json.dumps(data))
        result,_=self.invoke('motion-build','--handoff',self.handoff)
        self.assertEqual(result.exit_code,1,result.output)

    def test_symlink_handoff_and_stale_artifacts_do_not_pass(self):
        self.assertEqual(self.plan()[0].exit_code,0)
        alias=self.root/'alias.json';alias.symlink_to(self.handoff)
        result,_=self.invoke('motion-build','--handoff',alias)
        self.assertEqual(result.exit_code,1,result.output)
        self.assertEqual(self.invoke('motion-build','--handoff',self.handoff)[0].exit_code,0)
        data=json.loads(self.handoff.read_text());runtime=Path(data['outputs']['runtime'])
        runtime.write_text('changed helper')
        result,_=self.invoke('motion-validate','--handoff',self.handoff)
        self.assertEqual(result.exit_code,1,result.output)

    def test_complete_distinct_profile_set_and_no_overwrite(self):
        original=self.profiles[1];self.profiles[1]=self.profiles[0]
        self.assertEqual(self.plan()[0].exit_code,1)
        self.profiles[1]=original
        self.assertEqual(self.plan()[0].exit_code,0)
        self.assertEqual(self.plan()[0].exit_code,1)


if __name__ == '__main__':
    unittest.main()
