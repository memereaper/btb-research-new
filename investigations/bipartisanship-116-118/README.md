# Does crossing the aisle get a bill further? (116th–118th Congress)

Bipartisanship Part 2. Built by `scripts/build_bipartisan_116_118.py` from `warehouse/sql/pathways-116-119.duckdb`. Results: `findings.json`.

## Finding

Bills that started with at least one cosponsor from the other party became law far more often. Excluding ceremonial bills, 3.33% of bipartisan-at-introduction bills became law, against 0.6% of bills whose original cosponsors were all from the sponsor's party and 1.02% of bills with no original cosponsors.

Bipartisan bills were 37% of bills introduced but 70.4% of the laws.

The gap holds for sponsors in the majority and in the minority, in each of the three Congresses, and it rises with the number of cross-party original cosponsors:

| Cross-party original cosponsors | Bills | Passed a chamber | Became law |
|---|---:|---:|---:|
| 0 | 16,137 | 2.91% | 0.6% |
| 1 | 10,810 | 9.9% | 2.86% |
| 2-4 | 4,963 | 12.17% | 3.36% |
| 5-9 | 710 | 17.18% | 6.76% |
| 10+ | 290 | 25.52% | 11.72% |

| Sponsor | Coalition at introduction | Bills | Cleared committee | Passed a chamber | Became law |
|---|---|---:|---:|---:|---:|
| Majority party | bipartisan | 10,222 | 18.59% | 12.31% | 3.65% |
| Majority party | same party | 9,165 | 7.24% | 3.93% | 0.69% |
| Majority party | solo | 6,896 | 10.09% | 5.0% | 1.38% |
| Minority party | bipartisan | 6,551 | 13.66% | 9.34% | 2.82% |
| Minority party | same party | 6,972 | 2.68% | 1.58% | 0.49% |
| Minority party | solo | 5,650 | 3.68% | 2.28% | 0.58% |

## What this does not show

This is an association, not proof that adding a cross-party cosponsor causes passage. Sponsors may recruit across the aisle for bills they already expect to move, and less contentious subjects attract both parties. We reduce two obvious confounds (ceremonial bills; majority status) but do not remove them. We measure coalition on the introduction date so that cosponsors who join because a bill is already moving are not counted: moving bills keep gaining cross-party cosponsors (laws averaged 2.67 at introduction and 8.57 by the end).

## Method

- Universe: 45,863 HR, S, H.J.Res. and S.J.Res. measures introduced in the 116th–118th Congresses with a Democratic or Republican sponsor (133 independent-sponsored bills reported separately). The 119th is in session and excluded from rates.
- Coalition at introduction: original cosponsors as marked in GovInfo BILLSTATUS. Cross-party means the other major party; independents are not counted as cross-party.
- Stages: Library of Congress action codes (reported 5000/14000; discharged 14500/H12300; passed House 8000; passed Senate 17000); law from official law identifiers. "Cleared committee" counts reported, discharged, or passed a chamber.
- Ceremonial: policy area Commemorations or titles designating a postal facility.
- Majority: chamber majority party per Congress (117th Senate Democratic via the Vice President).
- Check: our 118th original cross-party counts match the independent bipartisanship-v2 release for all 16,565 measures.

## Next

The 118th vote-level analysis (bipartisanship-v2) tests whether cross-party cosponsors later vote for the bill. Extending it to the 116th–117th needs House and Senate roll-call positions for those Congresses, which are not yet collected.
