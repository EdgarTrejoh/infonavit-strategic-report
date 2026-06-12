from __future__ import annotations

import math
from typing import Any

import pandas as pd

import config
from data_access import METRICA_CREDITOS, METRICA_MONTO

MONTO_COL = "Monto"
CREDITOS_COL = "Creditos"
TICKET_COL = "Ticket_Promedio"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        return _json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _safe_pct(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100


def _safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _estado_catalog() -> dict[int, str]:
    return {int(key): value for key, value in config.ESTADOS_MX.items()}


def build_extended_analytic_df(df: pd.DataFrame) -> pd.DataFrame:
    required_columns = {"anio", "mes", "estado", "linea", "producto", "metrica", "valor"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas en tabla larga: {sorted(missing)}")

    data = df[df["metrica"].isin([METRICA_MONTO, METRICA_CREDITOS])].copy()
    data["anio"] = pd.to_numeric(data["anio"], errors="coerce")
    data["mes"] = pd.to_numeric(data["mes"], errors="coerce")
    data["estado"] = pd.to_numeric(data["estado"], errors="coerce")
    data["valor"] = pd.to_numeric(data["valor"], errors="coerce")
    data = data.dropna(subset=["anio", "mes", "estado", "linea", "producto", "metrica", "valor"]).copy()
    data["anio"] = data["anio"].astype(int)
    data["mes"] = data["mes"].astype(int)
    data["estado"] = data["estado"].astype(int)
    data = data[(data["mes"] >= 1) & (data["mes"] <= 12)].copy()
    data["nombre_estado"] = data["estado"].map(_estado_catalog())
    data = data.dropna(subset=["nombre_estado"]).copy()

    pivot = (
        data.pivot_table(
            index=["anio", "mes", "estado", "nombre_estado", "linea", "producto"],
            columns="metrica",
            values="valor",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
        .rename(columns={METRICA_MONTO: MONTO_COL, METRICA_CREDITOS: CREDITOS_COL})
    )
    if MONTO_COL not in pivot.columns:
        pivot[MONTO_COL] = 0.0
    if CREDITOS_COL not in pivot.columns:
        pivot[CREDITOS_COL] = 0.0

    pivot[MONTO_COL] = pd.to_numeric(pivot[MONTO_COL], errors="coerce").fillna(0.0)
    pivot[CREDITOS_COL] = pd.to_numeric(pivot[CREDITOS_COL], errors="coerce").fillna(0.0)
    pivot["fecha"] = pd.to_datetime(dict(year=pivot["anio"], month=pivot["mes"], day=1), errors="coerce")
    pivot[TICKET_COL] = pivot.apply(
        lambda row: _safe_div(float(row[MONTO_COL]), float(row[CREDITOS_COL])),
        axis=1,
    )
    return pivot.reset_index(drop=True)


def _detect_month_limit(df: pd.DataFrame, current_year: int, month_limit: int | None) -> int:
    if month_limit is not None:
        if month_limit < 1 or month_limit > 12:
            raise ValueError("month_limit debe estar entre 1 y 12.")
        return int(month_limit)
    months = df.loc[df["anio"] == current_year, "mes"]
    if months.empty:
        return 12
    return int(months.max())


def _filter_ytd(df: pd.DataFrame, year: int, month_limit: int) -> pd.DataFrame:
    return df[(df["anio"] == year) & (df["mes"] <= month_limit)].copy()


def _metric_exists_in_ytd(df: pd.DataFrame, metric_name: str, year: int, month_limit: int) -> bool:
    data = df.copy()
    data["anio"] = pd.to_numeric(data["anio"], errors="coerce")
    data["mes"] = pd.to_numeric(data["mes"], errors="coerce")
    data = data.dropna(subset=["anio", "mes", "metrica"]).copy()
    data["anio"] = data["anio"].astype(int)
    data["mes"] = data["mes"].astype(int)
    filtered = data[(data["anio"] == year) & (data["mes"] <= month_limit)]
    return bool((filtered["metrica"] == metric_name).any())


def _summarize_period(df: pd.DataFrame) -> dict[str, float | None]:
    monto = float(df[MONTO_COL].sum()) if not df.empty else 0.0
    creditos = float(df[CREDITOS_COL].sum()) if not df.empty else 0.0
    return {
        "monto": monto,
        "creditos": creditos,
        "ticket_promedio": _safe_div(monto, creditos),
    }


def _ranking(
    df: pd.DataFrame,
    group_col: str,
    metric_col: str,
    metric_name: str,
    top_n: int = 10,
) -> list[dict[str, Any]]:
    if df.empty:
        return []
    grouped = (
        df.groupby(group_col, as_index=False)[metric_col]
        .sum()
        .rename(columns={group_col: "nombre", metric_col: metric_name})
        .sort_values(metric_name, ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    total = float(grouped[metric_name].sum()) if not grouped.empty else 0.0
    grouped["share"] = grouped[metric_name].map(lambda value: (float(value) / total) * 100 if total else 0.0)
    grouped["ranking"] = range(1, len(grouped) + 1)
    return _json_safe(grouped.to_dict(orient="records"))


def build_extended_context(
    df: pd.DataFrame,
    current_year: int,
    previous_year: int,
    month_limit: int | None = None,
) -> dict[str, Any]:
    data = build_extended_analytic_df(df)
    months_used = _detect_month_limit(data, current_year, month_limit)
    current = _filter_ytd(data, current_year, months_used)
    previous = _filter_ytd(data, previous_year, months_used)
    has_current_monto = _metric_exists_in_ytd(df, METRICA_MONTO, current_year, months_used)
    has_previous_monto = _metric_exists_in_ytd(df, METRICA_MONTO, previous_year, months_used)
    has_current_creditos = _metric_exists_in_ytd(df, METRICA_CREDITOS, current_year, months_used)
    has_previous_creditos = _metric_exists_in_ytd(df, METRICA_CREDITOS, previous_year, months_used)

    current_summary = _summarize_period(current)
    previous_summary = _summarize_period(previous)

    monto_actual = float(current_summary["monto"] or 0.0)
    monto_previo = float(previous_summary["monto"] or 0.0)
    creditos_actual = float(current_summary["creditos"] or 0.0) if has_current_creditos else None
    creditos_previo = float(previous_summary["creditos"] or 0.0) if has_previous_creditos else None
    ticket_actual = current_summary["ticket_promedio"] if has_current_creditos else None
    ticket_previo = previous_summary["ticket_promedio"] if has_previous_creditos else None

    warnings = []
    expected_months = set(range(1, months_used + 1))
    current_months = set(current["mes"].tolist())
    previous_months = set(previous["mes"].tolist())
    if months_used < 12:
        warnings.append("Comparacion YTD: no compara anios completos.")
    if not expected_months.issubset(current_months):
        warnings.append("El anio actual no contiene todos los meses esperados para la ventana comparable.")
    if not expected_months.issubset(previous_months):
        warnings.append("El anio previo no contiene todos los meses esperados para la ventana comparable.")
    if not has_current_monto:
        warnings.append(f"No se encontraron registros para la metrica {METRICA_MONTO} en el periodo actual consultado.")
    if not has_previous_monto:
        warnings.append(f"No se encontraron registros para la metrica {METRICA_MONTO} en el periodo previo consultado.")
    if not has_current_creditos:
        warnings.append(f"No se encontraron registros para la metrica {METRICA_CREDITOS} en el periodo actual consultado.")
    if not has_previous_creditos:
        warnings.append(f"No se encontraron registros para la metrica {METRICA_CREDITOS} en el periodo previo consultado.")
    if creditos_actual == 0 or creditos_previo == 0:
        warnings.append("El ticket promedio no puede calcularse para periodos con cero creditos.")

    estados_monto = _ranking(current, "nombre_estado", MONTO_COL, "monto") if has_current_monto else []
    estados_creditos = _ranking(current, "nombre_estado", CREDITOS_COL, "creditos") if has_current_creditos else []
    lineas_monto = _ranking(current, "linea", MONTO_COL, "monto") if has_current_monto else []
    lineas_creditos = _ranking(current, "linea", CREDITOS_COL, "creditos") if has_current_creditos else []
    productos_monto = _ranking(current, "producto", MONTO_COL, "monto") if has_current_monto else []
    productos_creditos = _ranking(current, "producto", CREDITOS_COL, "creditos") if has_current_creditos else []

    context = {
        "title": "Reporte ejecutivo INFONAVIT extendido",
        "period": {
            "current_year": current_year,
            "previous_year": previous_year,
            "month_limit": months_used,
            "comparability": "YTD comparable",
        },
        "summary": {
            "monto_actual": monto_actual,
            "monto_previo": monto_previo,
            "monto_variacion_abs": monto_actual - monto_previo,
            "monto_variacion_pct": _safe_pct(monto_actual, monto_previo),
            "creditos_actual": creditos_actual,
            "creditos_previo": creditos_previo,
            "creditos_variacion_abs": (
                None if creditos_actual is None or creditos_previo is None else creditos_actual - creditos_previo
            ),
            "creditos_variacion_pct": (
                None if creditos_actual is None or creditos_previo is None else _safe_pct(creditos_actual, creditos_previo)
            ),
            "ticket_promedio_actual": ticket_actual,
            "ticket_promedio_previo": ticket_previo,
            "ticket_promedio_variacion_abs": (
                None if ticket_actual is None or ticket_previo is None else ticket_actual - ticket_previo
            ),
            "ticket_promedio_variacion_pct": (
                None if ticket_actual is None or ticket_previo in (None, 0) else _safe_pct(ticket_actual, ticket_previo)
            ),
        },
        "drivers": {
            "linea_lider_monto": lineas_monto[0]["nombre"] if lineas_monto else None,
            "producto_lider_monto": productos_monto[0]["nombre"] if productos_monto else None,
            "estado_lider_monto": estados_monto[0]["nombre"] if estados_monto else None,
            "linea_lider_creditos": lineas_creditos[0]["nombre"] if lineas_creditos else None,
            "producto_lider_creditos": productos_creditos[0]["nombre"] if productos_creditos else None,
            "estado_lider_creditos": estados_creditos[0]["nombre"] if estados_creditos else None,
        },
        "rankings": {
            "estados_por_monto": estados_monto,
            "estados_por_creditos": estados_creditos,
            "lineas_por_monto": lineas_monto,
            "productos_por_monto": productos_monto,
        },
        "methodology": {
            "notes": [
                "Se usa ventana YTD comparable para evitar comparar anio completo contra anio parcial.",
                "Ticket promedio = monto colocado / numero de creditos formalizados.",
            ],
            "warnings": warnings,
        },
        "future_crosses": {
            "inflacion_inpc": "pendiente",
            "indice_shf": "pendiente",
            "salario_minimo": "pendiente",
            "imss_derechohabientes": "pendiente",
        },
    }
    return _json_safe(context)
