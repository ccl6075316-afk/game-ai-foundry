"""Phase3 minimal failing regression draft, investigation only (no source fixes)."""
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
ROOT=Path(__file__).resolve().parents[3];PORTABLE=ROOT/'resources/scripts/volume-fish/portable';WORK=Path(__file__).resolve().parent
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
    def test_spec_swap_after_verification_rejected_before_report(self):
        real_verify=parity.verify;output=self.folder/'must-not-exist.validation.json'
        def callback(*args,**kwargs):
            result=real_verify(*args,**kwargs);changed=copy.deepcopy(self.spec);changed['expected']['triangles']=999;self.specpath.write_text(json.dumps(changed));return result
        with patch.object(parity,'verify',side_effect=callback),patch.object(sys,'argv',['verify_parity.py','--spec',str(self.specpath),'--candidate',str(self.candidate),'--output',str(output)]),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises((ValueError,AssertionError,RuntimeError)):parity.main()
        self.assertFalse(output.exists(),'must not leave a fresh passing proof for unvalidated spec')

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GuardRegressions))
    (WORK/'phase3-beforefix.tests.json').write_text(json.dumps({'tests_run':result.testsRun,'failures':[{'case':str(case),'traceback':trace}for case,trace in result.failures],'errors':[{'case':str(case),'traceback':trace}for case,trace in result.errors],'success':result.wasSuccessful()},indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful()else 1)
