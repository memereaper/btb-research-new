# Reproducing the depth release

Python 3.12 was used. The only nonstandard required package is PyYAML 6.0.3. No paid API key is needed. Code is MIT; external data rights are separate.

1. Extract the core data/code bundle and any source bundles into the SAME parent directory. Each bundle uses `btb_bipartisanship_v2/` as its top-level directory. The SQLite bundle is optional for analysis; the six per-Congress raw GovInfo bulk bundles are optional for reading CSVs but required for exact bulk-input reproduction without refetching.
2. Install the package in requirements.txt in your own environment. Run `python test_depth_rules.py`.
3. To inspect the supplied release, run `python validate_release.py`. Missing optional raw sources are reported separately. Use the supplied `schema.json`, TableCatalog, FieldDictionary, and EXAMPLE_QUERIES.sql.
4. To rebuild from the exact archived inputs, run these scripts from this directory in order:
   - `python build_context.py`
   - `python collect_sources.py` (reuses the pinned input files already present)
   - `python build_member_votes.py`
   - `python collect_bill_texts.py` (reuses archived bill XML)
   - `python build_text_context.py`
   - `python documentary_sources.py`
   - `python build_analysis.py`
   - `python prepare_release.py`
   - `python validate_release.py`
5. If the bulk-input bundle is not present, `python fetch_official_bulk.py` attempts to retrieve files matching the saved SHA-256 hashes. Official bulk archives can be corrected later; a hash mismatch stops the operation rather than silently changing this release. Use the archived source bundle if a remote file changed.

For a NEW collection date, use a separate output directory and treat it as a new version. The collector's cached Git commit JSON and source manifests are intentional: preserve them to reproduce this release, replace them only for an explicitly new snapshot. Public API rate limits and temporary source outages can affect a fresh collection.

Several scripts print collection timestamps in diagnostics. Content hashes and tabular results are the substantive reproducibility controls; byte-for-byte equality of fresh timestamped manifests is not expected.

The six official bulk input bundles preserve all 24 original ZIP files unchanged, including their original schemas. File size is not counted as additional data observations.
