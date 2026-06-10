import json
from pathlib import Path

import pandas as pd
import pytest

import config
from sii_excel_etl import ejecutar_archivo_excel, normalizar_estado


def test_normalizar_estado_uses_configured_aliases(monkeypatch):
    monkeypatch.setattr(config, "ESTADO_ALIASES", {"CDMX": "Ciudad de México"})

    assert normalizar_estado(" CDMX ") == "Ciudad de México"


def test_valid_excel_uses_work_zone_and_manifest_ok(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    entrada = tmp_path / "datos_entrada"
    work = tmp_path / "datos_work"
    procesados = tmp_path / "datos_procesados"
    error = tmp_path / "datos_error"
    entrada.mkdir()

    source_file = entrada / "SII_2026.xlsx"
    excel_data = pd.DataFrame(
        [
            [None, None, None, "Linea II: Adquisicion de vivienda nueva"],
            [None, None, None, "Producto A"],
            [None, None, None, "Monto"],
            ["Aguascalientes", "Enero", None, 100.0],
        ]
    )
    excel_data.to_excel(source_file, index=False, header=False)

    df = ejecutar_archivo_excel(
        str(source_file),
        mover_procesados=False,
        usar_zona_trabajo=True,
        ruta_work=str(work),
        ruta_procesados=str(procesados),
        ruta_error=str(error),
    )

    assert source_file.exists()
    assert len(df) == 1
    assert df.loc[0, "anio"] == 2026
    assert df.loc[0, "estado"] == 1
    assert df.loc[0, "mes"] == 1
    assert df.loc[0, "valor"] == 100.0

    work_files = list(work.glob("SII_2026_*.xlsx"))
    assert len(work_files) == 1
    assert not list(error.glob("*.xlsx"))
    assert not list(procesados.glob("*.xlsx"))

    manifests = list((tmp_path / "logs" / "runs").glob("run_*.json"))
    assert len(manifests) == 1

    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["finished_at"]
    assert len(manifest["files"]) == 1

    file_entry = manifest["files"][0]
    assert file_entry["source_file"] == str(source_file.resolve())
    assert file_entry["work_file"] == str(work_files[0])
    assert file_entry["status"] == "ok"
    assert file_entry["message"] == "Archivo procesado correctamente."
    assert file_entry["error_type"] is None
    assert file_entry["destination"] is None


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
