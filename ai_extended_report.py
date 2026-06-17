from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

import httpx
from text_normalization import normalize_text_payload, repair_mojibake_text

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
PROMPT_VERSION = "ai_extended_report_system.v1"
ENGINE_VERSION = "extended_report.v1"
OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "ai_extended_report_system.txt"
AI_NOT_CONFIGURED = {"available": False, "reason": "AI service not configured"}
AI_UNAVAILABLE = {"available": False, "reason": "AI service unavailable"}
EXPECTED_KEYS = {
    "available",
    "executive_thesis",
    "executive_implication",
    "key_findings",
    "state_level_reading",
    "mix_effect_reading",
    "real_vs_nominal_reading",
    "risks_or_caveats",
    "recommended_next_crosses",
    "analytical_questions",
    "linkedin_angle",
    "confidence",
}
LEGACY_KEYS = {"committee_questions"}
LIST_FIELDS = ["key_findings", "risks_or_caveats", "recommended_next_crosses", "analytical_questions"]
TEXT_FIELDS = [
    "executive_thesis",
    "executive_implication",
    "state_level_reading",
    "mix_effect_reading",
    "real_vs_nominal_reading",
    "linkedin_angle",
]
VALID_CONFIDENCE = {"low", "medium", "high"}
PROHIBITED_UNSUPPORTED_TERMS = [
    "demanda",
    "riesgo crediticio",
    "calidad del portafolio",
    "rentabilidad",
    "estrategia",
    "mora",
    "perdida esperada",
    "originacion",
    "apetito de riesgo",
    "comportamiento del acreditado",
]
SENSITIVE_MARKERS = {
    "OPENAI_API_KEY",
    "INFONAVIT_API_KEY",
    "DATABASE_URL",
    "DB_PASSWORD",
    "connection string",
    "postgresql://",
    "postgresql+psycopg2://",
}
PHRASE_REPLACEMENTS = {
    "créditos otorgados": "créditos formalizados",
    "credito otorgado": "credito formalizado",
    "crédito otorgado": "crédito formalizado",
    "otorgados": "formalizados",
    "otorgado": "formalizado",
    "crecimiento sólido": "crecimiento observado",
    "crecimiento solido": "crecimiento observado",
}
PHRASE_REPLACEMENTS.update(
    {
        "creditos otorgados": "creditos formalizados",
        "cr\u00e9ditos otorgados": "cr\u00e9ditos formalizados",
        "creditos otorgado": "creditos formalizado",
        "cr\u00e9dito otorgado": "cr\u00e9dito formalizado",
        "crecimiento s\u00f3lido": "crecimiento observado",
    }
)


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _safe_subset(extended_report: dict[str, Any]) -> dict[str, Any]:
    return normalize_text_payload({
        "period": extended_report.get("period", {}),
        "summary": extended_report.get("summary", {}),
        "inflation_context": extended_report.get("inflation_context", {}),
        "line_family_analysis": extended_report.get("line_family_analysis", {}),
        "rankings": extended_report.get("rankings", {}),
        "analysis_frame": extended_report.get("analysis_frame", {}),
        "methodology": extended_report.get("methodology", {}),
        "warnings": extended_report.get("methodology", {}).get("warnings", []),
        "future_crosses": extended_report.get("future_crosses", {}),
    })


def _validate_minimum_report(extended_report: dict[str, Any]) -> bool:
    required = {"period", "summary", "methodology"}
    return isinstance(extended_report, dict) and required.issubset(extended_report)


def _build_user_prompt(extended_report: dict[str, Any]) -> str:
    safe_report = _safe_subset(extended_report)
    payload = json.dumps(safe_report, ensure_ascii=False, allow_nan=False)
    return (
        "Interpreta el siguiente JSON extendido de INFONAVIT y devuelve unicamente JSON valido con esta estructura: "
        '{"available": true, "executive_thesis": "", "executive_implication": "", "key_findings": [], '
        '"state_level_reading": "", "mix_effect_reading": "", "real_vs_nominal_reading": "", '
        '"risks_or_caveats": [], "recommended_next_crosses": [], "analytical_questions": [], "linkedin_angle": "", '
        '"confidence": "medium"}.\n\n'
        f"JSON extendido:\n{payload}"
    )


def _polish_ai_text(value: Any) -> str:
    text = repair_mojibake_text(value)
    for source, replacement in PHRASE_REPLACEMENTS.items():
        text = re.sub(re.escape(source), replacement, text, flags=re.IGNORECASE)
    return text


def _contains_sensitive_marker(text: str) -> bool:
    lower_text = text.lower()
    return any(marker.lower() in lower_text for marker in SENSITIVE_MARKERS)


def _normalize_for_match(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.lower().split())


def _contains_unsupported_terms(text: str, extended_report: dict[str, Any]) -> bool:
    report_text = _normalize_for_match(json.dumps(_safe_subset(extended_report), ensure_ascii=False, default=str))
    normalized_text = _normalize_for_match(text)
    for term in PROHIBITED_UNSUPPORTED_TERMS:
        normalized_term = _normalize_for_match(term)
        if re.search(rf"\b{re.escape(normalized_term)}\b", normalized_text) and normalized_term not in report_text:
            return True
    return False


def _future_cross_items(extended_report: dict[str, Any]) -> list[dict[str, str]]:
    future_crosses = extended_report.get("future_crosses", [])
    if isinstance(future_crosses, list):
        return [
            {
                "key": str(item.get("key", "")),
                "label": repair_mojibake_text(item["label"]),
            }
            for item in future_crosses
            if isinstance(item, dict) and item.get("label") and item.get("status") != "integrado"
        ]
    if isinstance(future_crosses, dict):
        items = []
        if "indice_shf" in future_crosses:
            items.append({"key": "indice_shf", "label": "Índice SHF de Precios de la Vivienda"})
        if "salario_minimo" in future_crosses:
            items.append({"key": "salario_minimo", "label": "Salario minimo"})
        if "imss_derechohabientes" in future_crosses:
            items.append({"key": "imss_derechohabientes", "label": "Derechohabientes IMSS"})
        for item in items:
            item["label"] = repair_mojibake_text(item["label"])
        return items
    return []


def _normalize_recommended_crosses(items: list[str], extended_report: dict[str, Any]) -> list[str]:
    pending_items = _future_cross_items(extended_report)
    if not pending_items:
        return []

    normalized = []
    for item in items:
        text = str(item)
        normalized_text = _normalize_for_match(text)
        replacement = None
        for pending in pending_items:
            key = _normalize_for_match(pending["key"])
            label = _normalize_for_match(pending["label"])
            if key and key in normalized_text or label and label in normalized_text:
                replacement = pending["label"]
                break
            if "shf" in normalized_text and "shf" in label:
                replacement = pending["label"]
                break
            if "salario" in normalized_text and "salario" in label:
                replacement = pending["label"]
                break
            if ("imss" in normalized_text or "derechohabientes" in normalized_text) and "imss" in label:
                replacement = pending["label"]
                break
        if replacement and replacement not in normalized:
            normalized.append(replacement)

    for pending in pending_items:
        if pending["label"] not in normalized:
            normalized.append(pending["label"])
    return normalized


def _has_state_rankings(extended_report: dict[str, Any]) -> bool:
    rankings = extended_report.get("rankings", {})
    return bool(rankings.get("estados_por_monto") or rankings.get("estados_por_creditos"))


def _dominant_tokens(text: str) -> set[str]:
    stopwords = {
        "para",
        "como",
        "con",
        "del",
        "por",
        "los",
        "las",
        "una",
        "uno",
        "que",
        "este",
        "esta",
        "entre",
        "reporte",
        "analisis",
        "infonavit",
    }
    normalized = _normalize_for_match(text)
    return {
        token
        for token in re.findall(r"[a-z0-9_]+", normalized)
        if len(token) >= 6 and token not in stopwords
    }


def _detect_quality_flags(normalized: dict[str, Any]) -> list[str]:
    text_blocks = [
        normalized.get("executive_thesis", ""),
        normalized.get("executive_implication", ""),
        normalized.get("mix_effect_reading", ""),
        normalized.get("real_vs_nominal_reading", ""),
        " ".join(normalized.get("key_findings", [])),
    ]
    token_sets = [_dominant_tokens(text) for text in text_blocks if text]
    comparisons = 0
    high_overlap = 0
    for idx, left in enumerate(token_sets):
        for right in token_sets[idx + 1 :]:
            if not left or not right:
                continue
            comparisons += 1
            overlap = len(left & right) / max(1, min(len(left), len(right)))
            if overlap >= 0.65:
                high_overlap += 1
    return ["possible_redundancy"] if comparisons and high_overlap >= 2 else []


def _normalize_ai_output(payload: dict[str, Any], extended_report: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    if "analytical_questions" not in payload and "committee_questions" in payload:
        payload = dict(payload)
        payload["analytical_questions"] = payload.get("committee_questions")
    if not EXPECTED_KEYS.issubset(payload):
        return None
    if payload.get("available") is not True:
        return None
    if not all(isinstance(payload.get(field), str) for field in TEXT_FIELDS):
        return None
    if not all(isinstance(payload.get(field), list) for field in LIST_FIELDS):
        return None
    if _has_state_rankings(extended_report) and not payload.get("state_level_reading", "").strip():
        return None

    normalized = dict(payload)
    for field in LIST_FIELDS:
        polished_items = [_polish_ai_text(item) for item in normalized[field]]
        normalized[field] = [
            item for item in polished_items if not _contains_unsupported_terms(item, extended_report)
        ]
    normalized["key_findings"] = normalized["key_findings"][:5]
    normalized["analytical_questions"] = normalized["analytical_questions"][:5]
    normalized["recommended_next_crosses"] = _normalize_recommended_crosses(
        normalized["recommended_next_crosses"], extended_report
    )
    for field in TEXT_FIELDS:
        normalized[field] = _polish_ai_text(normalized[field])
        if _contains_unsupported_terms(normalized[field], extended_report):
            return None
    if normalized.get("confidence") not in VALID_CONFIDENCE:
        normalized["confidence"] = "medium"
    normalized["quality_flags"] = _detect_quality_flags(normalized)
    normalized.pop("committee_questions", None)
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

    normalized_payload = _normalize_ai_output(payload, extended_report)
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
        "metadata": {
            "ai_model": os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            "prompt_version": PROMPT_VERSION,
            "engine_version": ENGINE_VERSION,
        },
    }


def render_ai_insight_markdown(payload: dict[str, Any]) -> str:
    insight = payload.get("ai_insight", {})
    if not insight.get("available"):
        reason = insight.get("reason", "AI service unavailable")
        return f"# Análisis asistido INFONAVIT\n\nAnálisis asistido no disponible: {reason}.\n"

    period = payload.get("period", {})
    summary = payload.get("extended_report_summary", {})
    metadata = payload.get("metadata", {})
    confidence = insight.get("confidence", "medium")
    inflation_text = "no disponible"
    if summary.get("inflation_available"):
        inflation_text = "disponible"

    lines = [
        "# Análisis asistido INFONAVIT",
        "",
        "## Metadata",
        f"- Periodo: {period.get('current_year')} vs {period.get('previous_year')}",
        f"- Comparabilidad: {period.get('comparability', 'YTD comparable')}",
        f"- Corte mensual: {period.get('month_limit')}",
        f"- Inflación INPC: {inflation_text}",
        f"- Confianza analítica: {confidence}",
        f"- Modelo IA: {metadata.get('ai_model', DEFAULT_OPENAI_MODEL)}",
        "",
        "## Tesis ejecutiva",
        insight.get("executive_thesis", ""),
        "",
        "## Implicación ejecutiva",
        insight.get("executive_implication", ""),
        "",
        "## Hallazgos clave",
    ]
    lines.extend(f"- {item}" for item in insight.get("key_findings", []))
    lines.extend(
        [
            "",
            "## Lectura estatal",
            insight.get("state_level_reading", ""),
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
    lines.extend(["", "## Preguntas para siguiente análisis"])
    lines.extend(f"- {item}" for item in insight.get("analytical_questions", []))
    lines.extend(["", "## Siguientes cruces recomendados"])
    lines.extend(f"- {item}" for item in insight.get("recommended_next_crosses", []))
    if insight.get("quality_flags"):
        lines.extend(["", "## Alertas de calidad narrativa"])
        lines.extend(f"- {item}" for item in insight.get("quality_flags", []))
    lines.extend(["", "## Ángulo para comunicación", insight.get("linkedin_angle", "")])
    return "\n".join(lines).strip() + "\n"
