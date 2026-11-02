#!/usr/bin/env python3
"""Read-only, bounded historical CDX x GitHub issue/PR/commit correlation.
8 exact origin variants (2 domains x www x HTTP/S); live probes are diagnostic.
An observed temporal match is NOT authorship, causality, or original WARC proof.
Python stdlib hosted I/O; existing freestanding C core remains unchanged.
"""
import argparse
import bisect
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

DOMAINS = ("cesarreis.com.br", "reisoffice.com.br")
REPOS = ("BLAKE3-team/BLAKE3", "rafaelmeloreisnovo/BLAKE3",
         "rafaelmeloreisnovo/WAYBACK", "rafaelmeloreisnovo/actions", "gradle/actions")
PAGE_SIZE = 100
MAX_CDX = 100
MAX_BYTES = 1048576
MAX_EVENTS = 50000
MAX_CANDIDATES = 1000
UTC = dt.timezone.utc

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def variants():
    return tuple(scheme + "://" + prefix + domain + "/"
                 for domain in DOMAINS for prefix in ("", "www.")
                 for scheme in ("http", "https"))

def approved(url, allow_live=False):
    p = urllib.parse.urlsplit(url)
    if p.username or p.password or p.fragment or p.port is not None:
        return False
    if allow_live and url in variants():
        return True
    if p.scheme != "https":
        return False
    if p.hostname == "web.archive.org":
        return p.path == "/cdx/search/cdx"
    if p.hostname == "api.github.com":
        parts = p.path.strip("/").split("/")
        return (len(parts) == 4 and parts[0] == "repos"
                and "/".join(parts[1:3]) in REPOS
                and parts[3] in ("commits", "issues"))
    return False

def fetch(url, live=False):
    if not approved(url, allow_live=live):
        return None, {"state": "BLOCKED_ALLOWLIST"}
    p = urllib.parse.urlsplit(url)
    headers = {"User-Agent": "RAFAELIA-WAYBACK-Timeline/1.0", "Accept": "application/json"}
    if live:
        headers["Accept"] = "text/html,*/*;q=0.1"
    token = os.environ.get("GITHUB_TOKEN", "")
    if p.hostname == "api.github.com" and token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=12) as r:
            if r.geturl() != url:
                return None, {"state": "BLOCKED_REDIRECT"}
            body = r.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                return None, {"state": "TOKEN_VAZIO_RESPONSE_LIMIT"}
            return body, {"state": "OK_HTTP_" + str(r.status),
                          "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    except urllib.error.HTTPError as exc:
        location = exc.headers.get("Location", "")
        return None, {"state": "HTTP_" + str(exc.code),
                      "location_sha256": hashlib.sha256(location.encode()).hexdigest()
                                         if location else None}
    except Exception as exc:
        return None, {"state": "TOKEN_VAZIO_FETCH_" + type(exc).__name__}

def cdx_url(origin, descending=False):
    if origin not in variants():
        raise ValueError("ORIGIN_NOT_ALLOWLISTED")
    q = {"url": origin, "matchType": "exact", "output": "json",
         "fl": "timestamp,original,statuscode,mimetype,digest,length",
         "from": "1994", "to": "2026", "limit": str(MAX_CDX + 1)}
    if descending:
        q["sort"] = "reverse"
    return "https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(q)

def cdx_rows(raw, origin):
    data = json.loads(raw)
    if data == []:
        return [], 0
    if not isinstance(data, list) or not data or not isinstance(data[0], list):
        raise ValueError("CDX_FORMAT")
    header = data[0]
    required = {"timestamp", "original", "statuscode", "digest"}
    if not required.issubset(header) or len(set(header)) != len(header):
        raise ValueError("CDX_HEADER")
    found, mismatches = [], 0
    for line in data[1:]:
        if not isinstance(line, list) or len(line) != len(header):
            raise ValueError("CDX_ROW")
        rec = dict(zip(header, line))
        stamp = rec["timestamp"]
        if not isinstance(stamp, str) or len(stamp) != 14 or not stamp.isdigit():
            raise ValueError("CDX_TIMESTAMP")
        parse_date(stamp)
        # CDX normalizes indexes; NEVER attribute another origin to this exact variant.
        if rec["original"] != origin:
            mismatches += 1
            continue
        found.append({"timestamp": stamp, "original": origin,
                      "statuscode": str(rec["statuscode"]),
                      "mimetype": str(rec.get("mimetype", ""))[:48],
                      "provider_digest": str(rec["digest"])[:100],
                      "length": str(rec.get("length", ""))[:20]})
    return found, mismatches

def parse_date(value):
    if len(value) == 14 and value.isdigit():
        return dt.datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("TIMESTAMP_WITHOUT_TZ")
    return stamp.astimezone(UTC)

def collect_cdx(origin):
    records, statuses = {}, []
    mismatches = 0
    for direction in (False, True):
        query = cdx_url(origin, direction)
        raw, status = fetch(query)
        entry = {"order": "descending" if direction else "ascending", **status}
        if raw is not None:
            try:
                rows, mismatch = cdx_rows(raw, origin)
                mismatches += mismatch
                for rec in rows:
                    records[(rec["timestamp"], rec["statuscode"], rec["provider_digest"])] = rec
                entry["records_matched"] = len(rows)
                entry["possibly_truncated"] = len(rows) >= MAX_CDX
            except Exception as exc:
                entry["state"] = "TOKEN_VAZIO_PARSE_" + type(exc).__name__
        statuses.append(entry)
    return {"origin": origin, "statuses": statuses, "mismatched_original_count": mismatches,
            "records": sorted(records.values(), key=lambda x: x["timestamp"]),
            "coverage": "SAMPLED_EARLIEST_LATEST_NOT_EXHAUSTIVE"}

def git_api(repo, kind, page):
    if repo not in REPOS or kind not in ("issues", "commits") or page < 1:
        raise ValueError("GITHUB_SCOPE")
    params = {"per_page": PAGE_SIZE, "page": page}
    if kind == "issues":
        params["state"] = "all"
    return ("https://api.github.com/repos/" + repo + "/" + kind +
            "?" + urllib.parse.urlencode(params))

def git_events(repo, kind, payload):
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("GITHUB_ARRAY")
    result = []
    for x in data:
        if not isinstance(x, dict):
            raise ValueError("GITHUB_RECORD")
        if kind == "commits":
            sha = x.get("sha")
            if not isinstance(sha, str) or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
                raise ValueError("COMMIT_SHA")
            commit = x.get("commit") or {}
            actor_fields = commit.get("author") or {}
            committer_fields = commit.get("committer") or {}
            for event_kind, field in (("commit_author", actor_fields), ("commit_committer", committer_fields)):
                stamp = field.get("date")
                if stamp:
                    parsed = parse_date(stamp)
                    result.append({"repo": repo, "kind": event_kind, "ref": sha,
                                   "timestamp_utc": parsed.isoformat(),
                                   "url": "https://github.com/" + repo + "/commit/" + sha})
        else:
            num = x.get("number")
            if not isinstance(num, int) or num <= 0:
                raise ValueError("ISSUE_NUMBER")
            typ = "pull_request" if "pull_request" in x else "issue"
            for field in ("created_at", "updated_at", "closed_at"):
                stamp = x.get(field)
                if stamp:
                    parsed = parse_date(stamp)
                    result.append({"repo": repo, "kind": typ + "_" + field, "ref": num,
                                   "timestamp_utc": parsed.isoformat(),
                                   "url": "https://github.com/" + repo + "/issues/" + str(num)})
    return result

def collect_git(repo, kind, pages):
    events, statuses = [], []
    truncated = False
    for page in range(1, pages + 1):
        raw, status = fetch(git_api(repo, kind, page))
        item = {"page": page, **status}
        if raw is None:
            statuses.append(item)
            break
        try:
            records = json.loads(raw)
            if not isinstance(records, list):
                raise ValueError("GITHUB_ARRAY")
            events.extend(git_events(repo, kind, raw))
            item["items"] = len(records)
            statuses.append(item)
            if len(records) < PAGE_SIZE:
                break
            if page == pages:
                truncated = True
        except Exception as exc:
            item["state"] = "TOKEN_VAZIO_PARSE_" + type(exc).__name__
            statuses.append(item)
            break
    return {"repo": repo, "kind": kind, "statuses": statuses,
            "possibly_truncated": truncated, "events": events,
            "coverage": "BOUNDED_GITHUB_API_PAGES"}

def correlate(archive, events):
    stamps = sorted(((parse_date(r["timestamp"]), r) for r in archive), key=lambda x: (x[0], x[1]["original"]))
    times = [p[0] for p in stamps]
    candidate_rows, totals = [], {"within_1_day": 0, "within_7_days": 0,
                                  "within_30_days": 0, "same_utc_day": 0}
    by_repo = {}
    for ev in events:
        t = parse_date(ev["timestamp_utc"])
        lo = bisect.bisect_left(times, t - dt.timedelta(days=30))
        hi = bisect.bisect_right(times, t + dt.timedelta(days=30))
        for capture_t, capture in stamps[lo:hi]:
            gap = abs((t - capture_t).total_seconds())
            days = int(gap // 86400)
            match = "WITHIN_30_DAYS"
            totals["within_30_days"] += 1
            if gap <= 7 * 86400:
                totals["within_7_days"] += 1
                match = "WITHIN_7_DAYS"
            if gap <= 86400:
                totals["within_1_day"] += 1
                match = "WITHIN_1_DAY"
            if capture_t.date() == t.date():
                totals["same_utc_day"] += 1
                match = "SAME_UTC_DAY"
            by_repo[ev["repo"]] = by_repo.get(ev["repo"], 0) + 1
            if len(candidate_rows) < MAX_CANDIDATES:
                candidate_rows.append({"origin": capture["original"],
                    "archive_timestamp": capture["timestamp"],
                    "archive_provider_digest": capture["provider_digest"],
                    "git_repo": ev["repo"], "git_kind": ev["kind"],
                    "git_ref": ev["ref"], "git_timestamp_utc": ev["timestamp_utc"],
                    "git_url": ev["url"], "gap_seconds": int(gap),
                    "relation": match, "causal_claim": False})
    candidate_rows.sort(key=lambda r: (r["gap_seconds"], r["origin"], r["git_repo"], str(r["git_ref"])))
    return {"counts": totals, "by_repo": by_repo,
            "candidate_rows": candidate_rows,
            "candidates_truncated": totals["within_30_days"] > len(candidate_rows)}

def digest_variant_relations(archive):
    groups = {}
    for rec in archive:
        digest = rec["provider_digest"]
        if digest and digest != "-":
            groups.setdefault(digest, set()).add(rec["original"])
    return {"digests_seen_across_variants": sum(len(s) > 1 for s in groups.values()),
            "samples": [{"provider_digest": d, "origins": sorted(s)}
                        for d, s in sorted(groups.items()) if len(s) > 1][:50],
            "interpretation": "PROVIDER_DIGEST_REUSE_NOT_INDEPENDENT_WARC_OR_AUTHORSHIP"}

def create_receipt(output, report):
    dest = Path(output)
    dest.mkdir(parents=True, exist_ok=False)
    raw = (json.dumps(report, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
    (dest / "receipt.json").write_bytes(raw)
    (dest / "SHA256SUMS").write_text(hashlib.sha256(raw).hexdigest() + "  receipt.json\n")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--pages", type=int, default=8, choices=(2, 8, 20))
    p.add_argument("--live", action="store_true", help="Explicit public GET for eight URL variants")
    p.add_argument("--authorized", action="store_true")
    args = p.parse_args()
    if not args.authorized:
        raise SystemExit("BLOCKED_HUMAN_AUTHORIZATION_REQUIRED")
    origin_set = variants()
    cdx = {x: collect_cdx(x) for x in origin_set}
    live = {x: fetch(x, live=True)[1] for x in origin_set} if args.live else {
        x: {"state": "NOT_RUN_EXPLICIT_LIVE_GET"} for x in origin_set}
    sources = {repo + "/" + kind: collect_git(repo, kind, args.pages)
               for repo in REPOS for kind in ("commits", "issues")}
    archive = [r for x in cdx.values() for r in x["records"]]
    events = [r for x in sources.values() for r in x["events"]]
    if len(events) > MAX_EVENTS:
        raise SystemExit("BLOCKED_EVENT_MEMORY_BUDGET")
    cross = correlate(archive, events)
    report = {
        "schema": "rafaelia.wayback.cross_origin_git_timeline.v1",
        "observed_at_utc": dt.datetime.now(UTC).isoformat(),
        "requested_origins": list(origin_set), "cdx": cdx, "live": live,
        "github_sources": sources, "relations": cross,
        "cross_variant_provider_digests": digest_variant_relations(archive),
        "archive_rows": len(archive), "github_event_rows": len(events),
        "source_is_original_warc": False, "all_history_exhausted": False,
        "missing_is_not_zero": True, "claim_allowed": False,
        "interpretation": "Temporal correlation only; HTTP non-authenticated; source/actor/causality unproved"}
    create_receipt(args.output, report)
    count = sum(len(x["records"]) for x in cdx.values())
    git_ok = sum(any(s["state"].startswith("OK_HTTP_") for s in x["statuses"])
                 for x in sources.values())
    print(json.dumps({"cdx_rows": count, "git_sources_ok": git_ok,
                      "events": len(events), "candidate_counts": cross["counts"],
                      "truncated": cross["candidates_truncated"], "claim_allowed": False},
                     sort_keys=True))
    if count == 0 or git_ok == 0:
        raise SystemExit("BLOCKED_REQUIRED_ONLINE_SOURCES_RECEIPT_SAVED")

if __name__ == "__main__":
    main()
