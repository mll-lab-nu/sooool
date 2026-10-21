import concurrent.futures as cf
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'environments/touhou'),str(ROOT/'environments/asterix')]
from runtime.subscription import retain_input
from latency_bench.latency.inverse_cdf import sample_inverse_cdf
from latency_bench.latency.samplers import build_sampler
from latency_bench.core.clock import EnvClock
from research.scheduler import VirtualScheduler
from simulate_5x import delay_frames

class ReproductionContracts(unittest.TestCase):
    def test_interpolated_cdf_bounds_and_quantiles(self):
        rng=random.Random(1)
        for q,expected in [(0,100),(.25,150),(.5,200),(.75,300),(1,400)]:
            self.assertEqual(sample_inverse_cdf(rng,[0,.5,1],[100,200,400],quantile=q),expected)

    def test_original_fitted_sampler_is_reproducible(self):
        config={'method':'iid','profile_path':str(ROOT/'profiles/asterix/sol-ultrafast-v3/window3_eighth_c8'),'seed':44}
        a=build_sampler(config,clock=EnvClock(env_fps=7.5,obs_fps=1.875))
        b=build_sampler(config,clock=EnvClock(env_fps=7.5,obs_fps=1.875))
        self.assertEqual([a.sample({"worker_slot":0})for _ in range(20)],[b.sample({"worker_slot":0})for _ in range(20)])

    def test_asterix_clock_uses_virtual_fps_not_display_fps(self):
        self.assertEqual(delay_frames(1.28),16)

    def test_early_ready_does_not_release_terminal_capacity(self):
        s=VirtualScheduler(1,first_valid_per_observation=True)
        f=cf.Future();f.set_result({'answer':'[3,1,0,0,12]'})
        s.submit(0,f,4,terminal_delay_frames=10)
        self.assertEqual(s.advance(3),[])
        self.assertEqual(s.advance(4)[0]['status'],'applied')
        self.assertFalse(s.available())
        s.advance(10);self.assertTrue(s.available())

    def test_read_only_cohort_input_is_reused_and_mismatch_rejected(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'prompt.txt';p.write_bytes(b'original');p.chmod(0o444)
            retain_input(p,b'original')
            with self.assertRaises(ValueError):retain_input(p,b'different')
            self.assertEqual(p.read_bytes(),b'original')

    def test_packaged_profiles_have_full_samples_and_joint_slots(self):
        a=json.loads((ROOT/'profiles/asterix/latency_5x_empirical.json').read_text())
        self.assertEqual(len(a['capture_to_complete_seconds']),596)
        t=json.loads((ROOT/'profiles/touhou/profile-control-early-study-v1.json').read_text())
        self.assertEqual(t['k'],4)
        self.assertEqual(len(t['joint_delay_vectors_s']),len(t['joint_terminal_delay_vectors_s']))
        self.assertTrue(all(len(v)==4 for v in t['joint_delay_vectors_s']))
        r=json.loads((ROOT/'profiles/rhythm/selected-native-joint.json').read_text())
        self.assertEqual(len(r['rows']),85)
        self.assertTrue(all(all(k in x for k in ('api_rtt_s','frame_age_s','transport_overhead_s'))for x in r['rows']))

if __name__=='__main__':unittest.main()
