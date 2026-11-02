import importlib.util, json, unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"host"/"replay_public.py"
s=importlib.util.spec_from_file_location("replay_public",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class TestReplay(unittest.TestCase):
 def test_host_and_paths(self):
  self.assertTrue(m.origin_allowed("http://www.cesarreis.com.br/","cesar_root"))
  self.assertTrue(m.origin_allowed("http://www.cesarreis.com.br/telas/prodfto.asp","prodfto_candidate"))
  self.assertFalse(m.origin_allowed("http://attacker.test/telas/prodfto.asp","prodfto_candidate"))
  self.assertFalse(m.origin_allowed("http://www.cesarreis.com.br/telas/prodfto.asp?token=x","prodfto_candidate"))
 def test_archive_memento_is_date_pinned(self):
  u=m.memento_url("20051215052151","http://www.cesarreis.com.br/","cesar_root")
  self.assertEqual(u,"https://web.archive.org/web/20051215052151id_/http://www.cesarreis.com.br/")
  with self.assertRaises(ValueError):m.memento_url("not-a-date","http://www.cesarreis.com.br/","cesar_root")
 def test_fixture_cdx_source_validated(self):
  data=json.dumps([["timestamp","original","statuscode","mimetype","digest","length"],
  ["20051215052151","http://www.cesarreis.com.br/telas/prodfto.asp","200",
  "text/html","MOCK","100"]])
  r=m.parse_cdx(data.encode(),"prodfto_candidate")
  self.assertEqual(r[0]["timestamp"],"20051215052151")
 def test_empty_is_unknown(self):
  self.assertEqual(m.parse_cdx(b"[]","cesar_root"),[])
 def test_cdx_cross_domain_is_denied(self):
  data=json.dumps([["timestamp","original","statuscode","mimetype","digest"],
  ["20051215052151","https://not-cesar.test/","200","text/html","MOCK"]])
  with self.assertRaisesRegex(ValueError,"MISMATCH"):m.parse_cdx(data.encode(),"cesar_root")
 def test_no_dynamic_path_generation(self):
  self.assertEqual(set(m.TARGETS),{"cesar_root","reis_root","prodfto_candidate"})
  self.assertEqual(m.MAX_MEMENTOS,2)
if __name__=="__main__":unittest.main()
