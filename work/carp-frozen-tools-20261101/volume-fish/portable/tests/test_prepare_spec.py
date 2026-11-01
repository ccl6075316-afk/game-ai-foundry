"""Recipe preparation derives references/counts and rejects bad explicit declarations."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_spec import ROOT, main, prepare
from fish_asset_spec import input_paths, load_spec, preflight, sha
from glb_io import read_glb
from pack_fish_material_atlas import write_glb
from test_asset_core import fixture


class PrepareSpecTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='prepare-unit-', dir=ROOT/'work/fish-portable-tools')
        self.folder = Path(self.temp.name)
        path, _ = fixture(self.folder)
        self.original = load_spec(path)
        self.inputs = input_paths(self.original)
        self.parts = self.folder/'parts.json'
        self.parts.write_text(json.dumps({'parts':self.original['parts'], 'species':'synthetic', 'viewer':{'model_scale':2}}))
        self.output = self.folder/'prepared.json'

    def tearDown(self):
        self.temp.cleanup()

    def run_prepare(self, **extra):
        return prepare(**self.inputs, parts=self.parts, output=self.output, **extra)

    def test_actual_inventory_refs_owner_and_presentation(self):
        result = self.run_prepare()
        spec = load_spec(self.output)
        self.assertEqual(spec['expected']['vertices'], 3)
        self.assertEqual(spec['expected']['bones'], 1)
        self.assertEqual(spec['expected']['clips'], 0)
        self.assertNotIn('source_mesh_objects', spec['expected'])
        self.assertEqual(spec['source_mesh_name'], 'Mesh')
        self.assertEqual(spec['viewer']['model_scale'], 2)
        self.assertEqual(result['part_count'], 1)
        self.assertTrue(preflight(self.output)['ok'])
        for key, ref in spec['inputs'].items():
            self.assertFalse(Path(ref['path']).is_absolute())
            self.assertEqual(ref['sha256'], sha(self.inputs[key]))

    def test_utf8_parts_and_packing_on_non_utf8_hosts(self):
        raw=json.loads(self.parts.read_text())
        raw['parts'][0]['name']='鱼鳍·原像素'
        self.parts.write_text(json.dumps(raw,ensure_ascii=False),encoding='utf8')
        packing=self.inputs['packing_report']
        report=json.loads(packing.read_text())
        report['source_note']='像素画·nearest'
        packing.write_text(json.dumps(report,ensure_ascii=False),encoding='utf8')
        self.run_prepare()
        spec=load_spec(self.output)
        self.assertEqual(spec['parts'][0]['name'],'鱼鳍·原像素')
        self.assertTrue(preflight(self.output)['ok'])

    def test_variable_clip_inventory_and_explicit_source_owner(self):
        path = self.inputs['reference_glb']
        doc, binary = read_glb(path)
        binary = bytearray(binary); binary.extend(b'\0' * (-len(binary)%4))
        view = len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':12})
        binary.extend(np.asarray([0,1,2], dtype='<f4').tobytes())
        accessor = len(doc['accessors'])
        doc['accessors'].append({'bufferView':view,'componentType':5126,'count':3,'type':'SCALAR','min':[0],'max':[2]})
        doc['animations'] = [{'name':'FixtureClip','channels':[{'sampler':0,'target':{'node':1,'path':'rotation'}}],
                              'samplers':[{'input':accessor,'output':doc['meshes'][0]['primitives'][0]['attributes']['WEIGHTS_0']}]}]
        write_glb(path, doc, binary)
        packing = json.loads(self.inputs['packing_report'].read_text())
        packing['candidates']['merged-mask']['sha256'] = sha(path)
        self.inputs['packing_report'].write_text(json.dumps(packing))
        self.run_prepare(source_mesh_name='ExplicitEditableOwner')
        spec = load_spec(self.output)
        self.assertEqual(spec['expected']['clips'], 1)
        self.assertEqual(spec['expected']['animation_channels'], 1)
        self.assertEqual(spec['source_mesh_name'], 'ExplicitEditableOwner')

    def test_invalid_role_and_part_count_do_not_create_output(self):
        for rows in ([{**self.original['parts'][0], 'role':''}], [{**self.original['parts'][0], 'role':0}], [],
                     [{**self.original['parts'][0], 'opaque_uv':False}]):
            self.parts.write_text(json.dumps(rows))
            with self.assertRaises(ValueError): self.run_prepare()
            self.assertFalse(self.output.exists())
        self.parts.write_text(json.dumps(self.original['parts'] + [{'name':'Extra','role':'fin','source_node':'Extra','source_surface':0}]))
        with self.assertRaisesRegex(ValueError, 'part count'): self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_arbitrary_explicit_role_is_preserved(self):
        row = {**self.original['parts'][0], 'role':'gill_cover', 'opaque_uv':False}
        self.parts.write_text(json.dumps([row]))
        self.run_prepare()
        self.assertEqual(load_spec(self.output)['parts'], [row])

    def test_atlas_binding_failure_does_not_create_output(self):
        packing = json.loads(self.inputs['packing_report'].read_text())
        packing['atlas']['sha256'] = '0'*64
        self.inputs['packing_report'].write_text(json.dumps(packing))
        with self.assertRaisesRegex(ValueError, 'bind atlas'): self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_alias_cli_is_single_failure_json_and_preserves_source(self):
        before = sha(self.inputs['source_blend'])
        argv = [value for key, path in self.inputs.items() for value in ('--'+key.replace('_','-'), str(path))]
        result = io.StringIO()
        with contextlib.redirect_stdout(result):
            code = main(argv + ['--parts',str(self.parts),'--output',str(self.inputs['source_blend']),'--json'])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(result.getvalue())['ok'])
        self.assertEqual(sha(self.inputs['source_blend']), before)


if __name__ == '__main__':
    unittest.main()
