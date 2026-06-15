from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "ai_extended_report_system.txt"
AI_NOT_CONFIGURED = {"available": False, "reason": "AI service not configured"}
AI_UNAVAILABLE = {"available": False, "reason": "AI service unavailable"}
EXPECTED_KEYS = {
    "available",
    "executive_thesis",
    "key_findings",
    "mix_effect_reading",
    "real_vs_nominal_reading",
    "risks_or_caveats",
    "recommended_next_crosses",
    "committee_questions",
    "linkedin_angle",
    "confidence",
}
LIST_FIELDS = ["key_findings", "risks_or_caveats", "recommended_next_crosses", "committee_questions"]
TEXT_FIELDS = [
    "executive_thesis",
    "mix_effect_reading",
    "real_vs_nominal_reading",
    "linkedin_angle",
]
VALID_CONFIDENCE = {"low", "medium", "high"}
SENSITIVE_MARKERS = {
    "OPENAI_API_KEY",
    "INFONAVIT_API_KEY",
    "DATABASE_URL",
    "DB_PASSWORD",
    "connection string",
    "postgresql://",
    "postgresql+psycopg2://",
}


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _safe_subset(extended_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "period": extended_report.get("period", {}),
        "summary": extended_report.get("summary", {}),
        "inflation_context": extended_report.get("inflation_context", {}),
        "line_family_analysis": extended_report.get("line_family_analysis", {}),
        "rankings": extended_report.get("rankings", {}),
        "methodology": extended_report.get("methodology", {}),
        "warnings": extended_report.get("methodology", {}).get("warnings", []),
        "future_crosses": extended_report.get("future_crosses", {}),
    }


def _validate_minimum_report(extended_report: dict[str, Any]) -> bool:
    required = {"period", "summary", "methodology"}
    return isinstance(extended_report, dict) and required.issubset(extended_report)


def _build_user_prompt(extended_report: dict[str, Any]) -> str:
    safe_report = _safe_subset(extended_report)
    payload = json.dumps(safe_report, ensure_ascii=False, allow_nan=False)
    return (
        "Interpreta el siguiente JSON extendido de INFONAVIT y devuelve unicamente JSON valido con esta estructura: "
        '{"available": true, "executive_thesis": "", "key_findings": [], '
        '"mix_effect_reading": "", "real_vs_nominal_reading": "", "risks_or_caveats": [], '
        '"recommended_next_crosses": [], "committee_questions": [], "linkedin_angle": "", '
        '"confidence": "medium"}.\n\n'
        f"JSON extendido:\n{payload}"
    )


def _contains_sensitive_marker(text: str) -> bool:
    lower_text = text.lower()
    return any(marker.lower() in lower_text for marker in SENSITIVE_MARKERS)


def _normalize_ai_output(payload: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or not EXPECTED_KEYS.issubset(payload):
        return None
    if payload.get("available") is not True:
        return None
    if not all(isinstance(payload.get(field), str) for field in TEXT_FIELDS):
        return None
    if not all(isinstance(payload.get(field), list) for field in LIST_FIELDS):
        return None

    normalized = dict(payload)
    for field in LIST_FIELDS:
        normalized[field] = [str(item) for item in normalized[field]]
    normalized["key_findings"] = normalized["key_findings"][:5]
    if normalized.get("confidence") not in VALID_CONFIDENCE:
        normalized["confidence"] = "medium"
    return normalized


def _call_openai_chat(system_prompt: str, user_prompt: str, api_key: str, model: str) -> dict[str, Any]:
    response = httpx.post(
        OPENAI_CHAT_COMPLETIONS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def generate_ai_extended_insight(extended_report: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return AI_NOT_CONFIGURED.copy()
    if not _validate_minimum_report(extended_report):
        return AI_UNAVAILABLE.copy()

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    system_prompt = _load_system_prompt()
    user_prompt = _build_user_prompt(extended_report)
    if _contains_sensitive_marker(user_prompt):
        logger.warning("AI insight skipped because prompt contains sensitive marker")
        return AI_UNAVAILABLE.copy()

    try:
        payload = _call_openai_chat(system_prompt, user_prompt, api_key, model)
    except Exception as exc:
        logger.warning("AI insight generation failed error_type=%s", type(exc).__name__)
        return AI_UNAVAILABLE.copy()

    normalized_payload = _normalize_ai_output(payload)
    if normalized_payload is None:
        logger.warning("AI insight generation returned invalid payload")
        return AI_UNAVAILABLE.copy()
    return normalized_payload


def build_ai_response_payload(extended_report: dict[str, Any], ai_insight: dict[str, Any]) -> dict[str, Any]:
    period = extended_report.get("period", {})
    summary = extended_report.get("summary", {})
    inflation = extended_report.get("inflation_context", {})
    return {
        "period": period,
        "extended_report_summary": {
            "monto_variacion_pct": summary.get("monto_variacion_pct"),
            "monto_variacion_real_pct": inflation.get("monto_variacion_real_pct"),
            "creditos_variacion_pct": summary.get("creditos_variacion_pct"),
            "ticket_promedio_variacion_pct": summary.get("ticket_promedio_variacion_pct"),
            "ticket_variacion_real_pct": inflation.get("ticket_variacion_real_pct"),
            "inflation_available": inflation.get("available"),
            "line_family_analysis_available": extended_report.get("line_family_analysis", {}).get("available"),
        },
        "ai_insight": ai_insight,
    }


def render_ai_insight_markdown(payload: dict[str, Any]) -> str:
    insight = payload.get("ai_insight", {})
    if not insight.get("available"):
        reason = insight.get("reason", "AI service unavailable")
        return f"# Analisis asistido INFONAVIT\n\nAnalisis asistido no disponible: {reason}.\n"

    lines = [
        "# Analisis asistido INFONAVIT",
        "",
        "## Tesis ejecutiva",
        insight.get("executive_thesis", ""),
        "",
        "## Hallazgos clave",
    ]
    lines.extend(f"- {item}" for item in insight.get("key_findings", []))
    lines.extend(
        [
            "",
            "## Lectura real vs nominal",
            insight.get("real_vs_nominal_reading", ""),
            "",
            "## Efecto mezcla",
            insight.get("mix_effect_reading", ""),
            "",
            "## Riesgos y cautelas",
        ]
    )
    lines.extend(f"- {item}" for item in insight.get("risks_or_caveats", []))
    lines.extend(["", "## Preguntas para comite"])
    lines.extend(f"- {item}" for item in insight.get("committee_questions", []))
    lines.extend(["", "## Siguientes cruces recomendados"])
    lines.extend(f"- {item}" for item in insight.get("recommended_next_crosses", []))
    lines.extend(["", "## Angulo para comunicacion", insight.get("linkedin_angle", "")])
    return "\n".join(lines).strip() + "\n"
