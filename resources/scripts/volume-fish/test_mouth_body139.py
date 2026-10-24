import unittest
import numpy as np
from validate_mouth_body139 import closed,binding_matches

class ActualBodyClosureTests(unittest.TestCase):
    def setUp(self):
        self.vertices=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
        self.faces=[[0,2,1],[0,1,3],[1,2,3],[2,0,3]]
    def test_material_seam_vertices_still_form_one_closed_shell(self):
        parts=[{'vertices':[self.vertices[i] for i in face],'triangles':[0,1,2]} for face in self.faces]
        self.assertEqual(closed(parts)['triangles'],4)
    def test_missing_body_face_blocks(self):
        with self.assertRaisesRegex(AssertionError,'Open/nonmanifold'):
            closed([{'vertices':self.vertices,'triangles':self.faces[:-1]}])
    def test_collapsed_face_cannot_hide_behind_weld(self):
        v=self.vertices+[[1e-9,0.,0.]]
        with self.assertRaisesRegex(AssertionError,'Degenerate'):
            closed([{'vertices':v,'triangles':self.faces+[[0,4,1]]}])
    def test_nonfinite_geometry_blocks(self):
        self.vertices[0][0]=float('nan')
        with self.assertRaisesRegex(AssertionError,'Invalid/empty'):
            closed([{'vertices':self.vertices,'triangles':self.faces}])
    def binding(self):
        weights=np.tile(np.array([.7,.2,.1,0],np.float32),(4,1));codes=(weights*np.float32(65535)).astype(np.uint16)
        ref={'vertices':self.vertices,'triangles':self.faces,'joints':[[0,1,2,3]]*4,'weights':weights.tolist()}
        actual={'skin_bind_names':['root','body','tail','spare'],'parts':[{'vertices':self.vertices,'triangles':self.faces,'bones':[0,1,2,3]*4,'weights':(codes.astype(np.float32)/65535).ravel().tolist()}]}
        return actual,ref
    def test_engine_quantized_weights_preserve_the_exact_binding(self):
        actual,ref=self.binding();binding_matches(actual,[ref],actual['skin_bind_names'])
    def test_one_weight_code_change_is_not_hidden_by_float_tolerance(self):
        actual,ref=self.binding();actual['parts'][0]['weights'][0]+=1/65535
        with self.assertRaisesRegex(AssertionError,'packed skin weights'):
            binding_matches(actual,[ref],actual['skin_bind_names'])
if __name__=='__main__':unittest.main()
