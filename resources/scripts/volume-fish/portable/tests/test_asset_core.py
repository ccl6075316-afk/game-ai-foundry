"""Tiny in-memory GLB unit regressions; no Blender or fish assets required."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fish_asset_spec import ROOT,SpecError,sha,preflight,load_spec,fresh_outputs,input_paths,declared_parts,artifact_output,allowed_output
from glb_io import read_glb
from verify_parity import verify
from pack_fish_material_atlas import write_glb


def fixture(folder,alpha=255):
    folder=Path(folder);binary=bytearray();doc={'asset':{'version':'2.0'},'buffers':[],'bufferViews':[],'accessors':[],'scene':0,'scenes':[{'nodes':[0,2]}],'nodes':[{'name':'Rig','children':[1]},{'name':'Bone'},{'name':'Mesh','mesh':0,'skin':0}],'skins':[{'joints':[1],'skeleton':0}],'meshes':[],'materials':[{'alphaMode':'MASK','alphaCutoff':.5,'doubleSided':False,'pbrMetallicRoughness':{'baseColorTexture':{'index':0},'roughnessFactor':1,'metallicFactor':0},'extensions':{'KHR_materials_specular':{'specularFactor':0}}}],'images':[],'textures':[{'source':0,'sampler':0}],'samplers':[{'magFilter':9728,'minFilter':9728,'wrapS':33071,'wrapT':33071}]}
    def rows(values,kind,component=5126):
        data=np.asarray(values,dtype={5126:'<f4',5123:'<u2'}[component]).tobytes();binary.extend(b'\0'*(-len(binary)%4));view=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':len(data)});binary.extend(data);idx=len(doc['accessors']);doc['accessors'].append({'bufferView':view,'componentType':component,'count':len(values),'type':kind});return idx
    attrs={'POSITION':rows([[0,0,0],[1,0,0],[0,1,0]],'VEC3'),'NORMAL':rows([[0,0,1]]*3,'VEC3'),'TEXCOORD_0':rows([[.25,.25],[.5,.25],[.25,.5]],'VEC2'),'JOINTS_0':rows([[0,0,0,0]]*3,'VEC4',5123),'WEIGHTS_0':rows([[1,0,0,0]]*3,'VEC4')}
    doc['meshes']=[{'primitives':[{'attributes':attrs,'indices':rows([[0],[1],[2]],'SCALAR',5123),'material':0}]}];doc['skins'][0]['inverseBindMatrices']=rows([np.eye(4).reshape(-1).tolist()],'MAT4')
    image=io.BytesIO();Image.new('RGBA',(4,4),(240,128,20,alpha)).save(image,format='PNG');payload=image.getvalue();atlas=folder/'atlas.png';atlas.write_bytes(payload);binary.extend(b'\0'*(-len(binary)%4));doc['images']=[{'bufferView':len(doc['bufferViews']),'mimeType':'image/png'}];doc['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':len(payload)});binary.extend(payload)
    reference=folder/'reference.glb';write_glb(reference,doc,binary);source=folder/'source.blend';source.write_bytes(b'synthetic source input placeholder for read-only preflight')
    report=folder/'packing.json';report.write_text(json.dumps({'candidates':{'merged-mask':{'sha256':sha(reference)}},'atlas':{'sha256':sha(atlas)},'parts':[{'node':'Body','surface':0,'new_vertex_range':[0,3],'new_index_range':[0,3]}]}))
    inputs={'source_blend':source,'reference_glb':reference,'atlas':atlas,'packing_report':report};spec={'kind':'fish_asset_finalization_spec','version':1,'inputs':{k:{'path':str(p.relative_to(ROOT)),'sha256':sha(p)}for k,p in inputs.items()},'source_mesh_name':'Mesh','expected':{'vertices':3,'triangles':1,'bones':1,'clips':0,'animation_channels':0,'mesh_count':1,'surface_count':1},'parts':[{'name':'Main','role':'body','source_node':'Body','source_surface':0}]}
    specpath=folder/'spec.json';specpath.write_text(json.dumps(spec));check=preflight(specpath);candidate=folder/'candidate.glb';doc['extras']={'geometry_parts':[{**p,'vertex_start':p['source_vertex_start']}for p in check['summary']['parts']]};write_glb(candidate,doc,binary);return specpath,candidate

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='core-unit-',dir=ROOT/'work/fish-portable-tools');self.folder=Path(self.tmp.name);self.specpath,self.candidate=fixture(self.folder);self.spec=load_spec(self.specpath);self.paths=input_paths(self.spec)
    def tearDown(self):self.tmp.cleanup()
    def modify_spec(self,change):
        value=copy.deepcopy(self.spec);change(value);self.specpath.write_text(json.dumps(value))
    def test_read_only_preflight_and_dynamic_parity(self):
        before={k:sha(p)for k,p in self.paths.items()};check=preflight(self.specpath);r=verify(self.paths['reference_glb'],self.candidate,self.spec,check['summary']['parts']);self.assertEqual(r['bones'],1);self.assertEqual(r['triangles'],1);self.assertEqual(r['native_clips'],{});self.assertEqual(before,{k:sha(p)for k,p in self.paths.items()})
    def test_body_opacity_opt_out_rejected(self):
        self.modify_spec(lambda s:s['parts'][0].update(opaque_uv=False))
        with self.assertRaisesRegex(SpecError,'opacity cannot be disabled'):load_spec(self.specpath)
    def test_allowed_artifact_roots(self):
        self.assertTrue(allowed_output(ROOT/'output/new-candidate'))
        self.assertTrue(allowed_output(ROOT/'projects/example/experiments/new-candidate'))
        self.assertFalse(allowed_output(ROOT/'projects/example/new-candidate'))
        self.assertFalse(allowed_output(Path('/private/tmp/new-candidate')))
    def test_output_parent_alias_rejected(self):
        with self.assertRaisesRegex(SpecError,'aliases an input'):artifact_output(self.folder,self.paths.values())
    def test_source_runner_dry_run_writes_nothing(self):
        from types import SimpleNamespace
        from run_source import run
        output=self.folder/'planned';result=run(SimpleNamespace(spec=self.specpath,output=output,blender=Path(sys.executable),execute=False,timeout=1))
        self.assertTrue(result['dry_run']);self.assertFalse(output.exists())
    def test_source_runner_failure_stops_and_records_stdout(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from run_source import run
        output=self.folder/'failed-run'
        with patch('run_source.subprocess.run',return_value=SimpleNamespace(returncode=1,stdout='failed author',stderr='error'))as process:
            with self.assertRaises(RuntimeError):run(SimpleNamespace(spec=self.specpath,output=output,blender=Path(sys.executable),execute=True,timeout=1))
        self.assertEqual(process.call_count,1);self.assertFalse((output/'final-spec.json').exists());self.assertEqual(json.loads((output/'manifest.json').read_text())['status'],'failed');self.assertIn('failed author',(output/'author.stdout.txt').read_text())
    def test_source_runner_timeout_preserves_stdout(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        import subprocess
        from run_source import run
        output=self.folder/'timeout-run'
        with patch('run_source.subprocess.run',side_effect=subprocess.TimeoutExpired(['blender'],1,output=b'partial stdout')):
            with self.assertRaises(subprocess.TimeoutExpired):run(SimpleNamespace(spec=self.specpath,output=output,blender=Path(sys.executable),execute=True,timeout=1))
        self.assertIn('partial stdout',(output/'author.stdout.txt').read_text());self.assertEqual(json.loads((output/'manifest.json').read_text())['status'],'failed')
    def test_count_mismatch_rejected(self):
        self.modify_spec(lambda s:s['expected'].update(triangles=1710))
        with self.assertRaisesRegex(SpecError,'Expected triangles'):preflight(self.specpath)
    def test_missing_part_rejected(self):
        self.modify_spec(lambda s:s['parts'][0].update(source_node='Missing'))
        with self.assertRaisesRegex(SpecError,'Missing declared part'):preflight(self.specpath)
    def test_input_hash_rejected(self):
        self.paths['atlas'].write_bytes(b'changed')
        with self.assertRaisesRegex(SpecError,'Stale reference'):preflight(self.specpath)
    def test_output_alias_rejected(self):
        with self.assertRaises(SpecError):fresh_outputs([self.paths['source_blend']],self.paths.values())
    def test_existing_output_rejected(self):
        with self.assertRaisesRegex(SpecError,'Fresh output'):fresh_outputs([self.candidate],self.paths.values())
    def test_rest_transform_mutation_rejected(self):
        d,b=read_glb(self.candidate);d['nodes'][1]['translation']=[0,.01,0];write_glb(self.candidate,d,b)
        with self.assertRaisesRegex(AssertionError,'Rest transform changed'):verify(self.paths['reference_glb'],self.candidate,self.spec)
    def test_hierarchy_cycle_rejected_without_loop(self):
        d,b=read_glb(self.candidate);d['nodes'][1]['children']=[0];write_glb(self.candidate,d,b)
        with self.assertRaisesRegex(AssertionError,'hierarchy cycle'):verify(self.paths['reference_glb'],self.candidate,self.spec)
    def test_hierarchy_out_of_range_rejected(self):
        d,b=read_glb(self.candidate);d['nodes'][0]['children']=[999];write_glb(self.candidate,d,b)
        with self.assertRaisesRegex(AssertionError,'Child index out of range'):verify(self.paths['reference_glb'],self.candidate,self.spec)
    def test_duplicate_joint_weight_mass_change_rejected(self):
        import struct
        for path in (self.paths['reference_glb'],self.candidate):
            d,b=read_glb(path);b=bytearray(b);acc=d['accessors'][d['meshes'][0]['primitives'][0]['attributes']['WEIGHTS_0']];view=d['bufferViews'][acc['bufferView']]
            for row in range(3):struct.pack_into('<4f',b,view['byteOffset']+row*16,.2,.8,0,0)
            write_glb(path,d,b)
        verify(self.paths['reference_glb'],self.candidate,self.spec)
        d,b=read_glb(self.candidate);b=bytearray(b);acc=d['accessors'][d['meshes'][0]['primitives'][0]['attributes']['WEIGHTS_0']];view=d['bufferViews'][acc['bufferView']];struct.pack_into('<f',b,view['byteOffset'],.1);write_glb(self.candidate,d,b)
        # The changed duplicate-slot mass is .9 and is now rejected as invalid before parity.
        with self.assertRaisesRegex(ValueError,'nonnegative and normalized'):verify(self.paths['reference_glb'],self.candidate,self.spec)
    def test_semantic_epsilon_not_relaxed(self):
        d,b=read_glb(self.candidate);import struct
        a=d['accessors'][d['meshes'][0]['primitives'][0]['attributes']['POSITION']];view=d['bufferViews'][a['bufferView']];b=bytearray(b);struct.pack_into('<f',b,view['byteOffset'],2e-6);write_glb(self.candidate,d,b)
        with self.assertRaises(AssertionError):verify(self.paths['reference_glb'],self.candidate,self.spec)
    def test_part_metadata_mutation_rejected(self):
        d,b=read_glb(self.candidate);d['extras']['geometry_parts'][0]['name']='Wrong';write_glb(self.candidate,d,b)
        with self.assertRaisesRegex(AssertionError,'Part metadata differs'):verify(self.paths['reference_glb'],self.candidate,self.spec,preflight(self.specpath)['summary']['parts'])
    def test_extra_material_map_rejected(self):
        d,b=read_glb(self.candidate);d['materials'][0]['normalTexture']={'index':0};write_glb(self.candidate,d,b)
        with self.assertRaisesRegex(AssertionError,'Unsupported packed material feature'):verify(self.paths['reference_glb'],self.candidate,self.spec)
    def test_body_alpha_requirement_not_relaxed(self):
        other=self.folder/'transparent';other.mkdir();specpath,candidate=fixture(other,alpha=127);spec=load_spec(specpath);inputs=input_paths(spec)
        with self.assertRaisesRegex(AssertionError,'Body alpha not fully opaque'):verify(inputs['reference_glb'],candidate,spec,preflight(specpath)['summary']['parts'])
    def test_opaque_material_mutation_rejected(self):
        d,b=read_glb(self.candidate);d['materials'][0]['alphaMode']='BLEND';write_glb(self.candidate,d,b)
        with self.assertRaises(AssertionError):verify(self.paths['reference_glb'],self.candidate,self.spec)

if __name__=='__main__':unittest.main()
