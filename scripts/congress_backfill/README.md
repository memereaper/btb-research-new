# Congress.gov backfill (93rd–107th Congress, 1973–2002)

Extends the Hugging Face dataset `AbhayHarika/between-the-bills-congress` (folder `btb-hf-dataset-v2/`, currently 108th–119th)
with the same per-Congress parquet schemas. Existing rows are never modified; each Congress is a new file
`<table>/congress_<N>.parquet`.

1. `python3 fetch.py 107 /data/dir` (core pass: detail, actions, cosponsors, committees, subjects), then `fetch.py 107 /data/dir --extra` (summaries, titles, text versions, related bills, amendments) — resumable raw snapshot `raw_107.jsonl` + `extra_107.jsonl` (one line per bill, appended only when complete; rerun to resume). Auth is proxy-injected (`X-Api-Key` for `*.congress.gov`); no key is handled here. Pacing: global 0.30 s gap (~12,000 requests/hour, below the 20,000 the API advertises), 8 threads, backoff on 429/5xx.
   endpoints are fetched, so the file is the checkpoint; rerun to resume). Auth is proxy-injected (`X-Api-Key` for `*.congress.gov`);
   no key is handled here. Pacing: global 0.75 s gap (<= 4,800 requests/hour), 4 worker threads, backoff on 429/5xx.
2. `python3 normalize.py 107 /data/dir /out/dir` — builds the 11 bill tables (bills, actions, cosponsors, committees, subjects,
   summaries, titles, related_bills, amendments, text_versions, laws) and `validation_107.json`
   (row counts, duplicate bill IDs, orphans).
3. Verify, then upload to `btb-hf-dataset-v2/<table>/congress_107.parquet` and update the README row counts / "108th–" wording.

Known differences vs the 108th+ GovInfo-derived tables (documented, not hidden):
- `amendments`: sponsor, chamber and dates are null (the list endpoint omits them); only purpose and latest action are filled.
- `committees.activity` capitalisation follows the API (`Referred To`) vs GovInfo (`Referred to`).
- cbo_estimates, committee_reports, recorded_votes are not produced (vote links stay in `actions.vote_*`).
- Nothing before 1973 is collected: Congress.gov bill data starts at the 93rd Congress.
- `cross_party` = cosponsor party differs from sponsor party (same definition as existing tables).

## Update: faster two-pass mode
Pacing is now a global 0.30 s gap (~12,000 requests/hour; the API advertises 20,000/hour) with 8 threads, superseding the numbers in step 1.
Run `fetch.py N DIR` (core: detail, actions, cosponsors, committees, subjects), then `fetch.py N DIR --extra`
(summaries, titles, text versions, related bills, amendments; writes `extra_N.jsonl`, merged by `normalize.py`).
