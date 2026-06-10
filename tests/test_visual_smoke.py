import pandas as pd

import config
from viz.macro import plot_09_carrera_anual


def test_plot_09_carrera_anual_smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTDIR", tmp_path)
    monkeypatch.setattr(config, "PDF_REPORT", None)
    monkeypatch.setattr(config, "ANIO_HISTORICO_INICIO", 2024)
    monkeypatch.setattr(config, "ANIO_PREVIO", 2025)
    monkeypatch.setattr(config, "ANIO_ANALISIS", 2026)
    monkeypatch.setattr(config, "ANIO_OBJETIVO", 2026)
    monkeypatch.setattr(config, "COLOR_INFONAVIT", "#691C32")
    monkeypatch.setattr(config, "COLOR_POS", "#235B4E")

    rows = []
    for anio, base in [(2024, 10.0), (2025, 12.0), (2026, 14.0)]:
        for mes in range(1, 5):
            rows.append(
                {
                    "fecha": pd.Timestamp(year=anio, month=mes, day=1),
                    "Monto": base * mes,
                }
            )

    df_global = pd.DataFrame(rows).set_index("fecha")

    plot_09_carrera_anual(df_global, [2024, 2025, 2026])

    output = tmp_path / "09_carrera_acumulada.png"
    assert output.exists()
    assert output.stat().st_size > 0
