import unittest
from fish_budget import triangle_policy, check_triangle_budget


class DisplayBudgetTests(unittest.TestCase):
    def test_sharks_have_minimum_6500_8000_tier_and_keep_larger_tiers(self):
        for species in ['blacktip_reef_shark', 'scalloped_hammerhead', 'great_hammerhead', 'smooth_hammerhead', 'whale_shark']:
            for cm, preferred, hard in [
                (30, 6500, 8000),
                (120, 6500, 8000),
                (150, 6500, 8000),
                (300, 6500, 8000),
                (300.001, 8500, 10000),
                (600, 8500, 10000),
                (600.001, 12000, 15000),
                (800, 12000, 15000),
            ]:
                with self.subTest(species=species, cm=cm):
                    p = triangle_policy(cm, species=species)
                    self.assertEqual((p['preferred_triangles'], p['hard_triangles']), (preferred, hard))
                    self.assertTrue(check_triangle_budget(hard, cm, species=species)['ok'])
                    with self.assertRaisesRegex(ValueError, 'exceeded'):
                        check_triangle_budget(hard + 1, cm, species=species)

    def test_dorsal_complex_species_and_explicit_group(self):
        for species in ['loggerhead', 'loggerhead_sea_turtle', 'skye_manta']:
            with self.subTest(species=species):
                p = triangle_policy(100, species=species)
                self.assertEqual(p['anatomical_group'], 'dorsal_complex')
                self.assertEqual((p['preferred_triangles'], p['hard_triangles']), (6500, 8000))
                self.assertTrue(check_triangle_budget(8000, 100, species=species)['ok'])
                with self.assertRaisesRegex(ValueError, 'exceeded'):
                    check_triangle_budget(8001, 100, species=species)
        # Giant manta (>300cm) promotes cleanly to 8500/10000
        p_big = triangle_policy(420, species='giant_manta', anatomical_group='dorsal_complex')
        self.assertEqual((p_big['preferred_triangles'], p_big['hard_triangles']), (8500, 10000))

    def test_multi_limb_cephalopods_and_crustaceans_get_8500_10000_even_when_small(self):
        for species, cm in [('blue_ring_octopus', 20), ('reef_squid', 45), ('spiny_lobster', 50)]:
            with self.subTest(species=species):
                p = triangle_policy(cm, species=species, anatomical_group='multi_limb')
                self.assertEqual(p['anatomical_group'], 'multi_limb')
                self.assertEqual((p['preferred_triangles'], p['hard_triangles']), (8500, 10000))
                self.assertTrue(check_triangle_budget(9200, cm, species=species, anatomical_group='multi_limb')['ok'])
                with self.assertRaisesRegex(ValueError, 'exceeded'):
                    check_triangle_budget(10001, cm, species=species, anatomical_group='multi_limb')

    def test_standard_bony_pbr_closeup_species_within_5000_tier(self):
        for species, tris, cm in [('red_seabream', 2810, 30), ('black_seabream', 2852, 35), ('sea_bass', 2858, 60)]:
            with self.subTest(species=species):
                res = check_triangle_budget(tris, cm, species=species)
                self.assertTrue(res['ok'])
                self.assertTrue(res['preferred_met'])
                self.assertEqual(res['hard_triangles'], 5000)

    def test_new_species_uses_explicit_anatomical_group_not_name_guessing(self):
        self.assertEqual(triangle_policy(80, species='new_species', anatomical_group='shark')['hard_triangles'], 8000)
        self.assertEqual(triangle_policy(80, species='shark_named_nonshark')['hard_triangles'], 5000)
        with self.assertRaises(ValueError):
            triangle_policy(80, species='x', anatomical_group='unknown_group')

    def test_strict_thresholds_and_lod_targets(self):
        for cm, preferred, hard, lod3_max in [
            (73.66, 4000, 5000, 64),
            (120, 4000, 5000, 64),
            (120.0001, 6500, 8000, 96),
            (150, 6500, 8000, 96),
            (300, 6500, 8000, 96),
            (300.0001, 8500, 10000, 128),
            (600, 8500, 10000, 128),
            (600.0001, 12000, 15000, 240),
            (800, 12000, 15000, 240),
        ]:
            with self.subTest(cm=cm):
                p = triangle_policy(cm)
                self.assertEqual((p['preferred_triangles'], p['hard_triangles']), (preferred, hard))
                self.assertEqual(p['lod_targets']['lod3'][1], lod3_max)

    def test_declared_config_cannot_promote_small_fish_to_larger_tier(self):
        with self.assertRaisesRegex(ValueError, 'display-length'):
            check_triangle_budget(5500, 73.66, 6000)
        with self.assertRaisesRegex(ValueError, 'exceeded'):
            check_triangle_budget(4500, 150, 4000)

    def test_invalid_inputs_rejected(self):
        for value in [None, True, 0, -1, float('nan'), float('inf'), '150']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                triangle_policy(value)
        for value in [True, 1.5, -1, None]:
            with self.assertRaises(ValueError):
                check_triangle_budget(value, 150)


if __name__ == '__main__':
    unittest.main()
