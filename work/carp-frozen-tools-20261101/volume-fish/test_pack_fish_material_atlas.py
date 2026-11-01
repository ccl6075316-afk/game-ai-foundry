"""Behavioral controls for atlas opacity, wrapping, linear colors and input safety."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
import pack_fish_material_atlas as pack


class PackingBehavior(unittest.TestCase):
    def fixture(self,path):
        doc={'asset':{'version':'2.0'},'scenes':[{'nodes':[0]}],'scene':0,'nodes':[{'name':'root','children':[1,2]},{'name':'Body','mesh':0,'skin':0},{'name':'Fin','mesh':1,'skin':0}],'skins':[{'joints':[0]}],'meshes':[],'materials':[],'textures':[{'source':0,'sampler':0}],'images':[],'samplers':[{'magFilter':9728,'minFilter':9728,'wrapS':10497,'wrapT':10497}],'accessors':[],'bufferViews':[]}
        binary=bytearray()
        def blob(raw):
            binary.extend(b'\0'*((-len(binary))%4));idx=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':len(raw)});binary.extend(raw);return idx
        def accessor(value,ctype,kind):
            idx=len(doc['accessors']);doc['accessors'].append({'bufferView':blob(value.tobytes()),'componentType':ctype,'type':kind,'count':len(value)});return idx
        attrs={
            'POSITION':accessor(np.asarray([[0,0,0],[1,0,0],[0,1,0]],dtype='<f4'),5126,'VEC3'),
            'NORMAL':accessor(np.tile(np.asarray([0,0,1],dtype='<f4'),(3,1)),5126,'VEC3'),
            'TEXCOORD_0':accessor(np.asarray([[-.25,-.25],[1.25,0],[0,1.25]],dtype='<f4'),5126,'VEC2'),
            'JOINTS_0':accessor(np.zeros((3,4),dtype=np.uint8),5121,'VEC4'),
            'WEIGHTS_0':accessor(np.tile(np.asarray([1,0,0,0],dtype='<f4'),(3,1)),5126,'VEC4')}
        indices=accessor(np.asarray([[0],[1],[2]],dtype='<u2'),5123,'SCALAR')
        pixels=np.asarray([[[12,34,56,0],[78,90,12,255]],[[34,56,78,255],[90,12,34,0]]],dtype=np.uint8)
        encoded=io.BytesIO();Image.fromarray(pixels).save(encoded,format='PNG');doc['images']=[{'bufferView':blob(encoded.getvalue()),'mimeType':'image/png'}]
        for name,alpha in [('Body','OPAQUE'),('Fin','MASK')]:
            doc['materials'].append({'name':name,'alphaMode':alpha,'pbrMetallicRoughness':{'metallicFactor':0,'baseColorTexture':{'index':0}}})
        doc['materials'].append({'name':'Cavity','alphaMode':'OPAQUE','pbrMetallicRoughness':{'metallicFactor':0,'baseColorFactor':[.188,.187,.173,1]}})
        doc['meshes']=[{'primitives':[{'attributes':attrs,'indices':indices,'material':0},{'attributes':attrs,'indices':indices,'material':2}]},{'primitives':[{'attributes':attrs,'indices':indices,'material':1}]}]
        pack.write_glb(path,doc,binary)

    def test_constant_color_survives_importer_ignoring_vertex_colors(self):
        with tempfile.TemporaryDirectory(prefix='atlas-test-',dir=Path(__file__).resolve().parents[3]/'work') as temp:
            root=Path(temp);source=root/'source.glb';self.fixture(source)
            report=pack.build(source,root/'output');oral=report['parts'][1];x,y=oral['atlas_placement'];atlas=np.asarray(Image.open(root/'output/atlas.png'))
            # Known sRGB8 encoding of the authored .188/.187/.173 linear factor.
            self.assertEqual(atlas[y+3,x+3].tolist(),[120,120,115,255])
            doc,binary=pack.read_glb(root/'output/merged-mask.glb')
            self.assertNotIn('COLOR_0',doc['meshes'][0]['primitives'][0]['attributes'])

    def test_complete_packing_preserves_body_opacity_fin_alpha_and_linear_cavity(self):
        with tempfile.TemporaryDirectory(prefix='atlas-test-',dir=Path(__file__).resolve().parents[3]/'work') as temp:
            root=Path(temp);source=root/'source.glb';self.fixture(source);before=pack.sha(source)
            report=pack.build(source,root/'output')
            self.assertEqual((report['triangles'],report['vertices'],report['surface_count_after']),(3,9,1))
            self.assertEqual(pack.sha(source),before)
            atlas=np.asarray(Image.open(root/'output/atlas.png'))
            parts=report['parts']
            for p in (parts[0],parts[2]):
                x,y=p['atlas_placement'];w,h=p['virtual_crop_size'];crop=atlas[y:y+h,x:x+w]
                if p['source_alpha_mode']=='OPAQUE':self.assertTrue((crop[:,:,3]==255).all())
                else:self.assertTrue((crop[:,:,3]==0).any())
            d,b=pack.read_glb(root/'output/merged-mask.glb');pr=d['meshes'][0]['primitives'][0]
            self.assertNotIn('COLOR_0',pr['attributes'])
            self.assertEqual(parts[1]['constant_color_encoding']['atlas_sRGB8_RGBA'],[120,120,115,255])
            self.assertLess(report['nearest_sampling_probe']['max_pixel_coordinate_error'],.001)
            # Same atlas and geometry; alpha behavior is the only variant change.
            e,eb=pack.read_glb(root/'output/merged-opaque.glb');self.assertEqual(b,eb)
            d['materials'][0]['alphaMode']='OPAQUE';d['materials'][0].pop('alphaCutoff');self.assertEqual(d,e)

    def test_alias_and_overwrite_rejected_without_changing_input(self):
        with tempfile.TemporaryDirectory(prefix='atlas-test-',dir=Path(__file__).resolve().parents[3]/'work') as temp:
            root=Path(temp);source=root/'source.glb';self.fixture(source);before=pack.sha(source)
            with self.assertRaises(AssertionError):pack.build(source,source)
            out=root/'output';out.mkdir();(out/'merged-mask.glb').write_bytes(b'Existing reviewer evidence')
            with self.assertRaises(AssertionError):pack.build(source,out)
            self.assertEqual((out/'merged-mask.glb').read_bytes(),b'Existing reviewer evidence')
            self.assertEqual(pack.sha(source),before)

    def test_incompatible_materials_rejected_before_any_output(self):
        with tempfile.TemporaryDirectory(prefix='atlas-test-',dir=Path(__file__).resolve().parents[3]/'work') as temp:
            root=Path(temp);source=root/'source.glb';self.fixture(source);d,b=pack.read_glb(source);d['materials'][1]['doubleSided']=True;pack.write_glb(source,d,b)
            with self.assertRaises(AssertionError):pack.build(source,root/'output')
            self.assertFalse((root/'output').exists())

    def test_repository_external_named_work_directory_rejected(self):
        with tempfile.TemporaryDirectory(prefix='atlas-test-',dir=Path(__file__).resolve().parents[3]/'work') as temp:
            source=Path(temp)/'source.glb';self.fixture(source);before=pack.sha(source)
            with self.assertRaises(AssertionError):pack.check_paths(source,Path('/private/tmp/work/atlas-must-not-write'))
            self.assertEqual(pack.sha(source),before)

    def test_extension_texture_reference_rejected_before_output(self):
        with tempfile.TemporaryDirectory(prefix='atlas-test-',dir=Path(__file__).resolve().parents[3]/'work') as temp:
            root=Path(temp);source=root/'source.glb';self.fixture(source);d,b=pack.read_glb(source)
            for material in d['materials']:material['extensions']={'KHR_materials_specular':{'specularFactor':0,'specularTexture':{'index':0}}}
            pack.write_glb(source,d,b)
            with self.assertRaises(AssertionError):pack.build(source,root/'output')
            self.assertFalse((root/'output').exists())

if __name__=='__main__':unittest.main()
