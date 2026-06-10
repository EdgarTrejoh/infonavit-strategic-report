from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


REPORT_TITLE = "Mini reporte ejecutivo INFONAVIT"
SECTION_IDS = ["summary_ytd", "drivers", "pareto_lineas", "ranking_estatal", "methodology"]


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "item"):
        return _json_safe(value.item())
    return value


def _format_money(value: Any) -> str:
    if value is None:
        return "N/D"
    return f"${float(value):,.2f}"


def _format_pct(value: Any) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):.2f}%"


def _top_line_summary(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No hay datos disponibles para calcular concentracion por linea."
    top = items[0]
    return (
        f"La linea con mayor monto es {top.get('linea', 'N/D')} "
        f"con participacion de {_format_pct(top.get('share'))}."
    )


def _top_state_summary(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No hay datos disponibles para ranking estatal."
    top = items[0]
    return (
        f"El estado lider es {top.get('estado', 'N/D')} "
        f"con participacion de {_format_pct(top.get('share'))}."
    )


def build_mini_report_json(ai_context: dict[str, Any]) -> dict[str, Any]:
    period = ai_context.get("periodo", {})
    summary = ai_context.get("summary", {})
    drivers = ai_context.get("drivers", {})
    pareto_lineas = ai_context.get("pareto_lineas", []) or []
    ranking_estatal = ai_context.get("ranking_estatal", []) or []
    warnings = ai_context.get("warnings", []) or []

    variation = summary.get("variacion_pct")
    summary_comment = (
        "El monto actual es "
        f"{_format_money(summary.get('monto_actual'))}, frente a "
        f"{_format_money(summary.get('monto_previo'))} del periodo previo; "
        f"la variacion comparable es {_format_pct(variation)}."
    )

    report = {
        "title": REPORT_TITLE,
        "period": {
            "current_year": period.get("current_year"),
            "previous_year": period.get("previous_year"),
            "month_limit": period.get("month_limit"),
            "comparability": period.get("comparability"),
        },
        "sections": [
            {
                "id": "summary_ytd",
                "title": "Resumen YTD comparable",
                "metric": _format_pct(variation),
                "comment": summary_comment,
                "data": summary,
            },
            {
                "id": "drivers",
                "title": "Principales impulsores",
                "comment": (
                    f"Linea lider: {drivers.get('linea_lider') or 'N/D'}; "
                    f"producto lider: {drivers.get('producto_lider') or 'N/D'}; "
                    f"estado lider: {drivers.get('estado_lider') or 'N/D'}."
                ),
                "data": drivers,
            },
            {
                "id": "pareto_lineas",
                "title": "Concentración por línea",
                "comment": _top_line_summary(pareto_lineas),
                "data": pareto_lineas,
            },
            {
                "id": "ranking_estatal",
                "title": "Ranking estatal",
                "comment": _top_state_summary(ranking_estatal),
                "data": ranking_estatal,
            },
            {
                "id": "methodology",
                "title": "Nota metodológica",
                "comment": (
                    "Se detectaron advertencias metodologicas."
                    if warnings
                    else "No se detectaron advertencias metodologicas relevantes."
                ),
                "data": warnings,
            },
        ],
        "warnings": warnings,
    }
    return _json_safe(report)


def _section_by_id(report_json: dict[str, Any], section_id: str) -> dict[str, Any]:
    for section in report_json.get("sections", []):
        if section.get("id") == section_id:
            return section
    return {}


def render_mini_report_markdown(report_json: dict[str, Any]) -> str:
    period = report_json.get("period", {})
    summary = _section_by_id(report_json, "summary_ytd")
    drivers = _section_by_id(report_json, "drivers")
    pareto = _section_by_id(report_json, "pareto_lineas")
    ranking = _section_by_id(report_json, "ranking_estatal")
    methodology = _section_by_id(report_json, "methodology")
    warnings = report_json.get("warnings", []) or []

    lines = [
        f"# {report_json.get('title', REPORT_TITLE)}",
        "",
        "## Periodo analizado",
        (
            f"{period.get('current_year', 'N/D')} vs {period.get('previous_year', 'N/D')}, "
            f"corte a mes {period.get('month_limit', 'N/D')}."
        ),
        f"Criterio: {period.get('comparability', 'N/D')}.",
        "",
        "## 1. Resumen YTD comparable",
        summary.get("comment", "Sin resumen disponible."),
        "",
        "## 2. Principales impulsores",
        drivers.get("comment", "Sin impulsores disponibles."),
        "",
        "## 3. Concentración por línea",
        pareto.get("comment", "Sin concentracion disponible."),
        "",
        "## 4. Ranking estatal",
        ranking.get("comment", "Sin ranking estatal disponible."),
        "",
        "## 5. Nota metodológica",
        methodology.get("comment", "Sin nota metodologica disponible."),
    ]

    if warnings:
        lines.extend(["", "Advertencias:"])
        lines.extend(f"- {warning}" for warning in warnings)

    return "\n".join(lines).strip() + "\n"


def save_mini_report_outputs(report_json: dict[str, Any], markdown: str, output_dir) -> tuple[Path, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_path = output_path / "mini_report.json"
    markdown_path = output_path / "mini_report.md"

    json_path.write_text(json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    return json_path, markdown_path


def generate_mini_report(ai_context: dict[str, Any], output_dir=None) -> tuple[dict[str, Any], str]:
    report_json = build_mini_report_json(ai_context)
    markdown = render_mini_report_markdown(report_json)
    if output_dir is not None:
        save_mini_report_outputs(report_json, markdown, output_dir)
    return report_json, markdown
