"""Exercise 077 coverage rejection without a renderer or filesystem fixtures."""
import io
import unittest
import numpy as np
from PIL import Image
from validate_standalone_body import missing_pixels


def png(pixels):
    stream=io.BytesIO();Image.fromarray(pixels).save(stream,format='PNG');stream.seek(0)
    return stream


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.reference=np.zeros((12,12,4),dtype='uint8')
        self.reference[2:10,2:10]=255

    def test_opaque_dark_mouth_is_coverage(self):
        actual=self.reference.copy();actual[:,:,:3]=0
        self.assertEqual(missing_pixels(png(actual),png(self.reference)),0)

    def test_one_transparent_body_pixel_is_rejected(self):
        actual=self.reference.copy();actual[5,5,3]=0
        self.assertEqual(missing_pixels(png(actual),png(self.reference)),1)

    def test_transparency_outside_reference_is_not_a_body_hole(self):
        actual=self.reference.copy();actual[0,0,3]=255
        self.assertEqual(missing_pixels(png(actual),png(self.reference)),0)

    def test_empty_reference_is_not_a_pass(self):
        with self.assertRaisesRegex(AssertionError,'Empty reference'):
            missing_pixels(png(self.reference),png(np.zeros_like(self.reference)))


if __name__=='__main__':
    unittest.main()
