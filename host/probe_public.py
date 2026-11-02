#!/usr/bin/env python3
"""Bounded PUBLIC metadata I/O adapter; hosted, NOT freestanding.
C99 freestanding core/raf_evidence_v2.c performs temporal correlation.
No photos, HTML body, forms, login, non-public files or source publishing.
"""
import argparse
import ctypes
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

MAX_RESPONSE=262144
CAP=24
CDX_HOSTS=("www.cesarreis.com.br","www.reisoffice.com.br")
TIME_WINDOWS=(("1996","2005"),("2006","2018"),("2019","2026"))
GIT_REPOS=("BLAKE3-team/BLAKE3","rafaelmeloreisnovo/BLAKE3")
MAX_FLAGS=20

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,hdrs,newurl):
        return None

def permitted(url):
    p=urllib.parse.urlsplit(url)
    if p.scheme!="https" or p.username or p.password or p.fragment or p.port not in (None,443):
        return False
    if p.hostname=="web.archive.org":
        return p.path=="/cdx/search/cdx"
    if p.hostname=="api.github.com":
        return p.path in tuple("/repos/"+r+"/commits" for r in GIT_REPOS)
    return False

def fetch_public(url):
    if not permitted(url):
        return None,"BLOCKED_URL_NOT_ALLOWLISTED"
    req=urllib.request.Request(url,headers={"User-Agent":"RAFAELIA-WAYBACK-ReadOnly-CI/2.0","Accept":"application/json"})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=12) as resp:
            if not permitted(resp.geturl()):return None,"BLOCKED_REDIRECT"
            raw=resp.read(MAX_RESPONSE+1)
            if len(raw)>MAX_RESPONSE:return None,"BLOCKED_SIZE_LIMIT"
            return raw,"OK_HTTP_"+str(resp.status)
    except urllib.error.HTTPError as exc:
        return None,"TOKEN_VAZIO_HTTP_"+str(exc.code)
    except Exception as exc:
        return None,"TOKEN_VAZIO_FETCH_"+type(exc).__name__

def cdx_url(host,year_from="1996",year_to="2026"):
    if host not in CDX_HOSTS:raise ValueError("HOST_NOT_ALLOWLISTED")
    query=urllib.parse.urlencode({"url":host+"/*","output":"json",
      "fl":"timestamp,original,statuscode,mimetype,digest,length",
      "from":year_from,"to":year_to,"filter":"statuscode:200","limit":str(CAP)})
    return "https://web.archive.org/cdx/search/cdx?"+query

def git_url(repo):
    if repo not in GIT_REPOS:raise ValueError("REPO_NOT_ALLOWLISTED")
    return "https://api.github.com/repos/"+repo+"/commits?per_page="+str(CAP)+"&page=1"

def read_cdx(payload):
    j=json.loads(payload)
    if not isinstance(j,list) or not j or not isinstance(j[0],list):
        raise ValueError("INVALID_CDX_HEADER")
    names=j[0]
    if len(names)!=len(set(names)) or not all(n in names for n in ("timestamp","original","statuscode")):
        raise ValueError("INVALID_CDX_FIELDS")
    records=[]
    for row in j[1:CAP+1]:
        if not isinstance(row,list) or len(row)!=len(names):raise ValueError("INVALID_CDX_ROW")
        p=dict(zip(names,row))
        if not isinstance(p["timestamp"],str) or not re.fullmatch(r"\d{14}",p["timestamp"]):
            raise ValueError("INVALID_CDX_TIMESTAMP")
        source=p["original"]
        if not isinstance(source,str) or not source.startswith(("http://","https://")):
            raise ValueError("INVALID_CDX_ORIGINAL")
        records.append({"timestamp":p["timestamp"],"original_sha256":hashlib.sha256(source.encode()).hexdigest(),
          "http_status":str(p["statuscode"]),"mimetype":str(p.get("mimetype",""))[:50],
          "provider_digest":str(p.get("digest",""))[:100],"length":str(p.get("length","TOKEN_VAZIO"))[:16]})
    return records

def read_git(payload):
    j=json.loads(payload)
    if not isinstance(j,list):raise ValueError("INVALID_GIT_ARRAY")
    records=[]
    for item in j[:CAP]:
        sha=item.get("sha")
        commit=item.get("commit") or {}
        stamp=((commit.get("committer") or {}).get("date"))
        if not isinstance(sha,str) or not re.fullmatch(r"[0-9a-f]{40}",sha) or not isinstance(stamp,str):
            raise ValueError("INVALID_GIT_COMMIT")
        try:
            utc=dt.datetime.fromisoformat(stamp.replace("Z","+00:00"))
            if utc.utcoffset()!=dt.timedelta(0):raise ValueError()
            ts=utc.strftime("%Y%m%d%H%M%S")
        except Exception as exc:
            raise ValueError("INVALID_GIT_DATE") from exc
        message=commit.get("message","")
        records.append({"sha":sha,"timestamp":ts,
          "message_sha256":hashlib.sha256(str(message).encode()).hexdigest(),
          "url":"https://github.com/"+item.get("repository_full_name","")+"/commit/"+sha
          if item.get("repository_full_name") in GIT_REPOS else "TOKEN_VAZIO_REPO_URL"})
    return records

class TimeMatch(ctypes.Structure):
    _fields_=[("gap_seconds",ctypes.c_ulonglong),("within_window",ctypes.c_uint),
      ("same_clock_minute",ctypes.c_uint),("month_apart_clock_match",ctypes.c_uint),
      ("month_distance",ctypes.c_uint),("same_calendar_day",ctypes.c_uint),
      ("exact_one_month",ctypes.c_uint)]

def load_core(path):
    lib=ctypes.CDLL(str(path))
    fn=lib.raf_stamp_compare
    fn.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint,ctypes.POINTER(TimeMatch)]
    fn.restype=ctypes.c_int
    return fn

def compare(archive,commits,fn):
    flagged=[]
    for origin,items in archive.items():
        for a in items:
            for repo,cs in commits.items():
                for c in cs:
                    out=TimeMatch()
                    ok=fn(a["timestamp"].encode("ascii"),c["timestamp"].encode("ascii"),60,ctypes.byref(out))
                    if ok!=0:raise ValueError("CORE_REJECTED_SOURCE_TIMESTAMP")
                    if out.month_apart_clock_match or out.within_window:
                        flagged.append({"archive_host":origin,"archive_timestamp":a["timestamp"],
                          "git_repo":repo,"git_sha":c["sha"],"git_timestamp":c["timestamp"],
                          "gap_seconds":int(out.gap_seconds),
                          "month_distance":int(out.month_distance),
                          "same_calendar_day":bool(out.same_calendar_day),
                          "exact_one_month":bool(out.exact_one_month),
                          "classification":("EXACT_ONE_MONTH_SAME_CLOCK_NOT_CAUSAL_EVIDENCE"
                            if out.exact_one_month else
                            "SAME_CLOCK_DIFFERENT_DATE_NOT_CAUSAL_EVIDENCE"
                            if out.month_apart_clock_match else
                            "NEAR_TIME_NOT_CAUSAL_EVIDENCE")})
                        if len(flagged)>=MAX_FLAGS:return flagged,True
    return flagged,False

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--core-so",required=True)
    ap.add_argument("--output-dir",required=True)
    args=ap.parse_args()
    fn=load_core(args.core_so)
    archive={};commits={};status={}
    for host in CDX_HOSTS:
        archive[host]=[]
        for year_from,year_to in TIME_WINDOWS:
            key="WAYBACK_"+host+"_"+year_from+"_"+year_to
            data,state=fetch_public(cdx_url(host,year_from,year_to))
            status[key]=state
            if data is None:continue
            try:
                batch=read_cdx(data)
                for item in batch:item["window"]=year_from+"_"+year_to
                archive[host].extend(batch)
            except Exception as exc:
                status[key]="TOKEN_VAZIO_INVALID_"+type(exc).__name__
    for repo in GIT_REPOS:
        data,state=fetch_public(git_url(repo))
        status["GITHUB_"+repo]=state
        if data is None:commits[repo]=[];continue
        try:commits[repo]=read_git(data)
        except Exception as exc:status["GITHUB_"+repo]="TOKEN_VAZIO_INVALID_"+type(exc).__name__;commits[repo]=[]
    matches,truncated=compare(archive,commits,fn)
    receipt={"schema":"rafaelia.wayback.public_probe.v3",
      "observed_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "kind":"BOUNDED_PUBLIC_METADATA_NOT_ARCHIVE_BODY",
      "source_statuses":status,"archive_metadata":archive,"git_metadata":commits,
      "clock_candidates":matches,"clock_candidates_truncated":truncated,
      "scope":"2 sites x 3 time windows (1996-2005,2006-2018,2019-2026) x at most 24 CDX records/window; 2 git repos x 24 commits, sample only; NOT exhaustive",
      "no_raw_html":True,"no_photos":True,"no_form_submission":True,
      "human_actor":"TOKEN_VAZIO_NOT_ATTESTED","claim_allowed":False}
    out=Path(args.output_dir)
    out.mkdir(parents=True,exist_ok=False)
    raw=(json.dumps(receipt,sort_keys=True,ensure_ascii=True,separators=(",",":"))+"\n").encode("ascii")
    (out/"receipt.json").write_bytes(raw)
    (out/"SHA256SUMS").write_text(hashlib.sha256(raw).hexdigest()+"  receipt.json\n")
    print("WAYBACK_PUBLIC_PROBE="+json.dumps({"sources":status,
      "archive_samples":{k:len(v) for k,v in archive.items()},
      "git_samples":{k:len(v) for k,v in commits.items()},
      "clock_candidates":len(matches),
      "exact_month_matches":sum(bool(r["exact_one_month"]) for r in matches),
      "claim_allowed":False},sort_keys=True))
if __name__=="__main__":
    main()
