# Between the Bills: Bipartisanship depth release v2.0.0

Prepared October 26, 2026. This is a research release prepared for reuse and open publication, not a claim that an article, repository, or public API has been published.

## Research question

When legislators cosponsor across party lines, how does that support relate to later votes, changes in the bill, institutional position, and legislative progress?

The main vote analysis covers the complete 118th Congress universe of HR, S, HJRES, and SJRES measures. It includes 16,565 measures, 169,544 cosponsor records, 581 unique source-linked roll calls, and 208,471 individual member-vote positions. A separate fixed-time coalition table covers 76,867 measures in the six completed Congresses conventionally labeled 2013-2024. Full congressional terms extend into early January of the next odd-numbered year.

## Start with these files

- `data/AnalyticalPairs118.csv`: 8,408 unique bill-member pairs at the latest eligible original-chamber primary disposition. Includes dated party affiliations, prior-Congress ideology, tenure, committee context, vote purpose, CBO link timing, and observed text-change context.
- `data/BillAnalyticalContext118.csv`: the full 16,565-measure denominator with sponsor context and original/30/90-day coalition measures.
- `data/CosponsorVoteEvents118.csv`: all 11,477 exact-ID cosponsor-to-vote matches before selecting the analysis cohort. Future joins, nonprimary votes, and timing ambiguities remain visible.
- `data/RetentionSensitivity118.csv`: alternative denominators and timing rules. Not Voting is separated from Nay, and independents are not folded into same-party D/R comparisons.
- `data/BillVoteCoverage118.csv`: selection into linked roll calls and primary disposition votes across the entire bill population.
- `data/BillLandmarks2013_2024.csv`: 30/90-day active sponsorship and risk-set flags for six Congresses.
- `CASE_DOSSIERS.md`: eight documentary leads and explicit unanswered questions; includes all six bills with an active cross-party cosponsor Nay in the primary selected cohort.
- `data/TableCatalog.csv`, `data/FieldDictionary.csv`, `schema.json`: units, counts, field types, missingness, and joins.
- `btb_bipartisanship_v2.sqlite`: the CSV tables in SQLite, with integer booleans, nullable numeric fields, stable indices, and SQL example queries.

## Substantive additions

1. **What the vote meant.** Passage, suspension passage, concurrence, concurrence with amendment, conference report, cloture, motion to proceed, recommittal, tabling, budget waiver, point of order, and veto override are separately coded. The primary analysis uses passage/suspension passage/plain concurrence/conference-report dispositions. Veto overrides and concurrence with amendment are retained as separate events and excluded from that primary cohort. A procedural Yea is not automatically policy endorsement.
2. **When support existed.** Cosponsor join and withdrawal dates are preserved. Date-level active support requires joining on or before the vote and no withdrawal by that date. A strict sensitivity rule excludes same-day joins/withdrawals. Eight matched source events involve a join after an earlier vote and 354 have same-day ordering uncertainty. No matched event in this extract has a recorded withdrawal by its vote date; withdrawals elsewhere in the full cosponsor census remain present.
3. **Dated identities and affiliations.** House Bioguide IDs and Senate LIS IDs join to a pinned @unitedstates roster; every one of the 208,471 member positions resolves by exact identifiers. Party registration/affiliation and caucus are distinct. Dated party-affiliation ranges are used when provided. One official vote party label conflicts with the roster, and one sponsor label differs from the dated affiliation; both versions are preserved in audit tables. Do not silently replace official vote party labels.
4. **Institutional position.** Service days before the event and referred-committee membership/leadership are supplied. Committee assignments come from 23 historical Git snapshots comprising 85,813 membership observations, including subcommittees. Snapshot dates are observation dates, not appointment-effective dates. A membership observation can be stale; age and same-day flags are supplied. Events before the first available February 17, 2023 snapshot remain unknown, not false.
5. **Ideology before the outcome period.** Term-specific Nokken-Poole scores from the 117th Congress are available as lagged controls. New members or members without same-chamber prior scores remain missing. The 118th DW-NOMINATE field is retained as descriptive context, not a clean pre-outcome predictor. Prior-year estimates still reflect their source's model and later corrections; they are not a real-time archived prediction.
6. **What happened to the wording.** All 1,383 XML bill versions available in the catalog for the 390 measures with source-linked roll calls are archived and extracted. Exact sets of normalized five-word sequences measure lexical overlap, with paragraph excerpts for inspection. There are 1,364 unique version-pair comparisons. No similarity threshold is treated as proof of policy equivalence, policy abandonment, or legislative influence. Ninety-seven versions have no date in the status catalog and are excluded from dated as-of selection. Same-day version order and unpublished floor amendments make text-at-vote proxies uncertain; strict-before-date alternatives are supplied.
7. **Budget and related vehicles.** The release includes 1,496 CBO estimate links/titles/publication dates/descriptions, 21,057 committee referrals, 32,133 committee/subcommittee activities, and 13,203 source-described bill relationships. CBO links are metadata references supplied through GovInfo, not newly extracted numerical budget estimates, and score timing does not prove the estimate covers the exact voted text. A related enacted bill is not proof that every provision survived.
8. **Research rather than a raw aggregate.** The release compares cross- and same-party members within the same bill-vote event, supplies equal-bill weighting, separates participation from opposition, and records coverage selection. It supplies historical landmark cohorts that exclude measures already enacted by the support-measurement date and flag insufficient term follow-up.

## Revised descriptive result

In the latest primary disposition cohort, 1,743 cross-party bill-member pairs consist of 1,640 Yea/Aye positions, 14 Nay/No positions, two Present positions, and 87 Not Voting positions. Yea is 94.09% of all recorded positions and 99.15% of Yea/Nay votes. The corresponding same-party D/R cohort has 6,658 pairs: 6,456 Yea/Aye, 17 Nay/No, and 185 Not Voting. Its Yea/Nay-only rate is 99.74%.

These are conditional, descriptive rates for bills that reached source-linked primary recorded votes. They are not rates for all introduced bills, promises, negotiations, or causal effects. Each member can appear on many bills; any inferential model should account for dependence by bill and member. Among the 274 enacted measures in the full 118th universe, 190 have no source-linked roll-call XML in this extract. This does not mean none received a recorded vote; it makes the linkage coverage and voice-vote/other pathways explicit.

## Historical landmark rules

At day 30 or 90 after introduction, count cosponsors whose join date is on/before the cutoff and whose withdrawal date is absent or after it. Same-day withdrawals are excluded under this conservative date rule and separately counted. The source-party historical table uses the official bill record's D/R labels; it is not fully normalized to dated affiliations. Dated affiliation counts are provided separately for the focal 118th Congress. Keep those definitions distinct.

A landmark is observable only before the congressional term ends. Enactment-risk comparisons exclude measures already enacted by the landmark. Final enactment is the observed bill lifecycle outcome and may occur after Congress adjourns, while a presented bill awaits presidential action. `days_from_introduction_to_congress_end` describes legislative time available, not a censoring date that discards later presidential action. This addresses time-ordering but does not eliminate confounding or selection.

## Documentary depth and limits

The dossiers distinguish source facts, attributed explanations, and unanswered questions. For H.R. 8070, Houlahan's June 14 office statement attributes her opposition to added amendments; Smith's June 12 public remarks describe conditional support. The Armed Services committees' December statement identifies H.R. 5009 as the negotiated vehicle based on H.R. 8070 and S. 4638. These are documentary checks, not interviews or proof of every member's motives. The six primary Nay cases are not evidence of wrongdoing or broken promises.

## Reuse and publication

Read `DATA_SOURCES.md`, `DATA_LICENSE.md`, and `LICENSE` before redistribution. BTB code is supplied under MIT; BTB's own documentation and transformations are offered under CC0 to the extent BTB holds rights. That does not relicense upstream datasets, model scores, or archived web pages. Voteview's data are publicly downloadable with citation guidance, but no explicit SPDX data license was verified here; retain its attribution and check source terms before asserting unrestricted redistribution of upstream files.

No GitHub repository, DOI, independent peer review, or global originality claim is implied. `CITATION.cff` provides a suggested citation without inventing one.
