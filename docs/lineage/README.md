# Legislative lineage: category, claim wording and audit (2026-11-15)

Status: plan plus first collection. Nothing here is a verified result; no "first" or "largest" claim is approved.

## Chosen aspect
Legislative evolution: how a bill's text and identity change across versions, companions, reintroductions, amendments and enactment. Accountability (objections, votes), spending and GAO oversight attach later through the shared keys in data-model.md. They are not collected here.

## Audit: what we hold vs. what lineage needs
| Need | Held | Gap |
|---|---|---|
| Bill identity, actions, sponsors, cosponsors | 108th-119th (HF, GovInfo BILLSTATUS); 113-118 sealed locally; 93rd-107th backfill running in another thread | none for 108+ |
| Text-version listing (version code, date, URL) | `text_versions` in pathways packages (metadata only) and HF `text_versions` | no full text, no sections |
| Full bill text | only objection-pilot packages (111, 112, 119) and committee-report text 104-119 | **full text of every version is the main gap** |
| Related bills (companion, identical, procedural, "related") | `related_bills` tables 116-117 (32,805 rows), HF 108+ | links are from Congress.gov and change often; no text-based verification |
| Amendments and what was folded in | HF `amendments` 108+ (sponsor/dates null for backfill) | no text of amendments, no incorporation evidence |
| Outcome (enacted law) | `laws`, law_identifiers | no map from enrolled text back to source bills |
| Reintroductions | 9,104 candidates (pathway-research), unreviewed | text-confirmation missing |

## Coverage check (prior art, found 2026-11-15; web search only, not exhaustive)
- Congress.gov and GovInfo: official source of text versions and bill status. GovInfo bulk BILLS XML starts at the 113th Congress. Congress.gov text begins around the 101st per secondary descriptions; verify before relying on it.
- [hyperdemocracy/usc-textversion](https://huggingface.co/datasets/hyperdemocracy/usc-textversion) on Hugging Face: bill text versions for the 113th-118th derived from GovInfo bulk XML. So "largest bill-text corpus" is **not** a claim we can lead.
- [BillMap (Demand Progress)](https://github.com/unitedstates/BillMap): bill-level text similarity; its own notes say section-level matching is unreliable because of boilerplate.
- [congress-appropriations](https://cgorski.github.io/congress-appropriations/): provision-level linking, appropriations bills only.
- Academic: BICAM (Sci. Data 2025), Wilkerson et al. on policy idea flow (AJPS), LAWProM. See docs/collections/research-priorities-2026-11-05.md.
- Not yet checked: GovTrack, Voteview coverage of text, LegiScan, ProPublica Congress API (discontinued status unconfirmed), CRS, Policy Agendas Project.

## Candidate category (to be tested, not claimed)
"A public, source-linked, section-level lineage table connecting every bill version of the 113th-119th Congresses to the versions, companions, reintroductions and enacted laws it matches, with match method, score and evidence excerpts."
Why this one: raw text is already public (usc-textversion), so the contribution must be verified links. Leading it needs: (1) section-level coverage across all bill types and both chambers, (2) a hand-checked benchmark with reported precision/recall, (3) stable IDs and per-row evidence. Draft claim wording after benchmark: "the largest public, evidence-linked section-level lineage dataset of U.S. federal bills, N links across Congresses 113-119, precision P on a reviewed sample of n, as of DATE." Do not publish until a documented comparison against the sources above supports it.

## Collection started
`scripts/lineage/collect_bill_text.py`: GovInfo bulk BILLS XML for Congresses 118, 117, 116, 115, 114, 113, 119 in that order, all 8 measure types, both sessions. Writes `bill_text_versions` and `bill_text_sections` parquet plus per-unit checkpoint JSON (zip sha256, counts, retrieval time). Safe to rerun; finished units are skipped. Uses govinfo.gov only, so it does not use the shared api.congress.gov hourly budget of the 1973-2002 backfill.
Phase 2 (not started; needs coordination because it uses the Congress.gov API budget): text for the 101st-112th via the Congress.gov text endpoint.
