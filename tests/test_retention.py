import os
import time
from pathlib import Path

import config
from retention import apply_retention_policy


def _make_old_file(path: Path, days_old: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("old", encoding="utf-8")
    old_timestamp = time.time() - (days_old * 24 * 60 * 60)
    os.utime(path, (old_timestamp, old_timestamp))


def _configure_retention(monkeypatch, tmp_path, *, enabled, dry_run):
    monkeypatch.setattr(config, "RETENTION_ENABLED", enabled)
    monkeypatch.setattr(config, "RETENTION_DRY_RUN", dry_run)
    monkeypatch.setattr(
        config,
        "RETENTION_MAX_AGE_DAYS",
        {
            "datos_work": 7,
            "datos_error": 30,
            "datos_procesados": 90,
            "logs": 30,
            "manifests": 90,
        },
    )
    monkeypatch.setattr(config, "ETL_RUTA_WORK", str(tmp_path / "datos_work"))
    monkeypatch.setattr(config, "ETL_RUTA_ERROR", str(tmp_path / "datos_error"))
    monkeypatch.setattr(config, "ETL_RUTA_PROCESADOS", str(tmp_path / "datos_procesados"))
    monkeypatch.chdir(tmp_path)


def test_retention_disabled_does_not_delete(tmp_path, monkeypatch):
    _configure_retention(monkeypatch, tmp_path, enabled=False, dry_run=True)
    old_file = tmp_path / "datos_work" / "old.xlsx"
    _make_old_file(old_file, days_old=10)

    result = apply_retention_policy()

    assert result == []
    assert old_file.exists()


def test_retention_dry_run_keeps_expired_files(tmp_path, monkeypatch):
    _configure_retention(monkeypatch, tmp_path, enabled=True, dry_run=True)
    old_file = tmp_path / "datos_work" / "old.xlsx"
    _make_old_file(old_file, days_old=10)

    result = apply_retention_policy()

    assert result == [str(old_file)]
    assert old_file.exists()


def test_retention_deletes_only_expired_files_and_keeps_gitkeep(tmp_path, monkeypatch):
    _configure_retention(monkeypatch, tmp_path, enabled=True, dry_run=False)
    expired_file = tmp_path / "datos_work" / "old.xlsx"
    fresh_file = tmp_path / "datos_work" / "fresh.xlsx"
    gitkeep = tmp_path / "datos_work" / ".gitkeep"

    _make_old_file(expired_file, days_old=10)
    fresh_file.write_text("fresh", encoding="utf-8")
    gitkeep.write_text("", encoding="utf-8")
    os.utime(gitkeep, (time.time() - (100 * 24 * 60 * 60), time.time() - (100 * 24 * 60 * 60)))

    result = apply_retention_policy()

    assert result == [str(expired_file)]
    assert not expired_file.exists()
    assert fresh_file.exists()
    assert gitkeep.exists()
