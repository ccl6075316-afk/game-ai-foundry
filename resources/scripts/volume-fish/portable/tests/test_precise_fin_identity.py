"""Regression for Godot part reindexing that previously split the wrong edges."""
import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fin_vertex_identity import native_to_actual

class ActualFinIdentityTests(unittest.TestCase):
    def test_permuted_actual_vertices_recover_native_faces(self):
        points=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],float)
        permutation=np.array([2,0,3,1]);actual=points[permutation]*.6
        mapping=native_to_actual(points,actual,.6)
        native_triangle=np.array([0,1,2])
        np.testing.assert_array_equal(actual[mapping[native_triangle]],points[native_triangle]*.6)
        self.assertFalse(np.array_equal(actual[native_triangle],points[native_triangle]*.6))

    def test_same_count_wrong_shape_is_rejected(self):
        points=np.eye(3)
        with self.assertRaises(AssertionError):native_to_actual(points,points+.001,1)

    def test_coincident_or_ambiguous_vertices_are_rejected(self):
        points=np.array([[0,0,0],[0,0,0],[1,0,0]])
        with self.assertRaises(AssertionError):native_to_actual(points,points,1)

if __name__=='__main__':unittest.main()
