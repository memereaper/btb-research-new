# Scalable investigation delivery

The existing DuckDB/Parquet research system remains authoritative. This adds a separate PostgreSQL serving layer and read-only API; it does not turn GitHub into a database or make browsers download full collections.

## Implemented boundaries

1. Existing public-source collectors retain immutable fetched bytes and source metadata. A durable sequential collection runner records running/failed/complete jobs, locks concurrent runs, resumes completed-file caching, verifies outputs, and never publishes automatically. Its example plan broadens bill status to Congresses 113–119. The House collector is still a 2024 bill-linked subset and text collection is still a pilot: this infrastructure does not claim their missing coverage has been acquired.
2. A release builder verifies the historical, future, and new package files. It builds Congress-partitioned Zstandard Parquet for the historical bills/actions and a catalog referencing all research collections. The first serving release is the frozen historical investigation, excluding the ongoing 119th. Changing input bytes or the builder changes the release identity.
3. S3-compatible object storage archives bytes under SHA-256 keys. Identical bytes deduplicate. Uploads resume by checking size and SHA metadata. Original historical raw CSV/script snapshots, the new raw XML/ZIP/YAML cache and URL metadata are included with `--include-raw`. An immutable archive inventory and release manifest are uploaded last. Restore downloads are verified against full SHA-256. Remote metadata checks are not a substitute for restore drills.
4. PostgreSQL holds indexed serving bills, actions, summary cells, releases and promotion history. Bills/actions are partitioned by release. Bulk COPY imports are atomic: counts, foreign keys and summary totals must agree before readiness. Existing releases are never overwritten. Preparation does not publish; promotion updates a small investigation pointer in one transaction and logs a reason. Rollback promotes an existing ready version.
5. The API provides fixed read-only queries, 100-row maximum pages, filter-bound keyset cursors, indexed full-text search, statement/lock timeouts, bounded connection queues and caches, ETags, gzip and configured CORS. Charts aggregate precomputed summary cells; title searches use PostgreSQL text search and may return 503 rather than run indefinitely. There is no arbitrary SQL endpoint or browser credential.
6. The reverse proxy adds a shared per-client rate limit and bounded disk cache. Public traffic must reach it through HTTPS ingress; do not expose the API container directly. PostgreSQL connections use a dedicated SELECT-only login. Loader and object-storage credentials belong only in background jobs.
7. The WordPress shortcode is an isolated integration for the existing investigation. It pins a release, fetches 50 rows, requests small summary counts and opens source evidence on demand. It does not replace or modify the existing Explore plugin, visuals, or animations. The local preview exercises the same browser client. Installing the plugin and adding the shortcode is the final website step after the hosted backend is verified.

## Data contract

- Bill IDs: `congress-typeNumber`, e.g. `118-hr1015`; member crosswalk IDs: source Bioguide IDs; source bytes: SHA-256.
- Record identity is scoped to its source release. Historical action IDs and source-ordered current XML action IDs are not interchangeable cross-snapshot event identities. Preserve duplicates; do not join them by ordinal position across releases.
- Text versions must retain bill ID, official version/date, source URL and content hash. Text passage matches and reintroduction candidates stay explicitly unreviewed until validated.
- Every response names its release. References contain original source file/row and official source URL. Release manifests preserve input hashes and known limitations.
- Missing, no, not voting and same-day ambiguity remain separate. Ongoing Congresses do not enter completed-outcome denominators.
- Published investigations pin `release=`. Unpinned discovery can change on promotion; that is unsuitable for a fixed published claim.

## Scale and growth

Millions of actions do not imply millions of browser rows. Search sends a small page; a chart receives groups. The first release still contains 76,867 distinct bills and 401,161 actions. The synthetic benchmark is separate from these research records.

Object storage/Parquet scales independently of PostgreSQL. Keep bulk XML, full documents, analytical joins and text matching in background processing. PostgreSQL holds what visitors need. For larger serving data, add Congress partitions within each release, selective composite indexes supported by measured query plans, read replicas and independently scaled API replicas. Large searches may need a dedicated search index only when measurements justify it. Old releases can remain in the archive and be deliberately retired from live serving under a retention policy; do not silently break citations.

This foundation does not promise unlimited capacity, automatic infrastructure scaling, or a production traffic SLA. Capacity depends on host resources, query shape, write rate and traffic. Benchmark the selected production topology before changing capacity claims.

## Operational controls

- `monitor` checks readiness, data response size/latency and an expected release; it exits unsuccessfully on failure. Attach it to the chosen host's scheduler/monitor once connected. It sends no messages by itself.
- PostgreSQL/custom-format backup command and hash-based object storage upload are provided. Install matching PostgreSQL client tools in the backup job. Managed host backups/PITR remain a separate account configuration to verify.
- Request logs record route template, status, duration and request ID, excluding query strings and credentials. Host log retention and alert routing still need configuration.
- Track object bytes/operations, database disk/index growth, API p95 latency/errors, connection saturation, job failures and collection freshness. Set host billing alerts and enforce the agreed budget before activation; the application cannot impose a universal provider billing cap.
- Run restore drills into a separate database. Reconcile bill/action counts and summaries, then verify API responses before considering recovery successful.
