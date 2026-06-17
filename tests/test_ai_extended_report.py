import json

import httpx

from ai_extended_report import (
    build_ai_response_payload,
    generate_ai_extended_insight,
    render_ai_insight_markdown,
)


class _FakeResponse:
    def __init__(self, content):
        self._content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def _extended_report():
    return {
        "period": {"current_year": 2026, "previous_year": 2025, "month_limit": 4},
        "summary": {
            "monto_variacion_pct": 15.93,
            "creditos_variacion_pct": 32.18,
            "ticket_promedio_variacion_pct": -12.29,
        },
        "inflation_context": {
            "available": True,
            "monto_variacion_real_pct": 11.24,
            "ticket_variacion_real_pct": -15.84,
        },
        "line_family_analysis": {"available": True, "families": []},
        "rankings": {
            "estados_por_monto": [{"nombre": "Nuevo Leon", "monto": 120.0, "ranking": 1}],
            "estados_por_creditos": [{"nombre": "Jalisco", "creditos": 12.0, "ranking": 1}],
        },
        "methodology": {"warnings": ["Comparacion YTD: no compara anios completos."]},
        "future_crosses": [
            {
                "key": "inflacion_inpc",
                "label": "INPC general",
                "status": "integrado",
                "intended_use": "Deflactar variaciones nominales.",
            },
            {
                "key": "indice_shf",
                "label": "\u00cdndice SHF de Precios de la Vivienda",
                "status": "pendiente",
                "intended_use": "Contrastar contra precios de vivienda.",
            },
            {"key": "salario_minimo", "label": "Salario minimo", "status": "pendiente", "intended_use": ""},
            {
                "key": "imss_derechohabientes",
                "label": "Derechohabientes IMSS",
                "status": "pendiente",
                "intended_use": "",
            },
        ],
    }


def _ai_payload(**overrides):
    payload = {
        "available": True,
        "executive_thesis": "La colocacion crece en terminos reales, aunque el ticket promedio retrocede.",
        "executive_implication": "La lectura ejecutiva debe separar volumen, monto y composicion antes de interpretar el crecimiento.",
        "key_findings": ["Monto real positivo.", "Creditos al alza.", "Ticket real negativo."],
        "state_level_reading": "Nuevo Leon lidera por monto y Jalisco lidera por creditos, sin inferir causalidad regional.",
        "mix_effect_reading": "El efecto mezcla sugiere mayor peso de productos con ticket menor.",
        "real_vs_nominal_reading": "La lectura real confirma crecimiento de monto menor al nominal.",
        "risks_or_caveats": ["Comparacion YTD.", "No hay SHF integrado."],
        "recommended_next_crosses": ["indice SHF", "salario minimo", "IMSS derechohabientes"],
        "analytical_questions": ["Que estados explican el cambio?", "Que producto presiona ticket?"],
        "linkedin_angle": "El crecimiento real y el efecto mezcla cuentan una historia mas fina que el nominal.",
        "confidence": "medium",
    }
    payload.update(overrides)
    return payload


def _mock_openai(monkeypatch, payload):
    monkeypatch.setattr("ai_extended_report.httpx.post", lambda *args, **kwargs: _FakeResponse(json.dumps(payload)))


def test_generate_ai_extended_insight_returns_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert generate_ai_extended_insight(_extended_report()) == {
        "available": False,
        "reason": "AI service not configured",
    }


def test_generate_ai_extended_insight_returns_structured_payload(monkeypatch):
    calls = []
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _FakeResponse(__import__("json").dumps(_ai_payload()))

    monkeypatch.setattr("ai_extended_report.httpx.post", fake_post)

    result = generate_ai_extended_insight(_extended_report())

    assert result["available"] is True
    assert result["executive_implication"]
    assert result["confidence"] == "medium"
    assert result["state_level_reading"]
    assert calls[0]["json"]["model"] == "gpt-4.1-mini"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"


def test_generate_ai_extended_insight_prompt_includes_analysis_frame(monkeypatch):
    calls = []
    report = _extended_report()
    report["analysis_frame"] = {
        "main_signal": "creditos_y_monto_crecen_con_ticket_promedio_a_la_baja",
        "mix_effect_direction": "mayor_peso_de_familia_con_ticket_menor_presiona_ticket_agregado",
    }
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_post(url, headers, json, timeout):
        calls.append(json)
        return _FakeResponse(__import__("json").dumps(_ai_payload()))

    monkeypatch.setattr("ai_extended_report.httpx.post", fake_post)

    assert generate_ai_extended_insight(report)["available"] is True
    user_prompt = calls[0]["messages"][1]["content"]
    assert '"analysis_frame"' in user_prompt
    assert "creditos_y_monto_crecen_con_ticket_promedio_a_la_baja" in user_prompt


def test_generate_ai_extended_insight_uses_configured_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "custom-model")

    def fake_post(url, headers, json, timeout):
        assert json["model"] == "custom-model"
        return _FakeResponse(__import__("json").dumps(_ai_payload()))

    monkeypatch.setattr("ai_extended_report.httpx.post", fake_post)

    assert generate_ai_extended_insight(_extended_report())["available"] is True


def test_generate_ai_extended_insight_limits_key_findings_to_five(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    findings = [f"Hallazgo {idx}" for idx in range(1, 8)]
    _mock_openai(monkeypatch, _ai_payload(key_findings=findings))

    result = generate_ai_extended_insight(_extended_report())

    assert result["available"] is True
    assert result["key_findings"] == findings[:5]


def test_generate_ai_extended_insight_invalid_confidence_defaults_to_medium(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    _mock_openai(monkeypatch, _ai_payload(confidence="very-high"))

    result = generate_ai_extended_insight(_extended_report())

    assert result["available"] is True
    assert result["confidence"] == "medium"


def test_generate_ai_extended_insight_adds_quality_flag_for_redundancy(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    repeated = "Monto creditos ticket familia estado periodo comparable. " * 3
    _mock_openai(
        monkeypatch,
        _ai_payload(
            executive_thesis=repeated,
            executive_implication=repeated,
            mix_effect_reading=repeated,
            real_vs_nominal_reading=repeated,
            key_findings=[repeated, repeated, repeated],
        ),
    )

    result = generate_ai_extended_insight(_extended_report())

    assert result["available"] is True
    assert "possible_redundancy" in result["quality_flags"]


def test_generate_ai_extended_insight_maps_legacy_committee_questions(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    payload = _ai_payload()
    payload["committee_questions"] = ["Que estado lidera por monto?"]
    del payload["analytical_questions"]
    _mock_openai(monkeypatch, payload)

    result = generate_ai_extended_insight(_extended_report())

    assert result["available"] is True
    assert result["analytical_questions"] == ["Que estado lidera por monto?"]
    assert "committee_questions" not in result


def test_generate_ai_extended_insight_missing_required_field_returns_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    payload = _ai_payload()
    del payload["executive_thesis"]
    _mock_openai(monkeypatch, payload)

    assert generate_ai_extended_insight(_extended_report()) == {
        "available": False,
        "reason": "AI service unavailable",
    }


def test_generate_ai_extended_insight_missing_executive_implication_returns_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    payload = _ai_payload()
    del payload["executive_implication"]
    _mock_openai(monkeypatch, payload)

    assert generate_ai_extended_insight(_extended_report()) == {
        "available": False,
        "reason": "AI service unavailable",
    }


def test_generate_ai_extended_insight_requires_state_reading_when_state_rankings_exist(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    _mock_openai(monkeypatch, _ai_payload(state_level_reading=""))

    assert generate_ai_extended_insight(_extended_report()) == {
        "available": False,
        "reason": "AI service unavailable",
    }


def test_generate_ai_extended_insight_uses_full_future_cross_labels(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    _mock_openai(monkeypatch, _ai_payload(recommended_next_crosses=["indice SHF", "salario minimo"]))

    result = generate_ai_extended_insight(_extended_report())

    assert "\u00cdndice SHF de Precios de la Vivienda" in result["recommended_next_crosses"]
    assert "indice SHF" not in result["recommended_next_crosses"]
    assert "Salario minimo" in result["recommended_next_crosses"]
    assert "Derechohabientes IMSS" in result["recommended_next_crosses"]


def test_generate_ai_extended_insight_recommended_crosses_only_uses_pending_future_crosses(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    _mock_openai(
        monkeypatch,
        _ai_payload(
            recommended_next_crosses=[
                "composicion por familia",
                "monto colocado",
                "creditos",
                "ticket promedio",
                "rankings por estado",
                "inflacion INPC",
                "indice SHF",
            ]
        ),
    )

    result = generate_ai_extended_insight(_extended_report())

    assert result["recommended_next_crosses"] == [
        "\u00cdndice SHF de Precios de la Vivienda",
        "Salario minimo",
        "Derechohabientes IMSS",
    ]


def test_generate_ai_extended_insight_filters_unsupported_terms(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    _mock_openai(
        monkeypatch,
        _ai_payload(
            key_findings=[
                "El monto real crece.",
                "La demanda de creditos aumento.",
                "El ticket promedio baja.",
            ],
            analytical_questions=[
                "Que estado lidera por monto?",
                "Como cambia el riesgo crediticio?",
                "Que familia pesa mas en creditos?",
            ],
        ),
    )

    result = generate_ai_extended_insight(_extended_report())
    joined = " ".join(result["key_findings"] + result["analytical_questions"]).lower()

    assert result["available"] is True
    assert "demanda" not in joined
    assert "riesgo crediticio" not in joined


def test_generate_ai_extended_insight_falls_back_when_text_field_has_unsupported_terms(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    _mock_openai(monkeypatch, _ai_payload(executive_thesis="La demanda explica el resultado."))

    assert generate_ai_extended_insight(_extended_report()) == {
        "available": False,
        "reason": "AI service unavailable",
    }


def test_ai_output_preserves_accents_in_json_and_markdown(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    payload = _ai_payload(
        executive_thesis="El cr\u00e9dito muestra una lectura prudente para adquisici\u00f3n.",
        key_findings=[
            "Los cr\u00e9ditos formalizados aumentaron.",
            "La adquisici\u00f3n de vivienda existente gan\u00f3 peso.",
            "\u00bfCu\u00e1l es el siguiente cruce metodol\u00f3gico?",
        ],
        analytical_questions=["\u00bfCu\u00e1l familia explica m\u00e1s el cambio?"],
    )

    monkeypatch.setattr(
        "ai_extended_report.httpx.post",
        lambda *args, **kwargs: _FakeResponse(json.dumps(payload, ensure_ascii=False)),
    )

    result = generate_ai_extended_insight(_extended_report())
    response_payload = build_ai_response_payload(_extended_report(), result)
    markdown = render_ai_insight_markdown(response_payload)

    json.dumps(response_payload, ensure_ascii=False)
    assert "cr\u00e9dito" in result["executive_thesis"]
    assert "adquisici\u00f3n" in markdown
    assert "\u00bfCu\u00e1l" in markdown


def test_generate_ai_extended_insight_repairs_mojibake_and_polishes_domain_terms(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    payload = _ai_payload(
        executive_thesis="El cr\u00c3\u00a9dito tiene crecimiento s\u00c3\u00b3lido en cr\u00c3\u00a9ditos otorgados.",
        key_findings=[
            "Los cr\u00c3\u00a9ditos otorgados aumentaron.",
            "El crecimiento s\u00c3\u00b3lido del monto se mantiene.",
            "La adquisici\u00c3\u00b3n gana peso.",
        ],
        linkedin_angle="Crecimiento s\u00c3\u00b3lido en cr\u00c3\u00a9ditos otorgados.",
    )

    monkeypatch.setattr(
        "ai_extended_report.httpx.post",
        lambda *args, **kwargs: _FakeResponse(json.dumps(payload, ensure_ascii=False)),
    )

    result = generate_ai_extended_insight(_extended_report())
    joined = json.dumps(result, ensure_ascii=False)

    assert result["available"] is True
    assert "cr\u00e9dito" in joined
    assert "cr\u00e9ditos formalizados" in joined
    assert "crecimiento observado" in joined
    assert "otorgados" not in joined
    assert "cr\u00c3" not in joined
    assert "\u00c2" not in joined


def test_generate_ai_extended_insight_invalid_json_returns_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("ai_extended_report.httpx.post", lambda *args, **kwargs: _FakeResponse("not-json"))

    assert generate_ai_extended_insight(_extended_report()) == {
        "available": False,
        "reason": "AI service unavailable",
    }


def test_generate_ai_extended_insight_exception_returns_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_post(*args, **kwargs):
        raise httpx.ConnectError("connect failed")

    monkeypatch.setattr("ai_extended_report.httpx.post", fake_post)

    assert generate_ai_extended_insight(_extended_report()) == {
        "available": False,
        "reason": "AI service unavailable",
    }


def test_generate_ai_extended_insight_skips_prompt_with_sensitive_marker(monkeypatch):
    report = _extended_report()
    report["methodology"]["warnings"].append("DATABASE_URL=postgresql://secret")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert generate_ai_extended_insight(report) == {
        "available": False,
        "reason": "AI service unavailable",
    }


def test_ai_response_payload_and_markdown_render_expected_sections():
    payload = build_ai_response_payload(_extended_report(), _ai_payload())
    markdown = render_ai_insight_markdown(payload)

    json.dumps(payload)
    assert payload["ai_insight"]["available"] is True
    assert payload["metadata"]["prompt_version"] == "ai_extended_report_system.v1"
    assert payload["metadata"]["engine_version"] == "extended_report.v1"
    assert "# Análisis asistido INFONAVIT" in markdown
    assert "## Metadata" in markdown
    assert "## Tesis ejecutiva" in markdown
    assert "## Implicación ejecutiva" in markdown
    assert "## Hallazgos clave" in markdown
    assert "## Lectura estatal" in markdown
    assert "## Preguntas para siguiente análisis" in markdown
    assert "## Ángulo para comunicación" in markdown
    assert "## Preguntas para comite" not in markdown


def test_ai_markdown_renders_fallback_message():
    markdown = render_ai_insight_markdown({"ai_insight": {"available": False, "reason": "AI service not configured"}})

    assert "Análisis asistido no disponible: AI service not configured." in markdown
