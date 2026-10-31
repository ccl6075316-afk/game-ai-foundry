import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from task_power import keep_system_awake

class PowerScopeTests(unittest.TestCase):
 def test_system_only_request_and_prior_state_restored_even_on_failure(self):
  calls=[]
  def api(flags):calls.append(flags);return 0x80000000
  with self.assertRaisesRegex(RuntimeError,'job failed'):
   with keep_system_awake(api):raise RuntimeError('job failed')
  self.assertEqual(calls,[0x80000001,0x80000000])
 def test_rejected_request_does_not_start_job(self):
  ran=False
  with self.assertRaises(OSError):
   with keep_system_awake(lambda _:0):ran=True
  self.assertFalse(ran)
