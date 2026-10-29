# Between the Bills research pipeline

The original historical archive is now imported and validated locally: **76,867 measures and 401,161 action rows**, Congresses 113–118. Exact CSV sources, original parser scripts and upstream provenance are retained in immutable snapshots. No WordPress deployment occurs.

## Rebuild

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Extract the original Drive ZIP into imports/original_historical (data/ and scripts/).
python scripts/build_historical.py
python scripts/validate.py
python scripts/build_investigation.py where-bills-go-to-die
python -m unittest discover -s tests -v
```

Source: [historical data and methods archive](https://drive.google.com/file/d/1j3lqcLMBMg-HJN3at9YJlNqh1cyzzCmm/view). Preserve this exact archive; newly fetched GovInfo data may have changed. Raw archives stay outside Git history. The published dataset package includes its source hashes, links, normalized Parquet, outcomes, reconciliation and methods. Full rebuild requires the source ZIP; it is not downloadable by unauthenticated CI from private Drive.

## Data and publication

`warehouse/current.json` points to the last verified snapshot under `warehouse/snapshots/`. Builds create a separate temporary directory and promote only after validation; failures preserve the prior pointer. Snapshot identity includes source bytes and transformation code. Rerunning unchanged inputs verifies and reuses the snapshot. Original empty `warehouse/core/` tables are retained as scaffolding; **use the promoted snapshot**, not those starter tables.

Each snapshot has `raw/` (exact input files), `staging/` (all source columns as text plus file/row provenance), `core/` (typed bills and actions, complete historical features, outcomes), `investigation/`, a validation report and a checksummed manifest. Actions retain repeated source records. The combined bill CSV must exactly match the per-Congress CSVs. Schema, keys, references, dates and known totals fail loudly on error.

Publication produces `releases/<snapshot_id>/` and a ZIP. This contains compact Parquet, CSV/JSON outcomes, methods, source notes, the original-vs-rebuilt 118th reconciliation, and checksums. `datasets/historical-v1/` is the reviewed compact Git publication copy; source archives and environments are excluded. No service needs to run continuously: execute the pipeline when inputs or methods change. Nothing automatically updates the website.

## Research limits

This is the standardized historical reconstruction, with 129 stage differences from the originally published 118th dataset. Eleven sponsor IDs are absent. There are 568 pre-introduction action rows, retained in an audit CSV; some explicitly record earlier hearings, and others need review before elapsed-time analyses. See the [methodology](investigations/where-bills-go-to-die/methodology.md). The source ZIP contains CSV extracts and original parser code, not the underlying GovInfo XML ZIPs. Their upstream hashes are retained but not independently re-downloaded and verified.

[Future datasets](docs/future-datasets.md) can use the immutable CSV intake command. The cloud handoff’s **33 future investigation tables** are now staged locally and matched value-for-value against its completed Parquet outputs. Original methods and attribution are included. These extracts still require source-specific normalization and independent analytical review. See [cloud reconciliation](docs/cloud-handoff.md).

Run `python scripts/verify_future.py` to check future package hashes/counts. Use `python scripts/query.py --file investigations/where-bills-go-to-die/queries/02_outcomes.sql` to query the promoted historical snapshot, or query `future_<lowercase table name>` for future staging.

## Expanded pathways collection — October 28, 2026

New public-source packages add 21 tables: full 118/119 HR/S/HJRES/SJRES bill status, dated cosponsors, committee events, official relationships, text/CBO links, 275 bill-linked 2024 House votes, a pinned historical member crosswalk, and an explicit text-survival pilot. See [acquired inventory](docs/collections/inventory.md), [methods and prior-research priorities](docs/collections/methods.md) and [field missingness](docs/collections/field-completeness.csv). Existing historical/future releases are preserved.

```sh
python scripts/verify_collections.py --raw
python scripts/query_collections.py --sql 'SELECT later_congress,count(*) FROM research_reintroduction_candidates GROUP BY later_congress ORDER BY later_congress'
```

Reproduce using cached immutable source snapshots (run in this order in a clean output location; existing dated packages deliberately refuse replacement):

```sh
python scripts/collect_pathways.py --congress 118 119 --output datasets/pathways-2026-10-28
python scripts/collect_house_votes.py
python scripts/collect_members.py
python scripts/collect_text_pilot.py
python scripts/build_pathway_research.py
python scripts/write_collection_inventory.py
```

The collectors accept `--output` for a separately named snapshot; House/text collectors also accept `--status` to select the input status release. `--refresh` refetches source URLs and retains old content objects. Research SQL and package mappings are deliberately frozen to this release; review them explicitly for another scope. Offline CI verifies published data; collection does not run automatically on every push. New source tables retain string fields, with explicit typed comparisons in research SQL. Raw official XML/ZIP/YAML objects remain in the ignored local collection cache. The 119th is ongoing, recurrence/text matches are unverified candidates, and absence is never silently converted to opposition.

## Scalable website data platform

The new `btb_platform` package separates research processing from visitor requests. It builds content-addressed, Congress-partitioned Parquet releases; archives sources through S3-compatible storage; transactionally loads indexed PostgreSQL tables; and serves bounded, version-pinned summaries, bill searches and evidence through a read-only API. A separate WordPress shortcode integration uses 50-row pages. Existing investigations, animations and data releases remain unchanged.

Read [architecture and data contracts](docs/platform/architecture.md) and the [setup/publication/recovery runbook](docs/platform/runbook.md). Install `requirements-platform.lock`, then run `python -m btb_platform --help`. The platform CI workflow tests native PostgreSQL, COPY imports, reproducible builds and a million-row synthetic index workload. Local test evidence must not be presented as production capacity.

Current scope is **prepared and locally tested**, not cloud deployed. The user has no existing hosting accounts and requested preparation first. Cloud archive storage, a managed PostgreSQL account, a container/API host, production credentials, HTTPS, budgets, operational scheduling and the final WordPress installation await account setup. No paid resources or accounts were created.
