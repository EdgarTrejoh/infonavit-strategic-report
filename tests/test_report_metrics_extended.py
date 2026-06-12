import json

import pandas as pd
import pytest

from data_access import METRICA_CREDITOS, METRICA_MONTO
from mini_report_extended import generate_extended_report
from report_metrics_extended import build_extended_analytic_df, build_extended_context


def _long_metrics_df():
    rows = []
    for year, monto_total, creditos_total in [(2025, 100.0, 10.0), (2026, 120.0, 8.0)]:
        for month in range(1, 5):
            rows.extend(
                [
                    {
                        "anio": year,
                        "mes": month,
                        "estado": 1,
                        "linea": "L2 Nueva",
                        "producto": "Producto A",
                        "metrica": METRICA_MONTO,
                        "valor": monto_total / 4,
                    },
                    {
                        "anio": year,
                        "mes": month,
                        "estado": 1,
                        "linea": "L2 Nueva",
                        "producto": "Producto A",
                        "metrica": METRICA_CREDITOS,
                        "valor": creditos_total / 4,
                    },
                ]
            )
    rows.extend(
        [
            {
                "anio": 2026,
                "mes": 1,
                "estado": 9,
                "linea": "L4 Mejoras",
                "producto": "Producto B",
                "metrica": METRICA_MONTO,
                "valor": 20.0,
            },
            {
                "anio": 2026,
                "mes": 1,
                "estado": 9,
                "linea": "L4 Mejoras",
                "producto": "Producto B",
                "metrica": METRICA_CREDITOS,
                "valor": 2.0,
            },
        ]
    )
    return pd.DataFrame(rows)


def test_build_extended_analytic_df_calculates_ticket_promedio():
    analytic = build_extended_analytic_df(_long_metrics_df())

    current_first = analytic[(analytic["anio"] == 2026) & (analytic["mes"] == 1) & (analytic["linea"] == "L2 Nueva")]

    assert current_first["Monto"].iloc[0] == pytest.approx(30.0)
    assert current_first["Creditos"].iloc[0] == pytest.approx(2.0)
    assert current_first["Ticket_Promedio"].iloc[0] == pytest.approx(15.0)


def test_build_extended_context_calculates_ytd_monto_creditos_and_ticket_variations():
    context = build_extended_context(_long_metrics_df(), current_year=2026, previous_year=2025, month_limit=4)
    summary = context["summary"]

    assert summary["monto_actual"] == pytest.approx(140.0)
    assert summary["monto_previo"] == pytest.approx(100.0)
    assert summary["monto_variacion_pct"] == pytest.approx(40.0)
    assert summary["creditos_actual"] == pytest.approx(10.0)
    assert summary["creditos_previo"] == pytest.approx(10.0)
    assert summary["creditos_variacion_pct"] == pytest.approx(0.0)
    assert summary["ticket_promedio_actual"] == pytest.approx(14.0)
    assert summary["ticket_promedio_previo"] == pytest.approx(10.0)
    assert summary["ticket_promedio_variacion_pct"] == pytest.approx(40.0)


def test_build_extended_context_handles_zero_creditos_safely():
    df = _long_metrics_df()
    df.loc[(df["anio"] == 2026) & (df["metrica"] == METRICA_CREDITOS), "valor"] = 0.0

    context = build_extended_context(df, current_year=2026, previous_year=2025, month_limit=4)

    assert context["summary"]["ticket_promedio_actual"] is None
    assert context["summary"]["ticket_promedio_variacion_pct"] is None
    assert any("cero creditos" in warning for warning in context["methodology"]["warnings"])


def test_build_extended_context_warns_when_creditos_metric_is_missing():
    df = _long_metrics_df()
    df = df[df["metrica"] != METRICA_CREDITOS].copy()

    context = build_extended_context(df, current_year=2026, previous_year=2025, month_limit=4)

    assert context["summary"]["monto_actual"] > 0
    assert context["summary"]["creditos_actual"] is None
    assert context["summary"]["creditos_previo"] is None
    assert context["summary"]["ticket_promedio_actual"] is None
    assert context["rankings"]["estados_por_creditos"] == []
    assert any(METRICA_CREDITOS in warning for warning in context["methodology"]["warnings"])


def test_extended_report_json_serializes_and_markdown_contains_expected_terms():
    context = build_extended_context(_long_metrics_df(), current_year=2026, previous_year=2025, month_limit=4)

    report_json, markdown = generate_extended_report(context)

    json.dumps(report_json)
    assert report_json["title"] == "Reporte ejecutivo INFONAVIT extendido"
    assert "monto colocado" in markdown.lower() or "coloco" in markdown.lower()
    assert "creditos formalizados" in markdown.lower()
    assert "ticket promedio" in markdown.lower()
    assert "YTD comparable" in markdown
    assert "Nota metodologica" in markdown or "Nota metodológica" in markdown
    assert report_json["future_crosses"]["inflacion_inpc"] == "pendiente"


def test_extended_markdown_explains_credit_growth_with_ticket_decline():
    context = {
        "title": "Reporte ejecutivo INFONAVIT extendido",
        "period": {
            "current_year": 2026,
            "previous_year": 2025,
            "month_limit": 4,
            "comparability": "YTD comparable",
        },
        "summary": {
            "monto_actual": 81_244_735_597.05,
            "monto_previo": 70_081_745_285.25,
            "monto_variacion_pct": 15.93,
            "creditos_actual": 207_652.0,
            "creditos_previo": 157_102.0,
            "creditos_variacion_pct": 32.18,
            "ticket_promedio_actual": 391_254.29,
            "ticket_promedio_previo": 446_090.73,
            "ticket_promedio_variacion_pct": -12.29,
        },
        "drivers": {},
        "rankings": {},
        "methodology": {"notes": [], "warnings": ["Comparacion YTD: no compara anios completos."]},
        "future_crosses": {"inflacion_inpc": "pendiente"},
    }

    _, markdown = generate_extended_report(context)

    assert "El numero de creditos crecio, mientras que el ticket promedio disminuyo" in markdown
    assert "mayor volumen de creditos" in markdown
    assert "El numero de creditos crecio igual o mas rapido que el ticket promedio" not in markdown
