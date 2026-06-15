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
        "rankings": {},
        "methodology": {"warnings": ["Comparacion YTD: no compara anios completos."]},
        "future_crosses": {
            "indice_shf": "pendiente",
            "salario_minimo": "pendiente",
            "imss_derechohabientes": "pendiente",
        },
    }


def _ai_payload(**overrides):
    payload = {
        "available": True,
        "executive_thesis": "La colocacion crece en terminos reales, aunque el ticket promedio retrocede.",
        "key_findings": ["Monto real positivo.", "Creditos al alza.", "Ticket real negativo."],
        "mix_effect_reading": "El efecto mezcla sugiere mayor peso de productos con ticket menor.",
        "real_vs_nominal_reading": "La lectura real confirma crecimiento de monto menor al nominal.",
        "risks_or_caveats": ["Comparacion YTD.", "No hay SHF integrado."],
        "recommended_next_crosses": ["indice SHF", "salario minimo", "IMSS derechohabientes"],
        "committee_questions": ["Que estados explican el cambio?", "Que producto presiona ticket?"],
        "linkedin_angle": "El crecimiento real y el efecto mezcla cuentan una historia mas fina que el nominal.",
        "confidence": "medium",
    }
    payload.update(overrides)
    return payload


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
        return _FakeResponse(json_module.dumps(_ai_payload()))

    import json as json_module

    monkeypatch.setattr("ai_extended_report.httpx.post", fake_post)

    result = generate_ai_extended_insight(_extended_report())

    assert result["available"] is True
    assert result["confidence"] == "medium"
    assert calls[0]["json"]["model"] == "gpt-4.1-mini"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"


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

    def fake_post(*args, **kwargs):
        return _FakeResponse(json.dumps(_ai_payload(key_findings=findings)))

    monkeypatch.setattr("ai_extended_report.httpx.post", fake_post)

    result = generate_ai_extended_insight(_extended_report())

    assert result["available"] is True
    assert result["key_findings"] == findings[:5]


def test_generate_ai_extended_insight_invalid_confidence_defaults_to_medium(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_post(*args, **kwargs):
        return _FakeResponse(json.dumps(_ai_payload(confidence="very-high")))

    monkeypatch.setattr("ai_extended_report.httpx.post", fake_post)

    result = generate_ai_extended_insight(_extended_report())

    assert result["available"] is True
    assert result["confidence"] == "medium"


def test_generate_ai_extended_insight_missing_required_field_returns_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    payload = _ai_payload()
    del payload["executive_thesis"]

    def fake_post(*args, **kwargs):
        return _FakeResponse(json.dumps(payload))

    monkeypatch.setattr("ai_extended_report.httpx.post", fake_post)

    assert generate_ai_extended_insight(_extended_report()) == {
        "available": False,
        "reason": "AI service unavailable",
    }


def test_ai_output_preserves_accents_in_json_and_markdown(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    payload = _ai_payload(
        executive_thesis="El crédito muestra una lectura prudente para adquisición.",
        key_findings=[
            "Los créditos formalizados aumentaron.",
            "La adquisición de vivienda existente ganó peso.",
            "¿Cuál es el siguiente cruce metodológico?",
        ],
        committee_questions=["¿Cuál familia explica más el cambio?"],
    )

    def fake_post(*args, **kwargs):
        return _FakeResponse(json.dumps(payload, ensure_ascii=False))

    monkeypatch.setattr("ai_extended_report.httpx.post", fake_post)

    result = generate_ai_extended_insight(_extended_report())
    response_payload = build_ai_response_payload(_extended_report(), result)
    markdown = render_ai_insight_markdown(response_payload)

    json.dumps(response_payload, ensure_ascii=False)
    assert "crédito" in result["executive_thesis"]
    assert "adquisición" in markdown
    assert "¿Cuál" in markdown


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
    assert "# Analisis asistido INFONAVIT" in markdown
    assert "## Tesis ejecutiva" in markdown
    assert "## Hallazgos clave" in markdown
    assert "## Preguntas para comite" in markdown


def test_ai_markdown_renders_fallback_message():
    markdown = render_ai_insight_markdown({"ai_insight": {"available": False, "reason": "AI service not configured"}})

    assert "Analisis asistido no disponible: AI service not configured." in markdown
