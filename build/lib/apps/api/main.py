import asyncio
import csv
import hashlib
import hmac
import io
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from consignai.ai.explain import OllamaRuntime, explain
from consignai.data.generator import generate
from consignai.data.store import Store
from consignai.domain.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    ErrorResponse,
    EvidenceResponse,
    ImportReport,
    NarrativeResponse,
    OverviewResponse,
    Page,
)
from consignai.observability.http import BodyLimitMiddleware
from consignai.services.analysis import run_analysis
from consignai.services.ingestion import decode_upload, ingest, now
from consignai.services.jobs import weekly_job
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

logger = logging.getLogger("consignai.api")
logging.basicConfig(level=logging.INFO, format="%(message)s")
MAX_UPLOAD = 20 * 1024 * 1024


def create_app(db_path=None, seed_demo=None):
    database = db_path or os.getenv("CONSIGNAI_DB", "var/consignai.db")
    seed_demo = os.getenv("DEMO_SEED", "true").lower() == "true" if seed_demo is None else seed_demo
    store = Store(database)
    mode = os.getenv("APP_MODE", "demo")
    write_key = os.getenv("WRITE_API_KEY", "")
    read_key = os.getenv("READ_API_KEY", "")
    if mode not in {"demo", "secured"}:
        raise ValueError("APP_MODE must be demo or secured")
    if mode == "secured" and (len(write_key) < 24 or len(read_key) < 24):
        raise ValueError(
            "Secured mode needs separate READ_API_KEY and WRITE_API_KEY of at least 24 characters"
        )
    if mode == "secured" and hmac.compare_digest(write_key, read_key):
        raise ValueError("Read and write credentials must differ")

    async def scheduler():
        while True:
            try:
                if store.query("SELECT 1 FROM snapshots LIMIT 1"):
                    await run_in_threadpool(weekly_job, store)
            except Exception:
                logger.exception(json.dumps({"event": "weekly_job_failed"}))
            await asyncio.sleep(3600)

    @asynccontextmanager
    async def lifespan(app):
        app.state.ready = False
        if seed_demo and not store.query("SELECT 1 FROM snapshots LIMIT 1"):
            report = await run_in_threadpool(ingest, store, generate(), "synthetic-demo")
            if report["status"] != "accepted":
                raise RuntimeError("Demo data failed validation")
        if store.query("SELECT 1 FROM snapshots LIMIT 1") and not store.latest_run():
            await run_in_threadpool(run_analysis, store)
        app.state.ready = True
        task = asyncio.create_task(scheduler()) if os.getenv("WEEKLY_JOBS", "true") == "true" else None
        yield
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(
        title="ConsignAI",
        version="0.1.0",
        lifespan=lifespan,
        responses={
            400: {"model": ErrorResponse},
            401: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
        },
    )
    app.state.store, app.state.ready = store, False
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "api", "testserver"]
    )

    @app.middleware("http")
    async def observe(request, call_next):
        request.state.trace_id = str(uuid.uuid4())
        started = time.perf_counter()
        try:
            origin = request.headers.get("origin")
            allowed_origins = {
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://localhost:5177",
                "http://127.0.0.1:5177",
            }
            if request.method == "POST" and origin and origin not in allowed_origins:
                response = JSONResponse(
                    {
                        "error": {
                            "code": "origin_denied",
                            "message": "Untrusted browser origin",
                            "trace_id": request.state.trace_id,
                            "details": [],
                        }
                    },
                    status_code=403,
                )
            else:
                response = await call_next(request)
        except Exception:
            logger.exception(json.dumps({"event": "request_failed", "trace_id": request.state.trace_id}))
            response = JSONResponse(
                {
                    "error": {
                        "code": "internal_error",
                        "message": "Unexpected server error",
                        "trace_id": request.state.trace_id,
                        "details": [],
                    }
                },
                status_code=500,
            )
        response.headers["X-Trace-ID"] = request.state.trace_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        logger.info(
            json.dumps(
                {
                    "event": "request",
                    "trace_id": request.state.trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            )
        )
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return JSONResponse(
            {
                "error": {
                    "code": f"http_{exc.status_code}",
                    "message": str(exc.detail),
                    "trace_id": request.state.trace_id,
                    "details": [],
                }
            },
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        details = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(
            {
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "trace_id": request.state.trace_id,
                    "details": details,
                }
            },
            status_code=422,
        )

    def require_read(authorization: Annotated[str | None, Header()] = None):
        if mode == "secured" and not any(
            hmac.compare_digest(authorization or "", f"Bearer {key}") for key in (read_key, write_key)
        ):
            raise HTTPException(401, "Read authorization required")

    def require_write(x_api_key: Annotated[str | None, Header()] = None):
        if mode == "secured" and not hmac.compare_digest(x_api_key or "", write_key):
            raise HTTPException(401, "Write authorization required")

    def current_run(run_id=None):
        if run_id:
            found = store.query("SELECT payload FROM runs WHERE id=?", (run_id,))
            result = json.loads(found[0]["payload"]) if found else None
        else:
            result = store.latest_run()
        if not result:
            raise HTTPException(404, "No analysis found. Import data and run analysis.")
        result.setdefault("contractors", [])
        return result

    def cached(key, fingerprint):
        if not key or len(key) > 160:
            raise HTTPException(400, "A nonempty Idempotency-Key of at most 160 characters is required")
        row = store.query("SELECT fingerprint,response FROM idempotency WHERE key=?", (key,))
        if row:
            if row[0]["fingerprint"] != fingerprint:
                raise HTTPException(409, "Idempotency key already used for different input")
            return json.loads(row[0]["response"])
        return None

    def cache(key, fingerprint, response):
        with store.connect() as conn:
            conn.execute("INSERT INTO idempotency VALUES (?,?,?)", (key, fingerprint, json.dumps(response)))

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/ready", tags=["system"])
    def ready():
        if not app.state.ready:
            raise HTTPException(503, "Startup in progress")
        store.query("SELECT 1")
        return {"status": "ready"}

    @app.get("/api/v1/meta", dependencies=[Depends(require_read)], tags=["read"])
    def meta():
        return {
            "mode": mode,
            "ai_runtime": os.getenv("AI_RUNTIME", "none"),
            "data_version": store.version(),
            "upload_max_bytes": MAX_UPLOAD,
            "weekly_jobs": os.getenv("WEEKLY_JOBS", "true") == "true",
        }

    @app.get(
        "/api/v1/overview",
        response_model=OverviewResponse,
        dependencies=[Depends(require_read)],
        tags=["read"],
    )
    def overview():
        r = current_run()
        return {
            k: r[k]
            for k in (
                "id",
                "as_of",
                "created_at",
                "dataset_version",
                "algorithm_version",
                "parameters",
                "summary",
                "markets",
                "contractors",
                "trend",
            )
        } | {"stale_analysis": r["dataset_version"] != store.version()}

    @app.get("/api/v1/{collection}", response_model=Page, dependencies=[Depends(require_read)], tags=["read"])
    def collection(
        collection: str,
        q: str = Query("", max_length=100),
        market: str = "",
        kind: str = "",
        severity: str = "",
        limit: int = Query(50, ge=1, le=250),
        offset: int = Query(0, ge=0),
        run_id: str | None = None,
    ):
        if collection == "batches":
            items = [
                json.loads(r["report"])
                for r in store.query("SELECT report FROM batches ORDER BY created_at DESC")
            ]
        elif collection == "runs":
            items = store.query("SELECT id,created_at,as_of FROM runs ORDER BY created_at DESC")
        elif collection in {"positions", "alerts", "transfers", "contractors"}:
            items = current_run(run_id)[collection]
        else:
            raise HTTPException(404, "Unknown collection")
        if market:
            items = [p for p in items if p.get("market") == market]
        if kind:
            items = [p for p in items if p.get("kind") == kind]
        if severity:
            items = [p for p in items if p.get("severity") == severity]
        if q:
            items = [p for p in items if q.casefold() in json.dumps(p, ensure_ascii=False).casefold()]
        return {
            "items": items[offset : offset + limit],
            "total": len(items),
            "limit": limit,
            "offset": offset,
        }

    @app.get(
        "/api/v1/evidence/{location_id}/{sku}",
        response_model=EvidenceResponse,
        dependencies=[Depends(require_read)],
        tags=["read"],
    )
    def evidence(
        location_id: str,
        sku: str,
        limit: int = Query(50, ge=1, le=250),
        offset: int = Query(0, ge=0),
        run_id: str | None = None,
    ):
        r = current_run(run_id)
        p = next((p for p in r["positions"] if p["location_id"] == location_id and p["sku"] == sku), None)
        if not p:
            raise HTTPException(404, "Position not found in this analysis")
        args = (location_id, sku, p["opening_day"], p["snapshot_day"])
        entries = store.query(
            "SELECT r.body,l.delta FROM legs l JOIN records r ON l.movement_id=r.id WHERE l.location_id=? AND l.sku=? AND l.day>? AND l.day<=? ORDER BY l.day DESC,r.id LIMIT ? OFFSET ?",
            (*args, limit, offset),
        )
        snaps = store.query("SELECT body FROM records WHERE id IN (?,?)", (p["opening_id"], p["snapshot_id"]))
        return {
            "run_id": r["id"],
            "position": p,
            "snapshots": [json.loads(x["body"]) for x in snaps],
            "movements": [{**json.loads(x["body"]), "signed_delta": x["delta"]} for x in entries],
            "total": p["movement_count"],
            "offset": offset,
            "limit": limit,
            "alerts": [a for a in r["alerts"] if a["location_id"] == location_id and a["sku"] == sku],
        }

    @app.get("/api/v1/export/exceptions.csv", dependencies=[Depends(require_read)], tags=["read"])
    def export(market: str = "", kind: str = "", severity: str = "", q: str = "", run_id: str | None = None):
        alerts = current_run(run_id)["alerts"]
        fields = [
            "id",
            "severity",
            "kind",
            "location_name",
            "market",
            "sku",
            "material_name",
            "variance",
            "days_of_supply",
            "detail",
        ]
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for a in alerts:
            if (
                (market and a["market"] != market)
                or (kind and a["kind"] != kind)
                or (severity and a["severity"] != severity)
                or (q and q.casefold() not in json.dumps(a).casefold())
            ):
                continue
            writer.writerow(
                {
                    k: "'" + v
                    if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@", "\t", "\r"))
                    else v
                    for k, v in a.items()
                }
            )
        return Response(
            out.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="consignai-exceptions.csv"'},
        )

    @app.post(
        "/api/v1/commands/analyze",
        response_model=AnalysisResponse,
        dependencies=[Depends(require_write)],
        tags=["commands"],
    )
    def analyze(payload: AnalysisRequest, idempotency_key: Annotated[str | None, Header()] = None):
        fingerprint = "analyze:" + payload.model_dump_json()
        with store.lock:
            prior = cached(idempotency_key, fingerprint)
            if prior:
                return prior
            try:
                r = run_analysis(store, payload.as_of)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            response = {"id": r["id"], "as_of": r["as_of"], "summary": r["summary"]}
            cache(idempotency_key, fingerprint, response)
            return response

    @app.post(
        "/api/v1/commands/import",
        response_model=ImportReport,
        dependencies=[Depends(require_write)],
        tags=["commands"],
    )
    async def import_file(
        file: Annotated[UploadFile, File()], idempotency_key: Annotated[str | None, Header()] = None
    ):
        filename = file.filename or "upload"
        if Path(filename).suffix.lower() not in {".jsonl", ".ndjson", ".csv"}:
            raise HTTPException(415, "Use .jsonl, .ndjson or .csv")
        if file.content_type not in {
            "application/json",
            "application/x-ndjson",
            "text/plain",
            "text/csv",
            "application/octet-stream",
            "application/vnd.ms-excel",
        }:
            raise HTTPException(415, "Unsupported MIME type")
        data = await file.read(MAX_UPLOAD + 1)
        await file.close()
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "Upload exceeds 20 MiB")
        fingerprint = "import:" + Path(filename).suffix.lower() + ":" + hashlib.sha256(data).hexdigest()

        def execute():
            with store.lock:
                prior = cached(idempotency_key, fingerprint)
                if prior:
                    return prior
                try:
                    response = ingest(store, decode_upload(data, filename), filename)
                except (UnicodeDecodeError, ValueError, csv.Error) as exc:
                    raise HTTPException(422, "Malformed UTF-8 or CSV payload") from exc
                cache(idempotency_key, fingerprint, response)
                return response

        return await run_in_threadpool(execute)

    @app.post(
        "/api/v1/commands/explain/{alert_id:path}",
        response_model=NarrativeResponse,
        dependencies=[Depends(require_write)],
        tags=["commands"],
    )
    def explain_alert(alert_id: str, request: Request, run_id: str | None = None):
        r = current_run(run_id)
        a = next((a for a in r["alerts"] if a["id"] == alert_id), None)
        if not a:
            raise HTTPException(404, "Alert not found")
        records = []
        for rid in a["evidence_ids"]:
            rows = store.query("SELECT body FROM records WHERE id=?", (rid,))
            records.extend(json.loads(row["body"]) for row in rows)
        runtime = None
        if os.getenv("AI_RUNTIME", "none") == "ollama":
            runtime = OllamaRuntime(
                os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
                os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
            )
        result = explain(a, records, runtime, request.state.trace_id)
        result["telemetry"].update({"data_version": r["dataset_version"], "run_id": r["id"]})
        with store.connect() as conn:
            conn.execute(
                "INSERT INTO telemetry(created_at,payload) VALUES (?,?)",
                (now(), json.dumps(result["telemetry"])),
            )
        return result

    return app


app = create_app()
