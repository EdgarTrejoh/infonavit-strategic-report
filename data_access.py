from __future__ import annotations

import pandas as pd
from sqlalchemy import bindparam, text

import config

METRICA_MONTO = "Monto de crédito Infonavit"
METRICA_CREDITOS = "Número de créditos formalizados"
METRICA_MONTO_UTF8 = "Monto de crédito Infonavit"
METRICA_CREDITOS_UTF8 = "Número de créditos formalizados"
METRICA_MONTO_MOJIBAKE = "Monto de cr\u00c3\u00a9dito Infonavit"
METRICA_CREDITOS_MOJIBAKE = "N\u00c3\u00bamero de cr\u00c3\u00a9ditos formalizados"
METRICA_MONTO_ALIASES = [METRICA_MONTO, METRICA_MONTO_UTF8, METRICA_MONTO_MOJIBAKE]
METRICA_CREDITOS_ALIASES = [METRICA_CREDITOS, METRICA_CREDITOS_UTF8, METRICA_CREDITOS_MOJIBAKE]
METRICAS_EXTENDIDAS = [*METRICA_MONTO_ALIASES, *METRICA_CREDITOS_ALIASES]
DF_MASTER_COLUMNS = ["fecha", "linea", "producto", "nombre_estado", "Monto"]


def _estado_catalog() -> dict[int, str]:
    return {int(key): value for key, value in config.ESTADOS_MX.items()}


def _unique_strings(values: list[str]) -> list[str]:
    unique = []
    seen = set()
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return unique


def _historico_table_ref(engine) -> str:
    if getattr(engine.dialect, "name", "") == "sqlite":
        return "infonavit_historico"
    return "public.infonavit_historico"


def _connection_metadata(connection) -> dict:
    if getattr(connection.dialect, "name", "") != "postgresql":
        return {
            "dialect": getattr(connection.dialect, "name", "unknown"),
            "database": None,
            "schema": None,
            "user": None,
        }
    row = connection.execute(
        text(
            """
            SELECT
                current_database() AS database,
                current_schema() AS schema,
                current_user AS user
            """
        )
    ).mappings().first()
    return {
        "dialect": "postgresql",
        "database": row["database"] if row else None,
        "schema": row["schema"] if row else None,
        "user": row["user"] if row else None,
    }


def build_df_master_from_long_table(df: pd.DataFrame) -> pd.DataFrame:
    required_columns = {"anio", "mes", "estado", "linea", "producto", "metrica", "valor"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas en tabla larga: {sorted(missing)}")

    data = df[df["metrica"].isin(METRICA_MONTO_ALIASES)].copy()
    data["metrica"] = METRICA_MONTO

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
    table_ref = _historico_table_ref(engine)
    query = text(
        f"""
        SELECT anio, mes, estado, linea, producto, metrica, valor
        FROM {table_ref}
        WHERE metrica IN :metrica_monto_aliases
          AND (:start_year IS NULL OR anio >= :start_year)
          AND (:end_year IS NULL OR anio <= :end_year)
        """
    ).bindparams(bindparam("metrica_monto_aliases", expanding=True))
    params = {
        "metrica_monto_aliases": METRICA_MONTO_ALIASES,
        "start_year": int(start_year) if start_year is not None else None,
        "end_year": int(end_year) if end_year is not None else None,
    }
    with engine.connect() as connection:
        result = connection.execute(query, params)
        raw_df = pd.DataFrame(result.mappings().all(), columns=result.keys())
    return build_df_master_from_long_table(raw_df)


def load_long_metrics_from_db(engine, start_year: int | None = None, end_year: int | None = None) -> pd.DataFrame:
    table_ref = _historico_table_ref(engine)
    query = text(
        f"""
        SELECT anio, mes, estado, linea, producto, metrica, valor
        FROM {table_ref}
        WHERE metrica IN :metricas_extendidas
          AND (:start_year IS NULL OR anio >= :start_year)
          AND (:end_year IS NULL OR anio <= :end_year)
        """
    ).bindparams(bindparam("metricas_extendidas", expanding=True))
    params = {
        "metricas_extendidas": METRICAS_EXTENDIDAS,
        "start_year": int(start_year) if start_year is not None else None,
        "end_year": int(end_year) if end_year is not None else None,
    }
    with engine.connect() as connection:
        result = connection.execute(query, params)
        df = pd.DataFrame(result.mappings().all(), columns=result.keys())
    if not df.empty:
        metric_map = {alias: METRICA_MONTO for alias in METRICA_MONTO_ALIASES}
        metric_map.update({alias: METRICA_CREDITOS for alias in METRICA_CREDITOS_ALIASES})
        df["metrica"] = df["metrica"].map(metric_map).fillna(df["metrica"])
    return df


def get_db_metrics_diagnostics(engine, start_year: int | None = None, end_year: int | None = None) -> dict:
    table_ref = _historico_table_ref(engine)
    params = {
        "start_year": int(start_year) if start_year is not None else None,
        "end_year": int(end_year) if end_year is not None else None,
    }
    total_query = text(
        f"""
        SELECT COUNT(*) AS filas
        FROM {table_ref}
        WHERE (:start_year IS NULL OR anio >= :start_year)
          AND (:end_year IS NULL OR anio <= :end_year)
        """
    )
    years_query = text(
        f"""
        SELECT anio, COUNT(*) AS filas
        FROM {table_ref}
        WHERE (:start_year IS NULL OR anio >= :start_year)
          AND (:end_year IS NULL OR anio <= :end_year)
        GROUP BY anio
        ORDER BY anio
        """
    )
    metrics_query = text(
        f"""
        SELECT metrica, COUNT(*) AS filas, MIN(anio) AS min_anio, MAX(anio) AS max_anio
        FROM {table_ref}
        WHERE (:start_year IS NULL OR anio >= :start_year)
          AND (:end_year IS NULL OR anio <= :end_year)
        GROUP BY metrica
        ORDER BY metrica
        """
    )

    with engine.connect() as connection:
        connection_metadata = _connection_metadata(connection)
        total_rows = int(connection.execute(total_query, params).scalar() or 0)
        years = [dict(row) for row in connection.execute(years_query, params).mappings().all()]
        metrics = [dict(row) for row in connection.execute(metrics_query, params).mappings().all()]

    metric_names = {item["metrica"] for item in metrics}
    monto_aliases = _unique_strings(METRICA_MONTO_ALIASES)
    creditos_aliases = _unique_strings(METRICA_CREDITOS_ALIASES)
    return {
        "table": table_ref,
        "connection": connection_metadata,
        "filters": {"start_year": start_year, "end_year": end_year},
        "rows_total": total_rows,
        "years": years,
        "metrics": metrics,
        "expected_metrics": [
            {
                "canonical": METRICA_MONTO,
                "aliases": monto_aliases,
                "present": any(alias in metric_names for alias in monto_aliases),
            },
            {
                "canonical": METRICA_CREDITOS,
                "aliases": creditos_aliases,
                "present": any(alias in metric_names for alias in creditos_aliases),
            },
        ],
    }
