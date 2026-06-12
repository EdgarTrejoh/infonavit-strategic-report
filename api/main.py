from __future__ import annotations

import json
import logging
import os
import secrets
import time
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from data_access import load_df_master_from_db, validate_df_master_contract
from database import engine, health_check
from mini_report import generate_mini_report
from report_metrics import build_ai_context

logger = logging.getLogger(__name__)

SERVICE_NAME = "infonavit-strategic-report-api"
SAFE_DB_ERROR = "No se pudo conectar a PostgreSQL. Verifica host, puerto, base y credenciales."
SAFE_AUTH_ERROR = "API key requerida o invalida."
SAFE_AUTH_CONFIG_ERROR = "API key del servidor no configurada."
ENVIRONMENT = os.getenv("ENVIRONMENT", "local").lower()

app = FastAPI(
    title="INFONAVIT Strategic Report API",
    version="0.1.0",
    docs_url=None if ENVIRONMENT == "production" else "/docs",
    redoc_url=None if ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if ENVIRONMENT == "production" else "/openapi.json",
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started_at = time.perf_counter()

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "API request completed method=%s path=%s status_code=%s duration_ms=%s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected_api_key = os.getenv("INFONAVIT_API_KEY")
    if not expected_api_key:
        raise HTTPException(status_code=503, detail=SAFE_AUTH_CONFIG_ERROR)
    if not x_api_key or not secrets.compare_digest(x_api_key, expected_api_key):
        raise HTTPException(status_code=401, detail=SAFE_AUTH_ERROR)


@app.get("/db/health")
def database_health(_: None = Depends(require_api_key)):
    ok, message = health_check()
    if ok:
        return {"status": "ok", "database": "available"}
    return {
        "status": "error",
        "database": "unavailable",
        "message": SAFE_DB_ERROR if message else SAFE_DB_ERROR,
    }


def _validate_report_params(
    current_year: int,
    previous_year: int,
    start_year: int | None,
    end_year: int | None,
) -> None:
    if previous_year > current_year:
        raise HTTPException(status_code=422, detail="previous_year no debe ser mayor que current_year.")
    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(status_code=422, detail="start_year no debe ser mayor que end_year.")


def _build_report(
    current_year: int,
    previous_year: int,
    month_limit: int | None,
    start_year: int | None,
    end_year: int | None,
    request_id: str | None = None,
) -> tuple[dict, str]:
    if engine is None:
        raise HTTPException(status_code=503, detail=SAFE_DB_ERROR)

    try:
        total_start = time.perf_counter()
        db_start = time.perf_counter()
        df_master = load_df_master_from_db(engine, start_year=start_year, end_year=end_year)
        validate_df_master_contract(df_master)
        db_ms = round((time.perf_counter() - db_start) * 1000, 2)

        metrics_start = time.perf_counter()
        ai_context = build_ai_context(
            df_master,
            current_year=current_year,
            previous_year=previous_year,
            month_limit=month_limit,
        )
        metrics_ms = round((time.perf_counter() - metrics_start) * 1000, 2)

        render_start = time.perf_counter()
        report_json, markdown = generate_mini_report(ai_context, output_dir=None)
        json.dumps(report_json, ensure_ascii=False)
        render_ms = round((time.perf_counter() - render_start) * 1000, 2)
        total_ms = round((time.perf_counter() - total_start) * 1000, 2)
        logger.info(
            "mini_report_pipeline db_ms=%s metrics_ms=%s render_ms=%s total_ms=%s request_id=%s",
            db_ms,
            metrics_ms,
            render_ms,
            total_ms,
            request_id,
        )
        return report_json, markdown
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("No se pudo generar mini reporte: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="No se pudo generar el mini reporte.") from exc


@app.get("/mini-report/json")
def mini_report_json(
    request: Request,
    _: None = Depends(require_api_key),
    current_year: int = Query(2026, ge=2000, le=2100),
    previous_year: int = Query(2025, ge=2000, le=2100),
    month_limit: int | None = Query(None, ge=1, le=12),
    start_year: int | None = Query(None, ge=2000, le=2100),
    end_year: int | None = Query(None, ge=2000, le=2100),
):
    _validate_report_params(current_year, previous_year, start_year, end_year)
    report_json, _ = _build_report(
        current_year=current_year,
        previous_year=previous_year,
        month_limit=month_limit,
        start_year=start_year,
        end_year=end_year,
        request_id=getattr(request.state, "request_id", None),
    )
    return report_json


@app.get("/mini-report/markdown", response_class=PlainTextResponse)
def mini_report_markdown(
    request: Request,
    _: None = Depends(require_api_key),
    current_year: int = Query(2026, ge=2000, le=2100),
    previous_year: int = Query(2025, ge=2000, le=2100),
    month_limit: int | None = Query(None, ge=1, le=12),
    start_year: int | None = Query(None, ge=2000, le=2100),
    end_year: int | None = Query(None, ge=2000, le=2100),
):
    _validate_report_params(current_year, previous_year, start_year, end_year)
    _, markdown = _build_report(
        current_year=current_year,
        previous_year=previous_year,
        month_limit=month_limit,
        start_year=start_year,
        end_year=end_year,
        request_id=getattr(request.state, "request_id", None),
    )
    return markdown
