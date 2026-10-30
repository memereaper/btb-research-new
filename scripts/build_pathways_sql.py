#!/usr/bin/env python3
"""Build one typed SQL database covering the 116th-119th Congresses from the two
official GovInfo BILLSTATUS pathway packages, plus a record-grain inventory.

Rules (see docs/collections/pathways-116-119-sql.md):
- Inputs are verified packages; nothing is fetched.
- The two packages cover disjoint Congresses (116-117 and 118-119), so no bill,
  action or cosponsor record is counted twice across them.
- Raw rows are never dropped. Repeated action payloads, pre-introduction actions
  and missing sponsors are flagged, not deleted.
- Source strings are kept; typed columns are added alongside (dates, integers).
- Historical-v1 (113-118) is a separate snapshot and is NOT merged here, so its
  116-118 actions are not double counted as new events.
"""
import argparse, json, os, shutil, tempfile
from datetime import datetime, timezone
from pathlib import Path
import duckdb
from build_historical import ROOT, digest, quote
from verify_collections import verify

PACKAGES = {'pathways-116-117-2026-10-29': '116-117', 'pathways-2026-10-28': '118-119'}
TABLES = ['bills', 'actions', 'cosponsors', 'committees', 'committee_events', 'related_bills',
          'subjects', 'summaries', 'text_versions', 'cbo_estimates', 'vote_references']
# Grain = the key one row is supposed to represent.
GRAIN = {
    'bills': ['bill_id'],
    'actions': ['action_id'],
    'cosponsors': ['bill_id', 'sponsor_id', 'joined_date'],
    'committees': ['bill_id', 'committee_id'],
    'committee_events': ['bill_id', 'committee_id', 'event_name', 'event_date'],
    'related_bills': ['bill_id', 'related_bill_id', 'relationship', 'identified_by'],
    'subjects': ['bill_id', 'subject'],
    'summaries': ['bill_id', 'version_code', 'action_date'],
    'text_versions': ['bill_id', 'version_type', 'version_date', 'format_type', 'url'],
    'cbo_estimates': ['bill_id', 'url', 'publication_date'],
    'vote_references': ['bill_id', 'action_id', 'chamber', 'congress', 'session', 'roll_number'],
}
D = lambda col: f"TRY_CAST(NULLIF(left({col},10),'') AS DATE)"


def build(out_db: Path, doc_dir: Path):
    verify()
    # Build outside the repo (DuckDB needs to create and delete its WAL), then copy in.
    tmp = Path(tempfile.mkdtemp()) / out_db.name
    c = duckdb.connect(str(tmp))
    c.execute('SET threads=1; SET preserve_insertion_order=true;')
    for t in TABLES:
        parts = [f"SELECT *, {quote(rng)} AS source_collection FROM read_parquet({quote(ROOT/'datasets'/pkg/'tables'/(t+'.parquet'))})"
                 for pkg, rng in PACKAGES.items()]
        c.execute(f"CREATE TABLE raw_{t} AS " + ' UNION ALL BY NAME '.join(parts))

    c.execute(f"""CREATE TABLE bills AS SELECT *, CAST(congress AS INTEGER) AS congress_n,
        {D('introduced_date')} AS introduced_on, {D('latest_action_date')} AS latest_action_on,
        coalesce(law_identifiers,'') NOT IN ('','[]') AS became_law,
        coalesce(sponsor_id,'') = '' AS sponsor_missing
        FROM raw_bills ORDER BY congress_n, bill_type, TRY_CAST(bill_number AS INTEGER)""")
    c.execute(f"""CREATE TABLE actions AS
        SELECT a.*, {D('a.action_date')} AS action_on,
          {D('a.action_date')} < b.introduced_on AS before_introduction,
          count(*) OVER (PARTITION BY a.bill_id, a.action_date, coalesce(a.action_code,''), a.action_text) > 1 AS repeated_payload
        FROM raw_actions a JOIN bills b USING (bill_id) ORDER BY a.bill_id, action_on, TRY_CAST(a.source_order AS INTEGER)""")
    c.execute(f"""CREATE TABLE cosponsors AS SELECT *, {D('joined_date')} AS joined_on, {D('withdrawn_date')} AS withdrawn_on,
        lower(coalesce(is_original,'')) IN ('true','1','yes') AS original_cosponsor FROM raw_cosponsors""")
    c.execute(f"CREATE TABLE committee_events AS SELECT *, {D('event_date')} AS event_on FROM raw_committee_events")
    c.execute("""CREATE TABLE related_bills AS SELECT r.*, (b.bill_id IS NOT NULL) AS related_in_116_119
        FROM raw_related_bills r LEFT JOIN (SELECT bill_id FROM raw_bills) b ON b.bill_id = r.related_bill_id""")
    c.execute(f"CREATE TABLE summaries AS SELECT *, {D('action_date')} AS action_on FROM raw_summaries")
    c.execute(f"CREATE TABLE text_versions AS SELECT *, {D('version_date')} AS version_on FROM raw_text_versions")
    c.execute(f"CREATE TABLE cbo_estimates AS SELECT *, {D('publication_date')} AS published_on FROM raw_cbo_estimates")
    c.execute(f"CREATE TABLE vote_references AS SELECT *, {D('vote_date')} AS vote_on FROM raw_vote_references")
    for t in ['committees', 'subjects']:
        c.execute(f"CREATE TABLE {t} AS SELECT * FROM raw_{t}")
    for t in TABLES:
        c.execute(f"DROP TABLE raw_{t}")

    # Convenience views (derived; documented as such)
    c.execute("""CREATE VIEW bill_coalitions AS
        SELECT b.bill_id, b.congress_n, b.bill_type, b.sponsor_party,
          count(c.sponsor_id) AS cosponsors,
          count(c.sponsor_id) FILTER (WHERE c.withdrawn_on IS NULL) AS active_cosponsors,
          count(c.sponsor_id) FILTER (WHERE c.party NOT IN (b.sponsor_party) AND c.party <> '' AND b.sponsor_party <> '') AS cross_party_cosponsors,
          b.became_law
        FROM bills b LEFT JOIN cosponsors c USING (bill_id) GROUP BY ALL""")
    c.execute("""CREATE VIEW congress_overview AS
        SELECT congress_n, count(*) AS bills, count(*) FILTER (WHERE became_law) AS became_law,
               min(introduced_on) AS first_introduced, max(introduced_on) AS last_introduced
        FROM bills GROUP BY 1 ORDER BY 1""")

    # Record-grain inventory
    inv = []
    for t in TABLES:
        k = ', '.join(f"coalesce(CAST({x} AS VARCHAR),'')" for x in GRAIN[t])
        rows, keys = c.execute(f"SELECT count(*), count(DISTINCT ({k})) FROM {t}").fetchall()[0]
        by = dict(c.execute(f"SELECT source_collection, count(*) FROM {t} GROUP BY 1").fetchall())
        inv.append({'table': t, 'grain': GRAIN[t], 'rows': rows, 'distinct_grain_keys': keys,
                    'rows_sharing_a_grain_key': rows - keys, 'rows_116_117': by.get('116-117', 0), 'rows_118_119': by.get('118-119', 0)})
    c.execute("CREATE TABLE record_inventory AS SELECT * FROM read_json_auto(?)", [_tmpjson(inv)])

    q = lambda s: c.execute(s).fetchall()[0][0]
    flags = {
        'actions_repeated_payload_rows': q("SELECT count(*) FROM actions WHERE repeated_payload"),
        'actions_before_introduction': q("SELECT count(*) FROM actions WHERE before_introduction"),
        'bills_missing_sponsor_id': q("SELECT count(*) FROM bills WHERE sponsor_missing"),
        'related_bills_outside_116_119': q("SELECT count(*) FROM related_bills WHERE NOT related_in_116_119"),
        'bills_without_policy_area': q("SELECT count(*) FROM bills WHERE coalesce(policy_area,'')=''"),
    }
    total = sum(x['rows'] for x in inv)
    receipt = {
        'database': out_db.name, 'built_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'congresses': [116, 117, 118, 119],
        'inputs': {p: digest(ROOT/'datasets'/p/'package.json') for p in PACKAGES},
        'bills': q("SELECT count(*) FROM bills"), 'laws': q("SELECT count(*) FROM bills WHERE became_law"),
        'total_rows': total, 'rows_sharing_a_grain_key': sum(x['rows_sharing_a_grain_key'] for x in inv),
        'quality_flags': flags, 'tables': inv,
        'counting_rule': 'Rows are different record types (bills, actions, cosponsorships...). Congress coverage is disjoint across the two inputs, so no record is counted in both. They are not 1.7M independent bills or events.',
    }
    c.execute("CHECKPOINT"); c.close()
    shutil.copyfile(tmp, out_db)
    receipt['database_sha256'] = digest(out_db); receipt['database_bytes'] = out_db.stat().st_size
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir/'pathways-116-119-sql.json').write_text(json.dumps(receipt, indent=2, default=str) + '\n')
    return receipt


def _tmpjson(rows):
    f = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
    json.dump(rows, f); f.close(); return f.name


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, default=ROOT/'warehouse/sql/pathways-116-119.duckdb')
    a = p.parse_args(); a.output.parent.mkdir(parents=True, exist_ok=True)
    r = build(a.output, ROOT/'docs/collections')
    print(json.dumps({k: r[k] for k in ['bills', 'laws', 'total_rows', 'rows_sharing_a_grain_key', 'quality_flags', 'database_bytes']}, indent=2))
    for t in r['tables']:
        print(f"{t['table']:18}{t['rows']:>10,}  grain-dupes {t['rows_sharing_a_grain_key']:,}")
