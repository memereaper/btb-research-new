#!/usr/bin/env python3
"""Resumable Congress.gov API fetcher (raw snapshots).

Usage: fetch.py CONGRESS OUTDIR [--limit N]
Auth is proxy-injected (X-Api-Key); no key is read or sent here.
Writes OUTDIR/raw_{congress}.jsonl: one line per bill = {key, fetched_at, detail, <endpoint>: [pages...]}.
A bill line is appended only after all its endpoints are complete, so the file is the checkpoint.
Rate limit: <=12000 requests/hour (0.30 s global spacing, 8 threads), exponential backoff on 429/5xx.
"""
import json, os, sys, time, threading, urllib.request, urllib.error, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://api.congress.gov/v3"
MIN_GAP = 0.30  # ~12,000 requests/hour (API advertises 20,000/hour)
_last = [0.0]
_lock = threading.Lock()
WORKERS = 8
STATS = {"requests": 0}

def get(url, tries=4):
    if "format=json" not in url:
        url += ("&" if "?" in url else "?") + "format=json"
    for i in range(tries):
        with _lock:  # global pacing across threads
            wait = _last[0] + MIN_GAP - time.time()
            if wait > 0: time.sleep(wait)
            _last[0] = time.time(); STATS["requests"] += 1
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "btb-research/1.0"}), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(min(600, 5 * 2 ** i)); continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(min(600, 5 * 2 ** i))
    raise RuntimeError("giving up on " + url)

def pages(url, listkey):
    """Fetch all pages of an endpoint; returns list of items."""
    out, u = [], url + ("&" if "?" in url else "?") + "limit=250"
    while u:
        d = get(u)
        if d is None: break
        out.extend(d.get(listkey) or [])
        u = (d.get("pagination") or {}).get("next")
    return out

# detail field -> (endpoint path, list key)
CORE = {
    "actions": ("actions", "actions"), "cosponsors": ("cosponsors", "cosponsors"),
    "committees": ("committees", "committees"), "subjects": ("subjects", None),
}
EXTRA = {
    "summaries": ("summaries", "summaries"), "titles": ("titles", "titles"),
    "textVersions": ("text", "textVersions"), "relatedBills": ("relatedbills", "relatedBills"),
    "amendments": ("amendments", "amendments"),
}
ENDPOINTS = {**CORE, **EXTRA}

def fetch_bill(congress, b, endpoints=None):
    endpoints = endpoints or ENDPOINTS
    key = f"{congress}-{b['type']}-{b['number']}"
    d = get(f"{BASE}/bill/{congress}/{b['type']}/{b['number']}")
    if d is None:
        rec = {"key": key, "detail": None}
    else:
        det = d["bill"]
        rec = {"key": key, "full": endpoints is ENDPOINTS, "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "detail": det}
        for field, (path, lk) in endpoints.items():
            info = det.get(field)
            cnt = info.get("count", 0) if isinstance(info, dict) else (len(info) if info else 0)
            if cnt:
                u = f"{BASE}/bill/{congress}/{b['type']}/{b['number']}/{path}"
                try:
                    if lk is None:  # subjects nest under 'subjects'
                        dd = get(u + "?limit=250")
                        rec[field] = (dd or {}).get("subjects", {})
                    else:
                        rec[field] = pages(u, lk)
                except RuntimeError as e:  # persistent source-side error: record, don't crash
                    rec.setdefault("_errors", {})[field] = str(e)[:200]
    return rec

def fetch_extra(congress, rec):
    """Extras pass: reuse stored detail (counts), fetch only EXTRA endpoints."""
    det = rec["detail"]; t, n = det["type"].lower(), det["number"]
    out = {"key": rec["key"], "extra": True}
    for field, (path, lk) in EXTRA.items():
        info = det.get(field)
        cnt = info.get("count", 0) if isinstance(info, dict) else (len(info) if info else 0)
        if cnt:
            try: out[field] = pages(f"{BASE}/bill/{congress}/{t}/{n}/{path}", lk)
            except RuntimeError as e: out.setdefault("_errors", {})[field] = str(e)[:200]
    return out

def run_extra(congress, outdir, limit):
    raw = os.path.join(outdir, f"raw_{congress}.jsonl"); ext = os.path.join(outdir, f"extra_{congress}.jsonl")
    have = {k for k in (json.loads(l).get("key") for l in open(ext) if l.strip())} if os.path.exists(ext) else set()
    todo = []
    for l in open(raw):
        r = json.loads(l)
        if r.get("detail") and r["key"] not in have and not r.get("full"): todo.append(r)
    if limit: todo = todo[:limit]
    print(f"extras: todo={len(todo)}", flush=True); t0 = time.time()
    with open(ext, "a") as fh, ThreadPoolExecutor(WORKERS) as ex:
        for n, f in enumerate(as_completed([ex.submit(fetch_extra, congress, r) for r in todo]), 1):
            fh.write(json.dumps(f.result()) + "\n"); fh.flush()
            if n % 100 == 0: print(f"extras {n}/{len(todo)} requests={STATS['requests']} elapsed={time.time()-t0:.0f}s", flush=True)
    print("finished extras", congress, flush=True)

def main():
    congress, outdir = int(sys.argv[1]), sys.argv[2]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    os.makedirs(outdir, exist_ok=True)
    if "--extra" in sys.argv: return run_extra(congress, outdir, limit)
    raw = os.path.join(outdir, f"raw_{congress}.jsonl")
    idx = os.path.join(outdir, f"index_{congress}.json")
    done = set()
    if os.path.exists(raw):
        for line in open(raw):
            try: done.add(json.loads(line)["key"])
            except Exception: pass  # truncated last line is re-fetched
    if os.path.exists(idx):
        index = json.load(open(idx))
    else:
        index = [{"type": b["type"].lower(), "number": b["number"]} for b in pages(f"{BASE}/bill/{congress}", "bills")]
        json.dump(index, open(idx, "w"))
    todo = [b for b in index if f"{congress}-{b['type']}-{b['number']}" not in done]
    if limit: todo = todo[:limit]
    print(f"congress {congress}: index={len(index)} done={len(done)} todo={len(todo)}", flush=True)
    t0 = time.time()
    with open(raw, "a") as fh:
        ex = ThreadPoolExecutor(WORKERS)
        futs = [ex.submit(fetch_bill, congress, b, CORE) for b in todo]
        for n, f in enumerate(as_completed(futs), 1):
            rec = f.result()
            fh.write(json.dumps(rec) + "\n"); fh.flush()
            if n % 50 == 0:
                print(f"{n}/{len(todo)} requests={STATS['requests']} elapsed={time.time()-t0:.0f}s", flush=True)
    print("finished", congress, "requests", STATS["requests"], flush=True)

if __name__ == "__main__":
    main()
