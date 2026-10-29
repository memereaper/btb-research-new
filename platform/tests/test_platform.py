import json, os, shutil, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from botocore.exceptions import ClientError
from btb_platform.api import Cache, Limiter, decode_cursor, encode_cursor
from btb_platform.contracts import canonical, digest, release_id, verify_bundle
from btb_platform.storage import ObjectStore


class MemoryS3:
    def __init__(self):
        self.objects = {}
        self.uploads = 0

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        value, meta = self.objects[Key]
        return {"ContentLength": len(value), "Metadata": meta}

    def upload_file(self, path, bucket, key, ExtraArgs):
        self.objects[key] = (Path(path).read_bytes(), ExtraArgs["Metadata"])
        self.uploads += 1

    def download_file(self, bucket, key, path):
        Path(path).write_bytes(self.objects[key][0])


class ContractTests(unittest.TestCase):
    def test_cursor_bound_to_query_and_bounded(self):
        value = encode_cursor({"scope": "one", "after": "118-hr1"})
        self.assertEqual(decode_cursor(value, "one"), "118-hr1")
        for v in [value, "not base64", "x" * 1025]:
            with self.assertRaises(Exception):
                decode_cursor(v, "two")

    def test_object_resume_conflict_and_verified_restore(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "source"
            p.write_bytes(b"legislative evidence")
            sha = digest(p)
            client = MemoryS3()
            store = ObjectStore("test", client)
            self.assertEqual(store.put(p, "objects/" + sha), "uploaded")
            self.assertEqual(store.put(p, "objects/" + sha), "reused")
            self.assertEqual(client.uploads, 1)
            restored = Path(t) / "restored"
            store.restore("objects/" + sha, restored, sha)
            self.assertEqual(restored.read_bytes(), p.read_bytes())
            client.objects["objects/" + sha] = (b"changed", {"sha256": sha})
            with self.assertRaises(ValueError):
                store.restore("objects/" + sha, Path(t) / "bad", sha)
            self.assertFalse((Path(t) / "bad").exists())
            with self.assertRaises(ValueError):
                store.put(p, "objects/" + sha)

    def test_cache_and_rate_memory_bound(self):
        cache = Cache(capacity=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("c"), 3)
        limiter = Limiter(rate=2, capacity=2)
        self.assertTrue(limiter.allow("a"))
        self.assertTrue(limiter.allow("a"))
        self.assertFalse(limiter.allow("a"))
        limiter.allow("b")
        limiter.allow("c")
        self.assertEqual(len(limiter.clients), 2)

    def test_manifest_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            f = p / "bills"
            f.write_bytes(b"original")
            m = {
                "files": [
                    {"path": "bills", "sha256": digest(f), "bytes": f.stat().st_size}
                ]
            }
            rid = release_id(m)
            root = p / rid
            root.mkdir()
            f.rename(root / "bills")
            (root / "manifest.json").write_bytes(canonical(m))
            self.assertEqual(verify_bundle(root)[0], rid)
            (root / "bills").write_bytes(b"corrupted")
            with self.assertRaises(ValueError):
                verify_bundle(root)


@unittest.skipUnless(
    os.getenv("BTB_TEST_DATABASE_URL"), "Local/CI PostgreSQL URL required"
)
class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import duckdb
        from btb_platform import db

        cls.db = db
        cls.dsn = os.environ["BTB_TEST_DATABASE_URL"]
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        db.migrate(cls.dsn)
        with db.connect(cls.dsn) as c:
            cls.original = c.execute(
                "SELECT release_id FROM btb.investigations WHERE slug='where-bills-go-to-die'"
            ).fetchone()
        d = duckdb.connect()
        d.execute(
            """CREATE TABLE bills AS SELECT '118-hr'||i bill_id,118::INTEGER congress,'hr' bill_type,i::INTEGER bill_number,'Climate evidence '||i title,DATE '2023-01-03' introduced_date,CASE WHEN i=1 THEN 'Became law' ELSE 'No recorded progress' END outcome,NULL::DATE enacted_date,'A000001' sponsor_id,'https://www.govinfo.gov/test' source_url,'fixture.csv' source_id,i::VARCHAR source_record_id,'Environment' policy_area,'house' chamber,(i=1) bipartisan,'R' sponsor_party,'TX' sponsor_state FROM range(1,4) x(i)"""
        )
        d.execute(
            """CREATE TABLE actions AS SELECT 'action-'||i action_id,'118-hr1' bill_id,DATE '2023-01-03' action_date,'1000' action_code,'Introduced' action_text,'Intro' action_type,'House' source_system,i::BIGINT sequence_number,'fixture.csv' source_id,i::VARCHAR source_record_id FROM range(1,6) x(i)"""
        )
        d.execute(
            "CREATE TABLE summary_cells AS SELECT congress,chamber,policy_area,outcome,CASE WHEN bipartisan THEN 'yes' ELSE 'no' END bipartisan,count(*)::BIGINT bill_count FROM bills GROUP BY ALL"
        )
        work = cls.root / "fixture"
        (work / "serving").mkdir(parents=True)
        for name in ["bills", "actions", "summary_cells"]:
            d.execute(
                "COPY " + name + " TO ? (FORMAT PARQUET)",
                [str(work / "serving" / (name + ".parquet"))],
            )
        d.close()
        m = {
            "investigation": "where-bills-go-to-die",
            "coverage": {"bills": 3, "actions": 5, "congresses": [118]},
            "limits": ["Synthetic test records; not a published finding."],
            "files": [
                {
                    "path": str(p.relative_to(work)),
                    "sha256": digest(p),
                    "bytes": p.stat().st_size,
                }
                for p in work.rglob("*.parquet")
            ],
        }
        cls.rid = release_id(m)
        cls.bundle = cls.root / cls.rid
        work.rename(cls.bundle)
        (cls.bundle / "manifest.json").write_bytes(canonical(m))
        db.load(
            cls.bundle,
            cls.dsn,
            insert_batches=os.getenv("BTB_TEST_INSERT_BATCHES") == "1",
        )
        db.promote(cls.rid, "Automated local/CI test", cls.dsn)
        cls.env = patch.dict(
            os.environ, {"BTB_POOL_SIZE": "1", "BTB_RATE_PER_MINUTE": "10000"}
        )
        cls.env.start()

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        if cls.original:
            cls.db.promote(
                cls.original[0], "Restore pointer after automated test", cls.dsn
            )
        cls.temp.cleanup()

    def setUp(self):
        from fastapi.testclient import TestClient
        from btb_platform.api import create_app

        self.client = TestClient(create_app(self.dsn))
        self.client.__enter__()

    def tearDown(self):
        if self.client:
            self.client.__exit__(None, None, None)

    def close_client(self):
        self.client.__exit__(None, None, None)
        self.client = None

    def test_api_filters_summary_and_release(self):
        r = self.client.get(
            "/v1/bills", params={"release": self.rid, "bipartisan": "true"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["items"]), 1)
        s = self.client.get(
            "/v1/summary",
            params={"release": self.rid, "q": "climate", "bipartisan": "false"},
        ).json()
        self.assertEqual(s["total"], 2)
        empty = self.client.get(
            "/v1/bills",
            params={"release": self.rid, "q": "'; DROP TABLE btb.bills; --"},
        )
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(self.client.get("/health/ready").status_code, 200)

    def test_keyset_pagination_no_duplicates_and_cursor_filter_binding(self):
        params = {"release": self.rid, "limit": 1}
        ids = []
        while True:
            r = self.client.get("/v1/bills", params=params).json()
            ids += [b["bill_id"] for b in r["items"]]
            if not r["next_cursor"]:
                break
            params["cursor"] = r["next_cursor"]
        self.assertEqual(ids, ["118-hr1", "118-hr2", "118-hr3"])
        params["q"] = "changed"
        self.assertEqual(self.client.get("/v1/bills", params=params).status_code, 400)

    def test_actions_page_and_provenance(self):
        first = self.client.get(
            "/v1/bills/118-hr1/actions", params={"release": self.rid, "limit": 2}
        ).json()
        second = self.client.get(
            "/v1/bills/118-hr1/actions",
            params={"release": self.rid, "limit": 2, "cursor": first["next_cursor"]},
        ).json()
        self.assertEqual([x["sequence_number"] for x in second["items"]], [3, 4])
        self.assertEqual(second["items"][0]["source_id"], "fixture.csv")

    def test_cache_etag_cors_limits_and_read_only(self):
        p = "/v1/summary?release=" + self.rid
        r = self.client.get(p, headers={"Origin": "https://betweenthebills.com"})
        self.assertEqual(
            r.headers["access-control-allow-origin"], "https://betweenthebills.com"
        )
        self.assertEqual(
            self.client.get(
                p, headers={"If-None-Match": r.headers["etag"]}
            ).status_code,
            304,
        )
        self.assertEqual(self.client.get("/v1/bills?limit=1000000").status_code, 422)
        self.assertEqual(self.client.post("/v1/bills").status_code, 405)
        self.assertEqual(
            self.client.app.state.query("SHOW transaction_read_only")[0][
                "transaction_read_only"
            ],
            "on",
        )

    def test_failed_release_does_not_replace_current(self):
        m = json.loads((self.bundle / "manifest.json").read_text())
        m["coverage"]["bills"] = 4
        bad = self.root / release_id(m)
        shutil.copytree(self.bundle, bad)
        (bad / "manifest.json").write_bytes(canonical(m))
        self.close_client()
        with self.assertRaises(ValueError):
            self.db.load(
                bad,
                self.dsn,
                insert_batches=os.getenv("BTB_TEST_INSERT_BATCHES") == "1",
            )
        with self.db.connect(self.dsn) as c:
            self.assertEqual(
                c.execute(
                    "SELECT release_id FROM btb.investigations WHERE slug='where-bills-go-to-die'"
                ).fetchone()[0],
                self.rid,
            )
            self.assertIsNone(
                c.execute(
                    "SELECT 1 FROM btb.releases WHERE release_id=%s", (bad.name,)
                ).fetchone()
            )

    def test_promotion_requires_ready_release(self):
        self.close_client()
        with self.assertRaises(ValueError):
            self.db.promote("btb-v1-" + "0" * 24, "not loaded", self.dsn)


if __name__ == "__main__":
    unittest.main()
