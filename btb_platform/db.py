"""Transactional PostgreSQL loading; public API has a separate read-only credential."""

import json, os, time
from pathlib import Path
import duckdb, psycopg
from psycopg import sql
from .contracts import ROOT, canonical, checked_release, verify_bundle

COLUMNS = {
    "bills": "bill_id congress bill_type bill_number title introduced_date outcome enacted_date sponsor_id source_url source_id source_record_id policy_area chamber bipartisan sponsor_party sponsor_state".split(),
    "actions": "action_id bill_id action_date action_code action_text action_type source_system sequence_number source_id source_record_id".split(),
    "summary_cells": "congress chamber policy_area outcome bipartisan bill_count".split(),
}


def connect(dsn=None):
    for attempt in range(3):
        try:
            return psycopg.connect(
                dsn or os.environ["BTB_ADMIN_DATABASE_URL"],
                connect_timeout=5,
                prepare_threshold=None,
            )
        except psycopg.OperationalError:
            if attempt == 2:
                raise
            time.sleep(0.1 * (attempt + 1))


def migrate(dsn=None):
    with connect(dsn) as c:
        c.execute("SELECT pg_advisory_xact_lock(hashtext('btb-schema'))")
        c.execute((ROOT / "btb_platform/migrations/001.sql").read_text())


def load(bundle, dsn=None, insert_batches=False):
    rid, m = verify_bundle(bundle)
    bundle = Path(bundle)
    # Atomic entire-release load: a failed import cannot become visible or displace the current release.
    with connect(dsn) as c:
        c.execute("SELECT pg_advisory_xact_lock(hashtext('btb-load'))")
        existing = c.execute(
            "SELECT status FROM btb.releases WHERE release_id=%s", (rid,)
        ).fetchone()
        if existing:
            if existing[0] != "ready":
                raise ValueError("Existing release is not ready")
            print("Verified release already loaded:", rid)
            return rid
        import hashlib

        c.execute(
            "INSERT INTO btb.releases(release_id,manifest_sha256,manifest,status,bill_count,action_count) VALUES(%s,%s,%s,%s,%s,%s)",
            (
                rid,
                hashlib.sha256(canonical(m)).hexdigest(),
                json.dumps(m),
                "loading",
                m["coverage"]["bills"],
                m["coverage"]["actions"],
            ),
        )
        for name in ["bills", "actions"]:
            ident = "r_" + rid.removeprefix("btb-v1-") + "_" + name
            c.execute(
                sql.SQL(
                    "CREATE TABLE btb.{} PARTITION OF btb.{} FOR VALUES IN ({})"
                ).format(sql.Identifier(ident), sql.Identifier(name), sql.Literal(rid))
            )
        d = duckdb.connect()
        for name, columns in COLUMNS.items():
            cur = d.execute(
                "SELECT "
                + ",".join('"' + x + '"' for x in columns)
                + " FROM read_parquet(?)",
                [str(bundle / "serving" / (name + ".parquet"))],
            )
            statement = sql.SQL("COPY btb.{} ({}) FROM STDIN").format(
                sql.Identifier(name),
                sql.SQL(",").join(map(sql.Identifier, ["release_id"] + columns)),
            )
            if insert_batches:
                # Compatibility path for PostgreSQL protocol test runtimes lacking COPY.
                while rows := cur.fetchmany(500):
                    slots = sql.SQL(",").join(
                        sql.SQL("(" + ",".join(["%s"] * (len(columns) + 1)) + ")")
                        for _ in rows
                    )
                    insert = (
                        sql.SQL("INSERT INTO btb.{} ({}) VALUES ").format(
                            sql.Identifier(name),
                            sql.SQL(",").join(
                                map(sql.Identifier, ["release_id"] + columns)
                            ),
                        )
                        + slots
                    )
                    c.execute(insert, [v for row in rows for v in (rid,) + row])
            else:
                with c.cursor().copy(statement) as copy:
                    while rows := cur.fetchmany(5000):
                        for row in rows:
                            copy.write_row((rid,) + row)
        d.close()
        for name, total in [
            ("bills", m["coverage"]["bills"]),
            ("actions", m["coverage"]["actions"]),
        ]:
            n = c.execute(
                sql.SQL("SELECT count(*) FROM btb.{} WHERE release_id=%s").format(
                    sql.Identifier(name)
                ),
                (rid,),
            ).fetchone()[0]
            if n != total:
                raise ValueError("Loaded count mismatch: " + name)
        if (
            c.execute(
                "SELECT sum(bill_count) FROM btb.summary_cells WHERE release_id=%s",
                (rid,),
            ).fetchone()[0]
            != m["coverage"]["bills"]
        ):
            raise ValueError("Summary mismatch")
        c.execute("UPDATE btb.releases SET status='ready' WHERE release_id=%s", (rid,))
    with connect(dsn) as c:
        for name in ["bills", "actions", "summary_cells"]:
            c.execute(sql.SQL("ANALYZE btb.{}").format(sql.Identifier(name)))
    print("Loaded and reconciled:", rid)
    return rid


def promote(rid, reason, dsn=None):
    checked_release(rid)
    if not reason.strip():
        raise ValueError("Promotion requires a reason")
    with connect(dsn) as c:
        c.execute("SELECT pg_advisory_xact_lock(hashtext('btb-promote'))")
        row = c.execute(
            "SELECT status,manifest->>'investigation' FROM btb.releases WHERE release_id=%s",
            (rid,),
        ).fetchone()
        if not row or row[0] != "ready":
            raise ValueError("Only ready releases can be promoted")
        slug = row[1]
        old = c.execute(
            "SELECT release_id FROM btb.investigations WHERE slug=%s FOR UPDATE",
            (slug,),
        ).fetchone()
        c.execute(
            "INSERT INTO btb.investigations(slug,release_id) VALUES(%s,%s) ON CONFLICT(slug) DO UPDATE SET release_id=EXCLUDED.release_id,updated_at=now()",
            (slug, rid),
        )
        c.execute(
            "INSERT INTO btb.release_events(slug,old_release,new_release,reason) VALUES(%s,%s,%s,%s)",
            (slug, old[0] if old else None, rid, reason),
        )
    print("Promoted:", rid)
