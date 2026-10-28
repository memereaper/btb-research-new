# Cloud work reconciled on the Mac

The completed “Implement Explore Page Optimization” chat supplied a [GitHub-ready handoff](https://drive.google.com/file/d/1ISgVTNV_R5n9K1Zm5zkhciTXxVwaPXT7/view). It is preserved, without overwriting local files, under ignored `imports/cloud-handoff/btb-research-new/`. This retains the cloud pipeline, query tools, 49-table catalog, normalized historical results and input ZIPs. Its active cloud version was 1aac43365582f4e9.

The Mac historical importer was already built with stronger combined/per-Congress equality checks and an audit of pre-introduction actions. It remains the active implementation to avoid replacing the local snapshot pointer and schema with the cloud pipeline's different layout. Cloud investigation SQL and the direct-Parquet query workflow were reused. All 33 supplied future CSV tables were independently imported on the Mac, counted with Python's CSV reader and compared in both directions, including duplicate multiplicity and blank values, against completed cloud staging. Every comparison passed.

The future package lives under `datasets/bipartisanship-v2/`. It includes source hashes, counts, table columns, checksums, original methods and attribution. Raw packages, archived web pages and source code remain local in imports. Original data rights are retained; no claim that Voteview or third-party content inherits BTB's code license. Future tables are staged source extracts, not independently recertified findings or normalized entity tables.

Reproduce future staging after extracting the supplied future-data-code.zip:

```sh
python scripts/stage_future.py imports/future-original/btb_bipartisanship_v2
python scripts/verify_future.py
python scripts/query.py --sql 'SELECT count(*) FROM future_cosponsorevents118'
```

If the versioned publication already exists, verify it; create a separately named publication for a changed source rather than overwriting it. The archive extraction and current local table comparison have already been performed.
