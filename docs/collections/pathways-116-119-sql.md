# Pathways SQL database: 116th–119th Congress

Built 2026-10-30T01:37:54+00:00 by `scripts/build_pathways_sql.py`; checked by `scripts/verify_pathways_sql.py`. File: `warehouse/sql/pathways-116-119.duckdb` (not in Git; 250 MB, SHA-256 `1134c4d4dd88367c…`). Rebuild it from the two verified packages in about 15 seconds.

## What it is

One typed DuckDB database joining the two official GovInfo BILLSTATUS pathway packages: `pathways-116-117-2026-10-29` (116th–117th) and `pathways-2026-10-28` (118th–119th). It holds **1,765,337 records** across 11 record types, describing **63,173 bills** (HR, S, H.J.Res., S.J.Res.), of which **1,122 became law**.

The 119th Congress was still in session when collected (latest introduction October 26, 2026). Keep it out of completed-outcome rates.

## Counting rule

The two inputs cover different Congresses, so no record appears in both. The total is a count of records of different kinds (bills, actions, cosponsorships, subjects…), not 1.7 million independent bills or events. Historical-v1 (113th–118th) is a separate snapshot and is deliberately not merged, so its 116th–118th actions are not counted again.

| Table | Grain (one row per…) | Rows | 116–117 | 118–119 | Rows sharing a grain key |
|---|---|---:|---:|---:|---:|
| bills | bill_id | 63,173 | 29,582 | 33,591 | 0 |
| actions | action_id | 290,617 | 142,568 | 148,049 | 0 |
| cosponsors | bill_id, sponsor_id, joined_date | 680,906 | 357,680 | 323,226 | 1 |
| committees | bill_id, committee_id | 81,501 | 38,657 | 42,844 | 0 |
| committee_events | bill_id, committee_id, event_name, event_date | 120,879 | 59,127 | 61,752 | 811 |
| related_bills | bill_id, related_bill_id, relationship, identified_by | 58,265 | 32,805 | 25,460 | 26 |
| subjects | bill_id, subject | 332,232 | 243,832 | 88,400 | 0 |
| summaries | bill_id, version_code, action_date | 51,179 | 34,672 | 16,507 | 0 |
| text_versions | bill_id, version_type, version_date, format_type, url | 77,258 | 36,786 | 40,472 | 0 |
| cbo_estimates | bill_id, url, publication_date | 5,165 | 2,465 | 2,700 | 120 |
| vote_references | bill_id, action_id, chamber, congress, session, roll_number | 4,162 | 2,133 | 2,029 | 0 |

958 rows repeat another row's grain key exactly as the source publishes them (for example one CBO estimate listed twice with two title spellings). They are kept. Excluding them gives **1,764,379 distinct records**.

## Flags kept, not deleted

- 26,641 action rows share date, code and text with another action on the same bill (mostly House floor actions, which BILLSTATUS repeats). Column `actions.repeated_payload`. Not automatically duplicates.
- 215 actions are dated before the bill's introduction date. Column `actions.before_introduction`.
- 11 bills have no sponsor ID. Column `bills.sponsor_missing`.
- 1,436 related-bill links point outside the 116th–119th. Column `related_bills.related_in_116_119`.
- 241 bills have no policy area.
- Cosponsors who withdrew and later rejoined appear once per joining, which is correct.

## Typed columns and views

Every source string column is kept. Added alongside: `congress_n`, `introduced_on`, `latest_action_on`, `became_law`, `action_on`, `joined_on`, `withdrawn_on`, `original_cosponsor`, `event_on`, `version_on`, `published_on`, `vote_on`, plus `source_collection`.

- `congress_overview`: bills, laws and introduction range per Congress.
- `bill_coalitions`: per bill, cosponsors, active cosponsors and cross-party cosponsors (derived from listed party codes; independents count as cross-party relative to D or R sponsors).
- `record_inventory`: the table above.

## Spot checks against official totals

Laws per Congress from this database: 116th 344, 117th 365, 118th 274, 119th 139 to date. The 116th and 118th match the official public-law counts. The 117th is 3 above the commonly cited 362 public laws; the gap is probably private laws but has not been checked.

## Limits

Subject coverage lags for recent bills (2.6 subject terms per bill in the 118th–119th versus 8.2 in the 116th–117th) because the Library of Congress indexes subjects over time; do not compare subject counts across these periods. Text-version rows are references, not full texts. CBO rows are estimate metadata, not extracted scores. Vote rows are references to roll calls cited by actions, not member positions (see `house-2024-pathway-votes` for those). This database is local and analytical; it is not loaded into the hosted Supabase serving database, which keeps only the published historical release under its free 500 MB allowance.

## Use

```sh
python3 scripts/build_pathways_sql.py   # build
python3 scripts/verify_pathways_sql.py  # check
duckdb warehouse/sql/pathways-116-119.duckdb "SELECT * FROM congress_overview"
```
