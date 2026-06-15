from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


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


def _money_mdp(value: Any) -> str:
    if value is None:
        return "N/D"
    return f"{float(value) / 1_000_000:,.1f} mdp"


def _number(value: Any) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.0f}"


def _money(value: Any) -> str:
    if value is None:
        return "N/D"
    return f"${float(value):,.0f}"


def _pct(value: Any) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):.2f}%"


def _top_name(items: list[dict[str, Any]]) -> str:
    if not items:
        return "N/D"
    return str(items[0].get("nombre") or "N/D")


def _family_metric_text(current: dict[str, Any], previous: dict[str, Any], variations: dict[str, Any]) -> list[str]:
    return [
        (
            f"Monto colocado: {_money_mdp(current.get('monto'))} vs {_money_mdp(previous.get('monto'))}; "
            f"variacion nominal {_pct(variations.get('monto_nominal_pct'))} y real "
            f"{_pct(variations.get('monto_real_pct'))}."
        ),
        (
            f"Creditos: {_number(current.get('creditos'))} vs {_number(previous.get('creditos'))}; "
            f"variacion {_pct(variations.get('creditos_pct'))}."
        ),
        (
            f"Ticket promedio: {_money(current.get('ticket_promedio'))} vs {_money(previous.get('ticket_promedio'))}; "
            f"variacion nominal {_pct(variations.get('ticket_nominal_pct'))} y real "
            f"{_pct(variations.get('ticket_real_pct'))}."
        ),
        (
            f"Participacion en monto: {_pct(variations.get('share_monto_actual_pct'))} vs "
            f"{_pct(variations.get('share_monto_previo_pct'))} del total."
        ),
        (
            f"Participacion en creditos: {_pct(variations.get('share_creditos_actual_pct'))} vs "
            f"{_pct(variations.get('share_creditos_previo_pct'))} del total."
        ),
    ]


def _volume_ticket_interpretation(creditos_pct: Any, ticket_pct: Any) -> str:
    if creditos_pct is None or ticket_pct is None:
        return "No hay datos suficientes para interpretar la relacion entre volumen de creditos y ticket promedio."

    creditos_variation = float(creditos_pct)
    ticket_variation = float(ticket_pct)

    if creditos_variation >= 0 and ticket_variation < 0:
        return (
            "El numero de creditos crecio, mientras que el ticket promedio disminuyo; "
            "por lo tanto, el crecimiento del monto colocado se explica principalmente "
            "por mayor volumen de creditos, no por creditos de mayor monto promedio."
        )
    if creditos_variation >= 0 and ticket_variation >= 0:
        return "El monto colocado crecio por una combinacion de mayor volumen de creditos y mayor ticket promedio."
    if creditos_variation < 0 and ticket_variation >= 0:
        return (
            "Aunque el numero de creditos disminuyo, el ticket promedio aumento; "
            "esto indica que el monto colocado estuvo sostenido por creditos de mayor monto promedio."
        )
    return (
        "Tanto el numero de creditos como el ticket promedio disminuyeron, "
        "lo que apunta a una contraccion combinada en volumen y monto promedio."
    )


def _real_growth_read(metric_name: str, value: Any) -> str:
    if value is None:
        return f"No hay datos suficientes para interpretar la variacion real de {metric_name}."
    if float(value) >= 0:
        return f"{metric_name} crecio en terminos reales."
    return f"{metric_name} disminuyo en terminos reales."


def _ticket_real_read(value: Any) -> str:
    if value is None:
        return "No hay datos suficientes para interpretar el ticket promedio frente a la inflacion comparable."
    if float(value) >= 0:
        return "El ticket promedio supero la inflacion comparable."
    return "El ticket promedio perdio terreno frente a la inflacion comparable."


def build_extended_report_json(context: dict[str, Any]) -> dict[str, Any]:
    return _json_safe(context)


def render_extended_report_markdown(report_json: dict[str, Any]) -> str:
    period = report_json.get("period", {})
    summary = report_json.get("summary", {})
    drivers = report_json.get("drivers", {})
    rankings = report_json.get("rankings", {})
    methodology = report_json.get("methodology", {})
    inflation = report_json.get("inflation_context", {}) or {}
    line_family_analysis = report_json.get("line_family_analysis", {}) or {}
    warnings = methodology.get("warnings", []) or []
    notes = methodology.get("notes", []) or []

    monto_pct = summary.get("monto_variacion_pct")
    creditos_pct = summary.get("creditos_variacion_pct")
    ticket_pct = summary.get("ticket_promedio_variacion_pct")

    volume_ticket_read = _volume_ticket_interpretation(creditos_pct, ticket_pct)

    lines = [
        f"# {report_json.get('title', 'Reporte ejecutivo INFONAVIT extendido')}",
        "",
        "## Periodo analizado",
        (
            f"{period.get('current_year', 'N/D')} vs {period.get('previous_year', 'N/D')}, "
            f"corte a mes {period.get('month_limit', 'N/D')}."
        ),
        f"Criterio: {period.get('comparability', 'N/D')}.",
        "",
        "## 1. Resumen ejecutivo",
        (
            f"En el periodo YTD comparable {period.get('current_year', 'N/D')} vs "
            f"{period.get('previous_year', 'N/D')}, INFONAVIT coloco "
            f"{_money_mdp(summary.get('monto_actual'))} frente a "
            f"{_money_mdp(summary.get('monto_previo'))} del anio previo, equivalente a "
            f"una variacion de {_pct(monto_pct)}."
        ),
        (
            f"El numero de creditos formalizados fue de {_number(summary.get('creditos_actual'))} "
            f"frente a {_number(summary.get('creditos_previo'))}, con una variacion de "
            f"{_pct(creditos_pct)}."
        ),
        (
            f"El ticket promedio se ubico en {_money(summary.get('ticket_promedio_actual'))}, "
            f"contra {_money(summary.get('ticket_promedio_previo'))} del periodo previo, "
            f"con variacion de {_pct(ticket_pct)}. {volume_ticket_read}"
        ),
        "",
    ]
    if inflation.get("available"):
        monto_real = inflation.get("monto_variacion_real_pct")
        ticket_real = inflation.get("ticket_variacion_real_pct")
        lines.extend(
            [
                "## 2. Contexto de inflacion comparable",
                (
                    f"La inflacion promedio comparable del periodo fue "
                    f"{_pct(inflation.get('inflation_pct'))}."
                ),
                (
                    f"Con ajuste por inflacion, el monto colocado registro una variacion real de "
                    f"{_pct(monto_real)} frente a {_pct(inflation.get('monto_variacion_nominal_pct'))} nominal. "
                    f"{_real_growth_read('El monto colocado', monto_real)}"
                ),
                (
                    f"El ticket promedio registro una variacion real de {_pct(ticket_real)} frente a "
                    f"{_pct(inflation.get('ticket_variacion_nominal_pct'))} nominal. "
                    f"{_ticket_real_read(ticket_real)}"
                ),
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## 2. Contexto de inflacion comparable",
                "No hay datos suficientes para calcular variaciones reales porque el servicio de inflacion no estuvo disponible o no fue configurado.",
                "",
            ]
        )
    lines.append("## 3. Analisis por familia de linea")
    families = line_family_analysis.get("families", []) or []
    if families:
        for family in families:
            lines.extend(
                [
                    f"### {family.get('family', 'N/D')}",
                    *_family_metric_text(
                        family.get("current", {}) or {},
                        family.get("previous", {}) or {},
                        family.get("variations", {}) or {},
                    ),
                    f"Lectura: {family.get('executive_reading') or 'N/D'}",
                    "",
                ]
            )
    else:
        lines.extend(["No hay datos suficientes para el analisis por familia de linea.", ""])
    lines.extend(
        [
            "## 4. Principales impulsores",
            (
                f"Por monto, la linea lider es {drivers.get('linea_lider_monto') or 'N/D'}, "
                f"el producto lider es {drivers.get('producto_lider_monto') or 'N/D'} y "
                f"el estado lider es {drivers.get('estado_lider_monto') or 'N/D'}."
            ),
            (
                f"Por creditos, la linea lider es {drivers.get('linea_lider_creditos') or 'N/D'}, "
                f"el producto lider es {drivers.get('producto_lider_creditos') or 'N/D'} y "
                f"el estado lider es {drivers.get('estado_lider_creditos') or 'N/D'}."
            ),
            "",
            "## 5. Rankings ejecutivos",
            f"Estado lider por monto: {_top_name(rankings.get('estados_por_monto', []))}.",
            f"Estado lider por creditos: {_top_name(rankings.get('estados_por_creditos', []))}.",
            f"Linea lider por monto: {_top_name(rankings.get('lineas_por_monto', []))}.",
            f"Producto lider por monto: {_top_name(rankings.get('productos_por_monto', []))}.",
            "",
            "## 6. Cruces futuros",
            "Indice SHF, salario minimo e IMSS derechohabientes quedan como cruces futuros pendientes. No se interpretan todavia como variables integradas.",
            "",
            "## 7. Nota metodologica",
        ]
    )
    lines.extend(f"- {note}" for note in notes)
    if warnings:
        lines.extend(f"- Advertencia: {warning}" for warning in warnings)
    else:
        lines.append("- No se detectaron advertencias metodologicas relevantes.")
    return "\n".join(lines).strip() + "\n"


def save_extended_report_outputs(report_json: dict[str, Any], markdown: str, output_dir) -> tuple[Path, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / "mini_report_extended.json"
    markdown_path = output_path / "mini_report_extended.md"
    json_path.write_text(json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    return json_path, markdown_path


def generate_extended_report(context: dict[str, Any], output_dir=None) -> tuple[dict[str, Any], str]:
    report_json = build_extended_report_json(context)
    markdown = render_extended_report_markdown(report_json)
    if output_dir is not None:
        save_extended_report_outputs(report_json, markdown, output_dir)
    return report_json, markdown
