"""Offline adversarial gates for the eight-origin and GitHub timeline collector."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / "host" / "cross_timeline.py"
spec = importlib.util.spec_from_file_location("cross_timeline", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class CrossTimelineTests(unittest.TestCase):
    def test_eight_variants_exact(self):
        v = m.variants()
        self.assertEqual(len(v), 12)
        self.assertEqual(len(set(v)), 12)
        for d in m.DOMAINS:
            self.assertEqual(sum(d in x for x in v), 4)
        self.assertIn("http://cesarreis.com.br/", v)
        self.assertIn("https://www.reisoffice.com.br/", v)
        self.assertIn("http://reisoffice.com/", v)
        self.assertIn("https://www.reisoffice.com/", v)

    def test_https_archive_transport_and_no_open_redirect(self):
        self.assertTrue(m.approved(m.cdx_url(m.variants()[0])))
        self.assertTrue(m.approved(m.git_api("BLAKE3-team/BLAKE3", "issues", 1)))
        self.assertFalse(m.approved("http://web.archive.org/cdx/search/cdx?url=x"))
        self.assertFalse(m.approved("https://evil.test/cdx/search/cdx"))
        self.assertFalse(m.approved("https://api.github.com/repos/evil/bad/issues"))
        self.assertFalse(m.approved("https://www.reisoffice.com.br/evil", allow_live=True))
        self.assertFalse(m.approved("http://reisoffice.com.br/", allow_live=False))
        self.assertTrue(m.approved("http://reisoffice.com.br/", allow_live=True))

    def test_archive_does_not_collapse_scheme_or_www(self):
        v = "https://www.cesarreis.com.br/"
        raw = json.dumps([["timestamp","original","statuscode","mimetype","digest","length"],
            ["20080919000000",v,"200","text/html","A","100"],
            ["20080919000000","http://www.cesarreis.com.br/","200","text/html","B","100"],
            ["20080919000000","https://cesarreis.com.br/","301","text/html","C","100"]]).encode()
        rows, mismatch = m.cdx_rows(raw, v)
        self.assertEqual(len(rows), 1)
        self.assertEqual(mismatch, 2)
        self.assertEqual(rows[0]["provider_digest"], "A")

    def test_reis_domains_never_merge_by_suffix(self):
        archive_origin = "https://reisoffice.com/"
        distinct_origin = "https://reisoffice.com.br/"
        payload = json.dumps([["timestamp","original","statuscode","mimetype","digest","length"],
            ["20080501153240",archive_origin,"200","text/html","SAME","10"],
            ["20080501153240",distinct_origin,"200","text/html","SAME","10"]]).encode()
        observed, rejected = m.cdx_rows(payload, archive_origin)
        self.assertEqual((len(observed), rejected), (1, 1))
        self.assertEqual(observed[0]["original"], archive_origin)

    def test_missing_is_not_zero(self):
        self.assertEqual(m.cdx_rows(b"[]", m.variants()[0]), ([],0))
        with self.assertRaises(ValueError):
            m.cdx_rows(b"{}", m.variants()[0])

    def test_github_issue_and_pr_classification(self):
        payload = json.dumps([
            {"number":1,"created_at":"2020-01-01T00:00:00Z",
             "updated_at":"2020-01-02T00:00:00Z","closed_at":None},
            {"number":2,"pull_request":{},"created_at":"2020-01-03T00:00:00Z",
             "updated_at":"2020-01-04T00:00:00Z","closed_at":"2020-01-05T00:00:00Z"}]).encode()
        events = m.git_events("BLAKE3-team/BLAKE3","issues",payload)
        self.assertEqual(len(events), 5)
        self.assertIn("pull_request_closed_at", [x["kind"] for x in events])
        self.assertIn("issue_created_at", [x["kind"] for x in events])

    def test_author_and_committer_distinct(self):
        c = json.dumps([{"sha":"a"*40,
            "commit":{"author":{"date":"2020-01-02T00:00:00Z"},
                      "committer":{"date":"2020-01-03T00:00:00Z"}}}]).encode()
        ev = m.git_events("rafaelmeloreisnovo/BLAKE3","commits",c)
        self.assertEqual({x["kind"] for x in ev}, {"commit_author","commit_committer"})

    def test_temporal_matches_not_causality(self):
        origin = m.variants()[0]
        capture = [{"timestamp":"20200101000000","original":origin,"provider_digest":"D"}]
        event = [{"repo":"BLAKE3-team/BLAKE3","kind":"issue_created_at","ref":1,
                  "timestamp_utc":"2020-01-01T03:00:00+00:00","url":"https://github.com/BLAKE3-team/BLAKE3/issues/1"}]
        r = m.correlate(capture, event)
        self.assertEqual(r["counts"]["same_utc_day"], 1)
        self.assertFalse(r["candidate_rows"][0]["causal_claim"])

    def test_bounded_append_only_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "receipt1"
            m.create_receipt(dest, {"claim_allowed":False})
            self.assertTrue((dest / "SHA256SUMS").exists())
            with self.assertRaises(FileExistsError):
                m.create_receipt(dest, {"claim_allowed":True})

if __name__ == "__main__":
    unittest.main()
