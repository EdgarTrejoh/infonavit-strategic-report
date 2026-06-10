import json
import math

import pandas as pd
import pytest

from report_metrics import (
    build_ai_context,
    compute_mix_producto_linea,
    compute_pareto_lineas,
    compute_ranking_estatal,
    compute_yoy_comparable,
    compute_ytd_acumulado,
)


def _synthetic_df():
    rows = []
    for year, monthly_amounts in {
        2025: [25, 25, 25, 25] + [10] * 8,
        2026: [30, 30, 30, 30],
    }.items():
        for month, amount in enumerate(monthly_amounts, start=1):
            rows.append(
                {
                    "fecha": pd.Timestamp(year=year, month=month, day=1),
                    "linea": "L2 Nueva",
                    "producto": "Producto A",
                    "nombre_estado": "Estado A",
                    "Monto": amount * 0.7,
                }
            )
            rows.append(
                {
                    "fecha": pd.Timestamp(year=year, month=month, day=1),
                    "linea": "L4 Mejoras",
                    "producto": "Producto B",
                    "nombre_estado": "Estado B",
                    "Monto": amount * 0.3,
                }
            )
    return pd.DataFrame(rows)


def _contains_non_finite(value):
    if isinstance(value, dict):
        return any(_contains_non_finite(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_non_finite(item) for item in value)
    return isinstance(value, float) and (math.isnan(value) or math.isinf(value))


def test_ytd_acumulado_uses_comparable_months():
    result = compute_ytd_acumulado(_synthetic_df(), current_year=2026, previous_year=2025)

    assert result["monto_actual"] == pytest.approx(120)
    assert result["monto_previo"] == pytest.approx(100)
    assert result["diferencia_abs"] == pytest.approx(20)
    assert result["variacion_pct"] == pytest.approx(20)
    assert result["month_limit"] == 4
    assert result["meses_usados"] == [1, 2, 3, 4]


def test_yoy_comparable_does_not_compare_full_previous_year_against_partial_current_year():
    result = compute_yoy_comparable(_synthetic_df(), current_year=2026, previous_year=2025)

    assert result["monto_actual"] == pytest.approx(120)
    assert result["monto_previo"] == pytest.approx(100)
    assert result["monto_previo"] != pytest.approx(180)
    assert result["comparability"] == "YTD comparable"
    assert result["month_limit"] == 4


def test_mix_producto_linea_shares_sum_to_100_and_ranking_is_descending():
    result = compute_mix_producto_linea(_synthetic_df(), year=2026)

    assert sum(row["share"] for row in result) == pytest.approx(100)
    assert result[0]["linea"] == "L2 Nueva"
    assert result[0]["producto"] == "Producto A"
    assert result[0]["ranking"] == 1
    assert result[0]["monto"] > result[1]["monto"]


def test_pareto_lineas_orders_descending_and_computes_cumulative_share():
    result = compute_pareto_lineas(_synthetic_df(), year=2026)

    assert [row["linea"] for row in result] == ["L2 Nueva", "L4 Mejoras"]
    assert result[0]["share"] == pytest.approx(70)
    assert result[0]["share_acumulado"] == pytest.approx(70)
    assert result[1]["share_acumulado"] == pytest.approx(100)
    assert result[0]["concentracion_principal"] is True
    assert result[1]["concentracion_principal"] is True


def test_ranking_estatal_respects_top_n_and_identifies_leader():
    df = pd.concat(
        [
            _synthetic_df(),
            pd.DataFrame(
                [
                    {
                        "fecha": pd.Timestamp(year=2026, month=1, day=1),
                        "linea": "L5 Pasivos",
                        "producto": "Producto C",
                        "nombre_estado": "Estado C",
                        "Monto": 5,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    result = compute_ranking_estatal(df, year=2026, top_n=2)

    assert len(result) == 2
    assert result[0]["estado"] == "Estado A"
    assert result[0]["ranking"] == 1


def test_build_ai_context_is_json_ready_and_contains_expected_contract():
    context = build_ai_context(_synthetic_df(), current_year=2026, previous_year=2025)

    json.dumps(context)

    assert isinstance(context, dict)
    assert set(context).issuperset(
        {
            "periodo",
            "summary",
            "drivers",
            "pareto_lineas",
            "ranking_estatal",
            "warnings",
        }
    )
    assert context["periodo"]["month_limit"] == 4
    assert context["drivers"]["linea_lider"] == "L2 Nueva"
    assert context["drivers"]["producto_lider"] == "Producto A"
    assert context["drivers"]["estado_lider"] == "Estado A"
    assert not _contains_non_finite(context)
