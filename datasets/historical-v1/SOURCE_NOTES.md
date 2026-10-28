# Where Bills Go to Die: historical data release

Scope: six completed Congresses, 113th through 118th, commonly labeled 2013-2024. Includes HR, S, HJRES, and SJRES measures. Does not include simple or concurrent resolutions. Each measure is a separate introduced legislative vehicle; companion bills are not collapsed.

The release contains 76,867 unique measures and 401,161 dated legislative action rows, extracted from 24 official GovInfo BILLSTATUS bulk ZIP archives. Source URLs, archive checksums, download sizes, collection code, and quality diagnostics are included. All archives parsed with zero record errors. Thirteen legacy XML records required field/wrapper normalization. Eleven source records have no sponsor Bioguide ID; missing source values remain blank.

Files:
- bills_2013_2024.csv: combined bill table, one row per Congress-measure ID.
- bills_113.csv through bills_118.csv: per-Congress tables with the same columns.
- actions_113.csv through actions_118.csv: dated source action text/codes for tracing milestones.
- congress_summary.csv: counts and enacted rates by Congress.
- 118_published_reconciliation.csv: cell differences between rebuilt 118th records and the original published CSV, with old and new values.
- source_manifest.json: exact bulk archive URLs and SHA-256 checksums.
- quality_report.json: completeness, unique IDs, missingness, and date boundaries.
- scripts/: reproducible downloader and parser.

Date boundary: Congress membership defines inclusion. The nominal years 2013-2024 describe the six Congresses, not a strict January 1-December 31 filter. Congressional terms continue into early January of the next odd-numbered year. This preserves the original 118th Congress population and includes introduction dates through January 3, 2025. See quality_report.json for the counts outside nominal calendar years.

Milestones and classification:
- passed_house: earliest official action code 8000.
- passed_senate: earliest official action code 17000.
- reported: earliest full committee report action 5000/14000, with top-level committee activity fallback. Subcommittee reports are stored separately.
- committee_discharged: earliest official action 5500/14500. Discharge is not a committee report.
- committee_action: earliest hearing, markup, ordering-to-report, report, or relevant committee/subcommittee activity. Where action-date and timestamp records differ, action dates are preferred when observed.
- ordered_reported, committee_hearing, committee_markup, subcommittee_reported: separate dates, so ordering a report or a subcommittee event is not mistaken for a full committee report.
- vetoed: action 31000 or explicit presidential veto text.
- became_law: earliest action 36000/BecameLaw; law identifiers also inform enactment classification.
- Stage hierarchy: enacted; vetoed and not enacted; both chambers; one chamber; full committee report or discharge; committee activity; no committee progress/chamber passage recorded.
- No recorded committee progress/chamber passage is not proof that a bill received no other action. Floor activity and unsuccessful procedural events remain in the action tables.
- bipartisan_at_introduction: opposite D/R party among official original cosponsors. Independent labels are preserved but do not satisfy the strict D/R rule.
- identical_bill_enacted: a measure not itself enacted has an explicitly 'Identical bill' relationship to another measure enacted in that same Congress. This does not detect provisions incorporated into unrelated legislation or prove all policy content failed.

Comparison with the published 118th dataset:
Population remains 16,565 measures. Passage and enactment dates match the published fields. Standardized stage classification differs for 129 measures: 125 previously placed in the reported category are classified as committee activity because the report was from a subcommittee rather than a full committee, and four previously in the no-progress category have recorded discharges. There are also 341 report-date differences and 14 committee-activity-date differences. The original published files are preserved separately in the parent data folder. This release makes those distinctions explicit for comparison across Congresses; it does not change the website automatically.

Sources:
https://www.govinfo.gov/bulkdata/BILLSTATUS
https://github.com/usgpo/bill-status
Original article: https://betweenthebills.com/explore/where-bills-go-to-die/
Retrieved: 2026-10-26.
