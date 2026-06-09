from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd


BASE_REQUIRED_COLUMNS = {
    "id_reporte",
    "anio",
    "estado",
    "mes",
    "linea",
    "producto",
    "metrica",
    "valor",
}


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _non_empty_string_mask(series: pd.Series) -> pd.Series:
    return series.notna() & (series.astype(str).str.strip() != "")


def validate_consolidated_dataframe(
    df: pd.DataFrame,
    *,
    required_years: Iterable[int] | None = None,
    valid_states: Iterable[int] | None = None,
    valid_metrics: Iterable[str] | None = None,
    require_unique_id: bool = False,
) -> ValidationResult:
    result = ValidationResult()

    missing = BASE_REQUIRED_COLUMNS - set(df.columns)
    if missing:
        result.errors.append(f"Faltan columnas obligatorias: {sorted(missing)}")
        return result

    ids_validos = _non_empty_string_mask(df["id_reporte"])
    if not ids_validos.all():
        result.errors.append(f"Hay {(~ids_validos).sum()} registros sin id_reporte.")

    duplicated_ids = int(df.duplicated(subset=["id_reporte"], keep=False).sum())
    if duplicated_ids:
        message = f"Hay {duplicated_ids} filas con id_reporte duplicado."
        if require_unique_id:
            result.errors.append(message)
        else:
            result.warnings.append(message)

    anios = pd.to_numeric(df["anio"], errors="coerce")
    meses = pd.to_numeric(df["mes"], errors="coerce")
    valores = pd.to_numeric(df["valor"], errors="coerce")
    estados = pd.to_numeric(df["estado"], errors="coerce")

    if anios.isna().any() or (anios <= 0).any():
        result.errors.append("La columna anio contiene valores invalidos.")

    meses_invalidos = meses.isna() | ~meses.between(1, 12)
    if meses_invalidos.any():
        result.errors.append(f"La columna mes contiene {int(meses_invalidos.sum())} valores fuera de 1-12.")

    if valores.isna().any():
        result.errors.append(f"La columna valor contiene {int(valores.isna().sum())} valores no numericos.")

    if valid_states is not None:
        valid_states_set = {int(v) for v in valid_states}
        unknown_states = sorted(set(estados.dropna().astype(int)) - valid_states_set)
        if unknown_states:
            result.errors.append(f"Estados no reconocidos en catalogo: {unknown_states}")

    if valid_metrics is not None:
        valid_metrics_set = {str(v) for v in valid_metrics}
        unknown_metrics = sorted(set(df["metrica"].dropna().astype(str)) - valid_metrics_set)
        if unknown_metrics:
            result.errors.append(f"Metricas no reconocidas: {unknown_metrics}")

    for col in ("linea", "producto", "metrica"):
        invalid = ~_non_empty_string_mask(df[col])
        if invalid.any():
            result.errors.append(f"La columna {col} contiene {int(invalid.sum())} valores vacios.")

    available_years = set(anios.dropna().astype(int))
    for year in required_years or []:
        if int(year) not in available_years:
            result.errors.append(
                f"El anio configurado {year} no existe en el dataset. "
                f"Anios disponibles: {sorted(available_years)}"
            )

    return result


def temporal_comparability_warnings(
    df: pd.DataFrame,
    *,
    current_year: int,
    previous_year: int,
) -> list[str]:
    if "anio" not in df.columns or "mes" not in df.columns:
        return ["No se pudo evaluar comparabilidad temporal: faltan columnas anio o mes."]

    data = df.copy()
    data["anio"] = pd.to_numeric(data["anio"], errors="coerce")
    data["mes"] = pd.to_numeric(data["mes"], errors="coerce")
    data = data.dropna(subset=["anio", "mes"])

    current_months = sorted(data.loc[data["anio"] == current_year, "mes"].astype(int).unique())
    previous_months = sorted(data.loc[data["anio"] == previous_year, "mes"].astype(int).unique())

    warnings: list[str] = []
    if not current_months or not previous_months:
        return warnings

    current_max_month = max(current_months)
    previous_max_month = max(previous_months)
    if current_max_month < previous_max_month:
        warnings.append(
            "Comparabilidad temporal: el anio de analisis tiene datos hasta el mes "
            f"{current_max_month}, pero el anio previo tiene datos hasta el mes {previous_max_month}. "
            "Para graficas YoY se recomienda usar ventana YTD comparable."
        )

    return warnings


def format_validation_messages(result: ValidationResult) -> list[str]:
    messages = [f"ERROR: {msg}" for msg in result.errors]
    messages.extend(f"ADVERTENCIA: {msg}" for msg in result.warnings)
    return messages
