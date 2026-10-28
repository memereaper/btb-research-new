# Acquired collection inventory — October 28, 2026

Counts overlap across relational tables. Do not add them as independent people, bills or events. Source fields retain strings; research SQL casts dates/numbers explicitly.

| Package / table | Rows | Fields |
|---|---:|---:|
| pathways-2026-10-28 / actions | 148,049 | 12 |
| pathways-2026-10-28 / bills | 33,591 | 23 |
| pathways-2026-10-28 / cbo_estimates | 2,700 | 8 |
| pathways-2026-10-28 / committee_events | 61,752 | 8 |
| pathways-2026-10-28 / committees | 42,844 | 8 |
| pathways-2026-10-28 / cosponsors | 323,226 | 13 |
| pathways-2026-10-28 / related_bills | 25,460 | 9 |
| pathways-2026-10-28 / subjects | 88,400 | 6 |
| pathways-2026-10-28 / summaries | 16,507 | 9 |
| pathways-2026-10-28 / text_versions | 40,472 | 9 |
| pathways-2026-10-28 / vote_references | 2,029 | 12 |
| house-2024-pathway-votes / positions | 118,488 | 8 |
| house-2024-pathway-votes / votes | 275 | 19 |
| member-crosswalk-2026-10-28 / member_identifiers | 97,319 | 4 |
| member-crosswalk-2026-10-28 / member_terms | 45,535 | 12 |
| member-crosswalk-2026-10-28 / members | 12,770 | 9 |
| text-survival-pilot-2026-10-28 / passage_candidates | 42 | 7 |
| text-survival-pilot-2026-10-28 / text_pairs | 24 | 8 |
| text-survival-pilot-2026-10-28 / text_sections | 2,148 | 7 |
| pathway-research-2026-10-28 / reintroduction_candidates | 9,104 | 12 |
| pathway-research-2026-10-28 / cosponsor_vote_observations | 4,743 | 22 |

Per-field missingness: field-completeness.csv. Exact URLs, retrieval timestamps, SHA-256 and HTTP response headers: sources.json. Methods, source scope and join limits: methods.md. Each dataset package includes its own checksums, catalog and validation report. Raw source bytes remain local under warehouse/collection-cache/objects/<sha256>. Sources were retrieved across a time window, not as a transactionally simultaneous extract.

21 acquired/derived collection tables; 225 field-level completeness checks; 327 raw source snapshots referenced.
