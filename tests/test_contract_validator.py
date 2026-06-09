import pandas as pd

from contract_validator import (
    format_validation_messages,
    temporal_comparability_warnings,
    validate_consolidated_dataframe,
)


def _base_df():
    return pd.DataFrame(
        [
            {
                "id_reporte": "id-2025-01",
                "anio": 2025,
                "estado": 1,
                "mes": 1,
                "linea": "Linea II",
                "producto": "Producto A",
                "metrica": "Monto",
                "valor": 100.0,
            },
            {
                "id_reporte": "id-2026-01",
                "anio": 2026,
                "estado": 1,
                "mes": 1,
                "linea": "Linea II",
                "producto": "Producto A",
                "metrica": "Monto",
                "valor": 120.0,
            },
        ]
    )


def test_required_columns():
    df = _base_df().drop(columns=["valor"])

    result = validate_consolidated_dataframe(df)

    assert not result.ok
    assert any("Faltan columnas obligatorias" in error for error in result.errors)


def test_id_reporte_not_null():
    df = _base_df()
    df.loc[0, "id_reporte"] = None

    result = validate_consolidated_dataframe(df)

    assert not result.ok
    assert any("sin id_reporte" in error for error in result.errors)


def test_id_reporte_unique_can_be_error():
    df = _base_df()
    df.loc[1, "id_reporte"] = df.loc[0, "id_reporte"]

    result = validate_consolidated_dataframe(df, require_unique_id=True)

    assert not result.ok
    assert any("duplicado" in error for error in result.errors)


def test_mes_range():
    df = _base_df()
    df.loc[0, "mes"] = 13

    result = validate_consolidated_dataframe(df)

    assert not result.ok
    assert any("fuera de 1-12" in error for error in result.errors)


def test_required_years_must_exist():
    df = _base_df()

    result = validate_consolidated_dataframe(df, required_years=[2024, 2025, 2026])

    assert not result.ok
    assert any("2024" in error and "no existe" in error for error in result.errors)


def test_temporal_comparability_warning_for_partial_year():
    df = pd.concat(
        [
            _base_df(),
            pd.DataFrame(
                [
                    {
                        "id_reporte": f"id-2025-{mes:02d}",
                        "anio": 2025,
                        "estado": 1,
                        "mes": mes,
                        "linea": "Linea II",
                        "producto": "Producto A",
                        "metrica": "Monto",
                        "valor": 100.0,
                    }
                    for mes in range(2, 13)
                ]
            ),
        ],
        ignore_index=True,
    )

    warnings = temporal_comparability_warnings(df, current_year=2026, previous_year=2025)

    assert warnings
    assert "YTD comparable" in warnings[0]


def test_format_validation_messages_prefixes_levels():
    df = _base_df()
    df.loc[1, "id_reporte"] = df.loc[0, "id_reporte"]

    result = validate_consolidated_dataframe(df, require_unique_id=False)
    messages = format_validation_messages(result)

    assert result.ok
    assert any(message.startswith("ADVERTENCIA:") for message in messages)
