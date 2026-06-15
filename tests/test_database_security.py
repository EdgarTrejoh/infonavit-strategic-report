import importlib
import logging

import database


SENSITIVE_DSN = "postgresql+psycopg2://api_user:SUPER_SECRET_PASSWORD@db.example.com:5432/infonavit"
SAFE_DB_ERROR = "No se pudo conectar a PostgreSQL. Verifica host, puerto, base y credenciales."
SENSITIVE_TERMS = [
    "SUPER_SECRET_PASSWORD",
    "api_user",
    "db.example.com",
    "postgresql+psycopg2://",
    "DATABASE_URL",
]


def _assert_no_sensitive_terms(text: str) -> None:
    for term in SENSITIVE_TERMS:
        assert term not in text


def test_database_engine_initialization_failure_does_not_log_dsn(monkeypatch, caplog):
    import sqlalchemy

    def fake_create_engine(*args, **kwargs):
        raise RuntimeError(f"cannot create engine for {SENSITIVE_DSN}")

    monkeypatch.setenv("DATABASE_URL", SENSITIVE_DSN)
    monkeypatch.setattr(sqlalchemy, "create_engine", fake_create_engine)

    with caplog.at_level(logging.WARNING):
        reloaded = importlib.reload(database)

    log_text = caplog.text
    assert reloaded.engine is None
    assert "RuntimeError" in log_text
    _assert_no_sensitive_terms(log_text)

    importlib.reload(database)


def test_health_check_failure_returns_safe_message_and_does_not_log_dsn(monkeypatch, caplog):
    class FakeEngine:
        def connect(self):
            raise RuntimeError(f"could not connect using {SENSITIVE_DSN}")

    monkeypatch.setattr(database, "engine", FakeEngine())

    with caplog.at_level(logging.WARNING):
        ok, message = database.health_check()

    assert ok is False
    assert message == SAFE_DB_ERROR
    assert "RuntimeError" in caplog.text
    _assert_no_sensitive_terms(caplog.text)
    _assert_no_sensitive_terms(message)


def test_database_url_env_value_is_not_logged_on_failure(monkeypatch, caplog):
    import sqlalchemy

    def fake_create_engine(*args, **kwargs):
        raise RuntimeError(f"DATABASE_URL failed: {SENSITIVE_DSN}")

    monkeypatch.setenv("DATABASE_URL", SENSITIVE_DSN)
    monkeypatch.setattr(sqlalchemy, "create_engine", fake_create_engine)

    with caplog.at_level(logging.WARNING):
        importlib.reload(database)

    _assert_no_sensitive_terms(caplog.text)

    importlib.reload(database)
