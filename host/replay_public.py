#!/usr/bin/env python3
"""WAYBACK: bounded historical memento -> freestanding C snapshot bridge.
Hosted adapter for public TLS/CDX/Wayback ONLY. Neither WARC nor original ASP.
No HTML, photographs, URLs with sensitive query strings or form bodies published.
"""
import argparse, ctypes, datetime as dt, hashlib, json, re
from pathlib import Path
import urllib.parse, urllib.request, urllib.error

TARGETS={
 "cesar_root":("www.cesarreis.com.br","/"),
 "reis_root":("www.reisoffice.com.br","/"),
 "prodfto_candidate":("www.cesarreis.com.br","/telas/prodfto.asp"),
}
MAX_HTTP=1048576
MAX_CDX=65536
MAX_MEMENTOS=2
MAX_LINKS=48

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):return None

class Snapshot(ctypes.Structure):
 _fields_=[("raw_sha256",ctypes.c_ubyte*32),
  ("first_keywords_sha256",ctypes.c_ubyte*32),
  ("first_link_sha256",ctypes.c_ubyte*32)]+[(name,ctypes.c_uint) for name in (
  "has_keywords","has_link","tags","meta","keywords","description",
  "links","images","forms","scripts","comments","post_forms","get_forms",
  "onsubmit_forms","asp_refs","inc_refs")]
class Span(ctypes.Structure):
 _fields_=[("begin",ctypes.c_uint),("end",ctypes.c_uint)]
class Event(ctypes.Structure):
 _fields_=[("kind",ctypes.c_uint),("flags",ctypes.c_uint),
           ("tag",Span),("value",Span),("auxiliary",Span)]
def hex32(b):return bytes(b).hex()
def origin_allowed(url,target):
 try:
  u=urllib.parse.urlsplit(url)
  host,path=TARGETS[target]
  return (u.scheme in ("http","https") and u.hostname==host and
          u.port in (None,80,443) and not u.username and not u.password
          and u.path.lower()==path.lower() and not u.query and not u.fragment)
 except ValueError:return False
def cdx_url(target,descending=False):
 host,path=TARGETS[target]
 q=urllib.parse.urlencode({"url":host+path,"output":"json",
   "fl":"timestamp,original,statuscode,mimetype,digest,length",
   "filter":"statuscode:200","from":"1996","to":"2026","limit":"3",
   "sort":"reverse" if descending else "default"})
 return "https://web.archive.org/cdx/search/cdx?"+q
def memento_url(timestamp,original,target):
 if not re.fullmatch("[0-9]{14}",timestamp) or not origin_allowed(original,target):
  raise ValueError("INVALID_MEMENTO_PROVENANCE")
 return "https://web.archive.org/web/"+timestamp+"id_/"+original
def fetch(url,limit):
 p=urllib.parse.urlsplit(url)
 if p.scheme!="https" or p.hostname!="web.archive.org" or p.username or p.password or p.fragment:
  return None,{"state":"BLOCKED_ARCHIVE_SCOPE"}
 if not (p.path=="/cdx/search/cdx" or p.path.startswith("/web/")):
  return None,{"state":"BLOCKED_ARCHIVE_PATH"}
 request=urllib.request.Request(url,headers={
  "User-Agent":"RAFAELIA-WAYBACK-ScopedReadOnly/1.0",
  "Accept":"application/json" if p.path.startswith("/cdx/") else "text/html"})
 try:
  opener=urllib.request.build_opener(NoRedirect())
  with opener.open(request,timeout=12) as response:
   if response.status!=200:return None,{"state":"HTTP_"+str(response.status)}
   content_type=response.headers.get("Content-Type","").split(";")[0].lower()
   if p.path.startswith("/web/") and content_type not in ("text/html","application/xhtml+xml"):
    return None,{"state":"NON_HTML_MEMENTO","content_type":content_type[:50]}
   raw=response.read(limit+1)
   if len(raw)>limit:return None,{"state":"BODY_TOO_LARGE"}
   return raw,{"state":"HTTP_200","content_type":content_type[:50]}
 except urllib.error.HTTPError as e:
  return None,{"state":"HTTP_"+str(e.code)}
 except Exception as e:
  return None,{"state":"TOKEN_VAZIO_"+type(e).__name__}
def parse_cdx(raw,target):
 j=json.loads(raw)
 if j==[]:return []
 if not isinstance(j,list) or not j or not isinstance(j[0],list):
  raise ValueError("INVALID_CDX_HEADER")
 cols=j[0]
 if len(cols)!=len(set(cols)) or not all(x in cols for x in
     ("timestamp","original","statuscode","mimetype","digest")):
  raise ValueError("INVALID_CDX_COLUMNS")
 ret=[]
 for row in j[1:4]:
  if not isinstance(row,list) or len(row)!=len(cols):raise ValueError("INVALID_CDX_ROW")
  rec=dict(zip(cols,row))
  if not isinstance(rec["timestamp"],str) or not re.fullmatch("[0-9]{14}",rec["timestamp"]):
   raise ValueError("INVALID_CDX_TIMESTAMP")
  if not origin_allowed(rec["original"],target):
   raise ValueError("CDX_TARGET_MISMATCH")
  if rec["statuscode"]!="200":continue
  ret.append({"timestamp":rec["timestamp"],"original":rec["original"],
    "provider_digest":str(rec.get("digest",""))[:80],
    "mimetype":str(rec.get("mimetype",""))[:60]})
 return ret
def open_core(path):
 lib=ctypes.CDLL(str(Path(path).resolve()))
 lib.raf_snapshot_bytes.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(Snapshot)]
 lib.raf_snapshot_bytes.restype=ctypes.c_int
 lib.raf_html_next.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint),ctypes.POINTER(Event)]
 lib.raf_html_next.restype=ctypes.c_int
 return lib
def analyze(lib,body):
 if len(body)>MAX_HTTP:raise ValueError("BODY_TOO_LARGE")
 buffer=ctypes.create_string_buffer(body)
 snap=Snapshot()
 r=lib.raf_snapshot_bytes(buffer,len(body),ctypes.byref(snap))
 if r!=0:raise ValueError("C_SNAPSHOT_ERROR_"+str(r))
 tags={}
 for name,_ in Snapshot._fields_:
  if name not in ("raw_sha256","first_keywords_sha256","first_link_sha256"):
   tags[name]=int(getattr(snap,name))
 # Href/src edges are hashed: never publish query values or unreviewed image URLs.
 cursor=ctypes.c_uint(0);ev=Event()
 edges=[];matches={"prodfto":0,"produtos":0,"busca":0,"menus":0}
 while True:
  r=lib.raf_html_next(buffer,len(body),ctypes.byref(cursor),ctypes.byref(ev))
  if r==0:break
  if r<0:raise ValueError("C_EVENT_ERROR_"+str(r))
  if ev.flags&128 or ev.kind not in (3,4,7,8):continue
  a,b=ev.value.begin,ev.value.end
  if b<a or b>len(body):raise ValueError("C_SPAN_OUT_OF_BOUNDS")
  href=body[a:b]
  low=href.lower().split(b"?",1)[0]
  for key in matches:
   if (key+".asp").encode("ascii") in low:matches[key]+=1
  if len(edges)<MAX_LINKS and href:
   edges.append({"type":int(ev.kind),"href_sha256":hashlib.sha256(href).hexdigest(),
     "asp_extension":b".asp" in low,"inc_extension":b".inc" in low})
 return {"raw_replay_sha256":hex32(snap.raw_sha256),
   "first_keywords_sha256":hex32(snap.first_keywords_sha256) if snap.has_keywords else None,
   "first_link_sha256":hex32(snap.first_link_sha256) if snap.has_link else None,
   "counts":tags,"matched_known_asp_reference_counts":matches,
   "edges_hashed":edges,"edges_truncated":sum(tags[k] for k in ("links","images","scripts"))>MAX_LINKS,
   "evidence_type":"WAYBACK_REPLAY_BYTES_NOT_ORIGINAL_WARC"}
def run(lib):
 outcome={}
 for target in TARGETS:
  rec={"capture_index_status":[],"capture_index_count":0,"mementos":[],"comparison":"TOKEN_VAZIO_NO_PAIR"}
  seen={}
  for desc in (False,True):
   raw,state=fetch(cdx_url(target,desc),MAX_CDX)
   rec["capture_index_status"].append({"direction":"latest" if desc else "earliest",**state})
   if raw is None:continue
   try:
    for z in parse_cdx(raw,target):seen[z["timestamp"]]=z
   except Exception as e:
    rec["capture_index_status"][-1]={"state":"TOKEN_VAZIO_CDX_PARSE_"+type(e).__name__}
  rec["capture_index_count"]=len(seen)
  ordered=sorted(seen)
  if ordered:
   chosen=[ordered[0],ordered[-1]] if len(ordered)>1 else ordered
   for stamp in chosen[:MAX_MEMENTOS]:
    source=seen[stamp]
    url=memento_url(stamp,source["original"],target)
    data,status=fetch(url,MAX_HTTP)
    obs={"capture_utc":stamp,"provider_digest":source["provider_digest"],
         "archive_lookup_sha256":hashlib.sha256(url.encode()).hexdigest(),**status}
    if data is not None:
     try:obs["snapshot"]=analyze(lib,data)
     except Exception as e:obs["state"]="TOKEN_VAZIO_C_PARSER_"+type(e).__name__
    rec["mementos"].append(obs)
   if len(rec["mementos"])==2:
    a,b=rec["mementos"]
    if "snapshot" in a and "snapshot" in b:
     s1,s2=a["snapshot"],b["snapshot"]
     rec["comparison"]={"same_original_path":True,
        "raw_bytes_changed":s1["raw_replay_sha256"]!=s2["raw_replay_sha256"],
        "keywords_value_changed":s1["first_keywords_sha256"]!=s2["first_keywords_sha256"],
        "links_count_changed":s1["counts"]["links"]!=s2["counts"]["links"],
        "evidence_scope":"TWO_REPLAY_RESPONSES_NOT_RAW_WARC"}
  outcome[target]=rec
 return outcome
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--core-so",required=True)
 ap.add_argument("--output",required=True)
 args=ap.parse_args()
 lib=open_core(args.core_so)
 result={"schema":"rafaelia.wayback.replay.v1",
   "captured_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
   "producer":"WAYBACK","targets":run(lib),
   "no_raw_html_saved":True,"no_photos_downloaded":True,
   "no_forms_submitted":True,"client_core":"C99_FREESTANDING_V2",
   "rights_review":"TOKEN_VAZIO","actor":"TOKEN_VAZIO",
   "original_warc":"TOKEN_VAZIO_NOT_OBTAINED","claim_allowed":False}
 out=Path(args.output)
 out.mkdir(parents=True,exist_ok=False)
 body=(json.dumps(result,sort_keys=True,separators=(",",":"),ensure_ascii=True)+"\n").encode()
 (out/"receipt.json").write_bytes(body)
 (out/"SHA256SUMS").write_text(hashlib.sha256(body).hexdigest()+"  receipt.json\n")
 stats={k:{"captured_mementos":sum("snapshot" in x for x in v["mementos"]),
          "index_count":v["capture_index_count"],
          "comparison":v["comparison"],
          "statuses":[z["state"] for z in v["capture_index_status"]]} for k,v in result["targets"].items()}
 print("WAYBACK_REPLAY_SCOPED="+json.dumps(stats,sort_keys=True))
if __name__=="__main__":main()
