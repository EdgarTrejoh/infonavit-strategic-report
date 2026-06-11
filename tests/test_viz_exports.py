def test_viz_exports_functions_used_by_main():
    import viz

    expected_exports = [
        "crear_portada_pdf",
        "plot_01_monto_nacional",
        "plot_02_volumen_nacional",
        "plot_03_ticket_nacional",
        "plot_04_mix_productos",
        "plot_09_carrera_anual",
        "plot_22_reporte_ejecutivo",
        "plot_24_yoy_por_linea",
        "plot_40_cagr_productos",
    ]

    for name in expected_exports:
        assert hasattr(viz, name)
        assert callable(getattr(viz, name))
        assert name in viz.__all__
