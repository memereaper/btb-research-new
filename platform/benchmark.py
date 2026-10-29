"""Explicit synthetic scale test in an isolated schema; never modifies research releases."""

import argparse, json, os, statistics, time
from pathlib import Path
import psycopg


def benchmark(dsn, rows=1000000):
    if rows < 1000000 or rows > 10000000:
        raise ValueError("Benchmark scope must be 1–10 million rows")
    # Refuse remote production databases: this generator is for local/CI disposable databases only.
    from psycopg.conninfo import conninfo_to_dict

    if conninfo_to_dict(dsn).get("host") not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Synthetic benchmark requires a local database")
    with psycopg.connect(dsn, prepare_threshold=None) as c:
        c.execute("CREATE SCHEMA IF NOT EXISTS btb_benchmark")
        if c.execute("SELECT to_regclass('btb_benchmark.actions')").fetchone()[0]:
            raise ValueError(
                "Benchmark already exists; use a fresh disposable database"
            )
        t = time.perf_counter()
        c.execute(
            "CREATE TABLE btb_benchmark.actions AS SELECT g::bigint action_id, ('118-hr'||(1+(g%%16565)))::text bill_id, (g/16565)::bigint sequence_number, 'Synthetic action, not a legislative record'::text action_text FROM generate_series(1,%s) g",
            (rows,),
        )
        c.execute("ALTER TABLE btb_benchmark.actions ADD PRIMARY KEY(action_id)")
        c.execute(
            "CREATE INDEX actions_bill_page ON btb_benchmark.actions(bill_id,sequence_number,action_id)"
        )
        c.execute("ANALYZE btb_benchmark.actions")
        build = time.perf_counter() - t
        assert (
            c.execute("SELECT count(*) FROM btb_benchmark.actions").fetchone()[0]
            == rows
        )
        sql = "SELECT action_id,bill_id,sequence_number,action_text FROM btb_benchmark.actions WHERE bill_id=%s AND (sequence_number,action_id)>(%s,%s) ORDER BY sequence_number,action_id LIMIT 51"
        samples = []
        payload = 0
        for i in range(50):
            t = time.perf_counter()
            result = c.execute(sql, ("118-hr" + str(1 + i * 137), 0, 0)).fetchall()
            samples.append((time.perf_counter() - t) * 1000)
            payload = max(payload, len(json.dumps(result).encode()))
        plan = c.execute("EXPLAIN (FORMAT JSON) " + sql, ("118-hr1", 0, 0)).fetchone()[
            0
        ]
        if "Index" not in json.dumps(plan):
            raise AssertionError("Benchmark failed to use its paging index")
        return {
            "synthetic": True,
            "rows": rows,
            "build_and_index_seconds": round(build, 3),
            "warm_query_samples": len(samples),
            "query_ms_median": round(statistics.median(samples), 3),
            "query_ms_p95": round(sorted(samples)[int(len(samples) * 0.95) - 1], 3),
            "maximum_page_rows": 51,
            "maximum_page_json_bytes": payload,
            "plan": plan,
            "limits": "Local database microbenchmark; not production HTTP latency, uptime, traffic capacity, or a research finding.",
        }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, default=1000000)
    p.add_argument("--output", type=Path, default=Path("work/platform/benchmark.json"))
    a = p.parse_args()
    result = benchmark(os.environ["BTB_TEST_DATABASE_URL"], a.rows)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "plan"}, indent=2))
