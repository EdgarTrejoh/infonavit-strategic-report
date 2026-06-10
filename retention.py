from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import config

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent
SAFE_RETENTION_DIRS = (
    PROJECT_ROOT / "datos_work",
    PROJECT_ROOT / "datos_error",
    PROJECT_ROOT / "datos_procesados",
    PROJECT_ROOT / "logs",
    PROJECT_ROOT / "logs" / "runs",
)


@dataclass(frozen=True)
class RetentionTarget:
    name: str
    path: Path
    max_age_days: int


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _resolve_project_path(path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (PROJECT_ROOT / path).resolve()


def _is_safe_retention_path(path: Path) -> bool:
    resolved_path = _resolve_project_path(path)
    home_dir = Path.home().resolve()
    drive_root = Path(resolved_path.anchor).resolve()

    dangerous_paths = {
        PROJECT_ROOT,
        Path(".").resolve(),
        Path("/").resolve(),
        drive_root,
        home_dir,
    }
    if resolved_path in dangerous_paths:
        return False

    return any(
        resolved_path == safe_dir.resolve() or _is_relative_to(resolved_path, safe_dir.resolve())
        for safe_dir in SAFE_RETENTION_DIRS
    )


def _iter_candidate_files(path: Path):
    if not _is_safe_retention_path(path):
        logger.warning("Retention: ruta no permitida, se omite limpieza: %s", path)
        return

    path = _resolve_project_path(path)
    if not path.exists():
        return
    for item in path.rglob("*"):
        if item.is_file() and item.name != ".gitkeep":
            yield item


def _is_expired(path: Path, cutoff: datetime) -> bool:
    modified_at = datetime.fromtimestamp(path.stat().st_mtime)
    return modified_at < cutoff


def build_retention_targets() -> list[RetentionTarget]:
    max_age = getattr(config, "RETENTION_MAX_AGE_DAYS", {})
    return [
        RetentionTarget("datos_work", Path(config.ETL_RUTA_WORK), int(max_age.get("datos_work", 7))),
        RetentionTarget("datos_error", Path(config.ETL_RUTA_ERROR), int(max_age.get("datos_error", 30))),
        RetentionTarget(
            "datos_procesados",
            Path(config.ETL_RUTA_PROCESADOS),
            int(max_age.get("datos_procesados", 90)),
        ),
        RetentionTarget("logs", Path("logs"), int(max_age.get("logs", 30))),
        RetentionTarget("manifests", Path("logs") / "runs", int(max_age.get("manifests", 90))),
    ]


def apply_retention_policy() -> list[str]:
    if not getattr(config, "RETENTION_ENABLED", False):
        logger.info("Politica de retencion deshabilitada.")
        return []

    dry_run = bool(getattr(config, "RETENTION_DRY_RUN", True))
    deleted_or_planned: list[str] = []
    now = datetime.now()

    for target in build_retention_targets():
        cutoff = now - timedelta(days=target.max_age_days)
        for candidate in _iter_candidate_files(target.path) or []:
            if not _is_expired(candidate, cutoff):
                continue

            candidate_str = str(candidate)
            deleted_or_planned.append(candidate_str)
            if dry_run:
                logger.info(
                    "Retention dry-run: se limpiaria %s (%s, mayor a %s dias).",
                    candidate_str,
                    target.name,
                    target.max_age_days,
                )
                continue

            try:
                candidate.unlink()
                logger.info(
                    "Retention: archivo eliminado %s (%s, mayor a %s dias).",
                    candidate_str,
                    target.name,
                    target.max_age_days,
                )
            except Exception as exc:
                logger.exception("Retention: no se pudo eliminar %s: %s", candidate_str, exc)

    if not deleted_or_planned:
        logger.info("Politica de retencion ejecutada sin candidatos vencidos.")

    return deleted_or_planned
