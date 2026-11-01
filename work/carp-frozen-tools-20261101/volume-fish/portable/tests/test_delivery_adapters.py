"""Analysis adapters must retain source arrays and reject stale ownership."""
import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
from test_asset_core import fixture
from fish_asset_spec import ROOT,load_spec,sha
from parts import freeze
from logical_document import logical_document
from glb_io import read_glb,arrays

class DeliveryAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='delivery-adapter-',dir=ROOT/'work/fish-portable-tools');self.folder=Path(self.tmp.name)
        specpath,self.model=fixture(self.folder);self.spec=load_spec(specpath);self.manifest=self.folder/'parts.json';freeze(self.model,self.spec,self.manifest)
    def tearDown(self):self.tmp.cleanup()
    def test_analysis_keeps_actual_directed_arrays_and_source_immutable(self):
        before=sha(self.model);original,binary=read_glb(self.model);doc,blob,opacity=logical_document(self.model,'Main',[],self.manifest)
        node=next(n for n in doc['nodes']if'mesh'in n);self.assertEqual(node['name'],'Main');self.assertTrue(opacity['ok'])
        src=original['meshes'][0]['primitives'][0];dst=doc['meshes'][node['mesh']]['primitives'][0]
        for semantic in src['attributes']:
            np.testing.assert_array_equal(arrays(original,binary,src['attributes'][semantic]),arrays(doc,blob,dst['attributes'][semantic]))
        np.testing.assert_array_equal(arrays(original,binary,src['indices']),arrays(doc,blob,dst['indices']));self.assertEqual(before,sha(self.model))
    def test_changed_manifest_model_hash_rejected(self):
        value=json.loads(self.manifest.read_text(encoding='utf8'));value['model_sha256']='0'*64;self.manifest.write_text(json.dumps(value),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Stale or altered'):logical_document(self.model,'Main',[],self.manifest)
    def test_wrong_anatomical_inventory_rejected(self):
        with self.assertRaisesRegex(ValueError,'inventory differs'):logical_document(self.model,'Main',['invented_fin'],self.manifest)
    def test_changed_ownership_range_rejected(self):
        value=json.loads(self.manifest.read_text(encoding='utf8'));value['parts'][0]['vertex_range'][1]-=1;self.manifest.write_text(json.dumps(value),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Stale or altered'):logical_document(self.model,'Main',[],self.manifest)

if __name__=='__main__':unittest.main()
