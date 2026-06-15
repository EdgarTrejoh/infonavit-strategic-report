from __future__ import annotations

import math
import unicodedata
from typing import Any

import pandas as pd

import config
from data_access import METRICA_CREDITOS, METRICA_MONTO

MONTO_COL = "Monto"
CREDITOS_COL = "Creditos"
TICKET_COL = "Ticket_Promedio"
INFLATION_UNAVAILABLE_REASON = "Inflation service not configured or unavailable"
INFLATION_WARNING = (
    "No se integro inflacion comparable porque el servicio de inflacion no estuvo disponible o no fue configurado."
)
LINE_FAMILIES = [
    {
        "family": "Adquisicion de vivienda nueva",
        "line_match": "Linea II: Adquisicion de vivienda nueva",
        "match_terms": ["vivienda nueva", "l2 nueva", "linea ii adquisicion de vivienda nueva"],
    },
    {
        "family": "Adquisicion de vivienda existente",
        "line_match": "vivienda existente",
        "match_terms": ["vivienda existente", "l2 existente"],
    },
    {
        "family": "Mejoramiento",
        "line_match": "Linea IV: Mejoramientos",
        "match_terms": ["mejoramiento", "mejoramientos", "mejoras", "l4 mejoras"],
    },
]
FUTURE_CROSSES = [
    {
        "key": "indice_shf",
        "label": "Índice SHF de Precios de la Vivienda",
        "status": "pendiente",
        "intended_use": (
            "Contrastar monto colocado, ticket promedio y familias de credito contra la evolucion de precios "
            "de la vivienda."
        ),
    },
    {
        "key": "salario_minimo",
        "label": "Salario minimo",
        "status": "pendiente",
        "intended_use": "Evaluar la relacion entre ticket promedio, inflacion y poder adquisitivo.",
    },
    {
        "key": "imss_derechohabientes",
        "label": "Derechohabientes IMSS",
        "status": "pendiente",
        "intended_use": "Dimensionar la base potencial de acreditados y su relacion con creditos formalizados.",
    },
]


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


def _safe_share(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return (float(numerator) / float(denominator)) * 100


def _normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.lower().replace(":", " ").split())


def _real_variation_pct(nominal_pct: float | None, inflation_factor: float | None) -> float | None:
    if nominal_pct is None or inflation_factor in (None, 0):
        return None
    return (((1 + float(nominal_pct) / 100) / float(inflation_factor)) - 1) * 100


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


def _family_reading(
    monto_real_pct: float | None,
    ticket_real_pct: float | None,
    creditos_pct: float | None,
    share_monto_delta_pp: float | None = None,
    share_creditos_delta_pp: float | None = None,
    family_ticket_actual: float | None = None,
    aggregate_ticket_actual: float | None = None,
) -> str:
    candidates = []

    if (
        share_creditos_delta_pp is not None
        and share_creditos_delta_pp > 0
        and family_ticket_actual is not None
        and aggregate_ticket_actual is not None
        and family_ticket_actual < aggregate_ticket_actual
    ):
        candidates.append(
            "La familia gano peso en creditos y presiona a la baja el ticket promedio agregado por efecto mezcla."
        )
    if share_monto_delta_pp is not None and share_monto_delta_pp > 0:
        candidates.append("La familia gano participacion en monto colocado.")

    if monto_real_pct is None or ticket_real_pct is None:
        candidates.append("No hay inflacion comparable suficiente para interpretar variaciones reales.")
    else:
        if monto_real_pct > 0:
            candidates.append("El monto colocado crecio en terminos reales.")
        elif monto_real_pct < 0:
            candidates.append("El monto colocado disminuyo en terminos reales.")
        else:
            candidates.append("El monto colocado se mantuvo estable en terminos reales.")

        if ticket_real_pct > 0:
            candidates.append("El ticket promedio supero la inflacion comparable.")
        elif ticket_real_pct < 0:
            candidates.append("El ticket promedio perdio terreno frente a la inflacion comparable.")
        else:
            candidates.append("El ticket promedio se mantuvo practicamente estable en terminos reales.")

    if creditos_pct is None:
        candidates.append("No hay datos suficientes para interpretar el volumen de creditos.")
    elif creditos_pct > 0:
        candidates.append("El volumen de creditos aumento.")
    elif creditos_pct < 0:
        candidates.append("El volumen de creditos disminuyo.")
    else:
        candidates.append("El volumen de creditos se mantuvo estable.")

    selected = []
    for sentence in candidates:
        if sentence not in selected:
            selected.append(sentence)
        if len(selected) == 2:
            break
    return " ".join(selected)


def _empty_family_entry(family_config: dict[str, Any]) -> dict[str, Any]:
    return {
        "family": family_config["family"],
        "line_match": family_config["line_match"],
        "current": {"monto": None, "creditos": None, "ticket_promedio": None},
        "previous": {"monto": None, "creditos": None, "ticket_promedio": None},
        "variations": {
            "monto_nominal_pct": None,
            "monto_real_pct": None,
            "creditos_pct": None,
            "ticket_nominal_pct": None,
            "ticket_real_pct": None,
            "share_monto_actual_pct": None,
            "share_monto_previo_pct": None,
            "share_creditos_actual_pct": None,
            "share_creditos_previo_pct": None,
            "share_monto_delta_pp": None,
            "share_creditos_delta_pp": None,
        },
        "executive_reading": "No hay datos suficientes para esta familia en la ventana comparable.",
    }


def _build_line_family_analysis(
    current: pd.DataFrame,
    previous: pd.DataFrame,
    warnings: list[str],
) -> dict[str, Any]:
    families = []
    total_current = _summarize_period(current)
    total_previous = _summarize_period(previous)
    total_monto_current = float(total_current["monto"] or 0.0)
    total_monto_previous = float(total_previous["monto"] or 0.0)
    total_creditos_current = float(total_current["creditos"] or 0.0)
    total_creditos_previous = float(total_previous["creditos"] or 0.0)
    aggregate_ticket_actual = total_current["ticket_promedio"]
    current_norm = current.copy()
    previous_norm = previous.copy()
    current_norm["_linea_norm"] = current_norm["linea"].map(_normalize_text) if not current_norm.empty else []
    previous_norm["_linea_norm"] = previous_norm["linea"].map(_normalize_text) if not previous_norm.empty else []

    for family_config in LINE_FAMILIES:
        terms = [_normalize_text(term) for term in family_config["match_terms"]]

        if current_norm.empty:
            current_family = current_norm.copy()
        else:
            current_family = current_norm[current_norm["_linea_norm"].map(lambda text: any(term in text for term in terms))]
        if previous_norm.empty:
            previous_family = previous_norm.copy()
        else:
            previous_family = previous_norm[previous_norm["_linea_norm"].map(lambda text: any(term in text for term in terms))]

        if current_family.empty and previous_family.empty:
            families.append(_empty_family_entry(family_config))
            warnings.append(f"No se encontraron datos para la familia {family_config['family']} en la ventana comparable.")
            continue

        current_summary = _summarize_period(current_family)
        previous_summary = _summarize_period(previous_family)
        monto_actual = float(current_summary["monto"] or 0.0)
        monto_previo = float(previous_summary["monto"] or 0.0)
        creditos_actual = float(current_summary["creditos"] or 0.0)
        creditos_previo = float(previous_summary["creditos"] or 0.0)
        ticket_actual = current_summary["ticket_promedio"]
        ticket_previo = previous_summary["ticket_promedio"]
        monto_nominal_pct = _safe_pct(monto_actual, monto_previo)
        creditos_pct = _safe_pct(creditos_actual, creditos_previo)
        ticket_nominal_pct = None if ticket_actual is None or ticket_previo in (None, 0) else _safe_pct(ticket_actual, ticket_previo)
        share_monto_actual = _safe_share(monto_actual, total_monto_current)
        share_monto_previo = _safe_share(monto_previo, total_monto_previous)
        share_creditos_actual = _safe_share(creditos_actual, total_creditos_current)
        share_creditos_previo = _safe_share(creditos_previo, total_creditos_previous)
        share_monto_delta = (
            None if share_monto_actual is None or share_monto_previo is None else share_monto_actual - share_monto_previo
        )
        share_creditos_delta = (
            None
            if share_creditos_actual is None or share_creditos_previo is None
            else share_creditos_actual - share_creditos_previo
        )

        families.append(
            {
                "family": family_config["family"],
                "line_match": family_config["line_match"],
                "current": {
                    "monto": monto_actual,
                    "creditos": creditos_actual,
                    "ticket_promedio": ticket_actual,
                },
                "previous": {
                    "monto": monto_previo,
                    "creditos": creditos_previo,
                    "ticket_promedio": ticket_previo,
                },
                "variations": {
                    "monto_nominal_pct": monto_nominal_pct,
                    "monto_real_pct": None,
                    "creditos_pct": creditos_pct,
                    "ticket_nominal_pct": ticket_nominal_pct,
                    "ticket_real_pct": None,
                    "share_monto_actual_pct": share_monto_actual,
                    "share_monto_previo_pct": share_monto_previo,
                    "share_creditos_actual_pct": share_creditos_actual,
                    "share_creditos_previo_pct": share_creditos_previo,
                    "share_monto_delta_pp": share_monto_delta,
                    "share_creditos_delta_pp": share_creditos_delta,
                },
                "executive_reading": _family_reading(
                    None,
                    None,
                    creditos_pct,
                    share_monto_delta,
                    share_creditos_delta,
                    ticket_actual,
                    aggregate_ticket_actual,
                ),
            }
        )

    return {"available": True, "families": _json_safe(families)}


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
    line_family_analysis = _build_line_family_analysis(current, previous, warnings)

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
        "line_family_analysis": line_family_analysis,
        "future_crosses": [
            {
                "key": "inflacion_inpc",
                "label": "INPC general",
                "status": "pendiente",
                "intended_use": "Deflactar variaciones nominales de monto colocado y ticket promedio.",
            },
            *FUTURE_CROSSES,
        ],
    }
    return _json_safe(context)


def _mark_future_cross_integrated(future_crosses: Any, key: str) -> Any:
    if isinstance(future_crosses, list):
        updated = []
        found = False
        for item in future_crosses:
            if isinstance(item, dict) and item.get("key") == key:
                new_item = dict(item)
                new_item["status"] = "integrado"
                updated.append(new_item)
                found = True
            else:
                updated.append(item)
        if not found:
            updated.append({"key": key, "label": key, "status": "integrado", "intended_use": ""})
        return updated
    if isinstance(future_crosses, dict):
        updated = dict(future_crosses)
        updated[key] = "integrado"
        return updated
    return [{"key": key, "label": key, "status": "integrado", "intended_use": ""}]


def add_inflation_context(context: dict[str, Any], inflation_data: dict[str, Any] | None) -> dict[str, Any]:
    enriched = _json_safe(context.copy())
    methodology = enriched.setdefault("methodology", {})
    warnings = methodology.setdefault("warnings", [])
    future_crosses = enriched.setdefault("future_crosses", {})

    if not inflation_data:
        enriched["inflation_context"] = {
            "available": False,
            "reason": INFLATION_UNAVAILABLE_REASON,
        }
        if INFLATION_WARNING not in warnings:
            warnings.append(INFLATION_WARNING)
        return _json_safe(enriched)

    summary = enriched.get("summary", {})
    factor = float(inflation_data["factor"])
    monto_nominal = summary.get("monto_variacion_pct")
    ticket_nominal = summary.get("ticket_promedio_variacion_pct")

    enriched["inflation_context"] = {
        "available": True,
        "source": f"{inflation_data.get('source', 'N/D')} via inflacion-copilot-api",
        "indicator": inflation_data.get("indicator"),
        "method": inflation_data.get("method"),
        "current_period": inflation_data.get("current_period"),
        "previous_period": inflation_data.get("previous_period"),
        "factor": factor,
        "inflation_pct": inflation_data.get("inflation_pct"),
        "monto_variacion_nominal_pct": monto_nominal,
        "monto_variacion_real_pct": _real_variation_pct(monto_nominal, factor),
        "ticket_variacion_nominal_pct": ticket_nominal,
        "ticket_variacion_real_pct": _real_variation_pct(ticket_nominal, factor),
    }
    family_analysis = enriched.get("line_family_analysis", {})
    for family in family_analysis.get("families", []) or []:
        variations = family.get("variations", {})
        variations["monto_real_pct"] = _real_variation_pct(variations.get("monto_nominal_pct"), factor)
        variations["ticket_real_pct"] = _real_variation_pct(variations.get("ticket_nominal_pct"), factor)
        family["executive_reading"] = _family_reading(
            variations.get("monto_real_pct"),
            variations.get("ticket_real_pct"),
            variations.get("creditos_pct"),
            variations.get("share_monto_delta_pp"),
            variations.get("share_creditos_delta_pp"),
            family.get("current", {}).get("ticket_promedio"),
            enriched.get("summary", {}).get("ticket_promedio_actual"),
        )
    enriched["future_crosses"] = _mark_future_cross_integrated(future_crosses, "inflacion_inpc")
    return _json_safe(enriched)
