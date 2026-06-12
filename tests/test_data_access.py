import json

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from data_access import (
    DF_MASTER_COLUMNS,
    METRICA_CREDITOS,
    METRICA_MONTO,
    build_df_master_from_long_table,
    load_df_master_from_db,
    load_long_metrics_from_db,
    validate_df_master_contract,
)
from report_metrics import build_ai_context


def _long_table_df():
    return pd.DataFrame(
        [
            {
                "anio": 2025.0,
                "mes": 1.0,
                "estado": 1.0,
                "linea": "L2 Nueva",
                "producto": "Producto A",
                "metrica": "Monto de crédito Infonavit",
                "valor": 100.0,
            },
            {
                "anio": 2025,
                "mes": 1,
                "estado": 1,
                "linea": "L2 Nueva",
                "producto": "Producto A",
                "metrica": "Número de créditos formalizados",
                "valor": 3.0,
            },
            {
                "anio": 2026.0,
                "mes": 1.0,
                "estado": 9.0,
                "linea": "L4 Mejoras",
                "producto": "Producto B",
                "metrica": "Monto de crédito Infonavit",
                "valor": 120.0,
            },
        ]
    )


def test_build_df_master_filters_only_monto_metric():
    df_master = build_df_master_from_long_table(_long_table_df())

    assert len(df_master) == 2
    assert df_master["Monto"].sum() == pytest.approx(220)


def test_build_df_master_builds_fecha_with_first_day_and_casts_numeric_fields():
    df_master = build_df_master_from_long_table(_long_table_df())

    assert df_master.loc[0, "fecha"] == pd.Timestamp("2025-01-01")
    assert df_master.loc[1, "fecha"] == pd.Timestamp("2026-01-01")


def test_build_df_master_maps_estado_to_nombre_estado():
    df_master = build_df_master_from_long_table(_long_table_df())

    assert df_master.loc[0, "nombre_estado"] == "Aguascalientes"
    assert df_master.loc[1, "nombre_estado"] == "Ciudad de México"


def test_build_df_master_returns_exact_expected_columns():
    df_master = build_df_master_from_long_table(_long_table_df())

    assert list(df_master.columns) == DF_MASTER_COLUMNS


def test_validate_df_master_contract_fails_when_required_column_is_missing():
    df_master = build_df_master_from_long_table(_long_table_df()).drop(columns=["Monto"])

    with pytest.raises(ValueError, match="Faltan columnas"):
        validate_df_master_contract(df_master)


def test_validate_df_master_contract_fails_when_monto_is_not_numeric():
    df_master = build_df_master_from_long_table(_long_table_df())
    df_master["Monto"] = df_master["Monto"].astype(str)

    with pytest.raises(ValueError, match="Monto"):
        validate_df_master_contract(df_master)


def test_generated_df_master_feeds_report_metrics_ai_context_and_json_serializes():
    df_master = build_df_master_from_long_table(_long_table_df())

    context = build_ai_context(df_master, current_year=2026, previous_year=2025)

    assert context["periodo"]["current_year"] == 2026
    assert context["summary"]["monto_actual"] == pytest.approx(120)
    assert context["summary"]["monto_previo"] == pytest.approx(100)
    json.dumps(context)


def test_load_df_master_from_db_uses_sqlalchemy_connection_and_year_filters():
    engine = create_engine("sqlite:///:memory:")
    rows = [
        (2024, 1, 1, "L2 Nueva", "Producto A", METRICA_MONTO, 50.0),
        (2025, 1, 1, "L2 Nueva", "Producto A", METRICA_MONTO, 100.0),
        (2026, 1, 9, "L4 Mejoras", "Producto B", METRICA_MONTO, 120.0),
        (2026, 1, 9, "L4 Mejoras", "Producto B", METRICA_CREDITOS, 3.0),
    ]
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE infonavit_historico (
                    anio INTEGER,
                    mes INTEGER,
                    estado INTEGER,
                    linea TEXT,
                    producto TEXT,
                    metrica TEXT,
                    valor REAL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO infonavit_historico
                    (anio, mes, estado, linea, producto, metrica, valor)
                VALUES
                    (:anio, :mes, :estado, :linea, :producto, :metrica, :valor)
                """
            ),
            [
                {
                    "anio": anio,
                    "mes": mes,
                    "estado": estado,
                    "linea": linea,
                    "producto": producto,
                    "metrica": metrica,
                    "valor": valor,
                }
                for anio, mes, estado, linea, producto, metrica, valor in rows
            ],
        )

    df_master = load_df_master_from_db(engine, start_year=2025, end_year=2026)

    assert list(df_master.columns) == DF_MASTER_COLUMNS
    assert len(df_master) == 2
    assert df_master["fecha"].min() == pd.Timestamp("2025-01-01")
    assert df_master["fecha"].max() == pd.Timestamp("2026-01-01")
    assert df_master["Monto"].sum() == pytest.approx(220)

    context = build_ai_context(df_master, current_year=2026, previous_year=2025)
    json.dumps(context)


def test_load_long_metrics_from_db_reads_monto_and_creditos_with_year_filters():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE infonavit_historico (
                    anio INTEGER,
                    mes INTEGER,
                    estado INTEGER,
                    linea TEXT,
                    producto TEXT,
                    metrica TEXT,
                    valor REAL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO infonavit_historico
                    (anio, mes, estado, linea, producto, metrica, valor)
                VALUES
                    (:anio, :mes, :estado, :linea, :producto, :metrica, :valor)
                """
            ),
            [
                {
                    "anio": 2024,
                    "mes": 1,
                    "estado": 1,
                    "linea": "L2 Nueva",
                    "producto": "Producto A",
                    "metrica": METRICA_MONTO,
                    "valor": 50.0,
                },
                {
                    "anio": 2025,
                    "mes": 1,
                    "estado": 1,
                    "linea": "L2 Nueva",
                    "producto": "Producto A",
                    "metrica": METRICA_MONTO,
                    "valor": 100.0,
                },
                {
                    "anio": 2025,
                    "mes": 1,
                    "estado": 1,
                    "linea": "L2 Nueva",
                    "producto": "Producto A",
                    "metrica": METRICA_CREDITOS,
                    "valor": 10.0,
                },
            ],
        )

    df = load_long_metrics_from_db(engine, start_year=2025, end_year=2025)

    assert set(df["anio"]) == {2025}
    assert set(df["metrica"]) == {METRICA_MONTO, METRICA_CREDITOS}
    assert len(df) == 2
