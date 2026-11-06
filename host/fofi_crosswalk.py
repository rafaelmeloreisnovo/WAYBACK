#!/usr/bin/env python3
"""RAFAELIA FOFI->FIFO: bounded public provenance crosswalk.
Hosted HTTPS/JSON/ctypes is intentionally NOT freestanding. C core parses bytes.
This job samples public sources only. Never submits forms, collects photos,
executes scripts, or attributes an account event to a human operator.
"""
import argparse
import ctypes
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

REPOS=("BLAKE3-team/BLAKE3","rafaelmeloreisnovo/BLAKE3")
WEB={
 "cesar_root":("www.cesarreis.com.br","/"),
 "cesar_prodfto":("www.cesarreis.com.br","/telas/prodfto.asp"),
 "reis_root":("www.reisoffice.com.br","/"),
}
# Exact public publisher route linked to the historical photo notice.
NEWS={"ace_event":("www.aceguarulhos.com.br","/blog/sucesso-no-evento-dos-40-anos-da-ace-guarulhos-1/")}
TARGETS={**WEB,**NEWS}
ERAS=(("1996","2005"),("2006","2018"),("2019","2026"))
# Prior observed timestamp/path pairs: WAYBACK Actions 41387565492,
# artifact 13115766821. Pinned replay is NOT independently verified WARC.
PINNED={
 "cesar_prodfto":(("20060919065932","http://www.cesarreis.com.br/telas/prodfto.asp"),
                  ("20080220071408","http://www.cesarreis.com.br/telas/prodfto.asp")),
 "reis_root":(("20080501153240","http://www.reisoffice.com.br/"),
              ("20080630181756","http://www.reisoffice.com.br/"))
}
API_KINDS=("commits","pulls","issues","issues/comments","pulls/comments","comments")
PROVIDER_LIMIT=10
CDX_LIMIT=3
MAX_BYTES=1048576
MAX_API=262144
MAX_MARKERS=48
MAX_PAIRS=32

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,request,fp,code,msg,headers,newurl):return None

def digest(value):
 if isinstance(value,str):value=value.encode("utf-8")
 return hashlib.sha256(value).hexdigest()

def github_url(repo,kind):
 if repo not in REPOS or kind not in API_KINDS:raise ValueError("UNAUTHORIZED_API_ROUTE")
 base="https://api.github.com/repos/"+repo+"/"+kind
 q={"per_page":str(PROVIDER_LIMIT)}
 if kind in ("pulls","issues"):q.update({"state":"all","sort":"updated","direction":"desc"})
 if kind in ("issues/comments","pulls/comments"):q.update({"sort":"updated","direction":"desc"})
 return base+"?"+urllib.parse.urlencode(q)

def cdx_url(name,era):
 if name not in TARGETS or era not in ERAS:raise ValueError("UNAUTHORIZED_ARCHIVE_SCOPE")
 host,path=TARGETS[name]
 return "https://web.archive.org/cdx/search/cdx?"+urllib.parse.urlencode({
  "url":host+path,"output":"json",
  "fl":"timestamp,original,statuscode,mimetype,digest,length",
  "filter":"statuscode:200","from":era[0],"to":era[1],
  "limit":str(CDX_LIMIT)})

def origin_allowed(original,name):
 try:
  p=urllib.parse.urlsplit(original)
  host,path=TARGETS[name]
  return (p.scheme in ("http","https") and p.hostname==host and
    p.path.lower()==path.lower() and p.port in (None,80,443) and
    not p.username and not p.password and not p.query and not p.fragment)
 except ValueError:return False

def replay_url(name,timestamp,original):
 if name not in TARGETS or not origin_allowed(original,name) or not re.fullmatch(r"[0-9]{14}",timestamp):
  raise ValueError("MEMENTO_SOURCE_MISMATCH")
 return "https://web.archive.org/web/"+timestamp+"id_/"+original

def permitted(url):
 try:
  p=urllib.parse.urlsplit(url)
  if p.scheme!="https" or p.username or p.password or p.fragment or p.port not in (None,443):return False
  if p.hostname=="api.github.com":
   if any(re.fullmatch("/repos/"+re.escape(r)+"/commits/[0-9a-f]{40}",p.path) for r in REPOS):
    return p.query=="per_page=10"
   return p.path in ["/repos/"+r+"/"+k for r in REPOS for k in API_KINDS]
  if p.hostname=="web.archive.org":
   return p.path=="/cdx/search/cdx" or bool(re.fullmatch(r"/web/[0-9]{14}id_/https?://[^/]+/.*",p.path))
  return False
 except ValueError:return False

def get(url,cap):
 if not permitted(url):return None,"BLOCKED_SCOPE"
 req=urllib.request.Request(url,headers={
  "User-Agent":"RAFAELIA-WAYBACK-FOFI-ReadOnly/1.0",
  "Accept":"application/json" if "api.github.com" in url or "/cdx/" in url else "text/html"})
 try:
  with urllib.request.build_opener(NoRedirect()).open(req,timeout=15) as response:
   if response.status!=200 or not permitted(response.geturl()):return None,"BLOCKED_REDIRECT_OR_HTTP"
   typ=response.headers.get("Content-Type","").split(";")[0].strip().lower()
   if "/web/" in url and typ not in ("text/html","application/xhtml+xml"):
    return None,"NON_HTML_MEMENTO"
   data=response.read(cap+1)
   if len(data)>cap:return None,"BLOCKED_SIZE_LIMIT"
   return data,"OK_200"
 except urllib.error.HTTPError as e:return None,"TOKEN_VAZIO_HTTP_"+str(e.code)
 except Exception as e:return None,"TOKEN_VAZIO_"+type(e).__name__

def parse_cdx(raw,name):
 data=json.loads(raw)
 if data==[]:return []
 if not isinstance(data,list) or len(data)<1 or not isinstance(data[0],list):raise ValueError("CDX_SCHEMA")
 cols=data[0]
 if len(cols)!=len(set(cols)) or not set(("timestamp","original","statuscode","digest")).issubset(cols):
  raise ValueError("CDX_COLUMNS")
 result=[]
 for row in data[1:CDX_LIMIT+1]:
  if not isinstance(row,list) or len(row)!=len(cols):raise ValueError("CDX_ROW")
  e=dict(zip(cols,row))
  if not isinstance(e["timestamp"],str) or not re.fullmatch("[0-9]{14}",e["timestamp"]):
   raise ValueError("CDX_TIMESTAMP")
  if not origin_allowed(e["original"],name):raise ValueError("CDX_ORIGIN")
  if e["statuscode"]!="200":continue
  result.append(e)
 return result

def account_ref(user):
 login=(user or {}).get("login") if isinstance(user,dict) else None
 return digest(login.lower()) if isinstance(login,str) else None

def clean_date(s):
 if not isinstance(s,str):return None
 try:
  d=dt.datetime.fromisoformat(s.replace("Z","+00:00"))
  if d.tzinfo is None or d.utcoffset()!=dt.timedelta(0):return None
  return d.strftime("%Y-%m-%dT%H:%M:%SZ")
 except ValueError:return None

def clean_github(raw,repo,kind):
 data=json.loads(raw)
 if not isinstance(data,list):raise ValueError("GITHUB_SCHEMA")
 out=[]
 for o in data[:PROVIDER_LIMIT]:
  if not isinstance(o,dict):raise ValueError("GITHUB_ROW")
  e={"kind":kind,"repo":repo}
  if kind=="commits":
   sha=o.get("sha")
   if not isinstance(sha,str) or not re.fullmatch("[0-9a-f]{40}",sha):raise ValueError("GIT_SHA")
   c=o.get("commit") or {}
   e.update({"sha":sha,"parent_count":len(o.get("parents") or []),
     "author_date":clean_date((c.get("author") or {}).get("date")),
     "committer_date":clean_date((c.get("committer") or {}).get("date")),
     "message_sha256":digest(str(c.get("message",""))),
     "author_account_sha256":account_ref(o.get("author")),
     "committer_account_sha256":account_ref(o.get("committer")),
     "verification":str((c.get("verification") or {}).get("reason") or "TOKEN_VAZIO")[:40],
     "url":"https://github.com/"+repo+"/commit/"+sha})
  elif kind in ("issues","pulls"):
   n=o.get("number")
   if not isinstance(n,int) or n<1:raise ValueError("ISSUE_ID")
   is_pr=kind=="pulls" or bool(o.get("pull_request"))
   e.update({"number":n,"type":"PR" if is_pr else "ISSUE",
     "created_at":clean_date(o.get("created_at")),
     "updated_at":clean_date(o.get("updated_at")),
     "closed_at":clean_date(o.get("closed_at")),
     "merged_at":clean_date(o.get("merged_at")),
     "state":str(o.get("state","TOKEN_VAZIO"))[:20],
     "title_sha256":digest(str(o.get("title",""))),
     "body_sha256":digest(str(o.get("body") or "")),
     "actor_account_sha256":account_ref(o.get("user")),
     "url":"https://github.com/"+repo+("/pull/" if is_pr else "/issues/")+str(n)})
  else:
   n=o.get("id")
   if not isinstance(n,int) or n<1:raise ValueError("COMMENT_ID")
   e.update({"comment_id":n,"created_at":clean_date(o.get("created_at")),
     "updated_at":clean_date(o.get("updated_at")),
     "body_sha256":digest(str(o.get("body") or "")),
     "actor_account_sha256":account_ref(o.get("user")),
     "url":str(o.get("html_url") or "")[:400]})
  out.append(e)
 return out

class Span(ctypes.Structure):
 _fields_=[("begin",ctypes.c_uint),("end",ctypes.c_uint)]
class HtmlEvent(ctypes.Structure):
 _fields_=[("kind",ctypes.c_uint),("flags",ctypes.c_uint),
           ("tag",Span),("value",Span),("auxiliary",Span)]
class Marker(ctypes.Structure):
 _fields_=[("begin",ctypes.c_uint),("end",ctypes.c_uint),
           ("yyyymmdd",ctypes.c_uint),("notation",ctypes.c_uint)]
class Snapshot(ctypes.Structure):
 _fields_=[("raw_sha256",ctypes.c_ubyte*32),("first_keywords_sha256",ctypes.c_ubyte*32),
  ("first_link_sha256",ctypes.c_ubyte*32)]+[(n,ctypes.c_uint) for n in (
  "has_keywords","has_link","tags","meta","keywords","description",
  "links","images","forms","scripts","comments","post_forms","get_forms",
  "onsubmit_forms","asp_refs","inc_refs")]

def load_core(path):
 lib=ctypes.CDLL(str(Path(path).resolve()))
 lib.raf_next_date.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint),ctypes.POINTER(Marker)]
 lib.raf_next_date.restype=ctypes.c_int
 lib.raf_html_next.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint),ctypes.POINTER(HtmlEvent)]
 lib.raf_html_next.restype=ctypes.c_int
 lib.raf_snapshot_bytes.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(Snapshot)]
 lib.raf_snapshot_bytes.restype=ctypes.c_int
 return lib

def analyze_html(lib,raw):
 if len(raw)>MAX_BYTES:raise ValueError("TOO_LARGE")
 buffer=ctypes.create_string_buffer(raw)
 snap=Snapshot()
 if lib.raf_snapshot_bytes(buffer,len(raw),ctypes.byref(snap))!=0:raise ValueError("SNAPSHOT_REJECTED")
 cur=ctypes.c_uint(0);event=HtmlEvent();ranges=[];edge_map={};edge_occurrences=0
 # Assign a date token's context only if it lies inside a parsed tag.
 while True:
  rc=lib.raf_html_next(buffer,len(raw),ctypes.byref(cur),ctypes.byref(event))
  if rc==0:break
  if rc<0:raise ValueError("HTML_EVENT_REJECTED")
  if not(event.flags&128) and event.kind in (2,3,4,5,6,7,8):
   resource = None
   if event.kind in (3,4,7,8):
    a,b=int(event.value.begin),int(event.value.end)
    if b<a or b>len(raw):raise ValueError("HTML_SOURCE_SPAN_OUTSIDE_BUFFER")
    if b>a:
     edge_occurrences+=1
     value=raw[a:b]
     identifier=digest(value)
     resource=(a,b,identifier)
     path=value.split(b"?",1)[0].split(b"#",1)[0].lower()
     extension=path.rsplit(b".",1)[-1] if b"." in path else b""
     if extension not in (b"asp",b"htm",b"html",b"jpg",b"jpeg",b"png",
                          b"gif",b"pdf",b"js",b"css",b"inc",b"webp"):extension=b"other"
     edge_map.setdefault(identifier,{"href_sha256":identifier,
       "source_tag":{3:"ANCHOR",4:"IMAGE_REF",7:"SCRIPT_REF",8:"RESOURCE_REF"}.get(event.kind,"OTHER"),
       "extension":extension.decode("ascii")})
   ranges.append((int(event.tag.begin),int(event.tag.end),int(event.kind),resource))
 cur=ctypes.c_uint(0);mark=Marker();dates=[];total=0
 while True:
  rc=lib.raf_next_date(buffer,len(raw),ctypes.byref(cur),ctypes.byref(mark))
  if rc==0:break
  if rc<0:raise ValueError("DATE_MARKER_REJECTED")
  total+=1
  if len(dates)<MAX_MARKERS:
   context="HTML_TEXT_OR_SCRIPT_UNKNOWN"
   marker_resource=None
   for a,b,k,resource in ranges:
    if a<=mark.begin and mark.end<=b:
     if resource and resource[0]<=mark.begin and mark.end<=resource[1]:
      marker_resource=resource[2]
     context={2:"HTML_COMMENT_LITERAL",3:"LINK_TAG_LITERAL",4:"IMAGE_TAG_LITERAL",
              5:"FORM_TAG_LITERAL",6:"META_TAG_LITERAL",7:"SCRIPT_TAG_LITERAL",
              8:"RESOURCE_TAG_LITERAL"}.get(k,"OTHER_TAG_LITERAL")
     break
   dates.append({"yyyymmdd":int(mark.yyyymmdd),"notation":int(mark.notation),
                 "context":context,"attribute_value_sha256":marker_resource,"byte_offset":int(mark.begin)})
 fields=("links","images","comments","forms","scripts","keywords","description",
  "post_forms","get_forms","onsubmit_forms","asp_refs","inc_refs")
 return {"html_replay_sha256":bytes(snap.raw_sha256).hex(),
  "keywords_value_sha256":bytes(snap.first_keywords_sha256).hex() if snap.has_keywords else None,
  "first_link_sha256":bytes(snap.first_link_sha256).hex() if snap.has_link else None,
  "counts":{k:int(getattr(snap,k)) for k in fields},
  "date_marker_count":total,"date_marker_examples":dates,
  "date_marker_truncated":total>MAX_MARKERS,
  "date_semantics":"LITERAL_IN_HTML_NOT_PHOTO_CREATION_PROOF",
  "edge_occurrences":edge_occurrences,
  "distinct_hashed_edges":len(edge_map),
  "edge_index_sha256":digest("|".join(sorted(edge_map))),
  "hashed_edge_examples":[edge_map[k] for k in sorted(edge_map)[:64]],
  "edge_examples_truncated":len(edge_map)>64,
  "edge_semantics":"RAW_REPLAY_ATTRIBUTE_HASH_NOT_CANONICAL_ORIGIN_LINK"}

def compare_replays(mementos):
 changes=[]
 previous={}
 for b in sorted(mementos,key=lambda row:row["capture_utc"]):
  original=b["original_url"]
  a=previous.get(original)
  previous[original]=b
  if a and a["capture_utc"]!=b["capture_utc"] and "analysis" in a and "analysis" in b:
    x,y=a["analysis"],b["analysis"]
    changes.append({"original_url":original,"from":a["capture_utc"],"to":b["capture_utc"],
      "body_changed":x["html_replay_sha256"]!=y["html_replay_sha256"],
      "keywords_changed":x["keywords_value_sha256"]!=y["keywords_value_sha256"],
      "links_count_changed":x["counts"]["links"]!=y["counts"]["links"],
      "image_count_changed":x["counts"]["images"]!=y["counts"]["images"],
      "distinct_edge_count_changed":x["distinct_hashed_edges"]!=y["distinct_hashed_edges"],
      "edge_set_changed":x["edge_index_sha256"]!=y["edge_index_sha256"],
      "source_class":"REPLAY_HTML_NOT_ORIGINAL_WARC"})
 return changes

def collect_web(lib):
 out={}
 for name in TARGETS:
  obj={"query_statuses":{},"mementos":[],"coverage":"SAMPLED_NOT_EXHAUSTIVE"}
  for era in ERAS:
   key=era[0]+"_"+era[1]
   cdx,state=get(cdx_url(name,era),MAX_API)
   obj["query_statuses"][key]=state
   if cdx is None:continue
   try:records=parse_cdx(cdx,name)
   except Exception as e:
    obj["query_statuses"][key]="TOKEN_VAZIO_SCHEMA_"+type(e).__name__
    continue
   if not records:obj["query_statuses"][key]="OK_EMPTY_BOUNDED_QUERY"
   # One memento from each era. Never brute-force links/images.
   if not records:continue
   selected=[records[0]]
   if len(records)>1 and records[-1]["timestamp"]!=records[0]["timestamp"]:
    selected.append(records[-1])
   for item in selected:
    ts=item["timestamp"]
    url=replay_url(name,ts,item["original"])
    body,status=get(url,MAX_BYTES)
    entry={"original_url":item["original"],"capture_utc":ts,"source_ref_sha256":digest(url),
      "provider_digest":str(item.get("digest",""))[:80],"state":status,
      "evidence_locator":"CURRENT_BOUNDED_CDX"}
    if body is not None:
     try:entry["analysis"]=analyze_html(lib,body)
     except Exception as e:entry["state"]="TOKEN_VAZIO_C_REJECTED_"+type(e).__name__
    obj["mementos"].append(entry)
  # Evidence anchors from the previous independent Wayback replay run.
  # Never use the pinned dates as a substitute for current CDX metadata.
  observed={(x["capture_utc"],x["original_url"]) for x in obj["mementos"]}
  for timestamp,original in PINNED.get(name,()):
   if (timestamp,original) in observed:continue
   url=replay_url(name,timestamp,original)
   body,status=get(url,MAX_BYTES)
   entry={"original_url":original,"capture_utc":timestamp,"source_ref_sha256":digest(url),
          "provider_digest":"TOKEN_VAZIO_PREVIOUS_RECEIPT",
          "state":status,"evidence_locator":"PINNED_PRIOR_RUN_41387565492"}
   if body is not None:
    try:entry["analysis"]=analyze_html(lib,body)
    except Exception as e:entry["state"]="TOKEN_VAZIO_C_REJECTED_"+type(e).__name__
   obj["mementos"].append(entry)
  obj["mementos"].sort(key=lambda x:x["capture_utc"])
  obj["changes"]=compare_replays(obj["mementos"])
  out[name]=obj
 return out

def patch_sample(repo,sha):
 # One immutable commit per repository, first provider page only.
 url="https://api.github.com/repos/"+repo+"/commits/"+sha+"?per_page=10"
 raw,state=get(url,MAX_API)
 result={"commit_sha":sha,"url":url,"state":state,"scope":"FIRST_TEN_FILE_RECORDS"}
 if raw is None:return result
 try:
  data=json.loads(raw)
  if not isinstance(data,dict) or data.get("sha")!=sha or not isinstance(data.get("files"),list):
   raise ValueError("COMMIT_DETAIL_SCHEMA")
  files=[]
  for item in data["files"][:10]:
   if not isinstance(item,dict) or not isinstance(item.get("filename"),str):
    raise ValueError("COMMIT_FILE_SCHEMA")
   patch=item.get("patch")
   markers=[]
   if isinstance(patch,str):
    for line in patch.splitlines():
     if line[:1] not in ("+","-"):continue
     for token in re.findall(r"(?<![0-9])[0-9]{4}-[0-9]{2}-[0-9]{2}(?![0-9])",line[1:]):
      try:dt.date.fromisoformat(token)
      except ValueError:continue
      markers.append({"literal":token,"side":"added" if line[0]=="+" else "removed"})
      if len(markers)==16:break
     if len(markers)==16:break
   files.append({"path":item["filename"],"patch_sha256":digest(patch) if isinstance(patch,str) else None,
    "patch_state":"PROVIDER_FRAGMENT" if isinstance(patch,str) else "TOKEN_VAZIO_PATCH",
    "date_literals_first_16":markers})
  result["files"]=files
 except (ValueError,TypeError):result["state"]="TOKEN_VAZIO_COMMIT_DETAIL_SCHEMA"
 return result

def collect_github():
 out={}
 for repo in REPOS:
  obj={"records":{},"status":{}}
  for kind in API_KINDS:
   raw,state=get(github_url(repo,kind),MAX_API)
   obj["status"][kind]=state
   if raw is None:obj["records"][kind]=[];continue
   try:obj["records"][kind]=clean_github(raw,repo,kind)
   except Exception as e:
    obj["records"][kind]=[]
    obj["status"][kind]="TOKEN_VAZIO_SCHEMA_"+type(e).__name__
  commits=obj["records"]["commits"]
  obj["code_change_sample"]=patch_sample(repo,commits[0]["sha"]) if commits else {"state":"TOKEN_VAZIO_COMMIT"}
  out[repo]=obj
 return out

def git_uniqueness(git):
 keys=set();total=0;shadow=0
 for repo,v in git.items():
  for kind,rows in v["records"].items():
   for item in rows:
    total+=1
    if kind=="commits":key=(repo,"commit",item.get("sha"))
    elif kind in ("pulls","issues"):key=(repo,item.get("type"),item.get("number"))
    else:key=(repo,kind,item.get("comment_id"))
    if key in keys:shadow+=1
    keys.add(key)
 official={x["sha"] for x in git[REPOS[0]]["records"].get("commits",[])}
 fork={x["sha"] for x in git[REPOS[1]]["records"].get("commits",[])}
 return {"provider_rows":total,"unique_scoped_ids":len(keys),
  "duplicate_pr_issue_shadows_or_ids":shadow,
  "same_sha_in_both_scoped_repo_samples":len(official&fork),
  "scope":"sampled provider observations, not global repository history or personal actions"}

def terminal_coverage(web,git):
 missing_archive=[name for name in WEB
                  if not any("analysis" in m for m in web.get(name,{}).get("mementos",[]))]
 missing_git=[repo for repo,v in git.items()
              if not v["records"].get("commits")]
 return {"state":"PASS_SCOPED" if not missing_archive and not missing_git else "BLOCKED_PARTIAL_SOURCES",
         "supplemental_news_status":{name:("REPLAY_OBSERVED" if any("analysis" in m for m in web.get(name,{}).get("mementos",[])) else "TOKEN_VAZIO_NEWS_REPLAY") for name in NEWS},
         "required_archive_targets":list(WEB),"missing_archive_targets":missing_archive,
         "required_git_repositories":list(REPOS),"missing_git_repositories":missing_git,
         "rule":"Every requested site has >=1 HTML replay and every required Git repo has >=1 commit. No WARC/rights/authorship claims."}

def temporal_crosswalk(web,git):
 web_days=[]
 for name,scope in web.items():
  for x in scope["mementos"]:
   if "analysis" in x:web_days.append((name,x["capture_utc"][:8]))
 candidates=[];total=0
 for repo,p in git.items():
  for kind,rows in p["records"].items():
   for item in rows:
    dates=[item.get(k) for k in ("committer_date","created_at","updated_at")]
    for date in dates:
     if not date:continue
     day=date[:10].replace("-","")
     for name,stamp in web_days:
      if day==stamp:
       total+=1
       if len(candidates)<MAX_PAIRS:
        candidates.append({"archive_target":name,"capture_day":stamp,
          "git_repo":repo,"git_kind":kind,"github_id":item.get("sha") or item.get("number") or item.get("comment_id"),
          "classification":"SAME_CALENDAR_DAY_NOT_CAUSAL_EVIDENCE"})
 return {"observed_pairs":total,"candidates":candidates,"truncated":total>MAX_PAIRS}

def code_literal_crosswalk(web,git):
 index={}
 for target,scope in web.items():
  for capture in scope["mementos"]:
   for mark in capture.get("analysis",{}).get("date_marker_examples",[]):
    key=str(mark["yyyymmdd"])
    index.setdefault(key,[]).append({"target":target,"original_url":capture["original_url"],
     "capture_utc":capture["capture_utc"],"marker":mark})
 pairs=[]
 count=0
 for repo,scope in git.items():
  sample=scope.get("code_change_sample",{})
  for file in sample.get("files",[]):
   for marker in file["date_literals_first_16"]:
    for hit in index.get(marker["literal"].replace("-",""),[]):
     count+=1
     if len(pairs)<MAX_PAIRS:
      pairs.append({"repository":repo,"commit_sha":sample["commit_sha"],"path":file["path"],
       "patch_sha256":file["patch_sha256"],"code_marker":marker,"html_marker":hit})
 return {"observed_pairs":count,"examples":pairs,"truncated":count>len(pairs),
  "scope":"PROVIDER_PATCH_AND_REPLAY_SAMPLES_ONLY","classification":"EQUAL_DATE_LITERAL_ONLY"}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--core-so",required=True)
 ap.add_argument("--out",required=True)
 ap.add_argument("--offline",action="store_true",help="Pure offline bounded contract test")
 args=ap.parse_args()
 lib=load_core(args.core_so)
 if args.offline:
  sample=b"<img src='photo_2008-02-20.jpg'><!-- archived 20/02/2008 --><a href='prodfto.asp'>x</a>"
  record={"kind":"SYNTHETIC_ONLY","sample":analyze_html(lib,sample)}
 else:
  web=collect_web(lib);git=collect_github()
  record={"schema":"rafaelia.wayback.fofi_crosswalk.v1",
   "observed_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
   "source_boundaries":{"WAYBACK":"public replay HTML bytes, not original WARC",
    "GITHUB":"public REST API event metadata, not proof of human actor"},
   "archive":web,"github":git,
   "git_scope_uniqueness":git_uniqueness(git),
   "evidence_gate":terminal_coverage(web,git),
   "temporal_crosswalk":temporal_crosswalk(web,git),
   "code_literal_crosswalk":code_literal_crosswalk(web,git),
   "rights":"TOKEN_VAZIO_REVIEW_REQUIRED","human_operator":"TOKEN_VAZIO_NOT_ATTESTED",
   "html_bodies_published":False,"photo_bodies_downloaded":False,
   "comment_bodies_published":False,"claim_allowed":False}
 out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
 payload=(json.dumps(record,sort_keys=True,ensure_ascii=True,separators=(",",":"))+"\n").encode("ascii")
 (out/"receipt.json").write_bytes(payload)
 (out/"SHA256SUMS").write_text(digest(payload)+"  receipt.json\n")
 print("FOFI_STATUS="+json.dumps({"kind":record.get("schema","synthetic"),
  "archive":{k:{"mementos":sum("analysis" in x for x in v["mementos"]),
                  "status":v["query_statuses"]} for k,v in record.get("archive",{}).items()},
  "github":{k:{kind:len(v["records"][kind]) for kind in API_KINDS} for k,v in record.get("github",{}).items()},
  "git_unique":record.get("git_scope_uniqueness",{}).get("unique_scoped_ids","TOKEN_VAZIO"),
  "coverage_gate":record.get("evidence_gate",{}).get("state","TOKEN_VAZIO"),
  "temporal_pairs":record.get("temporal_crosswalk",{}).get("observed_pairs","TOKEN_VAZIO")},
  sort_keys=True))
if __name__=="__main__":main()

