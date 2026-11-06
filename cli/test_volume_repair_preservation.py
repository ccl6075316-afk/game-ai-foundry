"""Scoped inheritance must reject actual protected-data changes after rebinding."""
import copy
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import numpy as np
from PIL import Image
import volume_repair_preservation as v


class RepairPreservationTests(unittest.TestCase):
    def setUp(self):
        work=v.ROOT/'output/test-volume-repair-preservation';work.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=work);self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'fish.blend';self.source.write_bytes(b'fixture authoring source')
        self.doc={'asset':{'version':'2.0'},'buffers':[{}],'bufferViews':[],'accessors':[],
            'nodes':[{'name':'Body','mesh':0,'skin':0},{'name':'Caudal','mesh':1,'skin':0},{'name':'joint'}],
            'meshes':[],'skins':[{'joints':[2]}], 'materials':[{'pbrMetallicRoughness':{'baseColorTexture':{'index':0}},'alphaMode':'MASK','alphaCutoff':.5,'doubleSided':True}],
            'textures':[{'source':0,'sampler':0}],'samplers':[{'magFilter':9728,'minFilter':9728}], 'images':[]}
        self.bin=bytearray()
        def acc(a,kind,component):
            offset=len(self.bin);self.bin.extend(a.tobytes());self.bin.extend(b'\0'*((-len(self.bin))%4))
            bv=len(self.doc['bufferViews']);self.doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':a.nbytes})
            idx=len(self.doc['accessors']);self.doc['accessors'].append({'bufferView':bv,'componentType':component,'count':len(a),'type':kind});return idx
        for x in (0.,2.):
            p=np.array([[x,0,0],[x+1,0,0],[x,1,0]],'<f4')
            attrs={'POSITION':acc(p,'VEC3',5126),'NORMAL':acc(np.tile([0,0,1],(3,1)).astype('<f4'),'VEC3',5126),'TEXCOORD_0':acc(np.array([[.1,.1],[.2,.1],[.1,.2]],'<f4'),'VEC2',5126),'JOINTS_0':acc(np.zeros((3,4),'<u2'),'VEC4',5123),'WEIGHTS_0':acc(np.tile([1,0,0,0],(3,1)).astype('<f4'),'VEC4',5126)}
            self.doc['meshes'].append({'primitives':[{'attributes':attrs,'indices':acc(np.array([[0],[1],[2]],'<u2'),'SCALAR',5123),'material':0}]})
        self.doc['skins'][0]['inverseBindMatrices']=acc(np.eye(4,dtype='<f4').reshape(1,16),'MAT4',5126)
        stream=io.BytesIO();Image.new('RGBA',(8,8),(90,100,110,255)).save(stream,format='PNG');offset=len(self.bin);self.bin.extend(stream.getvalue());bv=len(self.doc['bufferViews']);self.doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(stream.getvalue())});self.doc['images']=[{'bufferView':bv,'mimeType':'image/png'}]
        self.model=self.root/'fish.glb';self.save();a=v.inspect_model(self.model)
        release=self.root/'accepted.json';self.write(release,{'user_acceptance':True,'fish':[{'species':'fixture','model':{'sha256':v.sha(self.model)}}]})
        self.snapshot={'kind':'accepted_caudal_repair_protected_snapshot','species':'fixture','baseline_model_sha256':v.sha(self.model),'baseline_source_sha256':v.sha(self.source),'accepted_release':self.ref(release),
            'part_inventory':[{'key':list(k),'affected_caudal':k[0]=='Caudal','triangles':p['triangles'],'canonical_directed_triangle_signature':p['signature'],'geometry_uv_normal_signature':p['geometry']}for k,p in a['parts'].items()],
            'rig_semantic_signature':a['rig'],'native_animation_semantic_signature':a['animation'],'node_graph':a['graph'],**{k:self.doc[k]for k in ('materials','textures','samplers')},
            'images':[{'index':0,'size':[8,8],'rgba_sha256':__import__('hashlib').sha256(a['images'][0].tobytes()).hexdigest()}]}
        self.snap=self.root/'snapshot.json';self.write(self.snap,self.snapshot)
        self.contract={'kind':'caudal_repair_preservation','species':'fixture','affected_anatomical_parts':['Caudal'],'model_sha256':v.sha(self.model),'source_sha256':v.sha(self.source),'accepted_snapshot':self.ref(self.snap)}
        bindings=self.root/'material-bindings.json';self.write(bindings,{'kind':'accepted_caudal_repair_material_bindings','species':'fixture','baseline_model_sha256':v.sha(self.model),'part_material_bindings':[{'key':list(k),'material':p['material']}for k,p in a['parts'].items()]});self.contract['accepted_material_bindings']=self.ref(bindings)
        self.contractpath=self.root/'contract.json'
    def ref(self,p):return {'path':str(p),'sha256':v.sha(p)}
    def write(self,p,obj):p.write_text(json.dumps(obj))
    def save(self):
        self.doc['buffers'][0]['byteLength']=len(self.bin);j=json.dumps(self.doc).encode();j+=b' '*((-len(j))%4);b=bytes(self.bin);b+=b'\0'*((-len(b))%4)
        self.model.write_bytes(b'glTF'+struct.pack('<II',2,28+len(j)+len(b))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(b),0x004e4942)+b)
    def check(self,task='repair'):
        self.contract['model_sha256']=v.sha(self.model);self.write(self.contractpath,self.contract)
        return v.validate_preservation(self.ref(self.contractpath),{'model':self.ref(self.model),'editable_source':self.ref(self.source)},'fixture',task)
    def mutate_float(self,attr,delta=.125):
        i=self.doc['meshes'][0]['primitives'][0]['attributes'][attr];a=self.doc['accessors'][i];o=self.doc['bufferViews'][a['bufferView']]['byteOffset'];x=struct.unpack_from('<f',self.bin,o)[0];struct.pack_into('<f',self.bin,o,x+delta);self.save()
    def test_real_stream_baseline_passes(self):self.assertEqual(self.check()['protected_parts'],1)
    def test_non_tail_position_rebinding_rejected(self):
        self.mutate_float('POSITION')
        with self.assertRaisesRegex(ValueError,'geometry'):self.check()
    def test_non_tail_normal_rebinding_rejected(self):
        self.mutate_float('NORMAL')
        with self.assertRaisesRegex(ValueError,'geometry'):self.check()
    def test_non_tail_uv_rebinding_rejected(self):
        self.mutate_float('TEXCOORD_0')
        with self.assertRaisesRegex(ValueError,'geometry'):self.check()
    def test_actual_partition_material_swap_rejected(self):
        self.doc['materials'].append(copy.deepcopy(self.doc['materials'][0]));self.doc['meshes'][0]['primitives'][0]['material']=1;self.save()
        with self.assertRaisesRegex(ValueError,'material binding'):self.check()
    def test_unreviewed_extra_drawing_stream_rejected(self):
        self.doc['meshes'][0]['primitives'][0]['attributes']['COLOR_0']=self.doc['meshes'][0]['primitives'][0]['attributes']['WEIGHTS_0'];self.save()
        with self.assertRaisesRegex(ValueError,'extra drawing'):self.check()
    def test_semantic_sampler_change_rejected(self):
        self.doc['samplers'][0]['minFilter']=9984;self.save()
        with self.assertRaisesRegex(ValueError,'sampler'):self.check()
    def test_literal_material_defaults_are_semantically_equal(self):
        self.doc['materials'][0]['pbrMetallicRoughness'].update(metallicFactor=1,roughnessFactor=1,baseColorFactor=[1,1,1,1]);self.save();self.check()
    def test_omitted_protected_part_rejected(self):
        self.doc['nodes'][0].pop('mesh');self.save()
        with self.assertRaisesRegex(ValueError,'partition'):self.check()
    def test_expanded_anatomical_scope_rejected(self):
        self.contract['affected_anatomical_parts'].append('body')
        with self.assertRaisesRegex(ValueError,'Only Caudal'):self.check()
    def test_snapshot_cannot_self_omit_protected_part(self):
        self.snapshot['part_inventory'][0]['affected_caudal']=True;self.write(self.snap,self.snapshot);self.contract['accepted_snapshot']=self.ref(self.snap)
        with self.assertRaisesRegex(ValueError,'omission'):self.check()
    def test_new_asset_cannot_inherit(self):
        with self.assertRaisesRegex(ValueError,'repair-only'):self.check('new')
    def test_arbitrary_weight_exception_is_not_a_tolerance(self):
        self.contract['source_preserved_export_serialization']=self.ref(self.snap)
        with self.assertRaisesRegex(ValueError,'serialization'):self.check()
    def test_complete_nearest_footprint_includes_triangle_interior(self):
        tri=np.array([[0.,0.],[8.,0.],[0.,8.]])
        self.assertTrue(v._touches_changed_texel(tri,np.array([2]),np.array([2])))
        self.assertFalse(v._touches_changed_texel(tri,np.array([7]),np.array([7])))
    def test_helper_is_standard_bound(self):
        from volume_sop import standard_snapshot
        self.assertEqual(standard_snapshot()['files']['cli/volume_repair_preservation.py'],v.sha(Path(v.__file__)))

if __name__=='__main__':unittest.main()
