from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

INFLATION_SERVICE_UNAVAILABLE_REASON = "Inflation service not configured or unavailable"
DEFAULT_TIMEOUT_SECONDS = 20.0
MAX_TIMEOUT_SECONDS = 60.0


def _get_timeout_seconds() -> float:
    raw_value = os.getenv("INFLACION_COPILOT_TIMEOUT_SECONDS")
    if raw_value is None:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        timeout = float(raw_value)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    if timeout <= 0:
        return DEFAULT_TIMEOUT_SECONDS
    return min(timeout, MAX_TIMEOUT_SECONDS)


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

    timeout = _get_timeout_seconds()
    response = None
    for attempt in (1, 2):
        try:
            response = httpx.get(url, params=params, timeout=timeout)
            break
        except httpx.ReadTimeout:
            logger.warning("Inflation service timeout attempt=%s", attempt)
            if attempt == 2:
                return None
        except httpx.HTTPError as exc:
            logger.warning("Inflation service request failed error_type=%s", type(exc).__name__)
            return None

    try:
        if response is None:
            return None
        if response.status_code != 200:
            logger.warning("Inflation service unavailable status_code=%s", response.status_code)
            return None
        payload = response.json()
    except ValueError as exc:
        logger.warning("Inflation service request failed error_type=%s", type(exc).__name__)
        return None

    if not isinstance(payload, dict) or not _is_valid_inflation_payload(payload):
        logger.warning("Inflation service returned invalid payload")
        return None
    return payload
