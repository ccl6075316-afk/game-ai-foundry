"""Regressions for optimized execution, material binding, skin validity and snapshots."""
import contextlib
import copy
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
PORTABLE=Path(__file__).resolve().parents[1];ROOT=PORTABLE.parents[3];WORK=ROOT/'work/fish-portable-tools'
sys.path.insert(0,str(PORTABLE));sys.path.insert(0,str(PORTABLE/'tests'))
from test_asset_core import fixture
from fish_asset_spec import load_spec,input_paths,preflight,sha
from glb_io import read_glb
from pack_fish_material_atlas import write_glb
import verify_parity as parity

class GuardRegressions(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='draft-',dir=WORK);self.folder=Path(self.temp.name);self.specpath,self.candidate=fixture(self.folder);self.spec=load_spec(self.specpath);self.inputs=input_paths(self.spec)
    def tearDown(self):self.temp.cleanup()
    def verify(self):return parity.verify(self.inputs['reference_glb'],self.candidate,self.spec)
    def position(self,value):
        doc,data=read_glb(self.candidate);data=bytearray(data);acc=doc['accessors'][doc['meshes'][0]['primitives'][0]['attributes']['POSITION']];view=doc['bufferViews'][acc['bufferView']];struct.pack_into('<f',data,view.get('byteOffset',0)+acc.get('byteOffset',0),value);write_glb(self.candidate,doc,data)
    def weight(self,path,rows):
        doc,data=read_glb(path);data=bytearray(data);acc=doc['accessors'][doc['meshes'][0]['primitives'][0]['attributes']['WEIGHTS_0']];view=doc['bufferViews'][acc['bufferView']]
        for row in range(acc['count']):struct.pack_into('<4f',data,view.get('byteOffset',0)+acc.get('byteOffset',0)+row*view.get('byteStride',16),*rows)
        write_glb(path,doc,data)
    def test_optimized_python_refuses_mismatching_candidate(self):
        self.position(.125)
        code="import sys;sys.path.insert(0,sys.argv[1]);from verify_parity import verify;verify(sys.argv[2],sys.argv[3])"
        result=subprocess.run([sys.executable,'-O','-c',code,str(PORTABLE),str(self.inputs['reference_glb']),str(self.candidate)],capture_output=True,text=True,timeout=5)
        self.assertNotEqual(result.returncode,0,'optimized verifier silently accepted .125 coordinate error')
        self.assertIn('Optimized Python is unsupported',result.stderr)
    def test_optimized_direct_glb_reader_refuses_execution(self):
        code="import sys;sys.path.insert(0,sys.argv[1]);import glb_io"
        result=subprocess.run([sys.executable,'-O','-c',code,str(PORTABLE)],capture_output=True,text=True,timeout=5)
        self.assertNotEqual(result.returncode,0);self.assertIn('Optimized Python is unsupported',result.stderr)
    def test_spec_snapshot_digest_binds_consumed_bytes(self):
        import hashlib
        from fish_asset_spec import load_spec_snapshot
        before=self.specpath.read_bytes();original=Path.read_bytes
        def changed_after_read(path):
            raw=original(path)
            if path.resolve()==self.specpath.resolve():
                replacement=copy.deepcopy(self.spec);replacement['expected']['triangles']=999;self.specpath.write_text(json.dumps(replacement))
            return raw
        with patch.object(Path,'read_bytes',new=changed_after_read):spec,digest=load_spec_snapshot(self.specpath)
        self.assertEqual(spec['expected']['triangles'],1);self.assertEqual(digest,hashlib.sha256(before).hexdigest());self.assertNotEqual(digest,sha(self.specpath))
    def test_glb_snapshot_digest_binds_consumed_bytes(self):
        import hashlib
        from glb_io import read_glb_snapshot
        before=self.candidate.read_bytes();replacement=before+b'changed after read';original=Path.read_bytes
        def changed_after_read(path):
            raw=original(path)
            if path.resolve()==self.candidate.resolve():self.candidate.write_bytes(replacement)
            return raw
        with patch.object(Path,'read_bytes',new=changed_after_read):doc,binary,digest=read_glb_snapshot(self.candidate)
        self.assertEqual(digest,hashlib.sha256(before).hexdigest());self.assertNotEqual(digest,sha(self.candidate));self.assertEqual(len(doc['meshes']),1)
    def test_negative_and_fractional_unused_joint_slots_rejected(self):
        import numpy as np
        original=self.candidate.read_bytes()
        for invalid in (-1,.5):
            with self.subTest(joint=invalid):
                self.candidate.write_bytes(original);doc,data=read_glb(self.candidate);data=bytearray(data);acc=doc['accessors'][doc['meshes'][0]['primitives'][0]['attributes']['JOINTS_0']];data.extend(b'\0'*(-len(data)%4));payload=np.asarray([[0,invalid,0,0]]*3,dtype='<f4').tobytes();acc['componentType']=5126;acc['bufferView']=len(doc['bufferViews']);acc['byteOffset']=0;doc['bufferViews'].append({'buffer':0,'byteOffset':len(data),'byteLength':len(payload)});data.extend(payload);write_glb(self.candidate,doc,data)
                with self.assertRaisesRegex(ValueError,'nonnegative integers'):self.verify()
    def test_primitive_missing_material_rejected(self):
        doc,data=read_glb(self.candidate);doc['meshes'][0]['primitives'][0].pop('material');write_glb(self.candidate,doc,data)
        with self.assertRaises((ValueError,AssertionError,RuntimeError)):self.verify()
    def test_primitive_out_of_range_material_rejected(self):
        doc,data=read_glb(self.candidate);doc['meshes'][0]['primitives'][0]['material']=999;write_glb(self.candidate,doc,data)
        with self.assertRaises((ValueError,AssertionError,RuntimeError)):self.verify()
    def test_tiny_positive_second_bone_stays_within_existing_tolerance(self):
        import numpy as np
        for path in (self.inputs['reference_glb'],self.candidate):
            doc,data=read_glb(path);data=bytearray(data);doc['nodes'].append({'name':'SecondBone'});doc['nodes'][0]['children'].append(3);doc['skins'][0]['joints'].append(3)
            acc=doc['accessors'][doc['skins'][0]['inverseBindMatrices']];view=doc['bufferViews'][acc['bufferView']];data.extend(b'\0'*(-len(data)%4));view['byteOffset']=len(data);payload=np.asarray([np.eye(4),np.eye(4)],dtype='<f4').tobytes();view['byteLength']=len(payload);data.extend(payload);acc['count']=2;write_glb(path,doc,data)
        doc,data=read_glb(self.candidate);data=bytearray(data);acc=doc['accessors'][doc['meshes'][0]['primitives'][0]['attributes']['JOINTS_0']];view=doc['bufferViews'][acc['bufferView']]
        for row in range(acc['count']):struct.pack_into('<H',data,view['byteOffset']+row*8+2,1)
        write_glb(self.candidate,doc,data);self.weight(self.candidate,[1,5e-8,0,0]);self.assertTrue(self.verify()['ok'])
    def test_unused_negative_weight_slot_rejected(self):
        self.weight(self.candidate,[1,-.5,0,0])
        with self.assertRaises((ValueError,AssertionError,RuntimeError)):self.verify()
    def test_hashbound_unnormalized_reference_rejected_in_preflight(self):
        self.weight(self.inputs['reference_glb'],[.5,0,0,0]);newhash=sha(self.inputs['reference_glb']);packing=json.loads(self.inputs['packing_report'].read_text());packing['candidates']['merged-mask']['sha256']=newhash;self.inputs['packing_report'].write_text(json.dumps(packing));self.spec['inputs']['reference_glb']['sha256']=newhash;self.spec['inputs']['packing_report']['sha256']=sha(self.inputs['packing_report']);self.specpath.write_text(json.dumps(self.spec))
        with self.assertRaises((ValueError,AssertionError,RuntimeError)):preflight(self.specpath)
    def test_candidate_swap_after_read_rejected(self):
        real_image=parity.image_pixels;changed=False
        def callback(*args,**kwargs):
            nonlocal changed
            result=real_image(*args,**kwargs)
            if not changed:self.position(.25);changed=True
            return result
        with patch.object(parity,'image_pixels',side_effect=callback):
            with self.assertRaises((ValueError,AssertionError,RuntimeError)):self.verify()
    def test_runner_output_swap_after_verify_rejected_before_final_spec(self):
        from types import SimpleNamespace
        import run_source
        output=self.folder/'raced-run';source=output/'source';real_verify=run_source.verify;calls=0
        def fake_process(*args,**kwargs):
            nonlocal calls
            calls+=1
            if calls==1:
                source.mkdir();(source/'fish.glb').write_bytes(self.candidate.read_bytes());(source/'fish.blend').write_bytes(b'synthetic')
            else:(output/'fish.glb').write_bytes(self.candidate.read_bytes())
            return SimpleNamespace(returncode=0,stdout='',stderr='')
        def swapped_after_verify(*args,**kwargs):
            result=real_verify(*args,**kwargs);self.position(.25);replacement=self.candidate.read_bytes();(output/'fish.glb').write_bytes(replacement);(source/'fish.glb').write_bytes(replacement);return result
        with patch('run_source.subprocess.run',side_effect=fake_process),patch('run_source.verify',side_effect=swapped_after_verify):
            with self.assertRaises(RuntimeError):run_source.run(SimpleNamespace(spec=self.specpath,output=output,blender=Path(sys.executable),execute=True,timeout=1))
        self.assertFalse((output/'final-spec.json').exists());self.assertEqual(json.loads((output/'manifest.json').read_text())['status'],'failed')
    def test_spec_swap_after_verification_rejected_before_report(self):
        real_verify=parity.verify;output=self.folder/'must-not-exist.validation.json'
        def callback(*args,**kwargs):
            result=real_verify(*args,**kwargs);changed=copy.deepcopy(self.spec);changed['expected']['triangles']=999;self.specpath.write_text(json.dumps(changed));return result
        with patch.object(parity,'verify',side_effect=callback),patch.object(sys,'argv',['verify_parity.py','--spec',str(self.specpath),'--candidate',str(self.candidate),'--output',str(output)]),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises((ValueError,AssertionError,RuntimeError)):parity.main()
        self.assertFalse(output.exists(),'must not leave a fresh passing proof for unvalidated spec')

if __name__=='__main__':unittest.main()
