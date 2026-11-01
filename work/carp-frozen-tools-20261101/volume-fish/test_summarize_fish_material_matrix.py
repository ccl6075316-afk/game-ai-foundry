"""Reject missing actual GPU work and misleading timing interpretations."""
import unittest
from summarize_fish_material_matrix import check_samples

def static_case():
    row={'motion_call_ms':0.,'engine_refresh_wait_ms':1.,'forced_draw_readback_ms':9.,'controlled_step_ms':10.,'draw_calls':900,'primitives':171000,'explicit_draw_signals':1}
    window={'can_draw':False,'minimized':True,'always_on_top':False,'root_visible':True,'viewport_rid_valid':True,'viewport_size':[1280,720],'viewport_update_mode':4}
    report={'protocol':'controlled-v1','kind':'fish_material_controlled_case','raw_samples':[dict(row)for _ in range(60)],'explicit_draw_signals_total':75,'actual_pose_changed':False,'actual_GPU_image_changed':False,'first_pose_sha256':'same-pose','last_pose_sha256':'same-pose','first_image_RGBA_sha256':'same-image','last_image_RGBA_sha256':'same-image','first_window_state':dict(window),'last_window_state':dict(window),'gpu_timer_available':False}
    for key in ('motion_call_ms','engine_refresh_wait_ms','forced_draw_readback_ms','controlled_step_ms','draw_calls','primitives'):report[key]={name:row[key]for name in ('p50','p95','min','max','mean')}
    return report

class ControlledValidity(unittest.TestCase):
    def test_minimized_window_is_valid_when_actual_GPU_work_present(self):
        r=check_samples(static_case(),100,False,'baseline9');self.assertEqual(r['primitives']['p50'],171000)
    def test_extra_or_missing_GPU_draw_rejected(self):
        for signals in (0,2):
            r=static_case();r['raw_samples'][20]['explicit_draw_signals']=signals
            with self.assertRaises(AssertionError):check_samples(r,100,False,'baseline9')
    def test_incomplete_geometry_work_rejected(self):
        for field,value in [('draw_calls',100),('primitives',0)]:
            r=static_case();r['raw_samples'][20][field]=value
            with self.assertRaises(AssertionError):check_samples(r,100,False,'baseline9')
    def test_no_pose_or_GPU_change_cannot_count_as_motion(self):
        with self.assertRaises(AssertionError):check_samples(static_case(),100,True,'baseline9')
    def test_partial_samples_and_extra_automatic_draws_rejected(self):
        r=static_case();r['raw_samples'].pop()
        with self.assertRaises(AssertionError):check_samples(r,100,False,'baseline9')
        r=static_case();r['explicit_draw_signals_total']=76
        with self.assertRaises(AssertionError):check_samples(r,100,False,'baseline9')
    def test_false_GPU_timer_and_inconsistent_step_composition_rejected(self):
        r=static_case();r['gpu_timer_available']=True
        with self.assertRaises(AssertionError):check_samples(r,100,False,'baseline9')
        r=static_case();r['raw_samples'][25]['controlled_step_ms']=1
        with self.assertRaises(AssertionError):check_samples(r,100,False,'baseline9')
if __name__=='__main__':unittest.main()
