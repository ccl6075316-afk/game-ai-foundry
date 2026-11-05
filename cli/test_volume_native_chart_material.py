"""Accepted constant oral preservation must not become a texture bypass."""
import copy
import io
import sys
import unittest
from pathlib import Path
from unittest import mock
import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parent))
import volume_native_chart_preservation as gate


class NativeMaterialTests(unittest.TestCase):
    def setUp(self):
        image=io.BytesIO();Image.new('RGBA',(1,1),(100,80,60,255)).save(image,format='PNG')
        self.png=image.getvalue()
        front=np.array([[.4,.1,.1],[.4,.1,-.1],[.4,-.1,-.1],[.4,-.1,.1]])
        rear=front.copy();rear[:,0]=0
        inner=front.copy();inner[:,0]=.3;inner[:,1:]*=.6
        body=[];oral=[]
        for i in range(4):
            j=(i+1)%4
            body.extend([[i,j,j+4],[i,j+4,i+4]])
            oral.extend([[j,i,i+4],[j,i+4,j+4]])
        body.extend([[4,6,5],[4,7,6]])
        oral.extend([[4,5,6],[4,6,7]])
        self.values={0:np.concatenate([front,rear]),1:np.zeros((8,2)),2:np.array(body),
                     3:np.concatenate([front,inner]),4:np.zeros((8,2)),5:np.array(oral),
                     6:np.tile([0,1,0,0],(8,1)),7:np.tile(np.array([.432123,.567877,0,0],dtype=np.float32),(8,1))}
        self.doc={'nodes':[{'name':'Closed_body','mesh':0,'skin':0},{'name':'body0'},{'name':'body1'}],
                  'skins':[{'joints':[1,2]}],
                  'meshes':[{'primitives':[{'attributes':{'POSITION':0,'TEXCOORD_0':1,'JOINTS_0':6,'WEIGHTS_0':7},'indices':2,'material':0},
                                           {'attributes':{'POSITION':3,'TEXCOORD_0':4,'JOINTS_0':6,'WEIGHTS_0':7},'indices':5,'material':1}]}],
                  'materials':[{'name':'Source body pixels','pbrMetallicRoughness':{'baseColorTexture':{'index':0}}},
                               {'name':'Source oral shadow / cavity only','doubleSided':True,
                                'pbrMetallicRoughness':{'baseColorFactor':[.035,.031,.028,1],
                                                      'metallicFactor':0,'roughnessFactor':.5}}],
                  'textures':[{'source':0,'sampler':0}],'samplers':[{'magFilter':9728,'minFilter':9728}],
                  'images':[{'bufferView':0}],'bufferViews':[{'byteLength':len(self.png)}]}

    def chart(self,doc,digest):
        with mock.patch.object(gate._io,'read_glb_snapshot',return_value=(doc,self.png,digest)), \
             mock.patch.object(gate._io,'arrays',side_effect=lambda d,b,i:self.values[i]):
            return gate.extract_chart('unused.glb')

    def validate(self,old,new):
        baseline=self.chart(old,'old');baseline.update(kind='accepted_native_chart_snapshot',species='fixture',
            source_sha256='image',accepted_material_scope='complete body and integrated mouth chart',
            release_record={'path':'release','sha256':'release'})
        current=self.chart(new,'new');_,counts=gate.shared_rim(current)
        report={'ok':True,'species':'fixture','source_sha256':'image','model_sha256':'new',
                'layout':'ordinary_multimesh','baseline_native_chart':{'path':'baseline','sha256':'baseline'},
                'preservation_domain':{'scope':'complete_body'},'complete_body_chart_preserved':True,
                'actual_3d_rim_transport':{'upper_edges':counts['upper'],'lower_edges':counts['lower']},
                'auxiliary_color_contribution_changes':0}
        candidates={'model':{'path':'candidate.glb','sha256':'new'},'source_image':{'path':'source.png','sha256':'image'}}
        release={'user_acceptance':True,'fish':[{'species':'fixture','model':{'sha256':'old'}}]}
        refs={'baseline':baseline,'release':release}
        with mock.patch.object(gate,'sha',side_effect=lambda p:'image' if Path(p).name=='source.png' else 'new'), \
             mock.patch.object(gate,'load_bound',side_effect=lambda r:copy.deepcopy(refs[r['path']])), \
             mock.patch.object(gate,'extract_chart',return_value=current):
            return gate.validate_preserved_domain(report,candidates,'fixture')

    def test_accepted_constant_oral_and_explicit_opaque_default_are_preserved(self):
        new=copy.deepcopy(self.doc)
        for m in new['materials']:m['alphaMode']='OPAQUE'
        self.assertGreater(self.validate(self.doc,new)['protected_faces'],0)

    def test_changed_oral_rgb_is_not_preservation_with_honest_new_model_identity(self):
        new=copy.deepcopy(self.doc);new['materials'][1]['pbrMetallicRoughness']['baseColorFactor'][0]+=.01
        with self.assertRaisesRegex(ValueError,'Changed protected material'):self.validate(self.doc,new)

    def test_same_colour_textured_oral_cannot_be_replaced_by_constant(self):
        old=copy.deepcopy(self.doc);old['materials'][1]['pbrMetallicRoughness']['baseColorTexture']={'index':0}
        with self.assertRaisesRegex(ValueError,'Changed protected material'):self.validate(old,self.doc)

    def test_constant_body_is_still_rejected(self):
        doc=copy.deepcopy(self.doc);doc['materials'][0]['pbrMetallicRoughness']={'baseColorFactor':[.1,.1,.1,1]}
        with self.assertRaisesRegex(ValueError,'Missing native base-colour image'):self.chart(doc,'new')

    def test_missing_explicit_rgba_is_not_a_default_colour_escape(self):
        doc=copy.deepcopy(self.doc);del doc['materials'][1]['pbrMetallicRoughness']['baseColorFactor']
        with self.assertRaises(ValueError):self.chart(doc,'new')

    def test_nonopaque_or_invalid_constant_is_rejected(self):
        for factor in [[.035,.031,.028,.9],[float('nan'),.031,.028,1],[1.1,.031,.028,1],[.1,.2,.3]]:
            with self.subTest(factor=factor):
                doc=copy.deepcopy(self.doc);doc['materials'][1]['pbrMetallicRoughness']['baseColorFactor']=factor
                with self.assertRaises(ValueError):self.chart(doc,'new')

    def test_blend_and_changed_culling_are_not_opaque_defaults(self):
        new=copy.deepcopy(self.doc);new['materials'][0]['alphaMode']='BLEND'
        with self.assertRaisesRegex(ValueError,'Changed protected material'):self.validate(self.doc,new)
        new=copy.deepcopy(self.doc);new['materials'][1]['doubleSided']=False
        with self.assertRaisesRegex(ValueError,'Changed protected material'):self.validate(self.doc,new)

    def split_oral_row(self,changed_skin=False):
        new=copy.deepcopy(self.doc)
        self.values.update({8:np.concatenate([self.values[3],self.values[3][:1]]),
            9:np.zeros((9,2)),10:np.tile([0,1,0,0],(9,1)),
            11:np.concatenate([self.values[7],self.values[7][:1]]),12:self.values[5].copy()})
        self.values[12][0,1]=8
        if changed_skin:
            self.values[11][8,0]+=np.float32(1e-7);self.values[11][8,1]-=np.float32(1e-7)
            self.assertTrue(np.array_equal((self.values[11][8]*65535).astype(int),(self.values[7][0]*65535).astype(int)))
        p=new['meshes'][0]['primitives'][1]
        p['attributes'].update(POSITION=8,TEXCOORD_0=9,JOINTS_0=10,WEIGHTS_0=11);p['indices']=12
        return new

    def test_constant_oral_draw_split_preserves_every_oriented_corner(self):
        new=self.split_oral_row()
        self.assertGreater(self.validate(self.doc,new)['protected_faces'],0)

    def test_distinct_float_skin_aliases_cannot_merge_even_in_same_gpu_bin(self):
        new=self.split_oral_row(changed_skin=True)
        with self.assertRaises(ValueError):self.validate(self.doc,new)

    def test_near_unit_float_weights_compare_normalized_runtime_bins(self):
        self.values[7][:]=np.array([.2,.8,0,0],dtype=np.float32)
        new=copy.deepcopy(self.doc)
        self.values[13]=self.values[7].copy()
        self.values[13][:,0]=np.float32(.200008)
        new['meshes'][0]['primitives'][1]['attributes']['WEIGHTS_0']=13
        # Unnormalized truncation falsely gives equal bins. The real importer
        # normalizes first: [13107,52428] becomes [13107,52427].
        self.assertTrue(np.array_equal((self.values[7]*65535).astype(int),
                                       (self.values[13]*65535).astype(int)))
        a=self.chart(self.doc,'old')['parts'][1]['named_skin_runtime_unorm16'][0]
        b=self.chart(new,'new')['parts'][1]['named_skin_runtime_unorm16'][0]
        self.assertEqual(a,[['body0',13107],['body1',52428]])
        self.assertEqual(b,[['body0',13107],['body1',52427]])
        with self.assertRaisesRegex(ValueError,'Changed constant oral deformation identity'):
            self.validate(self.doc,new)


if __name__=='__main__':unittest.main()
