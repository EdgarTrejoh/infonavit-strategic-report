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


def test_fetch_average_period_inflation_builds_expected_request_with_default_timeout(monkeypatch):
    calls = []
    monkeypatch.delenv("INFLACION_COPILOT_TIMEOUT_SECONDS", raising=False)

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
            "timeout": 20.0,
        }
    ]


def test_fetch_average_period_inflation_uses_valid_timeout_env(monkeypatch):
    calls = []
    monkeypatch.setenv("INFLACION_COPILOT_TIMEOUT_SECONDS", "12.5")

    def fake_get(url, params, timeout):
        calls.append(timeout)
        return _FakeResponse(payload=_inflation_payload())

    monkeypatch.setattr("inflation_client.httpx.get", fake_get)

    fetch_average_period_inflation(2026, 2025, 4, base_url="https://inflacion.example.test")

    assert calls == [12.5]


def test_fetch_average_period_inflation_caps_timeout_env(monkeypatch):
    calls = []
    monkeypatch.setenv("INFLACION_COPILOT_TIMEOUT_SECONDS", "120")

    def fake_get(url, params, timeout):
        calls.append(timeout)
        return _FakeResponse(payload=_inflation_payload())

    monkeypatch.setattr("inflation_client.httpx.get", fake_get)

    fetch_average_period_inflation(2026, 2025, 4, base_url="https://inflacion.example.test")

    assert calls == [60.0]


def test_fetch_average_period_inflation_uses_default_for_invalid_timeout_env(monkeypatch):
    calls = []
    monkeypatch.setenv("INFLACION_COPILOT_TIMEOUT_SECONDS", "not-a-number")

    def fake_get(url, params, timeout):
        calls.append(timeout)
        return _FakeResponse(payload=_inflation_payload())

    monkeypatch.setattr("inflation_client.httpx.get", fake_get)

    fetch_average_period_inflation(2026, 2025, 4, base_url="https://inflacion.example.test")

    assert calls == [20.0]


def test_fetch_average_period_inflation_uses_default_for_non_positive_timeout_env(monkeypatch):
    calls = []
    monkeypatch.setenv("INFLACION_COPILOT_TIMEOUT_SECONDS", "0")

    def fake_get(url, params, timeout):
        calls.append(timeout)
        return _FakeResponse(payload=_inflation_payload())

    monkeypatch.setattr("inflation_client.httpx.get", fake_get)

    fetch_average_period_inflation(2026, 2025, 4, base_url="https://inflacion.example.test")

    assert calls == [20.0]


def test_fetch_average_period_inflation_returns_none_without_base_url(monkeypatch):
    monkeypatch.delenv("INFLACION_COPILOT_URL", raising=False)

    assert fetch_average_period_inflation(2026, 2025, 4) is None


def test_fetch_average_period_inflation_returns_none_on_http_error(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        return _FakeResponse(status_code=500)

    monkeypatch.setattr("inflation_client.httpx.get", fake_get)

    assert fetch_average_period_inflation(2026, 2025, 4, base_url="https://inflacion.example.test") is None
    assert len(calls) == 1


def test_fetch_average_period_inflation_retries_once_after_read_timeout(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("timeout")
        return _FakeResponse(payload=_inflation_payload())

    monkeypatch.setattr("inflation_client.httpx.get", fake_get)

    payload = fetch_average_period_inflation(2026, 2025, 4, base_url="https://inflacion.example.test")

    assert payload["inflation_pct"] == 4.2133669155347775
    assert len(calls) == 2


def test_fetch_average_period_inflation_returns_none_after_two_read_timeouts(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr("inflation_client.httpx.get", fake_get)

    assert fetch_average_period_inflation(2026, 2025, 4, base_url="https://inflacion.example.test") is None
    assert len(calls) == 2


def test_fetch_average_period_inflation_does_not_retry_other_http_errors(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        raise httpx.ConnectError("connect failed")

    monkeypatch.setattr("inflation_client.httpx.get", fake_get)

    assert fetch_average_period_inflation(2026, 2025, 4, base_url="https://inflacion.example.test") is None
    assert len(calls) == 1


def test_fetch_average_period_inflation_returns_none_on_invalid_payload(monkeypatch):
    monkeypatch.setattr("inflation_client.httpx.get", lambda *args, **kwargs: _FakeResponse(payload={"factor": 1.0}))

    assert fetch_average_period_inflation(2026, 2025, 4, base_url="https://inflacion.example.test") is None
