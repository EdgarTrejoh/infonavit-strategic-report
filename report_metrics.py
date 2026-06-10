from __future__ import annotations

import math
from typing import Any

import pandas as pd


def _prepare_period_df(df: pd.DataFrame) -> pd.DataFrame:
    required_any = {"fecha"} | {"anio", "mes"}
    if "fecha" not in df.columns and not {"anio", "mes"}.issubset(df.columns):
        raise ValueError(f"El DataFrame debe incluir 'fecha' o 'anio' y 'mes': {required_any}")
    if "Monto" not in df.columns:
        raise ValueError("El DataFrame debe incluir la columna 'Monto'.")

    out = df.copy()
    if "fecha" in out.columns:
        fecha = pd.to_datetime(out["fecha"], errors="coerce")
        out["_anio"] = fecha.dt.year
        out["_mes"] = fecha.dt.month
    else:
        out["_anio"] = pd.to_numeric(out["anio"], errors="coerce")
        out["_mes"] = pd.to_numeric(out["mes"], errors="coerce")

    out["_monto"] = pd.to_numeric(out["Monto"], errors="coerce").fillna(0.0)
    out = out.dropna(subset=["_anio", "_mes"]).copy()
    out["_anio"] = out["_anio"].astype(int)
    out["_mes"] = out["_mes"].astype(int)
    return out[(out["_mes"] >= 1) & (out["_mes"] <= 12)].copy()


def _detect_month_limit(df: pd.DataFrame, current_year: int, month_limit: int | None) -> int:
    if month_limit is not None:
        if month_limit < 1 or month_limit > 12:
            raise ValueError("month_limit debe estar entre 1 y 12.")
        return int(month_limit)

    months = df.loc[df["_anio"] == current_year, "_mes"]
    if months.empty:
        return 12
    return int(months.max())


def _filter_ytd(df: pd.DataFrame, year: int, month_limit: int) -> pd.DataFrame:
    return df[(df["_anio"] == year) & (df["_mes"] <= month_limit)].copy()


def _safe_pct(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100


def _safe_share(value: float, total: float) -> float:
    if total == 0:
        return 0.0
    return (value / total) * 100


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return _json_safe(df.to_dict(orient="records"))


def compute_ytd_acumulado(
    df: pd.DataFrame,
    current_year: int,
    previous_year: int,
    month_limit: int | None = None,
) -> dict[str, Any]:
    data = _prepare_period_df(df)
    months_used = _detect_month_limit(data, current_year, month_limit)

    current_amount = float(_filter_ytd(data, current_year, months_used)["_monto"].sum())
    previous_amount = float(_filter_ytd(data, previous_year, months_used)["_monto"].sum())

    return _json_safe(
        {
            "monto_actual": current_amount,
            "monto_previo": previous_amount,
            "diferencia_abs": current_amount - previous_amount,
            "variacion_pct": _safe_pct(current_amount, previous_amount),
            "month_limit": months_used,
            "meses_usados": list(range(1, months_used + 1)),
        }
    )


def compute_yoy_comparable(
    df: pd.DataFrame,
    current_year: int,
    previous_year: int,
    month_limit: int | None = None,
) -> dict[str, Any]:
    summary = compute_ytd_acumulado(df, current_year, previous_year, month_limit)
    return _json_safe(
        {
            "current_year": current_year,
            "previous_year": previous_year,
            "month_limit": summary["month_limit"],
            "meses_usados": summary["meses_usados"],
            "comparability": "YTD comparable",
            "monto_actual": summary["monto_actual"],
            "monto_previo": summary["monto_previo"],
            "diferencia_abs": summary["diferencia_abs"],
            "variacion_pct": summary["variacion_pct"],
        }
    )


def compute_mix_producto_linea(
    df: pd.DataFrame,
    year: int,
    month_limit: int | None = None,
) -> list[dict[str, Any]]:
    data = _prepare_period_df(df)
    months_used = _detect_month_limit(data, year, month_limit)
    filtered = _filter_ytd(data, year, months_used)

    required = {"linea", "producto"}
    missing = required - set(filtered.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")

    grouped = (
        filtered.groupby(["linea", "producto"], as_index=False)["_monto"]
        .sum()
        .rename(columns={"_monto": "monto"})
        .sort_values("monto", ascending=False)
        .reset_index(drop=True)
    )
    total = float(grouped["monto"].sum()) if not grouped.empty else 0.0
    grouped["share"] = grouped["monto"].map(lambda value: _safe_share(float(value), total))
    grouped["ranking"] = range(1, len(grouped) + 1)
    return _records(grouped)


def compute_pareto_lineas(
    df: pd.DataFrame,
    year: int,
    month_limit: int | None = None,
) -> list[dict[str, Any]]:
    data = _prepare_period_df(df)
    months_used = _detect_month_limit(data, year, month_limit)
    filtered = _filter_ytd(data, year, months_used)
    if "linea" not in filtered.columns:
        raise ValueError("Falta columna requerida: 'linea'.")

    grouped = (
        filtered.groupby("linea", as_index=False)["_monto"]
        .sum()
        .rename(columns={"_monto": "monto"})
        .sort_values("monto", ascending=False)
        .reset_index(drop=True)
    )
    total = float(grouped["monto"].sum()) if not grouped.empty else 0.0
    grouped["share"] = grouped["monto"].map(lambda value: _safe_share(float(value), total))
    grouped["share_acumulado"] = grouped["share"].cumsum()
    grouped["ranking"] = range(1, len(grouped) + 1)
    grouped["concentracion_principal"] = grouped["share_acumulado"] <= 80
    if not grouped.empty:
        first_above_80 = grouped.index[grouped["share_acumulado"] >= 80]
        if len(first_above_80) > 0:
            grouped.loc[first_above_80[0], "concentracion_principal"] = True
    return _records(grouped)


def compute_ranking_estatal(
    df: pd.DataFrame,
    year: int,
    month_limit: int | None = None,
    top_n: int = 10,
) -> list[dict[str, Any]]:
    data = _prepare_period_df(df)
    months_used = _detect_month_limit(data, year, month_limit)
    filtered = _filter_ytd(data, year, months_used)

    state_col = "nombre_estado" if "nombre_estado" in filtered.columns else "estado"
    if state_col not in filtered.columns:
        raise ValueError("Falta columna requerida: 'nombre_estado' o 'estado'.")

    grouped = (
        filtered.groupby(state_col, as_index=False)["_monto"]
        .sum()
        .rename(columns={state_col: "estado", "_monto": "monto"})
        .sort_values("monto", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    total = float(filtered["_monto"].sum()) if not filtered.empty else 0.0
    grouped["share"] = grouped["monto"].map(lambda value: _safe_share(float(value), total))
    grouped["ranking"] = range(1, len(grouped) + 1)
    return _records(grouped)


def build_ai_context(
    df: pd.DataFrame,
    current_year: int,
    previous_year: int,
    month_limit: int | None = None,
) -> dict[str, Any]:
    data = _prepare_period_df(df)
    months_used = _detect_month_limit(data, current_year, month_limit)
    summary = compute_ytd_acumulado(data, current_year, previous_year, months_used)
    yoy = compute_yoy_comparable(data, current_year, previous_year, months_used)
    mix = compute_mix_producto_linea(data, current_year, months_used)
    pareto = compute_pareto_lineas(data, current_year, months_used)
    ranking_estatal = compute_ranking_estatal(data, current_year, months_used)

    warnings = []
    previous_months = set(data.loc[data["_anio"] == previous_year, "_mes"].tolist())
    current_months = set(data.loc[data["_anio"] == current_year, "_mes"].tolist())
    expected_months = set(range(1, months_used + 1))
    if not expected_months.issubset(current_months):
        warnings.append("El anio actual no contiene todos los meses esperados para la ventana comparable.")
    if not expected_months.issubset(previous_months):
        warnings.append("El anio previo no contiene todos los meses esperados para la ventana comparable.")
    if months_used < 12:
        warnings.append("Comparacion YTD: no compara anios completos.")

    leader = mix[0] if mix else {}
    state_leader = ranking_estatal[0] if ranking_estatal else {}

    context = {
        "periodo": {
            "current_year": current_year,
            "previous_year": previous_year,
            "month_limit": months_used,
            "comparability": "YTD comparable",
        },
        "summary": {
            "monto_actual": summary["monto_actual"],
            "monto_previo": summary["monto_previo"],
            "diferencia_abs": summary["diferencia_abs"],
            "variacion_pct": summary["variacion_pct"],
        },
        "yoy_comparable": yoy,
        "drivers": {
            "linea_lider": leader.get("linea"),
            "producto_lider": leader.get("producto"),
            "estado_lider": state_leader.get("estado"),
        },
        "pareto_lineas": pareto,
        "ranking_estatal": ranking_estatal,
        "warnings": warnings,
    }
    return _json_safe(context)
