import json

from mini_report import (
    SECTION_IDS,
    build_mini_report_json,
    generate_mini_report,
    render_mini_report_markdown,
    save_mini_report_outputs,
)


def _ai_context(warnings=None):
    return {
        "periodo": {
            "current_year": 2026,
            "previous_year": 2025,
            "month_limit": 4,
            "comparability": "YTD comparable",
        },
        "summary": {
            "monto_actual": 120.0,
            "monto_previo": 100.0,
            "diferencia_abs": 20.0,
            "variacion_pct": 20.0,
        },
        "drivers": {
            "linea_lider": "L2 Nueva",
            "producto_lider": "Producto A",
            "estado_lider": "Nuevo León",
        },
        "pareto_lineas": [
            {
                "linea": "L2 Nueva",
                "monto": 90.0,
                "share": 75.0,
                "share_acumulado": 75.0,
                "ranking": 1,
            }
        ],
        "ranking_estatal": [
            {
                "estado": "Nuevo León",
                "monto": 50.0,
                "share": 41.7,
                "ranking": 1,
            }
        ],
        "warnings": warnings or [],
    }


def test_build_mini_report_json_returns_serializable_dict():
    report = build_mini_report_json(_ai_context())

    assert isinstance(report, dict)
    json.dumps(report)


def test_build_mini_report_json_includes_title_period_sections_and_warnings():
    report = build_mini_report_json(_ai_context(["Comparacion YTD."]))

    assert report["title"] == "Mini reporte ejecutivo INFONAVIT"
    assert report["period"]["current_year"] == 2026
    assert isinstance(report["sections"], list)
    assert report["warnings"] == ["Comparacion YTD."]


def test_build_mini_report_json_generates_expected_sections():
    report = build_mini_report_json(_ai_context())

    assert [section["id"] for section in report["sections"]] == SECTION_IDS


def test_render_mini_report_markdown_returns_string_with_expected_titles():
    markdown = render_mini_report_markdown(build_mini_report_json(_ai_context()))

    assert isinstance(markdown, str)
    assert "Mini reporte ejecutivo INFONAVIT" in markdown
    assert "Resumen YTD comparable" in markdown
    assert "Principales impulsores" in markdown
    assert "Nota metodológica" in markdown


def test_render_mini_report_markdown_includes_warnings_when_present():
    markdown = render_mini_report_markdown(
        build_mini_report_json(_ai_context(["Comparacion YTD: no compara anios completos."]))
    )

    assert "Advertencias:" in markdown
    assert "Comparacion YTD" in markdown


def test_render_mini_report_markdown_handles_empty_warnings():
    markdown = render_mini_report_markdown(build_mini_report_json(_ai_context()))

    assert "No se detectaron advertencias metodologicas relevantes." in markdown
    assert "Advertencias:" not in markdown


def test_save_mini_report_outputs_writes_json_and_markdown(tmp_path):
    report = build_mini_report_json(_ai_context())
    markdown = render_mini_report_markdown(report)

    json_path, markdown_path = save_mini_report_outputs(report, markdown, tmp_path)

    assert json_path.name == "mini_report.json"
    assert markdown_path.name == "mini_report.md"
    assert json.loads(json_path.read_text(encoding="utf-8"))["title"] == report["title"]
    assert "Mini reporte ejecutivo INFONAVIT" in markdown_path.read_text(encoding="utf-8")


def test_generate_mini_report_returns_json_and_markdown():
    report, markdown = generate_mini_report(_ai_context())

    assert report["title"] == "Mini reporte ejecutivo INFONAVIT"
    assert "Mini reporte ejecutivo INFONAVIT" in markdown


def test_build_mini_report_json_handles_empty_lists_without_failing():
    context = _ai_context()
    context["pareto_lineas"] = []
    context["ranking_estatal"] = []

    report, markdown = generate_mini_report(context)

    json.dumps(report)
    assert "No hay datos disponibles" in markdown
