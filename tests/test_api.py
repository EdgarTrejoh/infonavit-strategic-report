from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import api.main as api_main


def _client():
    return TestClient(api_main.app)


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


def _assert_no_sensitive_error_details(text):
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


def test_db_health_does_not_expose_credentials(monkeypatch):
    monkeypatch.setattr(
        api_main,
        "health_check",
        lambda: (False, "postgresql://user:password@example.com/db"),
    )

    response = _client().get("/db/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["database"] == "unavailable"
    assert "DATABASE_URL" not in str(payload)
    assert "password" not in str(payload)
    assert "example.com" not in str(payload)


def test_mini_report_json_returns_expected_structure(monkeypatch):
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json?current_year=2026&previous_year=2025")

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


def test_mini_report_markdown_returns_plain_text(monkeypatch):
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/markdown")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.headers["content-type"].startswith("text/plain")
    assert "Mini reporte ejecutivo INFONAVIT" in response.text
    assert "Resumen YTD comparable" in response.text
    assert "Nota metodológica" in response.text


def test_mini_report_json_does_not_save_files(monkeypatch, tmp_path):
    _patch_report_flow(monkeypatch)
    output_dir = Path("outputs/mini_report")
    before = set(output_dir.glob("*")) if output_dir.exists() else set()

    response = _client().get("/mini-report/json")

    after = set(output_dir.glob("*")) if output_dir.exists() else set()
    assert response.status_code == 200
    assert after == before


def test_mini_report_json_rejects_month_limit_above_range(monkeypatch):
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json?month_limit=13")

    assert response.status_code == 422


def test_mini_report_json_rejects_month_limit_below_range(monkeypatch):
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json?month_limit=0")

    assert response.status_code == 422


def test_mini_report_json_rejects_current_year_out_of_range(monkeypatch):
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json?current_year=1999")

    assert response.status_code == 422


def test_mini_report_json_rejects_previous_year_greater_than_current_year(monkeypatch):
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json?current_year=2025&previous_year=2026")

    assert response.status_code == 422
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_json_rejects_start_year_greater_than_end_year(monkeypatch):
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/json?start_year=2026&end_year=2025")

    assert response.status_code == 422
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_markdown_applies_same_year_validation(monkeypatch):
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/markdown?current_year=2025&previous_year=2026")

    assert response.status_code == 422
    _assert_no_sensitive_error_details(response.text)


def test_mini_report_markdown_rejects_invalid_month_limit(monkeypatch):
    _patch_report_flow(monkeypatch)

    response = _client().get("/mini-report/markdown?month_limit=13")

    assert response.status_code == 422
    _assert_no_sensitive_error_details(response.text)
