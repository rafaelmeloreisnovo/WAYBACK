import importlib.util,json,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"host"/"fofi_crosswalk.py"
spec=importlib.util.spec_from_file_location("fofi_crosswalk",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class FofiTests(unittest.TestCase):
 def test_restrict_api_routes(self):
  self.assertTrue(m.permitted(m.github_url("BLAKE3-team/BLAKE3","pulls/comments")))
  self.assertTrue(m.permitted(m.github_url("rafaelmeloreisnovo/BLAKE3","issues")))
  for url in ["https://api.github.com/user","https://localhost/api",
              "http://api.github.com/repos/BLAKE3-team/BLAKE3/commits",
              "https://x:y@api.github.com/repos/BLAKE3-team/BLAKE3/commits"]:
   self.assertFalse(m.permitted(url),url)
 def test_allow_known_archives_and_three_windows(self):
  self.assertEqual(len(m.ERAS),3)
  self.assertEqual(len(m.WEB),3)
  self.assertTrue(m.permitted(m.cdx_url("cesar_prodfto",("2006","2018"))))
 def test_reject_historical_url_redirect_scope(self):
  self.assertFalse(m.origin_allowed("http://evil.org/telas/prodfto.asp","cesar_prodfto"))
  self.assertFalse(m.origin_allowed("http://www.cesarreis.com.br/telas/prodfto.asp?token=secret","cesar_prodfto"))
  with self.assertRaises(ValueError):
   m.replay_url("cesar_prodfto","2026","http://www.cesarreis.com.br/telas/prodfto.asp")
 def test_cdx_shape_and_provenance(self):
  data=json.dumps([["timestamp","original","statuscode","digest"],
     ["20080220071408","http://www.cesarreis.com.br/telas/prodfto.asp","200","MOCK"]]).encode()
  rows=m.parse_cdx(data,"cesar_prodfto")
  self.assertEqual(rows[0]["timestamp"],"20080220071408")
  self.assertEqual(m.parse_cdx(b"[]","cesar_prodfto"),[])
  with self.assertRaisesRegex(ValueError,"CDX_ORIGIN"):
   m.parse_cdx(data,"reis_root")
 def test_git_commit_other_users_are_not_attributed(self):
  obj=[{"sha":"a"*40,"parents":[{"sha":"b"*40}],
    "commit":{"message":"potential body with secret_token value",
     "committer":{"date":"2026-11-01T06:05:03Z"},
     "author":{"date":"2026-10-31T21:00:00Z"},
     "verification":{"reason":"unsigned"}},
    "author":{"login":"other-contributor"},"committer":{"login":"github-actions[bot]"}}]
  rows=m.clean_github(json.dumps(obj).encode(),"BLAKE3-team/BLAKE3","commits")
  self.assertEqual(rows[0]["verification"],"unsigned")
  self.assertEqual(rows[0]["parent_count"],1)
  self.assertNotIn("other-contributor",json.dumps(rows))
  self.assertNotIn("secret_token",json.dumps(rows))
 def test_pr_and_issue_separate(self):
  obj=[{"number":185,"title":"[HOLD]","body":"internal",
    "state":"closed","created_at":"2026-10-30T01:00:00Z",
    "merged_at":"2026-11-01T06:56:15Z","user":{"login":"someone"}}]
  rows=m.clean_github(json.dumps(obj).encode(),m.REPOS[1],"pulls")
  self.assertEqual(rows[0]["type"],"PR")
  self.assertEqual(rows[0]["merged_at"],"2026-11-01T06:56:15Z")
  self.assertNotIn("[HOLD]",json.dumps(rows))
  obj[0]["pull_request"]={"url":"x"}
  self.assertEqual(m.clean_github(json.dumps(obj).encode(),m.REPOS[1],"issues")[0]["type"],"PR")
 def test_comment_payload_only_hashed(self):
  j=[{"id":4321,"body":"personal name and address","created_at":"2026-11-01T06:00:00Z",
    "user":{"login":"contributor"},"html_url":"https://github.com/BLAKE3-team/BLAKE3/issues/1#issuecomment-4321"}]
  rows=m.clean_github(json.dumps(j).encode(),m.REPOS[0],"issues/comments")
  self.assertEqual(rows[0]["comment_id"],4321)
  self.assertNotIn("personal name",json.dumps(rows))
  self.assertNotIn("contributor",json.dumps(rows))
 def test_invalid_commit_sha_is_fail_closed(self):
  with self.assertRaisesRegex(ValueError,"GIT_SHA"):
   m.clean_github(b'[{"sha":"wrong","commit":{}}]',m.REPOS[0],"commits")
 def test_temporal_overlap_not_causality(self):
  web={"cesar_root":{"mementos":[{"capture_utc":"20261101060000","analysis":{"x":1}}]}}
  git={m.REPOS[0]:{"records":{"commits":[{"sha":"a"*40,"committer_date":"2026-11-01T13:00:00Z"}]}}}
  result=m.temporal_crosswalk(web,git)
  self.assertEqual(result["observed_pairs"],1)
  self.assertEqual(result["candidates"][0]["classification"],"SAME_CALENDAR_DAY_NOT_CAUSAL_EVIDENCE")
 def test_pr_issue_shadow_not_two_entities(self):
  o={repo:{"records":{"commits":[],"issues":[],"pulls":[],"comments":[],
        "issues/comments":[],"pulls/comments":[]}} for repo in m.REPOS}
  item={"type":"PR","number":185}
  o[m.REPOS[1]]["records"]["issues"].append(item)
  o[m.REPOS[1]]["records"]["pulls"].append(item)
  stats=m.git_uniqueness(o)
  self.assertEqual(stats["provider_rows"],2)
  self.assertEqual(stats["unique_scoped_ids"],1)
  self.assertEqual(stats["duplicate_pr_issue_shadows_or_ids"],1)
 def test_pinned_anchors_have_exact_prior_provenance(self):
  self.assertEqual(m.PINNED["cesar_prodfto"][1][0],"20080220071408")
  self.assertEqual(m.PINNED["reis_root"][0][0],"20080501153240")
  for name,anchors in m.PINNED.items():
   for ts,original in anchors:
    self.assertTrue(m.origin_allowed(original,name))
    self.assertTrue(m.permitted(m.replay_url(name,ts,original)))
 def test_terminal_gate_does_not_promote_partial_archive(self):
  web={k:{"mementos":[]} for k in m.WEB}
  web["cesar_root"]["mementos"]=[{"analysis":{"raw":"known"}}]
  git={repo:{"records":{"commits":[{"sha":"a"*40}]}} for repo in m.REPOS}
  gate=m.terminal_coverage(web,git)
  self.assertEqual(gate["state"],"BLOCKED_PARTIAL_SOURCES")
  self.assertIn("reis_root",gate["missing_archive_targets"])
  self.assertIn("cesar_prodfto",gate["missing_archive_targets"])
  web["cesar_prodfto"]["mementos"]=[{"analysis":{"raw":"known"}}]
  web["reis_root"]["mementos"]=[{"analysis":{"raw":"known"}}]
  self.assertEqual(m.terminal_coverage(web,git)["state"],"PASS_SCOPED")
if __name__=="__main__":unittest.main()
