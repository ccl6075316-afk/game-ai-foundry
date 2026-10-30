"""Synthetic arbitrary-inventory tests; no production fish or GPU renderer used."""
from __future__ import annotations
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import sys
import numpy as np
from PIL import Image
SCRIPTS=Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPTS/'portable'))
import parts
from pack_fish_material_atlas import write_glb
GODOT=Path.home()/'.gamefactory/toolchain/godot/Godot_mono.app/Contents/MacOS/Godot'

def fixture(folder, name, roles=('body','fin','aux'), bones=2, reorder=False, transparent=False, extra_body=False):
    """One surface, arbitrary explicit partitions, two source triangles per part."""
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    doc={'asset':{'version':'2.0'},'buffers':[],'bufferViews':[],'accessors':[],'nodes':[], 'meshes':[], 'skins':[], 'scenes':[{'nodes':[0,1]}],'scene':0,'extras':{'geometry_parts':[]}}
    binary=bytearray()
    def put(data,component_type=5126,kind='VEC3'):
        binary.extend(b'\0'*(-len(binary)%4)); offset=len(binary); raw=data.tobytes();binary.extend(raw)
        view=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw)})
        result=len(doc['accessors']);row={'bufferView':view,'componentType':component_type,'count':len(data),'type':kind}
        if kind=='VEC3':row.update(min=data.min(axis=0).tolist(),max=data.max(axis=0).tolist())
        doc['accessors'].append(row);return result
    positions=[];normals=[];uvs=[];joints=[];weights=[];indices=[];inventory=[]
    for i,role in enumerate(roles):
        local=np.array([[i*2,0,0],[i*2+.7,0,0],[i*2,.7,0],[i*2+.8,0,0],[i*2+1.5,0,0],[i*2+.8,.7,0]],dtype='<f4')
        uv=np.array([[.2,.2],[.7,.2],[.2,.7],[.3,.3],[.6,.3],[.3,.6]],dtype='<f4')
        order=np.array([2,0,1,5,3,4]) if reorder else np.arange(6);inverse=np.argsort(order)
        positions.extend(local[order]);uvs.extend(uv[order]);normals.extend([[0,0,1]]*6)
        joints.extend([[0,min(1,bones-1),0,0]]*6);weights.extend([[.6,.4,0,0]]*6)
        indices.extend((inverse+6*i).tolist())
        row={'name':f'part_{i}','role':role,'source_node':f'source_{i}','source_surface':0,'opaque_uv':role in parts.BODY_ROLES}
        inventory.append(row)
        doc['extras']['geometry_parts'].append({**row,'part_id':i,'vertex_start':i*6,'vertex_count':6,'index_start':i*6,'index_count':6})
    attrs={'POSITION':put(np.asarray(positions,dtype='<f4')),'NORMAL':put(np.asarray(normals,dtype='<f4')),'TEXCOORD_0':put(np.asarray(uvs,dtype='<f4'),kind='VEC2'),'JOINTS_0':put(np.asarray(joints,dtype='<u2'),5123,'VEC4'),'WEIGHTS_0':put(np.asarray(weights,dtype='<f4'),kind='VEC4')}
    index=put(np.asarray(indices,dtype='<u4').reshape(-1,1),5125,'SCALAR')
    rgba=np.full((8,8,4),255,dtype=np.uint8);rgba[:,:,:3]=[20,170,200]
    if transparent:rgba[3,3,3]=0
    png=io.BytesIO();Image.fromarray(rgba).save(png,format='PNG')
    binary.extend(b'\0'*(-len(binary)%4));image_offset=len(binary);binary.extend(png.getvalue());image_view=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':image_offset,'byteLength':len(png.getvalue())})
    doc.update(images=[{'bufferView':image_view,'mimeType':'image/png'}],samplers=[{'magFilter':9728,'minFilter':9728}],textures=[{'sampler':0,'source':0}],materials=[{'alphaMode':'MASK','alphaCutoff':.5,'doubleSided':True,'pbrMetallicRoughness':{'baseColorTexture':{'index':0},'baseColorFactor':[1,1,1,1],'roughnessFactor':1,'metallicFactor':0}}])
    doc['nodes']=[{'name':'Candidate','mesh':0,'skin':0}]+[{'name':f'Bone{i}',**({'children':[i+2]} if i<bones-1 else {})} for i in range(bones)]
    inverse_bind=put(np.tile(np.eye(4,dtype='<f4').reshape(1,16),(bones,1)),kind='MAT4')
    doc['skins']=[{'joints':list(range(1,bones+1)),'inverseBindMatrices':inverse_bind,'skeleton':1}]
    doc['meshes']=[{'name':'Candidate','primitives':[{'attributes':attrs,'indices':index,'material':0}]}]
    times=put(np.array([[0],[1]],dtype='<f4'),kind='SCALAR');rot=put(np.array([[0,0,0,1],[0,0,.2,.9797959]],dtype='<f4'),kind='VEC4')
    doc['animations']=[{'name':'swim','samplers':[{'input':times,'output':rot,'interpolation':'LINEAR'}],'channels':[{'sampler':0,'target':{'node':bones,'path':'rotation'}}]}]
    model=folder/(name+'.glb');write_glb(model,doc,binary)
    spec={'kind':'fish_asset_finalization_spec','version':1,'parts':inventory,'expected':{'mesh_count':1,'surface_count':1,'vertices':6*len(roles),'triangles':2*len(roles),'bones':bones,'clips':1,'animation_channels':1}}
    return model,spec,doc,binary

class PortablePartsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parts.OUTPUT_ROOT.mkdir(parents=True,exist_ok=True)
        cls.temp=Path(tempfile.mkdtemp(prefix='parts-tests-',dir=parts.OUTPUT_ROOT))
        cls.receipts=[]
    @classmethod
    def tearDownClass(cls):
        # Keep small reproducible summary; remove synthetic models, Godot caches and logs.
        if cls.receipts:
            (parts.OUTPUT_ROOT/'portable-parts-tests.validation.json').write_text(json.dumps({'kind':'portable_parts_synthetic_test_receipt','cases':cls.receipts,'scope':'Synthetic headless import tests only; no GPU or formal fish gate claim.','temporary_cleanup':'All synthetic GLBs, manifest mutations, projects, caches and process logs removed after receipt.'},indent=2)+'\n')
        shutil.rmtree(cls.temp)
    def test_arbitrary_inventory_and_body_surfaces(self):
        for roles,bones in [(('body','fin'),1),(('body','mouth','body_skin','fin','fin','aux','gill_cover'),4)]:
            with self.subTest(roles=roles):
                model,spec,_,_=fixture(self.temp,'inventory'+str(bones),roles,bones)
                manifest=parts.freeze(model,spec)
                self.assertEqual(len(manifest['parts']),len(roles));self.assertEqual(manifest['expected']['bones'],bones)
                self.assertEqual(len(manifest['body_opacity']['body_regions']),sum(r in parts.BODY_ROLES for r in roles))
    def test_body_role_cannot_skip_opacity_and_gpu_errors_fail(self):
        for role in parts.BODY_ROLES:
            with self.subTest(role=role), self.assertRaises(ValueError):
                parts.inventory({'parts':[{'name':'body','role':role,'source_node':'body','source_surface':0,'opaque_uv':False},{'name':'aux','role':'aux','source_node':'aux','source_surface':0,'opaque_uv':True}]})
        from validate_body_gpu import reject_engine_errors
        reject_engine_errors('GPU capture completed successfully')
        for marker in ('ERROR:', 'SCRIPT ERROR', 'Parse Error', 'Assertion failed'):
            with self.subTest(marker=marker), self.assertRaises(ValueError):reject_engine_errors('exit0 and stale oktrue receipt '+marker)

    def test_gpu_missing_pixel_comparator(self):
        from validate_body_gpu import missing_pixels
        opaque=self.temp/'opaque.png';negative=self.temp/'transparent.png'
        Image.fromarray(np.full((10,10,4),255,dtype=np.uint8)).save(opaque)
        pixels=np.full((10,10,4),255,dtype=np.uint8);pixels[5,5,3]=0;Image.fromarray(pixels).save(negative)
        self.assertEqual(missing_pixels(opaque,opaque),(0,100))
        self.assertEqual(missing_pixels(negative,opaque),(1,100))

    def test_bad_partitions_and_opaque_rectangle(self):
        for mutation in ('missing','duplicate','alpha','count'):
            model,spec,doc,binary=fixture(self.temp,'negative-'+mutation,transparent=mutation=='alpha')
            if mutation=='missing':doc['extras']['geometry_parts'].pop()
            if mutation=='duplicate':doc['extras']['geometry_parts'][1]=copy.deepcopy(doc['extras']['geometry_parts'][0])
            if mutation=='count':spec['expected']['triangles']=999
            write_glb(model,doc,binary)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):parts.freeze(model,spec)
    @unittest.skipUnless(GODOT.is_file(),'Existing Godot executable unavailable; no installation attempted')
    def test_native_output_rejects_dangling_file_symlink_and_directory(self):
        project=self.temp/'output-security-project';project.mkdir()
        (project/'project.godot').write_text('[application]\nconfig/name="Portable synthetic fixture"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
        model,spec,_,_=fixture(self.temp,'output-security')
        manifest_path=self.temp/'output-security-manifest.json';manifest_path.write_text(json.dumps(parts.freeze(model,spec)))
        target=self.temp/'dangling-target-must-not-be-created.json'
        link=self.temp/'dangling-output-report.json';link.symlink_to(target)
        directory=self.temp/'existing-output-directory';directory.mkdir()
        for output in (link,directory):
            with self.subTest(output=output.name):
                command=[str(GODOT),'--headless','--path',str(project),'--log-file',str(self.temp/'output-security.log'),'--script',str(SCRIPTS/'portable/validate_import.gd'),'--',str(manifest_path),str(output)]
                run=subprocess.run(command,text=True,capture_output=True,timeout=40,env={**os.environ,"DOTNET_ROOT":str(Path.home()/".gamefactory/toolchain/dotnet")})
                reports=[json.loads(line) for line in run.stdout.splitlines() if line.startswith('{')]
                self.assertTrue(reports,run.stdout+run.stderr)
                report=reports[-1]
                self.assertEqual(run.returncode,1,run.stdout+run.stderr)
                self.assertFalse(report['ok'])
                self.assertFalse(target.exists(),'Output followed a dangling file symlink and created its target')
                self.receipts.append({'case':'output-'+output.name,'expected_ok':False,'ok':report['ok'],'exit':run.returncode,'dangling_target_created':target.exists(),'report':report})
        self.assertTrue(link.is_symlink());self.assertTrue(directory.is_dir())

    @unittest.skipUnless(GODOT.is_file(),'Existing Godot executable unavailable; no installation attempted')
    def test_actual_godot_imports_and_negatives(self):
        project=self.temp/'project';project.mkdir();(project/'project.godot').write_text('[application]\nconfig/name="Portable synthetic fixture"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
        for name,roles,bones,reorder in [('small',('body','fin'),1,False),('varied',('body','mouth','fin','fin','aux','gill_cover'),4,True)]:
            model,spec,_,_=fixture(self.temp,name,roles,bones,reorder)
            manifest=parts.freeze(model,spec)
            for negative in ('none','normal','winding','count','partition','multiplicity'):
                altered=copy.deepcopy(manifest)
                if negative=='normal':altered['attributes']['NORMAL'][0]=[0,1,0]
                if negative=='winding':altered['indices'][1],altered['indices'][2]=altered['indices'][2],altered['indices'][1]
                if negative=='count':altered['expected']['bones']+=1
                if negative=='partition':altered['parts'][1]['source_node']=altered['parts'][0]['source_node']
                if negative=='multiplicity':altered['indices'][3:6]=altered['indices'][0:3]
                manifest_path=self.temp/(name+'-'+negative+'.json');manifest_path.write_text(json.dumps(altered))
                output=self.temp/(name+'-'+negative+'.report.json')
                cmd=[str(GODOT),'--headless','--path',str(project),'--log-file',str(self.temp/'engine.log'),'--script',str(SCRIPTS/'portable/validate_import.gd'),'--',str(manifest_path),str(output)]
                run=subprocess.run(cmd,text=True,capture_output=True,timeout=40,env={**os.environ,"DOTNET_ROOT":str(Path.home()/".gamefactory/toolchain/dotnet")})
                self.assertTrue(output.is_file(),run.stdout[-3000:]+run.stderr[-3000:])
                report=json.loads(output.read_text());self.receipts.append({'case':name+'-'+negative,'expected_ok':negative=='none','ok':report.get('ok'),'exit':run.returncode,'report':report})
                self.assertEqual(report['ok'],negative=='none',str(report)+run.stderr[-1000:])
                self.assertEqual(run.returncode,0 if negative=='none' else 1)

if __name__=='__main__':unittest.main()
