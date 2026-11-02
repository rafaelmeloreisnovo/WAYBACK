#!/usr/bin/env python3
"""RAFAELIA WAYBACK: conservative three-lane, append-only online custody cycle.
Metadata only. No content body/credentials emitted. No evidence implies causality.
One lane per CI matrix job: blake, cesar, reis. All requests are GET/read-only.
"""
import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile

UTC = dt.timezone.utc
REPOS = ("BLAKE3-team/BLAKE3", "rafaelmeloreisnovo/BLAKE3")
SITES = {"cesar": "cesarreis.com.br", "reis": "reisoffice.com.br"}
PAGE = 10
MAX_HTTP = 524288
MAX_ZIP = 2 * 1024 * 1024
WORDS = ("blacktrace", "breaktrace", "blakr", "black trace")
YMD = re.compile(r"(?<![0-9])(?:19[0-9]{2}|20[0-2][0-9])(?:[-/.][01][0-9][-/.][0-3][0-9])?(?![0-9])")
NOREDIRECT = type("NoRedirect", (urllib.request.HTTPRedirectHandler,),
    {"redirect_request": lambda self, req, fp, code, msg, headers, newurl: None})

def sha(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()

def iso(value):
    if not value:
        return None
    try:
        result = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(UTC).isoformat() if result.tzinfo else None
    except (ValueError, TypeError):
        return None

def sanitized_url(url):
    p = urllib.parse.urlsplit(url)
    return {"scheme": p.scheme, "host": p.hostname,
            "path": p.path[:240], "url_sha256": sha(url),
            "query_sha256": sha(p.query) if p.query else None}

def origins(lane):
    domain = SITES[lane]
    return tuple(s + "://" + pre + domain + "/"
                 for pre in ("", "www.") for s in ("http", "https"))

def source_allowed(url, lane):
    try:
        p = urllib.parse.urlsplit(url)
        if p.username or p.password or p.fragment or p.port is not None:
            return False
        return (p.scheme + "://" + (p.hostname or "") + "/") in origins(lane)
    except ValueError:
        return False

def archive_query(origin, year, month, offset):
    assert origin.startswith(("http://", "https://"))
    q = {"url": origin, "matchType": "prefix",
         "from": "%04d%02d" % (year, month),
         "to": "%04d%02d" % (year, month),
         "fl": "timestamp,original,statuscode,mimetype,digest,length",
         "output": "json", "limit": str(PAGE), "offset": str(offset)}
    return "https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(q)

class Gate:
    def __init__(self, budget):
        self.budget = budget
        self.requests = []
    def get(self, url, lane="blake", accept="application/json", auth=False):
        p = urllib.parse.urlsplit(url)
        if len(self.requests) >= self.budget:
            return None, {"status": "BUDGET_EXHAUSTED"}
        allowed = False
        if p.scheme == "https" and p.hostname == "api.github.com":
            parts = p.path.strip("/").split("/")
            if len(parts) >= 4 and parts[0] == "repos" and "/".join(parts[1:3]) in REPOS:
                allowed = parts[3] in ("issues", "commits", "pulls")
        if p.scheme == "https" and p.hostname == "web.archive.org":
            allowed = (p.path == "/cdx/search/cdx" or
                       (p.path.startswith("/web/") and lane in SITES))
        if not allowed:
            return None, {"status": "BLOCKED_ALLOWLIST"}
        headers = {"User-Agent": "RAFAELIA-WAYBACK-CUSTODY/1", "Accept": accept}
        token = os.environ.get("GITHUB_TOKEN", "")
        if auth and p.hostname == "api.github.com" and token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(url, headers=headers, method="GET")
        self.requests.append({"request_sha256": sha(url), "endpoint": p.hostname + p.path,
                              "method": "GET"})
        try:
            with urllib.request.build_opener(NOREDIRECT()).open(req, timeout=12) as response:
                if response.geturl() != url:
                    return None, {"status": "BLOCKED_REDIRECT"}
                body = response.read(MAX_HTTP + 1)
                if len(body) > MAX_HTTP:
                    return None, {"status": "BLOCKED_RESPONSE_LIMIT"}
                h = response.headers
                return body, {"status": "HTTP_" + str(response.status),
                    "body_sha256": sha(body),
                    "http_date": h.get("Date"),
                    "last_modified": h.get("Last-Modified"),
                    "etag_sha256": sha(h["ETag"]) if h.get("ETag") else None,
                    "bytes": len(body), "content_type": h.get("Content-Type", "")[:60]}
        except urllib.error.HTTPError as err:
            return None, {"status": "HTTP_" + str(err.code)}
        except Exception as err:
            return None, {"status": "TOKEN_VAZIO_" + type(err).__name__}

def json_data(body):
    item = json.loads(body)
    if not isinstance(item, (list, dict)):
        raise ValueError("INVALID_JSON_SHAPE")
    return item

def mentions(text):
    lowered = str(text or "").lower()
    return [w for w in WORDS if w in lowered]

def compact_event(kind, source, item, event_time=None):
    return {"kind": kind, "source": source, "ref": item.get("id", item.get("sha")),
            "html_url": item.get("html_url"), "at_utc": iso(event_time or item.get("created_at")),
            "updated_at_utc": iso(item.get("updated_at")),
            "state": item.get("state"), "commit_id": item.get("commit_id"),
            "in_reply_to_id": item.get("in_reply_to_id"),
            "path_sha256": sha(item["path"]) if isinstance(item.get("path"), str) else None,
            "actor": (item.get("user") or {}).get("login"),
            "body_sha256": sha(item["body"]) if isinstance(item.get("body"), str) else None,
            "matched_terms": mentions(item.get("body")),
            "source_payload_sha256": sha(json.dumps(item, sort_keys=True, separators=(",", ":")))}

def api(repo, suffix, **query):
    if repo not in REPOS:
        raise ValueError("UNKNOWN_REPOSITORY")
    return ("https://api.github.com/repos/" + repo + "/" + suffix +
            ("?" + urllib.parse.urlencode(query) if query else ""))

def repo_state(asof):
    return {"issues_page": 1, "commits_page": 1, "pending": [],
            "issues_exhausted": False, "commits_exhausted": False,
            "asof": asof}

def blake_cycle(state, gate):
    asof = dt.datetime.now(UTC).isoformat()
    data = []
    # Keep complete comment/review/timeline pagination cursors across CI cycles.
    # Alternate repository order so a busy upstream cannot starve a fork.
    repo_order = REPOS if state["cycle_index"] % 2 == 0 else tuple(reversed(REPOS))
    for repo in repo_order:
        pos = state.setdefault("repos", {}).setdefault(repo, repo_state(asof))
        if not pos["issues_exhausted"] and len(pos["pending"]) < 30:
            raw, status = gate.get(api(repo, "issues", state="all", sort="created",
                                        direction="asc", per_page=PAGE, page=pos["issues_page"]), auth=True)
            data.append({"kind": "issues_page", "repo": repo, "page": pos["issues_page"],
                         "status": status})
            if raw is not None:
                try:
                    items = json_data(raw)
                    if not isinstance(items, list): raise ValueError("ISSUES_NOT_LIST")
                    for item in items:
                        n = item.get("number")
                        if isinstance(n, int):
                            pos["pending"].append({"number": n, "is_pr": "pull_request" in item,
                                                   "detail_index": 0, "detail_page": 1})
                            data.append({"kind": "issue_or_pr", "repo": repo, "number": n,
                                "is_pr": "pull_request" in item, "state": item.get("state"),
                                "created_at": iso(item.get("created_at")),
                                "closed_at": iso(item.get("closed_at")),
                                "updated_at": iso(item.get("updated_at")),
                                "comments_count": item.get("comments"),
                                "title_sha256": sha(item.get("title", "")),
                                "body_sha256": sha(item["body"]) if item.get("body") else None,
                                "matched_terms": mentions((item.get("title") or "") + " " + (item.get("body") or "")),
                                "url": item.get("html_url")})
                    pos["issues_page"] += 1
                    pos["issues_exhausted"] = len(items) < PAGE
                except Exception as err:
                    data[-1]["parse_error"] = type(err).__name__
        if not pos["commits_exhausted"]:
            raw, status = gate.get(api(repo, "commits", per_page=PAGE, page=pos["commits_page"],
                                        until=pos["asof"]), auth=True)
            data.append({"kind": "commits_page", "repo": repo, "page": pos["commits_page"],
                         "status": status})
            if raw is not None:
                try:
                    items = json_data(raw)
                    if not isinstance(items, list): raise ValueError("COMMITS_NOT_LIST")
                    for item in items:
                        c = item.get("commit") or {}
                        sha40 = item.get("sha")
                        if not isinstance(sha40, str) or not re.fullmatch("[0-9a-f]{40}", sha40):
                            continue
                        data.append({"kind": "commit", "repo": repo, "sha": sha40,
                           "parents": [p.get("sha") for p in item.get("parents", [])],
                           "author_at": iso((c.get("author") or {}).get("date")),
                           "committer_at": iso((c.get("committer") or {}).get("date")),
                           "author_login": (item.get("author") or {}).get("login"),
                           "committer_login": (item.get("committer") or {}).get("login"),
                           "message_sha256": sha(c.get("message", "")),
                           "matched_terms": mentions(c.get("message")),
                           "url": item.get("html_url")})
                    pos["commits_page"] += 1
                    pos["commits_exhausted"] = len(items) < PAGE
                except Exception as err:
                    data[-1]["parse_error"] = type(err).__name__
    for repo in repo_order:
        pos = state["repos"][repo]
        if not pos["pending"]:
            continue
        pending = pos["pending"][0]
        num = pending["number"]
        tasks = [("issue_comments", "issues/%d/comments" % num),
                 ("timeline", "issues/%d/timeline" % num)]
        if pending["is_pr"]:
            tasks = [("pull", "pulls/%d" % num),
                     ("issue_comments", "issues/%d/comments" % num),
                     ("review_comments", "pulls/%d/comments" % num),
                     ("reviews", "pulls/%d/reviews" % num),
                     ("pull_commits", "pulls/%d/commits" % num),
                     ("timeline", "issues/%d/timeline" % num)]
        # A bounded slice is processed per repo; partial histories remain resumable.
        slots = 0
        while (pending["detail_index"] < len(tasks) and
               len(gate.requests) < gate.budget and slots < 4):
            kind, suffix = tasks[pending["detail_index"]]
            page = pending["detail_page"]
            raw, status = gate.get(api(repo, suffix, per_page=PAGE, page=page), auth=True)
            item = {"kind": kind, "repo": repo, "issue_number": num,
                    "detail_page": page, "status": status}
            if raw is None:
                item["state"] = "TOKEN_VAZIO_DETAIL_NOT_FETCHED_RETRY"
                data.append(item)
                break
            try:
                body = json_data(raw)
                if kind == "pull":
                    if not isinstance(body, dict): raise ValueError("PULL_NOT_OBJECT")
                    head = body.get("head") or {}
                    base = body.get("base") or {}
                    hrepo = (head.get("repo") or {}).get("full_name")
                    brepo = (base.get("repo") or {}).get("full_name")
                    item.update({"id": body.get("id"), "number": num,
                        "state": body.get("state"), "draft": body.get("draft"),
                        "merged": body.get("merged"), "merged_at": iso(body.get("merged_at")),
                        "closed_at": iso(body.get("closed_at")),
                        "created_at": iso(body.get("created_at")),
                        "updated_at": iso(body.get("updated_at")),
                        "merge_commit_sha": body.get("merge_commit_sha"),
                        "head": {"repo": hrepo, "sha": head.get("sha"), "ref": head.get("ref")},
                        "base": {"repo": brepo, "sha": base.get("sha"), "ref": base.get("ref")},
                        "merged_by": (body.get("merged_by") or {}).get("login"),
                        "cross_repo": hrepo != brepo if hrepo and brepo else None,
                        "source_payload_sha256": sha(raw)})
                    pending["detail_index"] += 1
                    pending["detail_page"] = 1
                elif isinstance(body, list):
                    if kind == "pull_commits":
                        item["events"] = [{"kind": "pull_commit", "sha": c.get("sha"),
                            "parents": [p.get("sha") for p in c.get("parents", [])],
                            "author_at": iso(((c.get("commit") or {}).get("author") or {}).get("date")),
                            "committer_at": iso(((c.get("commit") or {}).get("committer") or {}).get("date"))}
                            for c in body]
                    else:
                        item["events"] = [compact_event(kind, repo, c,
                            c.get("submitted_at") or c.get("created_at")) for c in body]
                        if kind == "timeline":
                            item["events"] = [
                                {**compact_event("timeline:" + str(c.get("event")), repo, c),
                                 "commit_id": c.get("commit_id"),
                                 "referenced_repo": ((c.get("source") or {}).get("issue") or {}).get("repository_url")}
                                for c in body]
                    item["possibly_truncated"] = len(body) >= PAGE
                    if len(body) >= PAGE:
                        pending["detail_page"] += 1
                    else:
                        pending["detail_index"] += 1
                        pending["detail_page"] = 1
                else:
                    raise ValueError("INVALID_DETAIL_SHAPE")
            except Exception as err:
                item["parse_error"] = type(err).__name__
                data.append(item)
                break
            data.append(item)
            slots += 1
        if pending["detail_index"] == len(tasks):
            pos["pending"].pop(0)
    return data

class HTMLSignals(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.signals = []
        self.counts = {"comments": 0, "meta": 0, "links": 0, "scripts": 0}
    def mark(self, src, value):
        value = str(value or "")
        matches = sorted(set(YMD.findall(value)))[:16]
        if matches and len(self.signals) < 40:
            self.signals.append({"location": src, "dates": matches, "value_sha256": sha(value)})
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            self.counts["meta"] += 1
            self.mark("meta:" + str(a.get("name") or a.get("property") or "")[:48],
                      a.get("content"))
        if tag in ("a", "link", "img", "script"):
            self.counts["links" if tag in ("a", "link") else "scripts"] += 1
            self.mark("attribute:" + tag, a.get("href") or a.get("src"))
        for key in ("datetime", "date", "data-date", "content"):
            if key in a and tag != "meta":
                self.mark("attribute:" + key, a.get(key))
    def handle_comment(self, data):
        self.counts["comments"] += 1
        self.mark("html_comment", data)
    def handle_data(self, data):
        self.mark("page_text", data)

def cdx_records(raw, lane, requested_origin=None):
    block = json_data(raw)
    if not isinstance(block, list) or not block:
        return [], 0
    cols = block[0]
    if not isinstance(cols, list) or len(cols) != len(set(cols)):
        raise ValueError("CDX_HEADER")
    if not {"timestamp", "original", "statuscode", "digest"}.issubset(cols):
        raise ValueError("CDX_COLUMNS")
    accepted, rejected = [], 0
    for line in block[1:]:
        if not isinstance(line, list) or len(line) != len(cols):
            raise ValueError("CDX_ROW")
        rec = dict(zip(cols, line))
        url = rec["original"]
        stamp = str(rec["timestamp"])
        if (not source_allowed(url, lane) or
            (requested_origin is not None and
             (urllib.parse.urlsplit(url).scheme + "://" +
              (urllib.parse.urlsplit(url).hostname or "") + "/") != requested_origin) or
            not re.fullmatch("[0-9]{14}", stamp)):
            rejected += 1
            continue
        accepted.append({"timestamp": stamp, **sanitized_url(url),
            "source_url": url if not urllib.parse.urlsplit(url).query else None,
            "provider_digest": rec.get("digest"), "status": rec.get("statuscode"),
            "mimetype": rec.get("mimetype"), "length": rec.get("length")})
    return accepted, rejected

def discovery_query(origin):
    q = {"url": origin, "matchType": "prefix",
         "from": "1994", "to": "2026", "output": "json",
         "fl": "timestamp,original,statuscode,mimetype,digest,length",
         "limit": "1"}
    return "https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(q)

def advance_month(cursor):
    cursor["month"] += 1
    if cursor["month"] > 12:
        cursor["month"] = 1
        cursor["year"] += 1
    cursor["offset"] = 0

def site_cycle(lane, state, gate):
    records = []
    pointers = state.setdefault("origins", {
        x: {"year": 1994, "month": 1, "offset": 0, "seen_page_sha256": None, "discovered": False}
        for x in origins(lane)})
    candidates = []
    for origin in origins(lane):
        pos = pointers[origin]
        if pos["year"] > 2026:
            records.append({"kind": "origin_coverage", "origin": origin, "state": "REACHED_END_2026"})
            continue
        discovering = not pos.get("discovered", False)
        query = discovery_query(origin) if discovering else archive_query(
            origin, pos["year"], pos["month"], pos["offset"])
        raw, status = gate.get(query, lane)
        row = {"kind": "cdx_discovery" if discovering else "cdx_page",
               "origin": origin, "year": pos["year"], "month": pos["month"],
               "offset": pos["offset"], "status": status}
        if raw is not None:
            try:
                found, rejected = cdx_records(raw, lane, requested_origin=origin)
                row["records"] = [{k: v for k, v in r.items() if k != "source_url"} for r in found]
                row["rejected_origin_rows"] = rejected
                row["sampling_limit"] = 1 if discovering else PAGE
                row["possibly_truncated"] = len(found) >= (1 if discovering else PAGE)
                if discovering:
                    if found:
                        earliest = sorted(found, key=lambda x: x["timestamp"])[0]["timestamp"]
                        pos["year"], pos["month"] = int(earliest[:4]), int(earliest[4:6])
                        pos["discovered"] = True
                        pos["offset"] = 0
                        row["first_indexed_capture"] = earliest
                    else:
                        row["state"] = "TOKEN_VAZIO_NO_EXACT_VARIANT_DISCOVERED_RETRY"
                elif status["body_sha256"] == pos["seen_page_sha256"] and pos["offset"] > 0:
                    row["state"] = "BLOCKED_REPEATED_PAGE_OFFSET_UNVERIFIED"
                else:
                    pos["seen_page_sha256"] = status["body_sha256"]
                    if len(found) >= PAGE:
                        pos["offset"] += PAGE
                    else:
                        advance_month(pos)
                    candidates.extend(x for x in found if
                        x["source_url"] and str(x["mimetype"]).lower().startswith("text/html") and
                        x["status"] == "200")
            except Exception as err:
                row["state"] = "TOKEN_VAZIO_PARSE_" + type(err).__name__
        records.append(row)
    # One small archived HTML replay for source dates, not the original WARC/server code.
    if candidates and len(gate.requests) < gate.budget:
        candidate = sorted(candidates, key=lambda r: (r["timestamp"], r["url_sha256"]))[0]
        memento = "https://web.archive.org/web/" + candidate["timestamp"] + "id_/" + candidate["source_url"]
        raw, status = gate.get(memento, lane, accept="text/html")
        meta = {"kind": "archived_html", "source": {k: v for k, v in candidate.items() if k != "source_url"},
                "status": status, "provenance": "WAYBACK_REPLAY_NOT_ORIGINAL_WARC"}
        if raw is not None:
            try:
                scanner = HTMLSignals()
                scanner.feed(raw.decode("utf-8", errors="replace"))
                meta["html_signals"] = scanner.signals
                meta["html_counts"] = scanner.counts
                meta["raw_replay_sha256"] = sha(raw)
                meta["no_raw_html_published"] = True
                history = state.setdefault("observed_hash_index", {})
                key = candidate["url_sha256"]
                old = history.get(key)
                if old is not None:
                    meta["comparison_to_prior_observation"] = {
                        "prior_sha256": old["raw_replay_sha256"],
                        "current_sha256": meta["raw_replay_sha256"],
                        "changed": old["raw_replay_sha256"] != meta["raw_replay_sha256"],
                        "prior_capture": old["timestamp"],
                        "current_capture": candidate["timestamp"],
                        "scope": "REPLAY_BYTES_NOT_ORIGINAL_WARC"}
                if key in history or len(history) < 1000:
                    history[key] = {"raw_replay_sha256": meta["raw_replay_sha256"],
                                    "timestamp": candidate["timestamp"]}
                else:
                    meta["history_state"] = "BLOCKED_HISTORY_INDEX_CAP"
            except Exception as err:
                meta["parse_state"] = "TOKEN_VAZIO_HTML_" + type(err).__name__
        records.append(meta)
    return records

def state_for(lane):
    return {"schema": "rafaelia.wayback.custody_cursor.v1", "lane": lane,
            "cycle_index": 0, "parent_receipt_sha256": None, "repos": {},
            "origins": {}, "status": "BOOTSTRAP_EXPLICIT"}

def verify_previous(blob, lane):
    if len(blob) > MAX_ZIP:
        raise ValueError("PREVIOUS_ARTIFACT_TOO_LARGE")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = z.namelist()
        if len(names) > 16 or any(".." in n or n.startswith("/") for n in names):
            raise ValueError("UNSAFE_ARCHIVE_ENTRY")
        def read(name):
            matches = [n for n in names if n.endswith("/" + name) or n == name]
            if len(matches) != 1:
                raise ValueError("MISSING_OR_DUPLICATE_" + name)
            info = z.getinfo(matches[0])
            if info.file_size > MAX_ZIP:
                raise ValueError("ZIP_BOMB")
            return z.read(matches[0])
        manifest = read("SHA256SUMS").decode("utf-8").splitlines()
        contents = {n: read(n) for n in ("cursor.json", "receipt.json")}
        for n in contents:
            expected = [line.split()[0] for line in manifest if line.endswith("  " + n)]
            if len(expected) != 1 or sha(contents[n]) != expected[0]:
                raise ValueError("CHECKSUM_MISMATCH_" + n)
        state = json.loads(contents["cursor.json"])
        receipt = json.loads(contents["receipt.json"])
        if state["lane"] != lane or receipt["lane"] != lane:
            raise ValueError("LANE_MISMATCH")
        if state["cycle_index"] != receipt["cycle_index"]:
            raise ValueError("CYCLE_MISMATCH")
        if state["parent_receipt_sha256"] != receipt.get("parent_receipt_sha256"):
            raise ValueError("CHAIN_PARENT_MISMATCH")
        return state, sha(contents["receipt.json"])

def artifact_blob(lane, provided_run):
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise ValueError("PREVIOUS_ARTIFACT_REQUIRES_GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo != "rafaelmeloreisnovo/WAYBACK":
        raise ValueError("REPOSITORY_AUTHORITY_MISMATCH")
    api_root = "https://api.github.com/repos/" + repo
    opener = urllib.request.build_opener(NOREDIRECT())
    def request(url, accept="application/vnd.github+json"):
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token,
            "User-Agent": "RAFAELIA-WAYBACK-Custody/1", "Accept": accept})
        with opener.open(req, timeout=15) as response:
            body = response.read(MAX_ZIP + 1)
            if len(body) > MAX_ZIP: raise ValueError("API_RESPONSE_TOO_BIG")
            return body
    if provided_run:
        url = api_root + "/actions/runs/" + str(provided_run) + "/artifacts?per_page=100"
    else:
        url = api_root + "/actions/artifacts?per_page=100"
    payload = json.loads(request(url))
    eligible = [a for a in payload.get("artifacts", [])
                if not a.get("expired") and
                a.get("name", "").startswith("wayback-custody-" + lane + "-") and
                (not provided_run or (a.get("workflow_run") or {}).get("id") == provided_run)]
    eligible.sort(key=lambda a: (a.get("created_at", ""), a.get("id", 0)), reverse=True)
    if not eligible:
        return None, None
    artifact = eligible[0]
    source_url = api_root + "/actions/artifacts/" + str(artifact["id"]) + "/zip"
    req = urllib.request.Request(source_url, headers={
        "Authorization": "Bearer " + token, "User-Agent": "RAFAELIA-WAYBACK-Custody/1"})
    try:
        opener.open(req, timeout=15)
        raise ValueError("EXPECTED_SIGNED_ARCHIVE_REDIRECT")
    except urllib.error.HTTPError as err:
        if err.code not in (301,302,303,307,308):
            raise
        location = err.headers.get("Location", "")
    p = urllib.parse.urlsplit(location)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("UNTRUSTED_ARTIFACT_REDIRECT")
    # GitHub hosted artifacts use signed GitHub/Azure blobs; restrict origin families.
    if not (p.hostname.endswith(".blob.core.windows.net") or
            p.hostname.endswith(".githubusercontent.com") or
            p.hostname.endswith(".actions.githubusercontent.com")):
        raise ValueError("UNKNOWN_ARTIFACT_HOST")
    raw = urllib.request.urlopen(location, timeout=20).read(MAX_ZIP + 1)
    return raw, {"artifact_id": artifact["id"], "created_at": artifact.get("created_at"),
                 "name": artifact.get("name"), "source_run": (artifact.get("workflow_run") or {}).get("id")}

def previous_state(lane, provided_run, allow_bootstrap):
    raw, metadata = artifact_blob(lane, provided_run)
    if raw is None:
        if allow_bootstrap and not provided_run:
            return state_for(lane), "TOKEN_VAZIO_FIRST_CYCLE_NO_PREVIOUS_ARTIFACT"
        raise ValueError("BLOCKED_PREVIOUS_ARTIFACT_NOT_FOUND")
    return verify_previous(raw, lane)

def write_receipt(output, state, records, gate, parent, lane):
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    state["cycle_index"] += 1
    state["parent_receipt_sha256"] = parent if len(parent) == 64 else None
    receipt = {"schema": "rafaelia.wayback.custody_cycle.v1", "lane": lane,
        "cycle_index": state["cycle_index"], "observed_at_utc": dt.datetime.now(UTC).isoformat(),
        "parent_receipt_sha256": state["parent_receipt_sha256"],
        "bootstrap_or_prev_state": parent if len(parent) != 64 else "HASH_VERIFIED",
        "requests_used": len(gate.requests), "request_budget": gate.budget,
        "requests": gate.requests, "records": records,
        "source_not_warc": True, "source_not_original_server_code": True,
        "no_raw_html_or_comment_text": True, "claim_allowed": False,
        "cursor_is_complete_historical_evidence": False,
        "retention": "GITHUB_ACTIONS_ARTIFACT_NOT_INDEPENDENT_PERMANENT_CUSTODY"}
    payloads = {"cursor.json": json.dumps(state, sort_keys=True, separators=(",", ":")).encode() + b"\n",
                "receipt.json": json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode() + b"\n"}
    for name, blob in payloads.items():
        (folder/name).write_bytes(blob)
    (folder/"SHA256SUMS").write_text("".join(sha(data) + "  " + name + "\n"
                                           for name, data in payloads.items()))
    print(json.dumps({"lane": lane, "cycle": state["cycle_index"],
         "request_count": len(gate.requests), "records": len(records),
         "receipt_sha256": sha(payloads["receipt.json"]), "claim_allowed": False}, sort_keys=True))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lane", required=True, choices=("blake","cesar","reis"))
    p.add_argument("--output", required=True)
    p.add_argument("--budget", type=int, default=12)
    p.add_argument("--previous-run", type=int, default=0)
    p.add_argument("--bootstrap-if-empty", action="store_true")
    p.add_argument("--fixture", action="store_true", help="no network: test rendering and cursor write")
    args = p.parse_args()
    if not 1 <= args.budget <= 20: raise SystemExit("INVALID_REQUEST_BUDGET")
    if args.fixture:
        state, parent = state_for(args.lane), "SYNTHETIC_NO_NETWORK"
        records = [{"kind": "synthetic", "claim_allowed": False}]
        gate = Gate(args.budget)
    else:
        state, parent = previous_state(args.lane, args.previous_run, args.bootstrap_if_empty)
        gate = Gate(args.budget)
        records = blake_cycle(state, gate) if args.lane == "blake" else site_cycle(args.lane, state, gate)
    write_receipt(args.output, state, records, gate, parent, args.lane)

if __name__ == "__main__":
    main()
