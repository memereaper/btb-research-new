#!/usr/bin/env python3
"""Normalize raw_{congress}.jsonl into per-table parquet matching btb-hf-dataset-v2 schemas.
Usage: normalize.py CONGRESS RAWDIR OUTDIR
Writes OUTDIR/{table}/congress_{N}.parquet and OUTDIR/validation_{N}.json
"""
import json, os, re, sys, html
import pyarrow as pa, pyarrow.parquet as pq

S = pa.string; I = pa.int64; B = pa.bool_
SCHEMAS = {
 "bills": [("bill_id",S),("congress",I),("bill_type",S),("bill_number",I),("title",S),("introduced_date",S),("origin_chamber",S),("policy_area",S),("sponsor_bioguide",S),("sponsor_name",S),("sponsor_party",S),("sponsor_state",S),("sponsor_district",S),("by_request",B),("n_cosponsors",I),("n_original_cosponsors",I),("n_cross_party_cosponsors",I),("n_original_cross_party",I),("n_withdrawn_cosponsors",I),("n_actions",I),("n_committees",I),("n_subjects",I),("n_amendments",I),("n_text_versions",I),("became_law",B),("law_type",S),("law_number",S),("latest_action_date",S),("latest_action_text",S),("update_date",S),("congress_url",S)],
 "actions": [("bill_id",S),("congress",I),("seq",I),("action_date",S),("action_time",S),("text",S),("type",S),("action_code",S),("source_code",S),("source_name",S),("committee_codes",S),("vote_chamber",S),("vote_roll",I),("vote_session",I),("vote_url",S)],
 "cosponsors": [("bill_id",S),("congress",I),("bioguide_id",S),("full_name",S),("party",S),("state",S),("district",S),("sponsorship_date",S),("withdrawn_date",S),("is_original",B),("cross_party",B)],
 "committees": [("bill_id",S),("congress",I),("system_code",S),("name",S),("chamber",S),("committee_type",S),("parent_code",S),("activity",S),("activity_date",S)],
 "subjects": [("bill_id",S),("congress",I),("subject",S)],
 "summaries": [("bill_id",S),("congress",I),("version_code",S),("action_date",S),("action_desc",S),("update_date",S),("text",S)],
 "titles": [("bill_id",S),("congress",I),("title_type",S),("title",S),("chamber",S),("version",S)],
 "related_bills": [("bill_id",S),("congress",I),("related_bill_id",S),("relationship",S),("identified_by",S)],
 "amendments": [("bill_id",S),("congress",I),("amendment_id",S),("chamber",S),("purpose",S),("sponsor_bioguide",S),("sponsor_party",S),("proposed_date",S),("submitted_date",S),("latest_action_date",S),("latest_action_text",S)],
 "text_versions": [("bill_id",S),("congress",I),("version",S),("date",S),("url",S)],
 "laws": [("bill_id",S),("congress",I),("law_type",S),("law_number",S)],
}
TAG = re.compile(r"<[^>]+>")
def plain(t): return re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", t or ""))).strip() or None
def s(x): return None if x is None else str(x)
def bid(c, t, n): return f"{c}-{str(t).lower()}-{n}"

def main():
    c, rawdir, out = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    rows = {t: [] for t in SCHEMAS}; missing = 0; seen = set()
    extras = {}
    ep = os.path.join(rawdir, f"extra_{c}.jsonl")
    if os.path.exists(ep):
        for l in open(ep):
            e = json.loads(l); extras.setdefault(e["key"], {}).update(e)
    for line in open(os.path.join(rawdir, f"raw_{c}.jsonl")):
        r = json.loads(line)
        if r["key"] in seen: continue
        seen.add(r["key"])
        for k, v in extras.get(r["key"], {}).items():
            if k not in ("key", "extra"): r[k] = v
        d = r.get("detail")
        if not d: missing += 1; continue
        b = bid(c, d["type"], d["number"])
        sp = (d.get("sponsors") or [{}])[0]
        cos = [x for x in r.get("cosponsors", [])]
        cosr = []
        for x in cos:
            cp = bool(sp.get("party") and x.get("party") and x["party"] != sp["party"])
            cosr.append({"bill_id": b, "congress": c, "bioguide_id": x.get("bioguideId"), "full_name": x.get("fullName"), "party": x.get("party"), "state": x.get("state"), "district": s(x.get("district")), "sponsorship_date": x.get("sponsorshipDate"), "withdrawn_date": x.get("sponsorshipWithdrawnDate"), "is_original": x.get("isOriginalCosponsor"), "cross_party": cp})
        rows["cosponsors"] += cosr
        for i, a in enumerate(r.get("actions", [])):
            rv = (a.get("recordedVotes") or [{}])[0]
            src = a.get("sourceSystem") or {}
            rows["actions"].append({"bill_id": b, "congress": c, "seq": i, "action_date": a.get("actionDate"), "action_time": a.get("actionTime"), "text": a.get("text"), "type": a.get("type"), "action_code": a.get("actionCode"), "source_code": s(src.get("code")), "source_name": src.get("name"), "committee_codes": ",".join(x["systemCode"] for x in a.get("committees", [])) or None, "vote_chamber": rv.get("chamber"), "vote_roll": rv.get("rollNumber"), "vote_session": rv.get("sessionNumber"), "vote_url": rv.get("url")})
        ncomm = 0
        for cm in r.get("committees", []):
            for parent, node in [(None, cm)] + [(cm.get("systemCode"), sc) for sc in cm.get("subcommittees", [])]:
                acts = node.get("activities") or [{}]
                for ac in acts:
                    ncomm += 1
                    rows["committees"].append({"bill_id": b, "congress": c, "system_code": node.get("systemCode"), "name": node.get("name"), "chamber": node.get("chamber"), "committee_type": node.get("type"), "parent_code": parent, "activity": ac.get("name"), "activity_date": ac.get("date")})
        subj = r.get("subjects") or {}
        names = [x["name"] for x in subj.get("legislativeSubjects", [])]
        rows["subjects"] += [{"bill_id": b, "congress": c, "subject": n} for n in names]
        for x in r.get("summaries", []):
            rows["summaries"].append({"bill_id": b, "congress": c, "version_code": s(x.get("versionCode")), "action_date": x.get("actionDate"), "action_desc": x.get("actionDesc"), "update_date": x.get("updateDate"), "text": plain(x.get("text"))})
        for x in r.get("titles", []):
            rows["titles"].append({"bill_id": b, "congress": c, "title_type": x.get("titleType"), "title": x.get("title"), "chamber": x.get("chamberName"), "version": x.get("billTextVersionName")})
        for x in r.get("relatedBills", []):
            for rd in x.get("relationshipDetails") or [{}]:
                rows["related_bills"].append({"bill_id": b, "congress": c, "related_bill_id": bid(x["congress"], x["type"], x["number"]), "relationship": rd.get("type"), "identified_by": rd.get("identifiedBy")})
        for x in r.get("amendments", []):
            la = x.get("latestAction") or {}
            rows["amendments"].append({"bill_id": b, "congress": c, "amendment_id": f"{x.get('congress')}-{str(x.get('type','')).lower()}-{x.get('number')}", "chamber": None, "purpose": x.get("purpose") or x.get("description"), "sponsor_bioguide": None, "sponsor_party": None, "proposed_date": None, "submitted_date": None, "latest_action_date": la.get("actionDate"), "latest_action_text": la.get("text")})
        for x in r.get("textVersions", []):
            fm = x.get("formats") or [{}]
            rows["text_versions"].append({"bill_id": b, "congress": c, "version": x.get("type"), "date": x.get("date"), "url": fm[0].get("url")})
        laws = d.get("laws") or []
        for l in laws:
            rows["laws"].append({"bill_id": b, "congress": c, "law_type": l.get("type"), "law_number": l.get("number")})
        la = d.get("latestAction") or {}
        n_orig = sum(1 for x in cosr if x["is_original"]); n_cp = sum(1 for x in cosr if x["cross_party"])
        rows["bills"].append({"bill_id": b, "congress": c, "bill_type": str(d["type"]).lower(), "bill_number": int(d["number"]), "title": d.get("title"), "introduced_date": d.get("introducedDate"), "origin_chamber": d.get("originChamber"), "policy_area": (d.get("policyArea") or {}).get("name"), "sponsor_bioguide": sp.get("bioguideId"), "sponsor_name": sp.get("fullName"), "sponsor_party": sp.get("party"), "sponsor_state": sp.get("state"), "sponsor_district": s(sp.get("district")), "by_request": sp.get("isByRequest") == "Y" if sp else None, "n_cosponsors": len(cosr), "n_original_cosponsors": n_orig, "n_cross_party_cosponsors": n_cp, "n_original_cross_party": sum(1 for x in cosr if x["cross_party"] and x["is_original"]), "n_withdrawn_cosponsors": sum(1 for x in cosr if x["withdrawn_date"]), "n_actions": len(r.get("actions", [])), "n_committees": len({x["system_code"] for x in rows["committees"] if x["bill_id"] == b}) if False else len(r.get("committees", [])), "n_subjects": len(names), "n_amendments": len(r.get("amendments", [])), "n_text_versions": len(r.get("textVersions", [])), "became_law": bool(laws), "law_type": laws[0].get("type") if laws else None, "law_number": laws[0].get("number") if laws else None, "latest_action_date": la.get("actionDate"), "latest_action_text": la.get("text"), "update_date": d.get("updateDate"), "congress_url": d.get("legislationUrl")})
    val = {"congress": c, "bills_without_detail": missing}
    for t, cols in SCHEMAS.items():
        sch = pa.schema([(n, ty()) for n, ty in cols])
        tab = pa.Table.from_pylist(rows[t], schema=sch)
        os.makedirs(os.path.join(out, t), exist_ok=True)
        pq.write_table(tab, os.path.join(out, t, f"congress_{c}.parquet"), compression="zstd")
        val[f"rows_{t}"] = len(rows[t])
    ids = {r["bill_id"] for r in rows["bills"]}
    val["duplicate_bill_ids"] = len(rows["bills"]) - len(ids)
    for t in ("actions", "cosponsors", "committees", "subjects", "summaries", "titles", "related_bills", "amendments", "text_versions", "laws"):
        val[f"orphans_{t}"] = sum(1 for r in rows[t] if r["bill_id"] not in ids)
    json.dump(val, open(os.path.join(out, f"validation_{c}.json"), "w"), indent=1)
    print(json.dumps(val))

if __name__ == "__main__":
    main()
