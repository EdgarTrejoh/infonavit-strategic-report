from __future__ import annotations

from typing import Any


MOJIBAKE_MARKERS = ("\u00c3", "\u00c2")


def repair_mojibake_text(value: Any) -> str:
    text = "" if value is None else str(value)
    for _ in range(3):
        if not any(marker in text for marker in MOJIBAKE_MARKERS):
            break
        repaired = None
        for encoding in ("cp1252", "latin1"):
            try:
                repaired = text.encode(encoding).decode("utf-8")
                break
            except UnicodeError:
                continue
        if repaired is None:
            break
        if not repaired or repaired == text:
            break
        text = repaired
    return text


def normalize_text_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalize_text_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_text_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(normalize_text_payload(item) for item in value)
    if isinstance(value, str):
        return repair_mojibake_text(value)
    return value
