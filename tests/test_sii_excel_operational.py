import json
from pathlib import Path

import pytest

from sii_excel_etl import ejecutar_archivo_excel


def test_invalid_excel_goes_to_error_zone_and_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    entrada = tmp_path / "datos_entrada"
    work = tmp_path / "datos_work"
    procesados = tmp_path / "datos_procesados"
    error = tmp_path / "datos_error"
    entrada.mkdir()

    source_file = entrada / "SII_2026.xlsx"
    source_file.write_text("contenido invalido que no es un xlsx real", encoding="utf-8")

    with pytest.raises(ValueError):
        ejecutar_archivo_excel(
            str(source_file),
            mover_procesados=False,
            usar_zona_trabajo=True,
            ruta_work=str(work),
            ruta_procesados=str(procesados),
            ruta_error=str(error),
        )

    assert source_file.exists()
    assert list(work.glob("SII_2026_*.xlsx"))
    assert list(error.glob("SII_2026_*.xlsx"))
    assert not list(procesados.glob("*.xlsx"))

    manifests = list((tmp_path / "logs" / "runs").glob("run_*.json"))
    assert len(manifests) == 1

    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["finished_at"]
    assert len(manifest["files"]) == 1

    file_entry = manifest["files"][0]
    assert file_entry["source_file"] == str(source_file.resolve())
    assert file_entry["status"] == "error"
    assert file_entry["work_file"]
    assert file_entry["destination"]
    assert file_entry["error_type"]


def test_csv_in_input_folder_is_skipped_in_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    entrada = tmp_path / "datos_entrada"
    entrada.mkdir()
    csv_file = entrada / "entrada.csv"
    csv_file.write_text("id_reporte,anio,estado,mes,linea,producto,metrica,valor\n", encoding="utf-8")

    from sii_excel_etl import ejecutar_concentrado

    ejecutar_concentrado(
        str(entrada),
        archivo_salida=str(tmp_path / "consolidado.csv"),
        mover_procesados=False,
        usar_zona_trabajo=True,
        ruta_work=str(tmp_path / "datos_work"),
        ruta_procesados=str(tmp_path / "datos_procesados"),
        ruta_error=str(tmp_path / "datos_error"),
    )

    manifests = list((tmp_path / "logs" / "runs").glob("run_*.json"))
    assert len(manifests) == 1

    manifest = json.loads(Path(manifests[0]).read_text(encoding="utf-8"))
    assert manifest["files"][0]["status"] == "skipped"
    assert "CSV detectado" in manifest["files"][0]["message"]
