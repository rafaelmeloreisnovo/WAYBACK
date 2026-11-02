#!/usr/bin/env python3
"""Join per-cycle verified GitHub and archive metadata; correlation != causality."""
import argparse
import datetime as dt
import json
from pathlib import Path
import zipfile
import io

from custody_cycle import (UTC, artifact_blob, verify_previous, iso, sha)

def load_verified_receipt(blob, lane):
    state, receipt_hash = verify_previous(blob, lane)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        name = next(n for n in z.namelist() if n == "receipt.json" or n.endswith("/receipt.json"))
        receipt = json.loads(z.read(name))
    return {"state": state, "receipt_sha256": receipt_hash, "receipt": receipt}

def gather_git(receipt):
    events = []
    for rec in receipt["records"]:
        repo = rec.get("repo")
        if rec.get("kind") == "commit":
            for kind, key in (("author", "author_at"), ("committer", "committer_at")):
                if rec.get(key):
                    events.append({"timestamp": rec[key], "kind": "commit_" + kind,
                        "repo": repo, "ref": rec["sha"]})
        if rec.get("kind") == "issue_or_pr":
            for kind in ("created_at", "closed_at", "updated_at"):
                if rec.get(kind):
                    events.append({"timestamp": rec[kind], "kind": kind, "repo": repo,
                                   "ref": rec["number"]})
        if rec.get("kind") == "pull":
            for kind in ("merged_at", "closed_at", "created_at", "updated_at"):
                if rec.get(kind):
                    events.append({"timestamp": rec[kind], "kind": "pull_" + kind,
                        "repo": repo, "ref": rec["number"], "head": rec.get("head"),
                        "base": rec.get("base"), "merge_commit_sha": rec.get("merge_commit_sha")})
        for item in rec.get("events", []):
            for kind in ("at_utc", "updated_at_utc", "author_at", "committer_at"):
                if item.get(kind):
                    events.append({"timestamp": item[kind], "kind": rec["kind"] + "_" + kind,
                        "repo": repo, "ref": rec.get("issue_number"), "event_id": item.get("ref")})
    return events

def gather_archives(receipt):
    captures = []
    for r in receipt["records"]:
        if r.get("kind") == "cdx_page":
            for c in r.get("records", []):
                captures.append({"timestamp": c["timestamp"], "origin": r["origin"],
                    "url_sha256": c["url_sha256"], "provider_digest": c.get("provider_digest"),
                    "status": c.get("status"), "mimetype": c.get("mimetype")})
    return captures

def join_receipts(receipts):
    events = gather_git(receipts["blake"])
    archive = gather_archives(receipts["cesar"]) + gather_archives(receipts["reis"])
    links = []
    counts = {"same_utc_day": 0, "within_1d": 0, "within_7d": 0, "within_30d": 0}
    max_pairs = 500
    for capture in archive:
        try:
            t = dt.datetime.strptime(capture["timestamp"], "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        except ValueError:
            continue
        for ev in events:
            s = iso(ev.get("timestamp"))
            if not s: continue
            v = dt.datetime.fromisoformat(s)
            gap = abs((v-t).total_seconds())
            if gap > 30 * 86400: continue
            counts["within_30d"] += 1
            if gap <= 7*86400: counts["within_7d"] += 1
            if gap <= 86400: counts["within_1d"] += 1
            if t.date() == v.date(): counts["same_utc_day"] += 1
            if len(links) < max_pairs:
                links.append({"capture": capture, "git_event": ev,
                    "gap_seconds": int(gap), "relation": "TEMPORAL_ONLY_NOT_CAUSAL"})
    links.sort(key=lambda r: (r["gap_seconds"], r["capture"]["url_sha256"], str(r["git_event"]["ref"])))
    return {"candidates": links, "candidate_counts": counts,
            "candidate_truncated": counts["within_30d"] > len(links),
            "git_events_observed_this_cycle": len(events),
            "archive_captures_observed_this_cycle": len(archive),
            "scope": "CURRENT_CYCLE_SAMPLED_METADATA_NOT_EXHAUSTIVE",
            "claim_allowed": False}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", type=int, required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    found, inputs = {}, {}
    for lane in ("blake","cesar","reis"):
        blob, meta = artifact_blob(lane, args.run_id)
        if blob is None: raise SystemExit("BLOCKED_MISSING_LANE_" + lane)
        verified = load_verified_receipt(blob, lane)
        found[lane] = verified["receipt"]
        inputs[lane] = {"sha256": verified["receipt_sha256"], "artifact": meta}
    result = {"schema": "rafaelia.wayback.three_lane_join.v1",
              "run_id": args.run_id, "created_at_utc": dt.datetime.now(UTC).isoformat(),
              "inputs": inputs, "cross_lanes": join_receipts(found),
              "historical_warc": "TOKEN_VAZIO_NOT_RETRIEVED",
              "cross_repo_origin_provenance": "GITHUB_HEAD_BASE_AND_TIMELINE_FIELDS_ONLY",
              "claim_allowed": False}
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    raw = (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (out/"receipt.json").write_bytes(raw)
    (out/"SHA256SUMS").write_text(sha(raw) + "  receipt.json\n")
    print(json.dumps({"joined": True, "run": args.run_id,
                      "counts": result["cross_lanes"]["candidate_counts"],
                      "receipt_sha256": sha(raw), "claim_allowed": False}, sort_keys=True))

if __name__ == "__main__":
    main()
