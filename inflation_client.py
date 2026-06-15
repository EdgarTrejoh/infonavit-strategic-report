from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

INFLATION_SERVICE_UNAVAILABLE_REASON = "Inflation service not configured or unavailable"


def _is_valid_inflation_payload(payload: dict[str, Any]) -> bool:
    required = {
        "current_year",
        "previous_year",
        "month_limit",
        "comparability",
        "current_period",
        "previous_period",
        "factor",
        "inflation_pct",
        "source",
        "indicator",
        "method",
    }
    if not required.issubset(payload):
        return False
    try:
        factor = float(payload["factor"])
    except (TypeError, ValueError):
        return False
    return factor > 0


def fetch_average_period_inflation(
    current_year: int,
    previous_year: int,
    month_limit: int,
    base_url: str | None = None,
) -> dict[str, Any] | None:
    service_url = (base_url or os.getenv("INFLACION_COPILOT_URL") or "").strip()
    if not service_url:
        return None

    url = f"{service_url.rstrip('/')}/inflation/average-period"
    params = {
        "current_year": int(current_year),
        "previous_year": int(previous_year),
        "month_limit": int(month_limit),
    }

    try:
        response = httpx.get(url, params=params, timeout=8.0)
        if response.status_code != 200:
            logger.warning("Inflation service unavailable status_code=%s", response.status_code)
            return None
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Inflation service request failed error_type=%s", type(exc).__name__)
        return None

    if not isinstance(payload, dict) or not _is_valid_inflation_payload(payload):
        logger.warning("Inflation service returned invalid payload")
        return None
    return payload
