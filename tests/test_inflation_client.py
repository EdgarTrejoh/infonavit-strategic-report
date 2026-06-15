import httpx

from inflation_client import fetch_average_period_inflation


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def _inflation_payload():
    return {
        "current_year": 2026,
        "previous_year": 2025,
        "month_limit": 4,
        "comparability": "YTD comparable",
        "current_period": {"start_date": "2026-01-01", "end_date": "2026-04-01", "avg_inpc": 144.8175},
        "previous_period": {"start_date": "2025-01-01", "end_date": "2025-04-01", "avg_inpc": 138.9625},
        "factor": 1.0421336691553478,
        "inflation_pct": 4.2133669155347775,
        "source": "INEGI / BigQuery",
        "indicator": "INPC - General",
        "method": "inflation_pct = ((avg_inpc_current_period / avg_inpc_previous_period) - 1) * 100",
    }


def test_fetch_average_period_inflation_builds_expected_request(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return _FakeResponse(payload=_inflation_payload())

    monkeypatch.setattr("inflation_client.httpx.get", fake_get)

    payload = fetch_average_period_inflation(
        current_year=2026,
        previous_year=2025,
        month_limit=4,
        base_url="https://inflacion.example.test/",
    )

    assert payload["inflation_pct"] == 4.2133669155347775
    assert calls == [
        {
            "url": "https://inflacion.example.test/inflation/average-period",
            "params": {"current_year": 2026, "previous_year": 2025, "month_limit": 4},
            "timeout": 8.0,
        }
    ]


def test_fetch_average_period_inflation_returns_none_without_base_url(monkeypatch):
    monkeypatch.delenv("INFLACION_COPILOT_URL", raising=False)

    assert fetch_average_period_inflation(2026, 2025, 4) is None


def test_fetch_average_period_inflation_returns_none_on_http_error(monkeypatch):
    monkeypatch.setattr("inflation_client.httpx.get", lambda *args, **kwargs: _FakeResponse(status_code=500))

    assert fetch_average_period_inflation(2026, 2025, 4, base_url="https://inflacion.example.test") is None


def test_fetch_average_period_inflation_returns_none_on_timeout(monkeypatch):
    def fake_get(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("inflation_client.httpx.get", fake_get)

    assert fetch_average_period_inflation(2026, 2025, 4, base_url="https://inflacion.example.test") is None
