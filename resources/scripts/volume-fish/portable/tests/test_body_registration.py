"""Pixel ownership and stale-provenance regression for generated skin registration."""
import json,tempfile,unittest,sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fish_asset_spec import ROOT
from register_body_donor import register,sha
class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='skin-register-',dir=ROOT/'work/fish-portable-tools');self.base=Path(self.tmp.name)
        rng=np.random.default_rng(123);image=np.repeat(np.repeat(rng.integers(0,255,(96,96,3),dtype='uint8'),3,axis=0),3,axis=1);self.source=self.base/'source.png';self.generated=self.base/'generated.png';Image.fromarray(image).save(self.source);image[120:140,120:140]=[255,30,70];Image.fromarray(image).save(self.generated)
        self.config=self.base/'protection.json';self.config.write_text(json.dumps({'source_sha256':sha(self.source),'source_size':[288,288],'protected_polygons_px':[[[110,110],[150,110],[150,150],[110,150]]]}))
    def tearDown(self):self.tmp.cleanup()
    def test_protected_original_rgba_and_nearest_registered_pixels(self):
        result=register(self.source,self.generated,self.config,self.base/'out');self.assertTrue(result['protected_RGBA_exact']);self.assertGreater(result['registration']['inliers'],20)
        output=np.asarray(Image.open(self.base/'out/body-source.png'));original=np.asarray(Image.open(self.source).convert('RGBA'));np.testing.assert_array_equal(output[120:140,120:140],original[120:140,120:140])
    def test_stale_source_rejected_before_output(self):
        Image.new('RGB',(288,288)).save(self.source)
        with self.assertRaises(AssertionError):register(self.source,self.generated,self.config,self.base/'out')
        self.assertFalse((self.base/'out').exists())
    def test_feather_keeps_owned_pixels_and_does_not_restore_removed_fin_alpha(self):
        image=np.asarray(Image.open(self.source).convert('RGBA')).copy()
        image[90:110,90:145,:3]=[245,25,60]
        image[105:110,105:110,3]=0
        Image.fromarray(image).save(self.generated)
        config=json.loads(self.config.read_text());config['completion_feather_px']=6
        self.config.write_text(json.dumps(config))
        register(self.source,self.generated,self.config,self.base/'out')
        output=np.asarray(Image.open(self.base/'out/body-source.png'))
        original=np.asarray(Image.open(self.source).convert('RGBA'))
        np.testing.assert_array_equal(output[110:151,110:151],original[110:151,110:151])
        self.assertTrue((output[106:109,106:109,3]==0).all())
        np.testing.assert_array_equal(output[93:98,93:98],image[93:98,93:98])
        self.assertTrue(np.any(output[109,120,:3]!=image[109,120,:3]))
if __name__=='__main__':unittest.main()
