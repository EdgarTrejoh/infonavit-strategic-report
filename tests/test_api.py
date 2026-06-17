import importlib
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import api.main as api_main

TEST_API_KEY = "test-api-key"


def _client():
    return TestClient(api_main.app)


def _auth_headers():
    return {"X-API-Key": TEST_API_KEY}


def _configure_api_key(monkeypatch):
    monkeypatch.setenv("INFONAVIT_API_KEY", TEST_API_KEY)


def _fake_df_master():
    return pd.DataFrame(
        {
            "fecha": [pd.Timestamp("2026-01-01")],
            "linea": ["L2 Nueva"],
            "producto": ["Producto A"],
            "nombre_estado": ["Nuevo León"],
            "Monto": [120.0],
        }
    )


def _fake_report():
    return {
        "title": "Mini reporte ejecutivo INFONAVIT",
        "period": {
            "current_year": 2026,
            "previous_year": 2025,
            "month_limit": 4,
            "comparability": "YTD comparable",
        },
        "sections": [
            {"id": "summary_ytd", "title": "Resumen YTD comparable", "data": {}},
            {"id": "drivers", "title": "Principales impulsores", "data": {}},
            {"id": "pareto_lineas", "title": "Concentración por línea", "data": []},
            {"id": "ranking_estatal", "title": "Ranking estatal", "data": []},
            {"id": "methodology", "title": "Nota metodológica", "data": []},
        ],
        "warnings": [],
    }


def _fake_markdown():
    return "\n".join(
        [
            "# Mini reporte ejecutivo INFONAVIT",
            "## 1. Resumen YTD comparable",
            "## 2. Principales impulsores",
            "## 3. Concentración por línea",
            "## 4. Ranking estatal",
            "## 5. Nota metodológica",
        ]
    )


def _fake_extended_report():
    return {
        "title": "Reporte ejecutivo INFONAVIT extendido",
        "period": {
            "current_year": 2026,
            "previous_year": 2025,
            "month_limit": 4,
            "comparability": "YTD comparable",
        },
        "summary": {
            "monto_actual": 120.0,
            "monto_previo": 100.0,
            "creditos_actual": 12.0,
            "creditos_previo": 10.0,
            "ticket_promedio_actual": 10.0,
            "ticket_promedio_previo": 10.0,
        },
        "drivers": {},
        "rankings": {},
        "methodology": {"notes": [], "warnings": []},
        "future_crosses": {"inflacion_inpc": "pendiente"},
    }


def _fake_extended_markdown():
    return "\n".join(
        [
            "# Reporte ejecutivo INFONAVIT extendido",
            "## 1. Resumen ejecutivo",
            "Monto colocado y numero de creditos formalizados.",
            "Ticket promedio.",
            "## 5. Nota metodologica",
        ]
    )


def _fake_ai_insight():
    return {
        "available": True,
        "executive_thesis": "Tesis ejecutiva.",
        "key_findings": ["Hallazgo uno", "Hallazgo dos", "Hallazgo tres"],
        "state_level_reading": "Lectura estatal descriptiva.",
        "mix_effect_reading": "Lectura de efecto mezcla.",
        "real_vs_nominal_reading": "Lectura real contra nominal.",
        "risks_or_caveats": ["Riesgo uno", "Riesgo dos"],
        "recommended_next_crosses": ["Índice SHF de Precios de la Vivienda", "salario minimo", "IMSS derechohabientes"],
        "analytical_questions": ["Pregunta uno?", "Pregunta dos?", "Pregunta tres?"],
        "linkedin_angle": "Angulo breve.",
        "confidence": "medium",
    }


def _patch_report_flow(monkeypatch):
    monkeypatch.setattr(api_main, "engine", object())
    monkeypatch.setattr(api_main, "load_df_master_from_db", lambda engine, start_year=None, end_year=None: _fake_df_master())
    monkeypatch.setattr(api_main, "validate_df_master_contract", lambda df: None)
    monkeypatch.setattr(
        api_main,
        "build_ai_context",
        lambda df, current_year, previous_year, month_limit=None: {"periodo": {"current_year": current_year}},
    )
    monkeypatch.setattr(
        api_main,
        "generate_mini_report",
        lambda ai_context, output_dir=None: (_fake_report(), _fake_markdown()),
    )


def _patch_extended_report_flow(monkeypatch):
    monkeypatch.setattr(api_main, "engine", object())
    monkeypatch.setattr(api_main, "load_long_metrics_from_db", lambda engine, start_year=None, end_year=None: _fake_df_master())
    monkeypatch.setattr(
        api_main,
        "build_extended_context",
        lambda df, current_year, previous_year, month_limit=None: {"period": {"current_year": current_year}},
    )
    monkeypatch.setattr(api_main, "fetch_average_period_inflation", lambda **kwargs: None)
    monkeypatch.setattr(api_main, "add_inflation_context", lambda context, inflation_data: context)
    monkeypatch.setattr(
        api_main,
        "generate_extended_report",
        lambda context, output_dir=None: (_fake_extended_report(), _fake_extended_markdown()),
    )


def _assert_no_sensitive_error_details(text):
    assert "INFONAVIT_API_KEY" not in text
    assert "DATABASE_URL" not in text
    assert "DB_PASSWORD" not in text
    assert "password" not in text
    assert "psycopg2" not in text
    assert "SQLAlchemy" not in text
    assert "Traceback" not in text
    assert "connection string" not in text.lower()


def test_health_returns_ok():
    response = _client().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "infonavit-strategic-report-api"}
    assert response.headers["X-Request-ID"]


def test_fastapi_docs_are_available_outside_production(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    reloaded = importlib.reload(api_main)

    response = TestClient(reloaded.app).get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "INFONAVIT Strategic Report API"


def test_fastapi_docs_are_disabled_in_production(monkeypatch):
    try:
        monkeypatch.setenv("ENVIRONMENT", "production")
        reloaded = importlib.reload(api_main)

        client = TestClient(reloaded.app)
        docs_response = client.get("/docs")
        openapi_response = client.get("/openapi.json")

        assert docs_response.status_code == 404
        assert openapi_response.status_code == 404
    finally:
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        importlib.reload(api_main)


def test_db_health_does_not_expose_credentials(monkeypatch):
    _configure_api_key(monkeypatch)
    monkeypatch.setattr(
        api_main,
        "health_check",
        lambda: (False, "postgresql://user:password@example.com/db"),
    )

    response = _client().get("/db/health", headers=_auth_headers())

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["database"] == "unavailable"
    assert "DATABASE_URL" not in str(payload)
    assert "password" not in str(payload)
    assert "example.com" not in str(payload)


def test_db_health_rejects_request_without_api_key(monkeypatch):
    _configure_api_key(monkeypatch)

    response = _client().get("/db/health")

    assert response.status_code == 401
    _assert_no_sensitive_error_details(response.text)


def test_db_health_returns_ok_with_api_key(monkeypatch):
    _configure_api_key(monkeypatch)
    monkeypatch.setattr(api_main, "health_check", lambda: (True, "Conexion PostgreSQL disponible."))

    response = _client().get("/db/health", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "available"}


def test_db_metrics_diagnostics_rejects_request_without_api_key(monkeypatch):
    _configure_api_key(monkeypatch)

    response = _client().get("/diagnostics/db-metrics")

    assert response.status_code == 401
    _assert_no_sensitive_error_details(response.text)


def test_db_metrics_diagnostics_returns_counts_with_api_key(monkeypatch):
    _configure_api_key(monkeypatch)
    monkeypatch.setattr(api_main, "engine", object())
    monkeypatch.setattr(
        api_main,
        "get_db_metrics_diagnostics",
        lambda engine, start_year=None, end_year=None: {
            "table": "infonavit_historico",
            "filters": {"start_year": start_year, "end_year": end_year},
            "rows_total": 4,
            "years": [{"anio": 2025, "filas": 2}, {"anio": 2026, "filas": 2}],
            "metrics": [{"metrica": "Monto de credito Infonavit", "filas": 2}],
            "expected_metrics": [{"canonical": "Monto de credito Infonavit", "present": True}],
        },
    )

    response = _client().get(
        "/diagnostics/db-metrics?start_year=2025&end_year=2026",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["table"] == "infonavit_historico"
    assert payload["filters"] == {"start_year": 2025, "end_year": 2026}
    assert payload["rows_total"] == 4
    assert "DATABASE_URL" not in response.text
    assert "password" not in response.text


def test_db_metrics_diagnostics_rejects_invalid_year_range(monkeypatch):
    _configure_api_key(monkeypatch)

    response = _client().get(
        "/diagnostics/db-metrics?start_year=2026&end_year=2025",
        headers=_auth_headers(),
    )

    assert response.status_code == 422
    _assert_no_sensitive_error_details(response.text)


def test_protected_endpoint_fails_if_server_api_key_is_not_configured(monkeypatch):
    monkeypatch.delenv("INFONAVIT_API_KEY", raising=False)

    response = _client().get("/mini-report/json", headers=_auth_headers())

    assert response.status_code == 503
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_json_returns_expected_structure(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json?current_year=2026&previous_year=2025", headers=_auth_headers())

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    payload = response.json()
    assert payload["title"] == "Mini reporte ejecutivo INFONAVIT"
    assert [section["id"] for section in payload["sections"]] == [
        "summary_ytd",
        "drivers",
        "pareto_lineas",
        "ranking_estatal",
        "methodology",
    ]


def test_mini_report_json_rejects_request_without_api_key(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json")

    assert response.status_code == 401
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_markdown_rejects_request_without_api_key(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/markdown")

    assert response.status_code == 401
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_json_rejects_invalid_api_key(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json", headers={"X-API-Key": "wrong"})

    assert response.status_code == 401
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_markdown_rejects_invalid_api_key(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/markdown", headers={"X-API-Key": "wrong"})

    assert response.status_code == 401
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_extended_json_rejects_request_without_api_key(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_extended_report_flow(monkeypatch)

    response = _client().get("/mini-report/extended/json")

    assert response.status_code == 401
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_extended_json_returns_expected_structure(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_extended_report_flow(monkeypatch)

    response = _client().get("/mini-report/extended/json", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Reporte ejecutivo INFONAVIT extendido"
    assert "summary" in payload
    assert "future_crosses" in payload


def test_mini_report_extended_markdown_returns_plain_text(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_extended_report_flow(monkeypatch)

    response = _client().get("/mini-report/extended/markdown", headers=_auth_headers())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "Reporte ejecutivo INFONAVIT extendido" in response.text
    assert "Ticket promedio" in response.text


def test_mini_report_ai_json_rejects_request_without_api_key(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_extended_report_flow(monkeypatch)

    response = _client().get("/mini-report/ai/json")

    assert response.status_code == 401
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_ai_markdown_rejects_request_without_api_key(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_extended_report_flow(monkeypatch)

    response = _client().get("/mini-report/ai/markdown")

    assert response.status_code == 401
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_ai_json_returns_ai_insight_with_mock(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_extended_report_flow(monkeypatch)
    monkeypatch.setattr(api_main, "generate_ai_extended_insight", lambda extended_report: _fake_ai_insight())

    response = _client().get("/mini-report/ai/json", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert "period" in payload
    assert "extended_report_summary" in payload
    assert payload["ai_insight"]["available"] is True
    assert payload["ai_insight"]["confidence"] == "medium"


def test_mini_report_ai_markdown_renders_expected_sections(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_extended_report_flow(monkeypatch)
    monkeypatch.setattr(api_main, "generate_ai_extended_insight", lambda extended_report: _fake_ai_insight())

    response = _client().get("/mini-report/ai/markdown", headers=_auth_headers())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "Análisis asistido INFONAVIT" in response.text
    assert "Tesis ejecutiva" in response.text
    assert "Hallazgos clave" in response.text
    assert "Lectura estatal" in response.text
    assert "Preguntas para siguiente análisis" in response.text
    assert "Preguntas para comite" not in response.text


def test_mini_report_extended_json_uses_inflation_context_when_available(monkeypatch):
    _configure_api_key(monkeypatch)
    monkeypatch.setattr(api_main, "engine", object())
    monkeypatch.setattr(api_main, "load_long_metrics_from_db", lambda engine, start_year=None, end_year=None: _fake_df_master())
    monkeypatch.setattr(
        api_main,
        "build_extended_context",
        lambda df, current_year, previous_year, month_limit=None: {
            "period": {"current_year": current_year, "previous_year": previous_year, "month_limit": 4},
            "summary": {"monto_variacion_pct": 20.0, "ticket_promedio_variacion_pct": -5.0},
        },
    )
    monkeypatch.setattr(
        api_main,
        "fetch_average_period_inflation",
        lambda current_year, previous_year, month_limit: {"factor": 1.04},
    )

    def fake_add_inflation_context(context, inflation_data):
        context["inflation_context"] = {"available": True, "factor": inflation_data["factor"]}
        return context

    monkeypatch.setattr(api_main, "add_inflation_context", fake_add_inflation_context)
    monkeypatch.setattr(api_main, "generate_extended_report", lambda context, output_dir=None: (context, "markdown"))

    response = _client().get("/mini-report/extended/json", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["inflation_context"] == {"available": True, "factor": 1.04}


def test_mini_report_markdown_returns_plain_text(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/markdown", headers=_auth_headers())

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.headers["content-type"].startswith("text/plain")
    assert "Mini reporte ejecutivo INFONAVIT" in response.text
    assert "Resumen YTD comparable" in response.text
    assert "Nota metodológica" in response.text


def test_mini_report_json_does_not_save_files(monkeypatch, tmp_path):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)
    output_dir = Path("outputs/mini_report")
    before = set(output_dir.glob("*")) if output_dir.exists() else set()

    response = _client().get("/mini-report/json", headers=_auth_headers())

    after = set(output_dir.glob("*")) if output_dir.exists() else set()
    assert response.status_code == 200
    assert after == before


def test_mini_report_json_rejects_month_limit_above_range(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json?month_limit=13", headers=_auth_headers())

    assert response.status_code == 422


def test_mini_report_json_rejects_month_limit_below_range(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json?month_limit=0", headers=_auth_headers())

    assert response.status_code == 422


def test_mini_report_json_rejects_current_year_out_of_range(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json?current_year=1999", headers=_auth_headers())

    assert response.status_code == 422


def test_mini_report_json_rejects_previous_year_greater_than_current_year(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get(
        "/mini-report/json?current_year=2025&previous_year=2026",
        headers=_auth_headers(),
    )

    assert response.status_code == 422
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_json_rejects_start_year_greater_than_end_year(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json?start_year=2026&end_year=2025", headers=_auth_headers())

    assert response.status_code == 422
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_markdown_applies_same_year_validation(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get(
        "/mini-report/markdown?current_year=2025&previous_year=2026",
        headers=_auth_headers(),
    )

    assert response.status_code == 422
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_markdown_rejects_invalid_month_limit(monkeypatch):
    _configure_api_key(monkeypatch)
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/markdown?month_limit=13", headers=_auth_headers())

    assert response.status_code == 422
    _assert_no_sensitive_error_details(response.text)
