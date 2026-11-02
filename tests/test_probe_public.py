import importlib.util
import json
import unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"host"/"probe_public.py"
sp=importlib.util.spec_from_file_location("probe_public",p)
m=importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)
class TestPublicProbe(unittest.TestCase):
 def test_disjoint_era_windows(self):
  self.assertEqual(m.TIME_WINDOWS,(("1996","2005"),("2006","2018"),("2019","2026")))
  url=m.cdx_url("www.reisoffice.com.br","2019","2026")
  from urllib.parse import parse_qs,urlsplit
  q=parse_qs(urlsplit(url).query)
  self.assertEqual(q["from"],["2019"])
  self.assertEqual(q["to"],["2026"])
  self.assertEqual(q["limit"],["24"])
 def test_allowed(self):
  self.assertTrue(m.permitted(m.cdx_url("www.cesarreis.com.br")))
  self.assertTrue(m.permitted(m.git_url("BLAKE3-team/BLAKE3")))
 def test_private_host_and_redirect_blocked(self):
  for url in ["http://web.archive.org/cdx/search/cdx?url=x",
             "https://127.0.0.1/cdx/search/cdx",
             "https://web.archive.org/web/2020/https://x",
             "https://foo:bar@api.github.com/repos/BLAKE3-team/BLAKE3/commits",
             "https://api.github.com/user"]:
   self.assertFalse(m.permitted(url),url)
 def test_cdx_sanitized(self):
  x=json.dumps([["timestamp","original","statuscode","mimetype","digest","length"],
      ["20051215052151","http://www.cesarreis.com.br/telas/prodfto.asp?token=secret","200",
       "text/html","MOCK","64"]]).encode()
  r=m.read_cdx(x)
  self.assertEqual(r[0]["timestamp"],"20051215052151")
  self.assertNotIn("secret",json.dumps(r))
 def test_bad_date(self):
  x=json.dumps([["timestamp","original","statuscode"],["BAD","http://www.cesarreis.com.br/","200"]])
  with self.assertRaisesRegex(ValueError,"TIMESTAMP"):m.read_cdx(x)
 def test_git_no_identity_claim(self):
  x=json.dumps([{"sha":"a"*40,"commit":{"message":"one change","committer":{"date":"2026-11-01T06:56:14Z"}}}])
  y=m.read_git(x.encode())
  self.assertEqual(y[0]["timestamp"],"20261101065614")
  self.assertNotIn("one change",json.dumps(y))
 def test_temporal_candidate_is_not_claim(self):
  def fake(a,b,tolerance,out):
   import ctypes
   p=ctypes.cast(out,ctypes.POINTER(m.TimeMatch))
   p.contents.gap_seconds=2419201
   p.contents.month_apart_clock_match=1
   p.contents.within_window=0
   p.contents.same_clock_minute=1
   p.contents.month_distance=210
   p.contents.same_calendar_day=1
   p.contents.exact_one_month=0
   return 0
  archive={"www.cesarreis.com.br":[{"timestamp":"20030721165004"}]}
  git={"BLAKE3-team/BLAKE3":[{"timestamp":"20261101065614","sha":"a"*40}]}
  matched,truncated=m.compare(archive,git,fake)
  self.assertFalse(truncated)
  self.assertEqual(matched[0]["classification"],"SAME_CLOCK_DIFFERENT_DATE_NOT_CAUSAL_EVIDENCE")
  self.assertEqual(matched[0]["month_distance"],210)
  self.assertFalse(matched[0]["exact_one_month"])
if __name__=="__main__":unittest.main()
