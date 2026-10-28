# Project brief for Claude and future contributors

## Mission

Build a reproducible, free, local-first research data system for Between the Bills using DuckDB, Parquet, SQL, Python, and versioned publication bundles. The work should make it possible to build original, unusually deep, checkable congressional investigations from public records. The long-term ambition is a distinctive, serious public-interest research project that can stand out in highly selective college applications. Treat that as a goal for the quality of the work, never as a guaranteed admissions outcome or a reason to exaggerate claims.

## Research starting point

The first published investigation, “Where Do Bills Go to Die?”, has been described as covering 76,867 bills and approximately 401,161 legislative actions from the 113th through 118th Congresses (2013–2024). Treat those as reported target totals, not verified warehouse counts. Reproduce and document them from the original source files before using them as validated results. Do not silently substitute newly downloaded data for the source records behind the published study. Preserve the raw inputs and their provenance, compute hashes, record retrieval dates and source versions, and document any corrections or changed inclusion rules.

The original 13 empty starter tables are preserved. The historical pipeline now uses immutable warehouse/snapshots directories and warehouse/current.json. Verified local imports contain 76,867 bills and 401,161 actions. The 33 future investigation tables have also been recovered from the cloud handoff, staged locally, and matched to cloud outputs; their findings are not independently recertified. Read README.md and the versioned methodology for source limitations and the 118th classification reconciliation. Never confuse empty starter tables with promoted snapshots.

## What good work looks like

- Every published number can be regenerated from checked-in SQL and a versioned input snapshot.
- Preserve original source files; normalize into staging and core tables with explicit mappings, stable identifiers, provenance, and documented missingness.
- Validate schemas, row counts, keys, joins, date ranges, duplicate handling, and known reference totals. Fail loudly when assumptions do not hold.
- Make the pipeline restartable and safe to rerun. Use temporary outputs and atomic promotion so an interrupted build cannot corrupt the last good dataset.
- Keep full source records and analytical outputs separate. Publish compact, documented CSV/JSON/Parquet artifacts with manifests, hashes, methods, and release identifiers.
- Prefer novel questions that require joining different record types or sources and produce useful, interpretable findings. Novelty must be demonstrated through a documented literature and data scan, not asserted without evidence.
- Make the work independently inspectable: include source links, query files, definitions, caveats, and a concise replication guide.
- Use free tools and public/open sources where their terms allow. Track attribution, license and access constraints. Do not commit credentials or private data.

## Build sequence

1. Inventory and protect all supplied work. Do not delete existing data, schema, or history.
2. Identify and ingest the original 2013–2024 bill and action sources, preserving exact files and recording checksums and retrieval metadata.
3. Build lossless staging, source-specific mappings, normalized core Parquet tables, and repeatable DuckDB SQL transformations.
4. Reconcile the resulting records against the reported 76,867 bills and approximately 401,161 actions. Investigate every material discrepancy and write down the resolution.
5. Reconstruct the first investigation's actual published methodology and outputs from its authoritative data. Keep any new interpretation or correction clearly versioned.
6. Add meaningful validation and reproducibility checks; generate a versioned, self-describing release bundle and test it from a clean checkout.
7. Only after a reviewable release exists, prepare a separate WordPress integration plan. Do not modify the live site or Explore plugin until Abhay reviews and approves deployment.

If source records are missing, stop before claiming ingestion or rebuilding published results. Provide a precise list of needed files and continue with source-independent infrastructure work.

## Website constraints

The public site uses a custom WordPress theme and Explore plugin. Preserve every existing theme, color palette, responsive layout, interactive behavior, and scroll animation. The research pipeline must build and validate locally first. Keep website integration isolated, versioned, and reversible. Never deploy, upload, or change the live WordPress site without explicit approval after Abhay can review the tested package and deployment steps.

## Handoff and communication

Before substantial changes, inspect the current repository and explain what is already present. Keep this file and the README aligned with the implementation. Report what is implemented, what data was actually ingested, validation evidence, unresolved source needs, and the next concrete step. Clearly distinguish verified results from targets, assumptions, and proposed analyses. Do not invent impact numbers, prestige, uniqueness, or claims about college admissions.
