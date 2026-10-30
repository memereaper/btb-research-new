#!/usr/bin/env python3
"""Bipartisanship, deeper cut: where in the process the cross-party advantage appears,
how fast, which committees and states, which member pairs, and a per-bill field for the
story graphic.

Reads warehouse/sql/pathways-116-119.duckdb. Uses the same bill classification as
build_bipartisan_116_118.py (setup()). Writes
  investigations/bipartisanship-116-118/deep.json          aggregates for the story
  datasets/pathways-116-119-serving/field.json             one character per bill (story graphic)
  datasets/pathways-116-119-serving/member_partners.json   top cross-party partners per member
Rates use completed Congresses (116th-118th). The 119th appears only where noted
(share bipartisan at introduction, which is known on day one).
"""
import json
import duckdb
from build_historical import ROOT
from build_bipartisan_116_118 import DB, setup

OUT_INV = ROOT/'investigations/bipartisanship-116-118'
OUT_SRV = ROOT/'datasets/pathways-116-119-serving'
COAL = ['bipartisan', 'same_party', 'solo']
STAGE = ['introduced', 'cleared_committee', 'passed_one', 'passed_both', 'law']
DAYS = [0, 7, 14, 30, 45, 60, 90, 120, 150, 180, 240, 300, 365, 450, 540, 630, 730]


def rows(c, sql, keys):
    return [dict(zip(keys, r)) for r in c.execute(sql).fetchall()]


def main():
    c = duckdb.connect(str(DB), read_only=True)
    c.execute("SET threads=2")
    setup(c)
    base = "congress_n BETWEEN 116 AND 118 AND coalition_at_intro IN ('bipartisan','same_party','solo') AND NOT ceremonial"
    D = {'scope': 'Bills and joint resolutions, 116th-118th Congresses (2019-2024), D or R sponsor, ceremonial bills excluded unless noted.'}

    # 1. Funnel: conversion at each gate, by coalition
    c.execute("""CREATE TEMP TABLE cmte AS SELECT bill_id,
        bool_or(lower(event_name) LIKE 'markup%' OR lower(event_name) LIKE 'hearings%' OR lower(event_name) LIKE 'reported%' OR lower(event_name) LIKE 'discharged%') AS committee_action
        FROM committee_events GROUP BY 1""")
    D['funnel'] = rows(c, f"""SELECT coalition_at_intro, count(*) n,
        sum(coalesce(k.committee_action,false) OR cleared_committee)::INT committee_action,
        sum(cleared_committee::INT) cleared, sum(passed_one::INT) passed_one, sum(passed_both::INT) passed_both, sum(became_law::INT) law
        FROM bp LEFT JOIN cmte k USING (bill_id) WHERE {base} GROUP BY 1 ORDER BY list_position({COAL}, coalition_at_intro)""",
        ['coalition', 'n', 'committee_action', 'cleared_committee', 'passed_one', 'passed_both', 'law'])

    # 2. Time to law: cumulative share enacted by days after introduction
    c.execute("""CREATE TEMP TABLE lawday AS SELECT a.bill_id, min(a.action_on) law_on FROM actions a
        WHERE a.action_code IN ('36000','41000','E40000') GROUP BY 1""")
    c.execute(f"""CREATE TEMP TABLE tl AS SELECT bp.bill_id, coalition_at_intro coal, became_law,
        CASE WHEN became_law THEN date_diff('day', introduced_on, coalesce(l.law_on, latest_action_on)) END d
        FROM bp LEFT JOIN lawday l USING (bill_id) WHERE {base}""")
    curves = {}
    for k in COAL:
        n = c.execute("SELECT count(*) FROM tl WHERE coal=?", [k]).fetchall()[0][0]
        pts = []
        for d in DAYS:
            m = c.execute("SELECT count(*) FROM tl WHERE coal=? AND became_law AND d<=?", [k, d]).fetchall()[0][0]
            pts.append(round(100 * m / n, 3))
        curves[k] = {'n': n, 'pct_law_by_day': pts}
    D['time_to_law'] = {'days': DAYS, 'curves': curves,
        'median_days_to_law': dict(c.execute("SELECT coal, median(d)::INT FROM tl WHERE became_law GROUP BY 1").fetchall()),
        'note': 'Days from introduction to the Became Public/Private Law action. A bill introduced late in a Congress has less time; all three groups share that limit.'}

    # 3. Snowball: when cross-party cosponsors arrive, and whether later support goes with success
    c.execute("""CREATE TEMP TABLE xj AS SELECT x.bill_id, date_diff('day', b.introduced_on, x.joined_on) dj
        FROM cosponsors x JOIN bp b USING (bill_id)
        WHERE b.sponsor_party IN ('D','R') AND x.party IN ('D','R') AND x.party<>b.sponsor_party AND x.joined_on IS NOT NULL""")
    snow = {}
    for st in STAGE:
        n = c.execute(f"SELECT count(*) FROM bp WHERE {base} AND furthest=?", [st]).fetchall()[0][0]
        pts = [round(c.execute(f"SELECT count(*) FROM xj JOIN bp USING (bill_id) WHERE {base} AND furthest=? AND dj<=?", [st, d]).fetchall()[0][0] / n, 2) for d in DAYS]
        snow[st] = {'n': n, 'avg_cross_party_cosponsors_by_day': pts}
    D['snowball'] = {'days': DAYS, 'by_furthest_stage': snow}
    # Late bridges: no cross-party original cosponsor, but one joined before the bill passed any chamber
    c.execute("""CREATE TEMP TABLE firstpass AS SELECT bill_id, min(action_on) p FROM actions WHERE action_code IN ('8000','17000') GROUP BY 1""")
    D['late_bridges'] = rows(c, f"""
        WITH g AS (SELECT bp.bill_id, bp.coalition_at_intro, bp.became_law, bp.passed_one,
          EXISTS (SELECT 1 FROM xj JOIN bp b2 USING (bill_id) WHERE xj.bill_id=bp.bill_id AND xj.dj>0
                  AND (fp.p IS NULL OR b2.introduced_on + xj.dj * INTERVAL 1 DAY < fp.p)) AS gained
          FROM bp LEFT JOIN firstpass fp USING (bill_id) WHERE {base})
        SELECT CASE WHEN coalition_at_intro='bipartisan' THEN 'bipartisan_at_intro'
                    WHEN gained THEN 'gained_cross_party_before_passage' ELSE 'never_cross_party_before_passage' END grp,
          count(*), round(100*avg(passed_one::INT),2), round(100*avg(became_law::INT),2)
        FROM g GROUP BY 1 ORDER BY 4 DESC""", ['group', 'bills', 'pct_passed_one', 'pct_became_law'])
    D['first_cross_join_days'] = rows(c, f"""
        WITH f AS (SELECT bill_id, min(dj) d FROM xj WHERE dj>0 GROUP BY 1)
        SELECT CASE WHEN d<=30 THEN '1-30' WHEN d<=90 THEN '31-90' WHEN d<=180 THEN '91-180' WHEN d<=365 THEN '181-365' ELSE '366+' END k, count(*)
        FROM f JOIN bp USING (bill_id) WHERE {base} AND coalition_at_intro<>'bipartisan' GROUP BY 1 ORDER BY min(d)""", ['days_after_intro', 'bills'])

    # 4. Committees of first referral
    c.execute("""CREATE TEMP TABLE firstref AS SELECT bill_id, arg_min(committee_id, coalesce(event_on, DATE '2100-01-01')) cid
        FROM committee_events WHERE lower(event_name)='referred to' AND coalesce(parent_committee_id,'')='' GROUP BY 1""")
    c.execute("CREATE TEMP TABLE cname AS SELECT committee_id cid, mode(committee_name) AS name, mode(chamber) AS chamber FROM committees GROUP BY 1")
    D['committees'] = rows(c, f"""
        SELECT n.name, n.chamber, count(*) bills, round(100*avg((coalition_at_intro='bipartisan')::INT),1) pct_bipartisan,
          round(100*avg(became_law::INT) FILTER (WHERE coalition_at_intro='bipartisan'),2) law_bip,
          round(100*avg(became_law::INT) FILTER (WHERE coalition_at_intro<>'bipartisan'),2) law_other,
          round(100*avg(cleared_committee::INT) FILTER (WHERE coalition_at_intro='bipartisan'),2) cleared_bip,
          round(100*avg(cleared_committee::INT) FILTER (WHERE coalition_at_intro<>'bipartisan'),2) cleared_other,
          count(*) FILTER (WHERE coalition_at_intro='bipartisan') n_bip
        FROM bp JOIN firstref f USING (bill_id) JOIN cname n USING (cid) WHERE {base}
        GROUP BY 1,2 HAVING count(*)>=400 AND count(*) FILTER (WHERE coalition_at_intro='bipartisan')>=100 ORDER BY bills DESC""",
        ['committee', 'chamber', 'bills', 'pct_bipartisan', 'pct_law_bipartisan', 'pct_law_other', 'pct_cleared_bipartisan', 'pct_cleared_other', 'bipartisan_bills'])

    # 5. States: the sponsor's delegation
    D['states'] = rows(c, f"""SELECT sponsor_state, count(*), round(100*avg((coalition_at_intro='bipartisan')::INT),1),
        round(100*avg(became_law::INT),2), sum(became_law::INT)
        FROM bp WHERE {base} AND sponsor_state IS NOT NULL GROUP BY 1 ORDER BY 1""",
        ['state', 'bills', 'pct_bipartisan', 'pct_law', 'laws'])

    # 6. Chamber and party of sponsor
    D['chamber_party'] = rows(c, f"""SELECT chamber, sponsor_party, coalition_at_intro, count(*), round(100*avg(became_law::INT),2)
        FROM bp WHERE {base} GROUP BY 1,2,3 ORDER BY 1,2,3""", ['chamber', 'party', 'coalition', 'bills', 'pct_law'])

    # 7. Share bipartisan at introduction, every Congress in this database (119th included: known on day one)
    D['share_bipartisan_at_intro'] = rows(c, """SELECT congress_n, chamber, count(*), round(100*avg((coalition_at_intro='bipartisan')::INT),1)
        FROM bp WHERE coalition_at_intro IN ('bipartisan','same_party','solo') GROUP BY 1,2 ORDER BY 1,2""",
        ['congress', 'chamber', 'bills', 'pct_bipartisan'])

    # 8. Identical companions in the other chamber
    D['companions'] = rows(c, f"""
        WITH comp AS (SELECT DISTINCT r.bill_id FROM related_bills r JOIN bp o ON o.bill_id=r.related_bill_id JOIN bp s ON s.bill_id=r.bill_id
          WHERE r.relationship='Identical bill' AND o.chamber<>s.chamber)
        SELECT coalition_at_intro, (bill_id IN (SELECT bill_id FROM comp)) has_companion, count(*), round(100*avg(became_law::INT),2)
        FROM bp WHERE {base} GROUP BY 1,2 ORDER BY 1,2""", ['coalition', 'has_identical_companion', 'bills', 'pct_law'])

    # 9. Member pairs (sponsor x cross-party cosponsor, either direction)
    c.execute("""CREATE TEMP TABLE pairs AS
        SELECT least(b.sponsor_id, x.sponsor_id) a, greatest(b.sponsor_id, x.sponsor_id) z, count(DISTINCT b.bill_id) bills,
          count(DISTINCT b.bill_id) FILTER (WHERE b.became_law) laws
        FROM bp b JOIN cosponsors x USING (bill_id)
        WHERE b.sponsor_party IN ('D','R') AND x.party IN ('D','R') AND x.party<>b.sponsor_party
          AND coalesce(b.sponsor_id,'')<>'' AND coalesce(x.sponsor_id,'')<>'' AND b.congress_n BETWEEN 116 AND 119
        GROUP BY 1,2""")
    c.execute("""CREATE TEMP TABLE mem AS SELECT id, any_value(name) AS name, mode(party) AS party, mode(state) AS state FROM (
        SELECT sponsor_id AS id, sponsor_name AS name, sponsor_party AS party, sponsor_state AS state FROM bp WHERE coalesce(sponsor_id,'')<>''
        UNION ALL SELECT sponsor_id, member_name, party, state FROM cosponsors WHERE coalesce(sponsor_id,'')<>'') GROUP BY 1""")
    c.execute("""CREATE TEMP TABLE memch AS SELECT sponsor_id id, CASE WHEN avg((chamber='Senate')::INT)>0.5 THEN 'Senate' ELSE 'House' END chamber
        FROM bp WHERE coalesce(sponsor_id,'')<>'' GROUP BY 1""")
    D['top_pairs'] = rows(c, """SELECT ma.name, ma.party, mz.name, mz.party, p.bills, p.laws FROM pairs p
        JOIN mem ma ON ma.id=p.a JOIN mem mz ON mz.id=p.z ORDER BY p.bills DESC LIMIT 20""",
        ['member_a', 'party_a', 'member_b', 'party_b', 'shared_bills', 'shared_laws'])
    partners = c.execute("""
        WITH e AS (SELECT a me, z other, bills, laws FROM pairs UNION ALL SELECT z, a, bills, laws FROM pairs),
        r AS (SELECT *, row_number() OVER (PARTITION BY me ORDER BY bills DESC, laws DESC) rk, count(*) OVER (PARTITION BY me) n_partners,
              sum(bills) OVER (PARTITION BY me) cross_ties FROM e)
        SELECT r.me, m.name, m.party, m.state, coalesce(ch.chamber,'House'), r.n_partners, r.cross_ties,
          list({'id': r.other, 'name': mo.name, 'party': mo.party, 'state': mo.state, 'bills': r.bills, 'laws': r.laws} ORDER BY r.rk)
        FROM r JOIN mem m ON m.id=r.me JOIN mem mo ON mo.id=r.other LEFT JOIN memch ch ON ch.id=r.me
        WHERE r.rk<=12 GROUP BY 1,2,3,4,5,6,7""").fetchall()
    # sponsor-side profile: how often each member's own bills start bipartisan, and how they fare
    prof = {r[0]: r[1:] for r in c.execute(f"""SELECT sponsor_id, count(*), round(100*avg((coalition_at_intro='bipartisan')::INT),1), sum(became_law::INT)
        FROM bp WHERE {base} GROUP BY 1""").fetchall()}
    mp = []
    for r in partners:
        p = prof.get(r[0], (0, None, 0))
        mp.append({'member_id': r[0], 'name': r[1], 'party': r[2], 'state': r[3], 'chamber': r[4], 'cross_party_partners': r[5],
                   'cross_party_ties': r[6], 'sponsored_116_118': p[0], 'pct_sponsored_bipartisan': p[1], 'laws_sponsored_116_118': p[2],
                   'partners': r[7]})
    (OUT_SRV/'member_partners.json').write_text(json.dumps(mp, separators=(',', ':'), default=str))

    # 10. The field: one character per bill, 116th-118th, every bill (ceremonial flagged)
    fr = c.execute("""SELECT coalition_at_intro, furthest, ceremonial, orig_cross FROM bp
        WHERE congress_n BETWEEN 116 AND 118 ORDER BY congress_n, introduced_on, bill_id""").fetchall()
    ci = {'bipartisan': 0, 'same_party': 1, 'solo': 2, 'other_sponsor': 3}
    si = {s: i for i, s in enumerate(STAGE)}
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
    dots = ''.join(alphabet[ci[a] * 10 + si[b] * 2 + (1 if cer else 0)] for a, b, cer, _ in fr)
    dose = ''.join(alphabet[min(x, 61)] for *_, x in fr)
    field = {'n': len(fr), 'encoding': 'char index = coalition*10 + stage*2 + ceremonial; coalition 0 bipartisan,1 same_party,2 solo,3 independent sponsor; stage 0 introduced..4 law',
             'alphabet': alphabet, 'dots': dots, 'orig_cross': dose, 'order': 'congress, introduced date, bill id'}
    (OUT_SRV/'field.json').write_text(json.dumps(field, separators=(',', ':')))
    D['field_counts'] = rows(c, """SELECT coalition_at_intro, furthest, ceremonial, count(*) FROM bp WHERE congress_n BETWEEN 116 AND 118 GROUP BY 1,2,3 ORDER BY 1,2,3""",
                             ['coalition', 'furthest', 'ceremonial', 'bills'])

    (OUT_INV/'deep.json').write_text(json.dumps(D, indent=1, default=str) + '\n')
    print(json.dumps({k: D[k] for k in ['funnel', 'late_bridges', 'companions']}, default=str))
    print('median days', D['time_to_law']['median_days_to_law'])
    print('committees', len(D['committees']), 'states', len(D['states']), 'members', len(mp), 'field', len(dots))



def export_actions_119():
    """119th Congress actions for the hosted API (the hosted release covers 113th-118th)."""
    import duckdb as _d
    c = _d.connect(str(DB), read_only=True)
    rows = c.execute("""SELECT a.action_id, a.bill_id, a.action_on::VARCHAR, a.action_code, a.action_type, left(a.action_text, 400)
        FROM actions a JOIN bills b USING (bill_id) WHERE b.congress_n=119 AND NOT coalesce(a.repeated_payload,false)
        ORDER BY a.bill_id, a.action_on, a.action_id""").fetchall()
    keys = ['action_id', 'bill_id', 'action_on', 'action_code', 'action_type', 'action_text']
    files = []
    step = 22000
    for i in range(0, len(rows), step):
        name = f'actions-119-{i // step:02d}.json'
        (OUT_SRV/name).write_text(json.dumps([dict(zip(keys, r)) for r in rows[i:i + step]], separators=(',', ':')))
        files.append(name)
    print('actions 119', len(rows), files)


if __name__ == '__main__':
    import sys
    export_actions_119() if 'actions' in sys.argv else main()
