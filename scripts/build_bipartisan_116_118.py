#!/usr/bin/env python3
"""Bipartisanship Part 2: does cross-party support at introduction go with getting further?

Reads warehouse/sql/pathways-116-119.duckdb (built by build_pathways_sql.py).
Writes
  investigations/bipartisanship-116-118/findings.json   aggregate results
  datasets/pathways-116-119-serving/*.json              compact tables for the hosted database
Completed Congresses only (116-118) in rates; the 119th is in session and is excluded from rates,
but included in the browse table with an in-progress label.
"""
import json
from pathlib import Path
import duckdb
from build_historical import ROOT

DB = ROOT/'warehouse/sql/pathways-116-119.duckdb'
OUT_INV = ROOT/'investigations/bipartisanship-116-118'
OUT_SRV = ROOT/'datasets/pathways-116-119-serving'
# Majority party by Congress and chamber (Senate 117th: Democrats via the Vice President's vote).
MAJ = {(116, 'House'): 'D', (116, 'Senate'): 'R', (117, 'House'): 'D', (117, 'Senate'): 'D',
       (118, 'House'): 'R', (118, 'Senate'): 'D', (119, 'House'): 'R', (119, 'Senate'): 'R'}
CHUNK = 8000


def main():
    c = duckdb.connect(str(DB), read_only=True)
    c.execute("CREATE TEMP TABLE maj(congress_n INT, chamber VARCHAR, party VARCHAR)")
    c.executemany("INSERT INTO maj VALUES (?,?,?)", [(k[0], k[1], v) for k, v in MAJ.items()])
    c.execute("""
    CREATE TEMP TABLE stage AS
    SELECT bill_id,
      bool_or(action_code IN ('5000','14000')) AS reported,
      bool_or(action_code IN ('14500','H12300')) AS discharged,
      bool_or(action_code = '8000') AS passed_house,
      bool_or(action_code = '17000') AS passed_senate,
      bool_or(action_code = '28000') AS presented
    FROM actions GROUP BY 1""")
    c.execute("""
    CREATE TEMP TABLE coal AS
    SELECT b.bill_id,
      count(x.sponsor_id) FILTER (WHERE x.original_cosponsor) AS orig_cosponsors,
      count(x.sponsor_id) FILTER (WHERE x.original_cosponsor AND x.party IN ('D','R') AND b.sponsor_party IN ('D','R') AND x.party <> b.sponsor_party) AS orig_cross,
      count(x.sponsor_id) AS all_cosponsors,
      count(x.sponsor_id) FILTER (WHERE x.party IN ('D','R') AND b.sponsor_party IN ('D','R') AND x.party <> b.sponsor_party) AS all_cross
    FROM bills b LEFT JOIN cosponsors x USING (bill_id) GROUP BY 1""")
    c.execute("""
    CREATE TEMP TABLE bp AS
    SELECT b.bill_id, b.congress_n, b.bill_type, b.bill_number, b.title, b.introduced_on, b.sponsor_id, b.sponsor_name,
      b.sponsor_party, b.sponsor_state, b.policy_area, b.became_law, b.latest_action_on, b.latest_action_text, b.congress_url,
      CASE WHEN b.bill_type IN ('hr','hjres') THEN 'House' ELSE 'Senate' END AS chamber,
      coalesce(co.orig_cosponsors,0) orig_cosponsors, coalesce(co.orig_cross,0) orig_cross,
      coalesce(co.all_cosponsors,0) all_cosponsors, coalesce(co.all_cross,0) all_cross,
      CASE WHEN b.sponsor_party NOT IN ('D','R') THEN 'other_sponsor'
           WHEN coalesce(co.orig_cosponsors,0)=0 THEN 'solo'
           WHEN coalesce(co.orig_cross,0)=0 THEN 'same_party'
           ELSE 'bipartisan' END AS coalition_at_intro,
      coalesce(s.reported,false) OR coalesce(s.discharged,false) OR coalesce(s.passed_house,false) OR coalesce(s.passed_senate,false) AS cleared_committee,
      coalesce(s.passed_house,false) OR coalesce(s.passed_senate,false) AS passed_one,
      coalesce(s.passed_house,false) AND coalesce(s.passed_senate,false) AS passed_both,
      (b.sponsor_party = m.party) AS sponsor_in_majority,
      (b.policy_area = 'Commemorations' OR lower(b.title) LIKE '%designate the facility of the united states postal service%'
        OR lower(b.title) LIKE 'to designate the facility%' ) AS ceremonial
    FROM bills b LEFT JOIN coal co USING (bill_id) LEFT JOIN stage s USING (bill_id)
    LEFT JOIN maj m ON m.congress_n=b.congress_n AND m.chamber=(CASE WHEN b.bill_type IN ('hr','hjres') THEN 'House' ELSE 'Senate' END)""")
    c.execute("""ALTER TABLE bp ADD COLUMN furthest VARCHAR; UPDATE bp SET furthest = CASE
        WHEN became_law THEN 'law' WHEN passed_both THEN 'passed_both' WHEN passed_one THEN 'passed_one'
        WHEN cleared_committee THEN 'cleared_committee' ELSE 'introduced' END""")

    rate = lambda where: c.execute(f"""
      SELECT coalition_at_intro, count(*) bills,
        round(100*avg(cleared_committee::int),2), round(100*avg(passed_one::int),2),
        round(100*avg(passed_both::int),2), round(100*avg(became_law::int),2), sum(became_law::int)
      FROM bp WHERE congress_n BETWEEN 116 AND 118 AND coalition_at_intro <> 'other_sponsor' AND {where}
      GROUP BY 1 ORDER BY 1""").fetchall()
    keys = ['coalition', 'bills', 'pct_cleared_committee', 'pct_passed_one_chamber', 'pct_passed_both', 'pct_became_law', 'laws']
    tab = lambda rows: [dict(zip(keys, r)) for r in rows]
    F = {
        'scope': 'HR, S, H.J.Res., S.J.Res. introduced in the 116th-118th Congresses (2019-2024); 119th excluded from rates (in session).',
        'definitions': {
            'coalition_at_intro': 'From original cosponsors (joined on the introduction date). bipartisan = at least one original cosponsor from the other major party; same_party = original cosponsors all from the sponsor\'s party or independents; solo = no original cosponsors. Independent sponsors are reported separately.',
            'stages': 'Library of Congress action codes: reported 5000/14000, discharged 14500/H12300, passed House 8000, passed Senate 17000; became law from law identifiers. Cleared committee = reported, discharged, or passed a chamber.',
            'majority': {f'{k[0]}-{k[1]}': v for k, v in MAJ.items() if k[0] <= 118},
            'ceremonial': 'Policy area Commemorations, or titles designating a postal facility. Shown as a sensitivity check.'},
        'all_bills': tab(rate('true')),
        'excluding_ceremonial': tab(rate('NOT ceremonial')),
        'majority_sponsor': tab(rate('sponsor_in_majority AND NOT ceremonial')),
        'minority_sponsor': tab(rate('NOT sponsor_in_majority AND NOT ceremonial')),
        'by_congress': [dict(zip(['congress', 'coalition', 'bills', 'pct_became_law'], r)) for r in c.execute("""
            SELECT congress_n, coalition_at_intro, count(*), round(100*avg(became_law::int),2) FROM bp
            WHERE congress_n BETWEEN 116 AND 118 AND coalition_at_intro<>'other_sponsor' GROUP BY 1,2 ORDER BY 1,2""").fetchall()],
        'dose_response': [dict(zip(['original_cross_party_cosponsors', 'bills', 'pct_passed_one_chamber', 'pct_became_law'], r)) for r in c.execute("""
            SELECT CASE WHEN orig_cross=0 THEN '0' WHEN orig_cross=1 THEN '1' WHEN orig_cross<5 THEN '2-4' WHEN orig_cross<10 THEN '5-9' ELSE '10+' END k,
              count(*), round(100*avg(passed_one::int),2), round(100*avg(became_law::int),2)
            FROM bp WHERE congress_n BETWEEN 116 AND 118 AND sponsor_party IN ('D','R') AND orig_cosponsors>0 AND NOT ceremonial
            GROUP BY 1 ORDER BY min(orig_cross)""").fetchall()],
        'laws_by_coalition': [dict(zip(['coalition', 'laws', 'pct_of_laws'], r)) for r in c.execute("""
            SELECT coalition_at_intro, count(*), round(100*count(*)/sum(count(*)) OVER (),1) FROM bp
            WHERE congress_n BETWEEN 116 AND 118 AND became_law GROUP BY 1 ORDER BY 2 DESC""").fetchall()],
        'later_coalition_growth': [dict(zip(['furthest', 'bills', 'avg_original_cross', 'avg_final_cross'], r)) for r in c.execute("""
            SELECT furthest, count(*), round(avg(orig_cross),2), round(avg(all_cross),2) FROM bp
            WHERE congress_n BETWEEN 116 AND 118 AND sponsor_party IN ('D','R') GROUP BY 1
            ORDER BY list_position(['introduced','cleared_committee','passed_one','passed_both','law'], furthest)""").fetchall()],
        'members_most_cross_party': [dict(zip(['member_id', 'name', 'party', 'cosponsorships', 'pct_cross_party'], r)) for r in c.execute("""
            SELECT x.sponsor_id, any_value(x.member_name), mode(x.party), count(*),
              round(100*avg((x.party IN ('D','R') AND b.sponsor_party IN ('D','R') AND x.party<>b.sponsor_party)::int),1) p
            FROM cosponsors x JOIN bills b USING (bill_id) WHERE b.congress_n BETWEEN 116 AND 118 AND x.party IN ('D','R')
            GROUP BY 1 HAVING count(*) >= 200 ORDER BY p DESC LIMIT 15""").fetchall()],
    }
    OUT_INV.mkdir(parents=True, exist_ok=True)
    (OUT_INV/'findings.json').write_text(json.dumps(F, indent=2, default=str) + '\n')

    # ---- compact serving tables (JSON arrays, for server-side loading) ----
    OUT_SRV.mkdir(parents=True, exist_ok=True)
    rows = c.execute("""SELECT bill_id, congress_n, bill_type, bill_number::INT, left(title,300), introduced_on::VARCHAR,
        sponsor_id, sponsor_name, sponsor_party, sponsor_state, policy_area, chamber, coalition_at_intro,
        orig_cosponsors, orig_cross, all_cosponsors, all_cross, furthest, became_law, ceremonial,
        coalesce(sponsor_in_majority,false), latest_action_on::VARCHAR, left(latest_action_text,220), congress_url
        FROM bp ORDER BY congress_n, bill_type, bill_number::INT""").fetchall()
    cols = ['bill_id', 'congress', 'bill_type', 'bill_number', 'title', 'introduced_on', 'sponsor_id', 'sponsor_name',
            'sponsor_party', 'sponsor_state', 'policy_area', 'chamber', 'coalition_at_intro', 'orig_cosponsors', 'orig_cross',
            'all_cosponsors', 'all_cross', 'furthest', 'became_law', 'ceremonial', 'sponsor_in_majority',
            'latest_action_on', 'latest_action_text', 'congress_url']
    files = []
    for i in range(0, len(rows), CHUNK):
        name = f'bills-{i // CHUNK:02d}.json'
        (OUT_SRV/name).write_text(json.dumps([dict(zip(cols, r)) for r in rows[i:i + CHUNK]], separators=(',', ':'), default=str))
        files.append(name)
    mem = c.execute("""SELECT x.sponsor_id, any_value(x.member_name), mode(x.party), mode(x.state), count(*),
        count(*) FILTER (WHERE x.party IN ('D','R') AND b.sponsor_party IN ('D','R') AND x.party<>b.sponsor_party),
        min(b.congress_n), max(b.congress_n)
        FROM cosponsors x JOIN bills b USING (bill_id) WHERE coalesce(x.sponsor_id,'')<>'' GROUP BY 1""").fetchall()
    (OUT_SRV/'members.json').write_text(json.dumps([dict(zip(['member_id', 'name', 'party', 'state', 'cosponsorships', 'cross_party_cosponsorships', 'first_congress', 'last_congress'], r)) for r in mem], separators=(',', ':')))
    (OUT_SRV/'manifest.json').write_text(json.dumps({'bills_files': files, 'bills_rows': len(rows), 'members_rows': len(mem),
        'source_database': DB.name}, indent=2) + '\n')
    print(json.dumps({k: F[k] for k in ['all_bills', 'excluding_ceremonial', 'majority_sponsor', 'minority_sponsor', 'laws_by_coalition']}, indent=1, default=str))
    print('serving rows', len(rows), 'members', len(mem), files)


if __name__ == '__main__':
    main()
