# Shared data model (draft v0.1)

Keys shared by all future research areas (accountability, spending, GAO oversight):
- `bill_id` = `{congress}-{type}{number}` (e.g. `118-hr1`), lowercase type.
- `version_id` = `{bill_id}-{version_code}` (e.g. `118-hr1-ih`, `-eh`, `-enr`).
- `section_id` = `{version_id}#{section_index}` (provisional: index within version; xml id kept as `section_xml_id`).
- `member_id` = bioguide ID (member-crosswalk package). `law_id` = `{congress}-pl-{number}` (public law). `report_id`, `roll_call_id` as in existing packages.

Tables (v0.1):
| Table | Grain | Status |
|---|---|---|
| bill_text_versions | one per text version | collecting |
| bill_text_sections | one per top-level section of a version | collecting |
| bill_relations | bill_id pair + relation (companion, identical, reintroduction, supersedes, folded_into) + source | planned; seeded from related_bills + reintroduction_candidates |
| version_alignments | section_id pair across versions of one bill (kept, modified, removed, added) + score | planned |
| provision_matches | section_id pair across different bills + method (exact hash, shingle Jaccard, embedding) + score + evidence_excerpt | planned |
| amendment_incorporation | amendment -> section it altered, evidence | planned, depends on amendment text |
| law_provenance | enrolled section -> source bill sections | planned |
| match_review | reviewer, label, date for benchmark rows | planned |

Rules: every match row carries method, score, source hashes and an excerpt; unmatched stays unmatched (no forced links); causal language is not used ("appears in", not "caused by"). Link keys for later areas: objections (`report_id`, `section_id`), votes (`roll_call_id`, `bill_id`), spending (`law_id`, program IDs), GAO (`recommendation_id`, `law_id`).
