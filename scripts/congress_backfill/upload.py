#!/usr/bin/env python3
"""Upload one normalized Congress to the HF dataset intake area (additive only).
Usage: upload.py CONGRESS NORMALIZED_DIR
Files: sources/congress/<table>/congress_NNN.parquet (three-digit Congress) and
sources/congress/backfill/manifest_NNN.json (rows, bytes, sha256, validation, known source errors).
Does NOT edit data/base catalogs, DATA_INDEX.json or README: the archive integrator owns those and adds the
backfill entry from this manifest. Commit is guarded by parent_commit so a concurrent change fails instead of overwriting.
"""
import hashlib, json, os, sys, time
from huggingface_hub import HfApi, CommitOperationAdd
REPO = "AbhayHarika/between-the-bills-congress"

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def main():
    c, d = int(sys.argv[1]), sys.argv[2]
    n = f"{c:03d}"
    val = json.load(open(os.path.join(d, f"validation_{c}.json")))
    ops, files = [], {}
    for t in sorted(x for x in os.listdir(d) if not x.endswith(".json")):
        p = os.path.join(d, t, f"congress_{c}.parquet")
        files[t] = {"path": f"sources/congress/{t}/congress_{n}.parquet", "rows": val[f"rows_{t}"], "bytes": os.path.getsize(p), "sha256": sha(p)}
        ops.append(CommitOperationAdd(files[t]["path"], p))
    man = {"congress": c, "source": "Congress.gov API v3 (api.congress.gov)", "tables": files, "validation": val}
    mp = os.path.join(d, f"manifest_{n}.json"); json.dump(man, open(mp, "w"), indent=1)
    ops.append(CommitOperationAdd(f"sources/congress/backfill/manifest_{n}.json", mp))
    api = HfApi()
    for i in range(4):
        try:
            head = api.repo_info(REPO, repo_type="dataset").sha
            r = api.create_commit(REPO, ops, repo_type="dataset", parent_commit=head,
                                  commit_message=f"Add {c}th Congress bill tables (Congress.gov API) to sources/congress")
            print(r.commit_url); return
        except Exception as e:
            print("retry", i, str(e)[:120]); time.sleep(2 ** (i + 1))
            # a 502 can arrive after the commit landed: do not re-commit if the manifest is already there
            try:
                if api.file_exists(REPO, f"sources/congress/backfill/manifest_{n}.json", repo_type="dataset"):
                    print("commit already landed; not retrying"); return
            except Exception:
                pass
    sys.exit(1)

if __name__ == "__main__":
    main()
