// Between the Bills open data API, v2. Read-only, fixed queries, no SQL input.
// Runs every query in a read-only transaction as the SELECT-only btb_reader role.
import postgres from 'npm:postgres@3.4.5';

const VERSION = '2.0.1';
const sql = postgres(Deno.env.get('SUPABASE_DB_URL')!, { max: 3, prepare: false, idle_timeout: 20 });
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'content-type',
};
const COALITIONS = ['bipartisan', 'same_party', 'solo', 'other_sponsor', 'not_bipartisan'];
const STAGES = ['introduced', 'cleared_committee', 'passed_one', 'passed_both', 'law'];
const FINDINGS = ['bipartisanship-116-118', 'bipartisanship-deep', 'bipartisanship-field', 'open-data-catalog'];
const COLS = 'bill_id, congress, bill_type, bill_number, title, introduced_on, sponsor_id, sponsor_name, sponsor_party, sponsor_state, policy_area, chamber, coalition_at_intro, orig_cosponsors, orig_cross, furthest, became_law, ceremonial, latest_action_on, latest_action_text, congress_url';
const ID = /^1(1[3-9])-(hr|s|hjres|sjres)\d{1,5}$/;
const MEMBER = /^[A-Z]\d{6}$/;

function json(body: unknown, status = 200, maxAge = 300) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...CORS, 'Content-Type': 'application/json; charset=utf-8', 'X-BTB-API': VERSION,
      'Cache-Control': status === 200 ? `public, max-age=${maxAge}, s-maxage=${maxAge}, stale-while-revalidate=86400` : 'no-store',
    },
  });
}

async function ro<T>(fn: (tx: postgres.TransactionSql) => Promise<T>): Promise<T> {
  return await sql.begin('read only', async (tx) => {
    await tx`set local role btb_reader`;
    await tx`set local statement_timeout = '3000ms'`;
    return await fn(tx);
  }) as T;
}

const ROUTES = {
  overview: 'Counts for every hosted table and the full Parquet catalog.',
  bills: 'Search and filter bills, 113th-119th Congress. Params: q, congress, coalition, furthest, party, chamber, policy, limit (<=50), cursor.',
  bill: 'One bill with its full action timeline. Param: id (e.g. 117-hr3684).',
  members: 'Find members. Params: q (name or state), limit (<=50).',
  member: 'One member with top cross-party partners. Param: id (Bioguide ID, e.g. F000466).',
  policy_areas: 'Policy areas with bill counts.',
  findings: 'Published research results. Param: key (' + FINDINGS.join(', ') + ').',
};

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { headers: CORS });
  if (req.method !== 'GET') return json({ error: 'GET only' }, 405);
  const p = new URL(req.url).searchParams;
  const route = p.get('route') ?? 'overview';
  try {
    if (route === 'routes') return json({ version: VERSION, routes: ROUTES }, 200, 86400);

    if (route === 'overview') {
      const out = await ro(async (tx) => {
        const congresses = await tx`
          select congress, count(*)::int bills, count(*) filter (where became_law)::int laws,
            count(*) filter (where coalition_at_intro = 'bipartisan')::int bipartisan_at_intro
          from btb.o_bills group by 1 order by 1`;
        const [a] = await tx`select (select coalesce(sum(action_count),0) from btb.releases where status = 'ready')::int + (select count(*) from btb.p_actions_119)::int actions`;
        const [m] = await tx`select count(*)::int members from btb.p_member_partners`;
        const [c] = await tx`select body->'total_rows' total_rows, body->'pinned_commit' pinned_commit, body->'tables' tables from btb.p_findings where key = 'open-data-catalog'`;
        const tables: Record<string, number> = {};
        for (const [k, v] of Object.entries((c?.tables ?? {}) as Record<string, { rows: number }>)) tables[k] = v.rows;
        const bills = congresses.reduce((s: number, r: { bills: number }) => s + r.bills, 0);
        return {
          version: VERSION,
          hosted: { bills, actions: a.actions, members: m.members, rows: bills + a.actions + m.members },
          warehouse: { rows: c?.total_rows ?? null, pinned_commit: c?.pinned_commit ?? null, tables },
          congresses,
          source: 'Library of Congress Bill Status records via GovInfo. 113th-115th from release btb-v1-f692dfc32a8b62a838e76aaf; 116th-119th from the pathways packages.',
        };
      });
      return json(out, 200, 3600);
    }

    if (route === 'findings') {
      const key = p.get('key') ?? 'bipartisanship-116-118';
      if (!FINDINGS.includes(key)) return json({ error: 'key: ' + FINDINGS.join(', ') }, 400);
      const rows = await ro((tx) => tx`select key, body, updated_at from btb.p_findings where key = ${key}`);
      return rows.length ? json(rows[0], 200, 21600) : json({ error: 'not found' }, 404);
    }

    if (route === 'policy_areas') {
      const rows = await ro((tx) => tx`select policy_area, bills from btb.o_policy_areas order by bills desc`);
      return json({ policy_areas: rows }, 200, 86400);
    }

    if (route === 'members') {
      const limit = Math.max(1, Math.min(50, Number(p.get('limit') ?? 20) || 20));
      const q = (p.get('q') ?? '').trim().slice(0, 60);
      const rows = await ro((tx) => q
        ? tx`select member_id, name, party, state, chamber, cross_party_partners, cross_party_ties, sponsored_116_118, pct_sponsored_bipartisan::float, laws_sponsored_116_118
             from btb.p_member_partners
             where name ilike ${'%' + q.replace(/[%_\\]/g, '') + '%'} or upper(state) = ${q.toUpperCase()}
             order by cross_party_ties desc limit ${limit}`
        : tx`select member_id, name, party, state, chamber, cross_party_partners, cross_party_ties, sponsored_116_118, pct_sponsored_bipartisan::float, laws_sponsored_116_118
             from btb.p_member_partners order by cross_party_ties desc limit ${limit}`);
      return json({ members: rows }, 200, 3600);
    }

    if (route === 'member') {
      const id = (p.get('id') ?? '').toUpperCase();
      if (!MEMBER.test(id)) return json({ error: 'id like F000466' }, 400);
      const rows = await ro((tx) => tx`select member_id, name, party, state, chamber, cross_party_partners, cross_party_ties, sponsored_116_118, pct_sponsored_bipartisan::float, laws_sponsored_116_118, partners from btb.p_member_partners where member_id = ${id}`);
      return rows.length ? json(rows[0], 200, 3600) : json({ error: 'not found' }, 404);
    }

    if (route === 'bill') {
      const id = (p.get('id') ?? '').toLowerCase();
      if (!ID.test(id)) return json({ error: 'id like 118-hr815 (113th-119th)' }, 400);
      const out = await ro(async (tx) => {
        const b = await tx`select ${tx.unsafe(COLS)} from btb.o_bills where bill_id = ${id}`;
        if (!b.length) return null;
        const actions = await tx`select action_on, action_code, action_type, action_text from btb.o_actions where bill_id = ${id} order by action_on, action_id limit 400`;
        return { ...b[0], actions };
      });
      return out ? json(out, 200, 3600) : json({ error: 'not found' }, 404);
    }

    if (route === 'bills') {
      const limit = Math.max(1, Math.min(50, Number(p.get('limit') ?? 25) || 25));
      const congress = Number(p.get('congress') ?? 0);
      const coalition = p.get('coalition') ?? '';
      const furthest = p.get('furthest') ?? '';
      const party = p.get('party') ?? '';
      const chamber = p.get('chamber') ?? '';
      const policy = (p.get('policy') ?? '').slice(0, 80);
      const q = (p.get('q') ?? '').trim().slice(0, 120);
      const cursor = p.get('cursor') ?? '';
      if (congress && (congress < 113 || congress > 119)) return json({ error: 'congress 113-119' }, 400);
      if (coalition && !COALITIONS.includes(coalition)) return json({ error: 'coalition: ' + COALITIONS.join(', ') }, 400);
      if (furthest && !STAGES.includes(furthest)) return json({ error: 'furthest: ' + STAGES.join(', ') }, 400);
      if (party && !['D', 'R', 'I'].includes(party)) return json({ error: 'party: D, R, I' }, 400);
      if (chamber && !['House', 'Senate'].includes(chamber)) return json({ error: 'chamber: House, Senate' }, 400);
      let cDate: string | null = null, cId: string | null = null;
      if (cursor) {
        const m = /^(\d{4}-\d{2}-\d{2})\|(1\d\d-[a-z]+\d+)$/.exec(cursor);
        if (!m) return json({ error: 'bad cursor' }, 400);
        cDate = m[1]; cId = m[2];
      }
      const idq = /^(1\d\d)-?(hr|s|hjres|sjres)\s*(\d+)$/i.exec(q.replace(/[.\s]/g, ''));
      const result = await ro(async (tx) => {
        const where = tx`
          true
          ${congress ? tx`and congress = ${congress}` : tx``}
          ${coalition === 'not_bipartisan' ? tx`and coalition_at_intro <> 'bipartisan'` : coalition ? tx`and coalition_at_intro = ${coalition}` : tx``}
          ${furthest ? tx`and furthest = ${furthest}` : tx``}
          ${party ? tx`and sponsor_party = ${party}` : tx``}
          ${chamber ? tx`and chamber = ${chamber}` : tx``}
          ${policy ? tx`and policy_area = ${policy}` : tx``}
          ${idq ? tx`and bill_id = ${(idq[1] + '-' + idq[2] + idq[3]).toLowerCase()}` : q ? tx`and search @@ websearch_to_tsquery('english', ${q})` : tx``}`;
        const rows = await tx`
          select ${tx.unsafe(COLS)} from btb.o_bills
          where ${where} ${cDate ? tx`and (introduced_on, bill_id) < (${cDate}::date, ${cId})` : tx``}
          order by introduced_on desc, bill_id desc limit ${limit + 1}`;
        const total = cursor ? null : (await tx`select count(*)::int n from btb.o_bills where ${where}`)[0].n;
        return { rows, total };
      });
      const more = result.rows.length > limit;
      const rows = result.rows.slice(0, limit);
      const last = rows[rows.length - 1];
      const next = more && last ? `${new Date(last.introduced_on).toISOString().slice(0, 10)}|${last.bill_id}` : null;
      return json({ total: result.total, count: rows.length, next_cursor: next, bills: rows }, 200, 300);
    }
    return json({ error: 'unknown route', routes: ROUTES }, 404);
  } catch (e) {
    console.error(e);
    return json({ error: 'query failed' }, 500);
  }
});
