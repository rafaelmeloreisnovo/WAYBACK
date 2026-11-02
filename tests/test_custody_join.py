import importlib.util
import sys
from pathlib import Path
import unittest

HOST = Path(__file__).resolve().parents[1] / "host"
sys.path.insert(0, str(HOST))
spec = importlib.util.spec_from_file_location("custody_join", HOST / "custody_join.py")
join = importlib.util.module_from_spec(spec)
spec.loader.exec_module(join)

class TestJoin(unittest.TestCase):
    def test_same_day_is_not_causation(self):
        b = {"records": [{"kind": "commit", "repo": "BLAKE3-team/BLAKE3",
                          "sha": "a"*40, "author_at": "2006-07-01T04:00:00+00:00"}]}
        c = {"records": [{"kind": "cdx_page", "origin": "http://cesarreis.com.br/",
                          "records": [{"timestamp": "20060701000000",
                                      "url_sha256": "b"*64, "provider_digest": "D"}]}]}
        r = join.join_receipts({"blake": b, "cesar": c, "reis": {"records": []}})
        self.assertGreater(r["candidate_counts"]["same_utc_day"], 0)
        self.assertFalse(r["claim_allowed"])
        self.assertEqual(r["candidates"][0]["relation"], "TEMPORAL_ONLY_NOT_CAUSAL")

    def test_empty_sample_never_claims_exhaustive(self):
        r = join.join_receipts({"blake": {"records": []},
                                "cesar": {"records": []}, "reis": {"records": []}})
        self.assertEqual(r["archive_captures_observed_this_cycle"], 0)
        self.assertIn("NOT_EXHAUSTIVE", r["scope"])

    def test_invalid_archive_timestamp_does_not_join(self):
        c = {"records": [{"kind": "cdx_page", "origin": "http://cesarreis.com.br/",
                          "records": [{"timestamp": "INVALID",
                                      "url_sha256": "b"*64}]}]}
        r = join.join_receipts({"blake": {"records": []}, "cesar": c,
                                "reis": {"records": []}})
        self.assertEqual(r["candidate_counts"]["within_30d"], 0)

if __name__ == "__main__":
    unittest.main()
