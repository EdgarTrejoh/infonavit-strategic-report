from __future__ import annotations

import pandas as pd
from sqlalchemy import text

import config

METRICA_MONTO = "Monto de crédito Infonavit"
DF_MASTER_COLUMNS = ["fecha", "linea", "producto", "nombre_estado", "Monto"]


def _estado_catalog() -> dict[int, str]:
    return {int(key): value for key, value in config.ESTADOS_MX.items()}


def build_df_master_from_long_table(df: pd.DataFrame) -> pd.DataFrame:
    required_columns = {"anio", "mes", "estado", "linea", "producto", "metrica", "valor"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas en tabla larga: {sorted(missing)}")

    data = df[df["metrica"] == METRICA_MONTO].copy()

    data["anio"] = pd.to_numeric(data["anio"], errors="coerce")
    data["mes"] = pd.to_numeric(data["mes"], errors="coerce")
    data["estado"] = pd.to_numeric(data["estado"], errors="coerce")
    data["Monto"] = pd.to_numeric(data["valor"], errors="coerce")
    data = data.dropna(subset=["anio", "mes", "estado", "Monto", "linea", "producto"]).copy()

    data["anio"] = data["anio"].astype(int)
    data["mes"] = data["mes"].astype(int)
    data["estado"] = data["estado"].astype(int)
    data["fecha"] = pd.to_datetime(
        dict(year=data["anio"], month=data["mes"], day=1),
        errors="coerce",
    )
    data["nombre_estado"] = data["estado"].map(_estado_catalog())

    df_master = data[DF_MASTER_COLUMNS].reset_index(drop=True).copy()
    validate_df_master_contract(df_master)
    return df_master


def validate_df_master_contract(df: pd.DataFrame) -> None:
    missing = set(DF_MASTER_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"df_master no cumple contrato. Faltan columnas: {sorted(missing)}")

    if df["fecha"].isna().any():
        raise ValueError("df_master no cumple contrato: 'fecha' contiene nulos.")
    if not pd.api.types.is_datetime64_any_dtype(df["fecha"]):
        raise ValueError("df_master no cumple contrato: 'fecha' debe ser datetime.")
    if not pd.api.types.is_numeric_dtype(df["Monto"]):
        raise ValueError("df_master no cumple contrato: 'Monto' debe ser numerico.")
    if df["nombre_estado"].isna().any():
        raise ValueError("df_master no cumple contrato: 'nombre_estado' contiene nulos.")
    if df["linea"].isna().any():
        raise ValueError("df_master no cumple contrato: 'linea' contiene nulos.")
    if df["producto"].isna().any():
        raise ValueError("df_master no cumple contrato: 'producto' contiene nulos.")


def load_df_master_from_db(engine, start_year: int | None = None, end_year: int | None = None) -> pd.DataFrame:
    query = text(
        """
        SELECT anio, mes, estado, linea, producto, metrica, valor
        FROM infonavit_historico
        WHERE metrica = :metrica_monto
          AND (:start_year IS NULL OR anio >= :start_year)
          AND (:end_year IS NULL OR anio <= :end_year)
        """
    )
    params = {
        "metrica_monto": METRICA_MONTO,
        "start_year": int(start_year) if start_year is not None else None,
        "end_year": int(end_year) if end_year is not None else None,
    }
    raw_df = pd.read_sql_query(query, engine, params=params)
    return build_df_master_from_long_table(raw_df)
