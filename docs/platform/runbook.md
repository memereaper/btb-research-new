# Platform setup, publication and recovery

All commands run from the repository root. The public website is unchanged by building, loading or local previewing. No hosting account is provisioned by these commands.

## Local and CI

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-platform.lock
.venv/bin/python -m btb_platform build
```

The build prints a content-addressed directory such as `work/platform/releases/btb-v1-<24 hex characters>`. Use its actual name below. PostgreSQL 17+ is supported by the supplied schema. With Docker, `platform/compose.yml` supplies a local database, app and proxy; it requires a password and a separately configured reader URL. The native PostgreSQL integration workflow uses an isolated disposable database and tests real COPY imports.

On this Mac, native PostgreSQL initialization could not obtain shared memory in the execution environment. Local verification therefore used PGlite's PostgreSQL engine over its socket adapter, with one connection and `load --insert-batches`. That is a test compatibility mode, not the production deployment or a concurrency-capacity benchmark. Native PostgreSQL COPY is covered by the CI job; do not label a queued job as passed.

## Connect hosting

Required services: a private S3-compatible archive bucket (Cloudflare R2 is supported), managed PostgreSQL, and a Python/container host with HTTPS ingress. They can be under one provider if appropriate. A database account alone does not host the Python API. DNS access is optional if using a host-provided HTTPS address initially; a dedicated API hostname can follow without moving WordPress.

1. User signs into existing accounts or creates them and accepts any terms personally. Confirm budget before enabling paid resources. Use the service's secure credential configuration rather than pasting keys into chat.
2. Create a private archive bucket; disable public development access. Give only the upload/backup job scoped bucket access. Configure retention for failed multipart uploads. Do not apply an automatic deletion policy to immutable research releases.
3. Provision PostgreSQL with verified backup/recovery settings. Create an importer/owner login and a separate reader login. Adapt `platform/reader-role.sql` for the actual database name and grant the reader only the listed tables.
4. Configure `platform/.env.example` names in the host's secret store. Use TLS-verified database URLs. The API receives only `BTB_DATABASE_URL`, allowed origins, pool/rate settings; no admin or S3 keys. Import/archive jobs receive their separate secrets. Size the total connection budget as replicas × processes × pool size plus job connections; stay under the host's connection allowance.
5. Deploy the container from `platform/Dockerfile` behind the supplied reverse proxy or equivalent managed ingress/cache/rate limits. Keep its listener private. If using multiple proxy instances, configure an edge-wide rate limit as well. Configure HTTPS and automatic restarts/health checks. Container image and ingress are prepared but need a real host to be exercised.

## Publish a release

```sh
# Set secrets securely in the job environment; do not commit .env files.
.venv/bin/python -m btb_platform archive-plan work/platform/releases/RELEASE --include-raw
.venv/bin/python -m btb_platform archive-upload work/platform/releases/RELEASE --include-raw
.venv/bin/python -m btb_platform migrate
.venv/bin/python -m btb_platform load work/platform/releases/RELEASE
# Only after archive receipt, database reconciliation and pinned smoke checks:
.venv/bin/python -m btb_platform promote RELEASE --reason 'Reviewed publication'
.venv/bin/python -m btb_platform monitor https://YOUR_API_HOST --expected-release RELEASE
```

`RELEASE` represents the complete actual release ID, including `btb-v1-`. The archive inventory path and manifest hash are retained locally in the release bundle. Publication tools are intentionally separate steps: uploading files alone does not change an investigation. Promote only after the full archive is verified. The public API never exposes these commands.

## WordPress integration

Copy `platform/wordpress/btb-data-platform.php` and `explorer.js` into a plugin folder and install the ZIP prepared in outputs. Set the public HTTPS API base in WordPress's server configuration:

```php
define('BTB_DATA_API_URL', 'https://YOUR_API_HOST');
```

Add `[btb_data_explorer release="ACTUAL_RELEASE_ID" congress="118"]` to a reviewed draft or staging copy of the investigation. Verify counts, search, pagination, source links, keyboard use, mobile layout and API outage behavior. This is an additional versioned explorer; switching the existing lab and all animation data sources is a later, explicitly reviewed migration. No existing theme or plugin file is patched by this package.

Title search uses PostgreSQL full-text semantics, not the existing lab's substring search. The selected release is the reconstructed historical dataset with its documented reconciliation; do not mix it into charts pinned to a different source version without review. Millions of squares should use labeled aggregation/zoom levels rather than an unbounded per-record canvas. The supplied explorer uses bounded tables and summaries and does not change any current square animation.

## Collection growth

```sh
# Inspect/edit the example first, giving each snapshot a new name.
.venv/bin/python -m btb_platform collect platform/collection-plan.example.json
```

Jobs retain status/logs under `work/platform/collection-jobs`. A failed run can be rerun, reusing acquired source files. Existing valid outputs are preserved. Changing a job definition requires a new job ID/output. The example expands bill status but does not claim to implement complete Senate voting or full legislative text acquisition. These remain separate source-specific collection projects.

## Backup, restore and rollback

```sh
# pg_dump must be available to this background job.
.venv/bin/python -m btb_platform backup-db work/platform/backups/UNIQUE_NAME.dump
# Verify archived source bytes into a fresh directory:
.venv/bin/python -m btb_platform restore-archive PATH_TO_ARCHIVE_RECEIPT work/platform/restored
# Restore previous investigation pointer; no data deletion:
.venv/bin/python -m btb_platform promote PRIOR_RELEASE --reason 'Rollback after validation'
```

Restore a database dump only into a separate new database using the managed host's restore process or matching `pg_restore` client. Run integrity and API checks before redirecting traffic. Full source archives also allow rebuilding serving data without relying solely on a database backup. Keep a copy outside the provider for independent disaster recovery.

A local drill is available with `archive-upload --local-dir DIRECTORY --include-raw` and `restore-archive ... --local-dir DIRECTORY`. It verifies real bytes but is **not** an independent off-machine backup. Restore produces the hash-keyed objects; manifests/catalogs map hashes back to source and package paths. Do not overwrite existing source files until their hashes agree.

## Test and measure

```sh
.venv/bin/python -m unittest discover -s tests -v
# Use a disposable LOCAL test database, never production:
BTB_TEST_DATABASE_URL=YOUR_LOCAL_TEST_URL .venv/bin/python -m unittest discover -s platform/tests -v
BTB_TEST_DATABASE_URL=YOUR_LOCAL_TEST_URL .venv/bin/python platform/benchmark.py --rows 1000000
```

The benchmark uses a separate synthetic schema and refuses to reuse it. Its microsecond/millisecond SQL timings are not internet response times. The CI workflow runs native PostgreSQL tests, deterministic rebuilds, the full real import and a million-row synthetic index test. Production concurrency, TLS/ingress, R2 behavior, billing controls and recovery must be checked on the actual hosting accounts before cutover.
