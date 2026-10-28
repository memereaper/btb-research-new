# v2.0.0, 2026-10-26

- Replaced Senate surname/state guesses with exact official LIS-to-Bioguide joins. Exact IDs now cover all 208,471 member positions; 34 additional cosponsor-vote event matches are recovered.
- Preserved official party labels beside dated roster affiliations and caucus labels, with explicit exceptions.
- Classified vote purposes; excluded veto overrides and concurrence-with-amendment from the primary supporting-disposition cohort while adding plain concurrence and conference-report dispositions.
- Removed future cosponsor joins from eligible cohorts and added same-day timing sensitivity.
- Kept Not Voting, Present, and Nay distinct; independents are not grouped as same-party D/R observations.
- Primary selected sample is now 8,408 bill-member pairs on 301 measures. The v1 sample of 8,393 pairs on 300 measures and its descriptive rates are superseded for this coding specification.
- Added committee snapshots, service context, lagged ideology, full text-version evidence for the roll-call-linked subset, CBO metadata, related-vehicle context, historical landmark cohorts, coverage audits, and eight documentary case dossiers.
- Added machine-readable schema, typed SQLite export, checksums, attribution, rights notes, reproduction scripts, and validation checks.
- The v1 files remain historical artifacts; v2 is a separate documented extension rather than a silent rewrite.
