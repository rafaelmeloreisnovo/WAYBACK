"""Offline, network-free falsifiers for three-lane archive/GitHub chain of custody."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

src = Path(__file__).resolve().parents[1] / "host" / "custody_cycle.py"
spec = importlib.util.spec_from_file_location("custody_cycle", src)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class CustodyTests(unittest.TestCase):
    def test_origin_matrix(self):
        for lane in ("cesar", "reis"):
            self.assertEqual(len(m.origins(lane)), 4)
            self.assertEqual(len(set(m.origins(lane))), 4)

    def test_original_url_validation(self):
        self.assertTrue(m.source_allowed("https://www.cesarreis.com.br/telas/prodfto.asp", "cesar"))
        self.assertFalse(m.source_allowed("https://outside.example/telas/prodfto.asp", "cesar"))
        self.assertFalse(m.source_allowed("http://user:secret@cesarreis.com.br/", "cesar"))
        self.assertFalse(m.source_allowed("https://www.cesarreis.com.br:444/", "cesar"))

    def test_cdx_preserves_variant_and_rejects_wrong_domain(self):
        origin = "http://cesarreis.com.br/"
        payload = json.dumps([["timestamp","original","statuscode","digest","mimetype","length"],
            ["20060701000000",origin + "telas/prodfto.asp","200","ABCDE","text/html","123"],
            ["20060701000000","https://www.reisoffice.com.br/","200","NO","text/html","11"]]).encode()
        found, bad = m.cdx_records(payload,"cesar")
        self.assertEqual((len(found),bad),(1,1))
        self.assertTrue(found[0]["source_url"].endswith("prodfto.asp"))

    def test_query_value_is_not_persisted(self):
        payload = json.dumps([["timestamp","original","statuscode","digest"],
            ["20060701000000","http://cesarreis.com.br/?token=private-example","200","H"]]).encode()
        found, _ = m.cdx_records(payload,"cesar")
        self.assertIsNone(found[0]["source_url"])
        self.assertNotIn("private-example",json.dumps({k:v for k,v in found[0].items() if k!="source_url"}))

    def test_years_in_html_comments_meta_links(self):
        h = m.HTMLSignals()
        h.feed("""<meta name="date" content="2006-07-01">
            <!-- updated 2008/02/20 --><a href="/ano/2005/report.html">x</a>""")
        dates = {d for r in h.signals for d in r["dates"]}
        self.assertIn("2006-07-01",dates)
        self.assertIn("2008/02/20",dates)
        self.assertIn("2005",dates)
        self.assertEqual(h.counts["comments"],1)
        self.assertNotIn("updated",str(h.signals))

    def test_commit_and_issue_timeline_helpers(self):
        self.assertEqual(m.iso("2025-01-01T13:10:00Z"),"2025-01-01T13:10:00+00:00")
        self.assertIsNone(m.iso("not a date"))
        self.assertTrue(m.mentions("BlackTrace discussion"))
        self.assertEqual(m.compact_event("comments","BLAKE3-team/BLAKE3",
            {"id":12,"body":"historical memo","created_at":"2025-02-01T00:00:00Z"})["at_utc"],
            "2025-02-01T00:00:00+00:00")

    def test_hard_budget_and_reject(self):
        g = m.Gate(1)
        data, state = g.get("https://attacker.test/steal")
        self.assertIsNone(data)
        self.assertEqual(state["status"],"BLOCKED_ALLOWLIST")
        self.assertEqual(len(g.requests),0)

    def test_month_rollover(self):
        c={"year":2005,"month":12,"offset":20}
        m.advance_month(c)
        self.assertEqual(c,{"year":2006,"month":1,"offset":0})

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            where = Path(root) / "receipt"
            st = m.state_for("blake")
            m.write_receipt(where,st,[],m.Gate(12),"SYNTHETIC_NO_NETWORK","blake")
            with self.assertRaises(FileExistsError):
                m.write_receipt(where,st,[],m.Gate(12),"SYNTHETIC_NO_NETWORK","blake")

    def test_previous_zip_sha_chain(self):
        with tempfile.TemporaryDirectory() as root:
            where=Path(root)/"receipt"
            st=m.state_for("cesar")
            m.write_receipt(where,st,[{"test":True}],m.Gate(12),"BOOTSTRAP","cesar")
            archive=io.BytesIO()
            with zipfile.ZipFile(archive,"w") as z:
                for path in where.iterdir(): z.write(path,arcname=path.name)
            prev,digest=m.verify_previous(archive.getvalue(),"cesar")
            self.assertEqual(prev["cycle_index"],1)
            self.assertEqual(len(digest),64)
            with self.assertRaises(ValueError): m.verify_previous(archive.getvalue(),"blake")

    def test_tampered_previous_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            where=Path(root)/"receipt"
            m.write_receipt(where,m.state_for("reis"),[],m.Gate(12),"BOOTSTRAP","reis")
            archive=io.BytesIO()
            with zipfile.ZipFile(archive,"w") as z:
                z.writestr("receipt.json",b'{"tampered":true}')
                for name in ("cursor.json","SHA256SUMS"):
                    z.write(where/name,arcname=name)
            with self.assertRaises(ValueError): m.verify_previous(archive.getvalue(),"reis")

if __name__=="__main__":
    unittest.main()
