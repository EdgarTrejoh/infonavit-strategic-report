from __future__ import annotations

import json
import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

from data_access import load_df_master_from_db, validate_df_master_contract
from database import engine, health_check
from mini_report import generate_mini_report
from report_metrics import build_ai_context

logger = logging.getLogger(__name__)

SERVICE_NAME = "infonavit-strategic-report-api"
SAFE_DB_ERROR = "No se pudo conectar a PostgreSQL. Verifica host, puerto, base y credenciales."

app = FastAPI(title="INFONAVIT Strategic Report API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/db/health")
def database_health():
    ok, message = health_check()
    if ok:
        return {"status": "ok", "database": "available"}
    return {
        "status": "error",
        "database": "unavailable",
        "message": SAFE_DB_ERROR if message else SAFE_DB_ERROR,
    }


def _build_report(
    current_year: int,
    previous_year: int,
    month_limit: int | None,
    start_year: int | None,
    end_year: int | None,
) -> tuple[dict, str]:
    if engine is None:
        raise HTTPException(status_code=503, detail=SAFE_DB_ERROR)

    try:
        df_master = load_df_master_from_db(engine, start_year=start_year, end_year=end_year)
        validate_df_master_contract(df_master)
        ai_context = build_ai_context(
            df_master,
            current_year=current_year,
            previous_year=previous_year,
            month_limit=month_limit,
        )
        report_json, markdown = generate_mini_report(ai_context, output_dir=None)
        json.dumps(report_json, ensure_ascii=False)
        return report_json, markdown
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("No se pudo generar mini reporte: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="No se pudo generar el mini reporte.") from exc


@app.get("/mini-report/json")
def mini_report_json(
    current_year: int = Query(2026),
    previous_year: int = Query(2025),
    month_limit: int | None = Query(None, ge=1, le=12),
    start_year: int | None = Query(None),
    end_year: int | None = Query(None),
):
    report_json, _ = _build_report(
        current_year=current_year,
        previous_year=previous_year,
        month_limit=month_limit,
        start_year=start_year,
        end_year=end_year,
    )
    return report_json


@app.get("/mini-report/markdown", response_class=PlainTextResponse)
def mini_report_markdown(
    current_year: int = Query(2026),
    previous_year: int = Query(2025),
    month_limit: int | None = Query(None, ge=1, le=12),
    start_year: int | None = Query(None),
    end_year: int | None = Query(None),
):
    _, markdown = _build_report(
        current_year=current_year,
        previous_year=previous_year,
        month_limit=month_limit,
        start_year=start_year,
        end_year=end_year,
    )
    return markdown
