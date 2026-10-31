import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from native_body_skin_transport import native_skin_spans,native_roof_coordinates


class NativeBodySkinTest(unittest.TestCase):
    def test_isolated_fin_fragment_cannot_expand_body_donor_into_transparency(self):
        # Old min/max spans bridged the transparent gap to a disconnected fin.
        pixels=np.zeros((100,20,4));pixels[10:80,:,3]=1;pixels[90:95,:,3]=1
        spans=native_skin_spans(pixels,{'fins':[]})
        np.testing.assert_array_equal(spans,np.tile([20.,89.],(20,1)))
    def test_signed_transverse_donor_is_continuous_and_not_a_reflected_column(self):
        sections=[[0,.2,.8,.05],[1,.2,.8,.05]];spans=np.tile([20.,80.],(100,1));points=np.array([[0,-.02,.3],[0,0,.3],[0,.02,.3]])
        c={'latitude_fade_start':.5,'latitude_full':.93,'longitudinal_window':[.1,.2,.7,.8],'pixel_density':1.,'transverse_source_fraction':.1,'dorsal_center_fraction':.19,'ventral_center_fraction':.82}
        xy,amount,density=native_roof_coordinates(points,sections,100,100,spans,c)
        self.assertTrue(np.all(amount==1));self.assertTrue(np.all(np.diff(xy[:,1])>0));self.assertEqual(xy[0,0],xy[-1,0])
        outside=np.array([[.4,0,.3],[0,0,0]])
        self.assertTrue(np.all(native_roof_coordinates(outside,sections,100,100,spans,c)[1]==0))


if __name__=='__main__':unittest.main()
