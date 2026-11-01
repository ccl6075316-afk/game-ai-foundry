import copy,unittest
from runtime_pose_coverage import validate_runtime_pose_coverage

class NativeCoverage(unittest.TestCase):
    def sample(self):
        return dict(native_cycle_revision=1,expected_fins=['Pectoral_left'],native_clip_seconds=4.,samples=[dict(action='Static',seconds=0.)]+[dict(action='Native',seconds=4.*i/25) for i in range(25)])
    def test_complete(self):
        self.assertEqual(validate_runtime_pose_coverage(self.sample()),{'Static':1,'Native':25})
    def test_invalid_variants(self):
        good=self.sample()
        variants=[]
        x=copy.deepcopy(good);x['samples'].pop();variants.append(x)
        x=copy.deepcopy(good);x['samples'][5]['seconds']=x['samples'][4]['seconds'];variants.append(x)
        x=copy.deepcopy(good);x['samples'][3]['seconds']=float('nan');variants.append(x)
        x=copy.deepcopy(good);x['motion_range_revision']=1;variants.append(x)
        x=copy.deepcopy(good);del x['native_cycle_revision'];variants.append(x)
        x=copy.deepcopy(good);x['expected_fins']=[];variants.append(x)
        for value in variants:
            with self.assertRaises(ValueError):validate_runtime_pose_coverage(value)
if __name__=='__main__':unittest.main()
