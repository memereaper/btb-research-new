"""Bounded read-only API. No public SQL, collection, upload, or promotion endpoints."""

import base64, hashlib, json, logging, os, threading, time, uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Literal
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from .contracts import BILL_RE, RELEASE_RE, canonical

log = logging.getLogger("btb.api")


class Cache:
    def __init__(self, capacity=256, ttl=300):
        self.data = OrderedDict()
        self.lock = threading.Lock()
        self.capacity = capacity
        self.ttl = ttl

    def get(self, key):
        with self.lock:
            item = self.data.get(key)
            if item and item[0] > time.monotonic():
                self.data.move_to_end(key)
                return item[1]
            self.data.pop(key, None)

    def put(self, key, value):
        with self.lock:
            self.data[key] = (time.monotonic() + self.ttl, value)
            self.data.move_to_end(key)
            while len(self.data) > self.capacity:
                self.data.popitem(last=False)


# Bounded per-process guard; production also uses the reverse proxy's shared rate limit.
class Limiter:
    def __init__(self, rate=120, capacity=10000):
        self.rate = rate
        self.capacity = capacity
        self.clients = OrderedDict()
        self.lock = threading.Lock()

    def allow(self, key):
        now = time.monotonic()
        with self.lock:
            start, n = self.clients.pop(key, (now, 0))
            if now - start >= 60:
                start, n = now, 0
            self.clients[key] = (start, n + 1)
            while len(self.clients) > self.capacity:
                self.clients.popitem(last=False)
            return n < self.rate


def encode_cursor(value):
    return base64.urlsafe_b64encode(canonical(value)).decode().rstrip("=")


def decode_cursor(value, scope):
    try:
        if len(value) > 1024:
            raise ValueError()
        data = json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))
        if data["scope"] != scope:
            raise ValueError()
        return data["after"]
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise HTTPException(400, "Cursor does not match this query")


def create_app(dsn=None):
    cache = Cache()
    limiter = Limiter(int(os.getenv("BTB_RATE_PER_MINUTE", "120")))

    @asynccontextmanager
    async def lifespan(app):
        url = dsn or os.environ["BTB_DATABASE_URL"]
        app.state.pool = ConnectionPool(
            url,
            min_size=1,
            max_size=int(os.getenv("BTB_POOL_SIZE", "8")),
            timeout=3,
            max_waiting=32,
            kwargs={
                "connect_timeout": 5,
                "prepare_threshold": None,
                "row_factory": dict_row,
                "options": "-c default_transaction_read_only=on -c statement_timeout=2500 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000",
            },
            open=True,
        )
        app.state.pool.wait(timeout=15)
        yield
        app.state.pool.close()

    app = FastAPI(
        title="Between the Bills data API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if os.getenv("BTB_ENABLE_DOCS") == "1" else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv(
            "BTB_ALLOWED_ORIGINS", "https://betweenthebills.com"
        ).split(","),
        allow_methods=["GET"],
        allow_headers=["If-None-Match"],
        expose_headers=["ETag", "X-Request-ID"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.middleware("http")
    async def guard(request, call_next):
        start = time.monotonic()
        rid = uuid.uuid4().hex
        if len(str(request.url)) > 4096:
            return JSONResponse({"detail": "Request too long"}, 414)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            return JSONResponse({"detail": "Read-only API"}, 405)
        if request.url.path.startswith("/v1/") and not limiter.allow(
            request.client.host if request.client else "unknown"
        ):
            return JSONResponse(
                {"detail": "Too many requests"}, 429, headers={"Retry-After": "60"}
            )
        try:
            response = await call_next(request)
        except (psycopg.Error, PoolTimeout):
            log.warning("database_unavailable request_id=%s", rid)
            response = JSONResponse(
                {"detail": "Data temporarily unavailable", "request_id": rid},
                503,
                headers={"Retry-After": "5", "Cache-Control": "no-store"},
            )
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        log.info(
            "request id=%s path=%s status=%s ms=%.1f",
            rid,
            request.scope.get("route").path
            if request.scope.get("route")
            else "unmatched",
            response.status_code,
            (time.monotonic() - start) * 1000,
        )
        return response

    def query(statement, params=()):
        with app.state.pool.connection() as c:
            with c.transaction():
                c.execute("SET TRANSACTION READ ONLY")
                c.execute("SET LOCAL statement_timeout = '2500ms'")
                c.execute("SET LOCAL lock_timeout = '1000ms'")
                return c.execute(statement, params).fetchall()

    app.state.query = query

    def resolve(value):
        if value:
            if not RELEASE_RE.fullmatch(value):
                raise HTTPException(422, "Invalid release identifier")
            rows = query(
                "SELECT release_id FROM btb.releases WHERE release_id=%s AND status='ready'",
                (value,),
            )
        else:
            rows = query(
                "SELECT release_id FROM btb.investigations WHERE slug='where-bills-go-to-die'"
            )
        if not rows:
            raise HTTPException(404, "Published release not found")
        return rows[0]["release_id"]

    def respond(request, data, pinned=False):
        payload = jsonable_encoder(data)
        tag = '"' + hashlib.sha256(canonical(payload)).hexdigest() + '"'
        headers = {
            "ETag": tag,
            "Cache-Control": "public, max-age=300, s-maxage=3600"
            if pinned
            else "public, max-age=30, s-maxage=30",
        }
        if request.headers.get("if-none-match") == tag:
            return Response(status_code=304, headers=headers)
        return JSONResponse(payload, headers=headers)

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        rows = query(
            "SELECT i.release_id FROM btb.investigations i JOIN btb.releases r USING(release_id) WHERE r.status='ready'"
        )
        if not rows:
            raise HTTPException(503, "No published release")
        return {"status": "ready", "releases": [r["release_id"] for r in rows]}

    @app.get("/v1/releases")
    def releases(request: Request):
        return respond(
            request,
            {
                "releases": query(
                    "SELECT release_id,created_at,bill_count,action_count,manifest->'coverage' coverage FROM btb.releases WHERE status='ready' ORDER BY created_at DESC LIMIT 20"
                )
            },
        )

    @app.get("/v1/investigations/where-bills-go-to-die")
    def investigation(request: Request, release: str | None = None):
        rid = resolve(release)
        data = cache.get(("investigation", rid))
        if data is None:
            info = query(
                "SELECT manifest,manifest_sha256 FROM btb.releases WHERE release_id=%s",
                (rid,),
            )[0]
            data = {
                "release_id": rid,
                "investigation": "where-bills-go-to-die",
                "coverage": info["manifest"]["coverage"],
                "limits": info["manifest"]["limits"],
                "manifest_sha256": info["manifest_sha256"],
                "outcomes": query(
                    "SELECT congress,outcome,sum(bill_count)::bigint bill_count FROM btb.summary_cells WHERE release_id=%s GROUP BY congress,outcome ORDER BY congress,outcome",
                    (rid,),
                ),
                "policy_areas": query(
                    "SELECT DISTINCT policy_area FROM btb.summary_cells WHERE release_id=%s ORDER BY policy_area",
                    (rid,),
                ),
            }
            cache.put(("investigation", rid), data)
        return respond(request, data, bool(release))

    @app.get("/v1/releases/{release}/manifest")
    def manifest(request: Request, release: str):
        rid = resolve(release)
        row = query(
            "SELECT manifest,manifest_sha256 FROM btb.releases WHERE release_id=%s",
            (rid,),
        )[0]
        return respond(request, {"release_id": rid, **row}, True)

    @app.get("/v1/summary")
    def summary(
        request: Request,
        release: str | None = None,
        congress: int | None = Query(None, ge=1, le=999),
        chamber: Literal["house", "senate"] | None = None,
        policy_area: str | None = Query(None, max_length=150),
        bipartisan: bool | None = None,
        q: str | None = Query(None, max_length=120),
    ):
        rid = resolve(release)
        where = ["release_id=%s"]
        values = [rid]
        for key, value in [
            ("congress", congress),
            ("chamber", chamber),
            ("policy_area", policy_area),
            (
                "bipartisan",
                None if bipartisan is None else "yes" if bipartisan else "no",
            ),
        ]:
            if value is not None:
                where.append(key + "=%s")
                values.append(value)
        table = "btb.summary_cells"
        aggregation = "sum(bill_count)"
        if q and q.strip():
            table = "btb.bills"
            aggregation = "count(*)"
            # Convert the summary's categorical boolean to the serving boolean.
            if bipartisan is not None:
                values[-1] = bipartisan
            where.append("search_vector @@ plainto_tsquery('english',%s)")
            values.append(q.strip())
        key = ("summary", table, tuple(values))
        data = cache.get(key)
        if data is None:
            rows = query(
                "SELECT outcome,"
                + aggregation
                + "::bigint bill_count FROM "
                + table
                + " WHERE "
                + " AND ".join(where)
                + " GROUP BY outcome ORDER BY outcome",
                values,
            )
            data = {
                "release_id": rid,
                "total": sum(r["bill_count"] for r in rows),
                "outcomes": rows,
            }
            cache.put(key, data)
        return respond(request, data, bool(release))

    @app.get("/v1/bills")
    def bills(
        request: Request,
        release: str | None = None,
        congress: int | None = Query(None, ge=1, le=999),
        chamber: Literal["house", "senate"] | None = None,
        policy_area: str | None = Query(None, max_length=150),
        outcome: str | None = Query(None, max_length=150),
        bipartisan: bool | None = None,
        q: str | None = Query(None, max_length=120),
        limit: int = Query(50, ge=1, le=100),
        cursor: str | None = Query(None, max_length=1024),
    ):
        rid = resolve(release)
        where = ["release_id=%s"]
        values = [rid]
        for key, value in [
            ("congress", congress),
            ("chamber", chamber),
            ("policy_area", policy_area),
            ("outcome", outcome),
            ("bipartisan", bipartisan),
        ]:
            if value is not None:
                where.append(key + "=%s")
                values.append(value)
        if q and q.strip():
            where.append("search_vector @@ plainto_tsquery('english',%s)")
            values.append(q.strip())
        scope = hashlib.sha256(canonical(values)).hexdigest()
        if cursor:
            after = decode_cursor(cursor, scope)
            if not isinstance(after, str) or not BILL_RE.fullmatch(after):
                raise HTTPException(400, "Invalid cursor")
            where.append("bill_id>%s")
            values.append(after)
        rows = query(
            "SELECT bill_id,congress,bill_type,bill_number,title,introduced_date,outcome,policy_area,chamber,bipartisan,source_url FROM btb.bills WHERE "
            + " AND ".join(where)
            + " ORDER BY bill_id LIMIT %s",
            values + [limit + 1],
        )
        more = len(rows) > limit
        rows = rows[:limit]
        return respond(
            request,
            {
                "release_id": rid,
                "items": rows,
                "next_cursor": encode_cursor(
                    {"scope": scope, "after": rows[-1]["bill_id"]}
                )
                if more
                else None,
            },
            bool(release),
        )

    @app.get("/v1/bills/{bill_id}")
    def bill(request: Request, bill_id: str, release: str | None = None):
        if not BILL_RE.fullmatch(bill_id):
            raise HTTPException(422, "Invalid bill identifier")
        rid = resolve(release)
        rows = query(
            "SELECT bill_id,congress,bill_type,bill_number,title,introduced_date,outcome,enacted_date,sponsor_id,source_url,source_id,source_record_id,policy_area,chamber,bipartisan,sponsor_party,sponsor_state FROM btb.bills WHERE release_id=%s AND bill_id=%s",
            (rid, bill_id),
        )
        if not rows:
            raise HTTPException(404, "Bill not found in release")
        return respond(request, {"release_id": rid, "bill": rows[0]}, bool(release))

    @app.get("/v1/bills/{bill_id}/actions")
    def actions(
        request: Request,
        bill_id: str,
        release: str | None = None,
        limit: int = Query(50, ge=1, le=100),
        cursor: str | None = Query(None, max_length=1024),
    ):
        if not BILL_RE.fullmatch(bill_id):
            raise HTTPException(422, "Invalid bill identifier")
        rid = resolve(release)
        if not query(
            "SELECT 1 FROM btb.bills WHERE release_id=%s AND bill_id=%s", (rid, bill_id)
        ):
            raise HTTPException(404, "Bill not found in release")
        values = [rid, bill_id]
        after = ""
        scope = hashlib.sha256(canonical(values)).hexdigest()
        if cursor:
            val = decode_cursor(cursor, scope)
            if (
                not isinstance(val, list)
                or len(val) != 2
                or type(val[0]) is not int
                or not isinstance(val[1], str)
                or len(val[1]) > 128
            ):
                raise HTTPException(400, "Invalid cursor")
            after = " AND (sequence_number,action_id)>(%s,%s)"
            values += val
        rows = query(
            "SELECT action_id,action_date,action_code,action_text,action_type,source_system,sequence_number,source_id,source_record_id FROM btb.actions WHERE release_id=%s AND bill_id=%s"
            + after
            + " ORDER BY sequence_number,action_id LIMIT %s",
            values + [limit + 1],
        )
        more = len(rows) > limit
        rows = rows[:limit]
        return respond(
            request,
            {
                "release_id": rid,
                "bill_id": bill_id,
                "items": rows,
                "next_cursor": encode_cursor(
                    {
                        "scope": scope,
                        "after": [rows[-1]["sequence_number"], rows[-1]["action_id"]],
                    }
                )
                if more
                else None,
            },
            bool(release),
        )

    return app
