"""Actual image-domain negatives; no Blender or production asset mutations."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_native_lip_donor import ROOT, check


class NativeLipDonorTests(unittest.TestCase):
    def setUp(self):
        temporary_root = ROOT / 'work/fish-portable-tools'
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rgba = np.full((64, 64, 4), 255, np.uint8)
        self.config = {'source': 'source.png', 'source_size': [64, 64],
                       'upper_inner_edge_px': [[10, 20], [20, 20], [30, 20]],
                       'lower_inner_edge_px': [[10, 40], [20, 40], [30, 40]],
                       'lip_source_transport': {'source_start_x': 10, 'source_end_x': 30,
                         'complete_native_lip': {'upper_width_px': 4, 'lower_width_px': 4, 'outer_fade_px': 2},
                         'inner_lip_return_px': 3, 'inner_lip_fade_px': 2}}

    def run_check(self):
        path = self.root / 'source.png'
        Image.fromarray(self.rgba).save(path)
        self.config['source_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        return check(self.config, self.root)

    def test_safe_bands_ignore_unrelated_transparency(self):
        self.rgba[2, 40, 3] = 0
        self.assertTrue(self.run_check()['ok'])

    def test_protected_lip_transparency_rejected(self):
        self.rgba[18, 18, 3] = 0
        report = self.run_check()
        self.assertFalse(report['ok'])
        self.assertIn([18, 18], report['lips'][0]['first_invalid_alpha_pixels_xy'])

    def test_exact_author_alpha_threshold(self):
        self.rgba[18, 18, 3] = 242
        self.assertFalse(self.run_check()['ok'])
        self.rgba[18, 18, 3] = 243
        self.assertTrue(self.run_check()['ok'])

    def test_half_pixel_rounding_can_reach_transparent_cell(self):
        self.config['upper_inner_edge_px'] = [[10, 21.5], [20, 21.5], [30, 21.5]]
        self.rgba[22, 20, 3] = 0
        self.assertFalse(self.run_check()['ok'])

    def test_whole_fade_band_out_of_bounds_rejected(self):
        self.config['lip_source_transport']['complete_native_lip']['upper_width_px'] = 25
        report = self.run_check()
        self.assertFalse(report['ok'])
        self.assertGreater(report['lips'][0]['out_of_bounds_segment_count'], 0)

    def test_changed_source_hash_rejected(self):
        self.run_check()
        (self.root / 'source.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Source hash changed'):
            check(self.config, self.root)

    def test_cavity_transport_cannot_inherit_outward_lip_pass(self):
        self.config['lip_source_transport']['transport_oral'] = True
        with self.assertRaisesRegex(ValueError, 'cannot approve'):
            self.run_check()


if __name__ == '__main__':
    unittest.main()
