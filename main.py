# ==========================================
# MÓDULO 06 — main.py
# Orquestador del Reporte Estratégico
# ==========================================

import os
import sys
import logging
import yaml
import warnings
import pandas as pd
from datetime import datetime
from pathlib import Path
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

# Importamos los módulos del proyecto
import config
import etl
import viz
from migrate_csv_to_pg import migrate
from database import health_check
from retention import apply_retention_policy

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"


def configurar_logging(log_file=None):
    """Configura logging para consola y, opcionalmente, archivo por corrida."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


configurar_logging()
logger = logging.getLogger(__name__)

# Ignorar advertencias no críticas
warnings.filterwarnings("ignore")

def cargar_configuracion_yaml():
    """Lee config.yaml e inyecta variables en config.py"""
    ruta_yaml = "config.yaml"
    if not os.path.exists(ruta_yaml):
        logger.error(f"No se encontró: {ruta_yaml}")
        sys.exit(1)

    with open(ruta_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Inyección de variables
    config.ANIO_ANALISIS = data["tiempo"]["anio_analisis"]
    config.ANIO_OBJETIVO = data["tiempo"]["anio_objetivo"]
    config.ANIO_PREVIO = data["tiempo"]["anio_previo"]
    config.ANIO_HISTORICO_INICIO = data["tiempo"]["anio_historico_inicio"]
    config.FECHA_INICIO_ANIO_ANALISIS = f"{config.ANIO_ANALISIS}-01-01"
    config.FECHA_INICIO_FILTROS = f"{config.ANIO_HISTORICO_INICIO}-01-01"

    config.FILE_INPUT = data["rutas"]["archivo_entrada"]
    config.OUTDIR = Path(data["rutas"]["carpeta_salida"])
    config.PDF_NAME_PREFIX = data["rutas"]["nombre_pdf_prefijo"]
    config.OUTDIR.mkdir(parents=True, exist_ok=True)

    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    config.LOG_FILE = logs_dir / f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    configurar_logging(config.LOG_FILE)
    logger.info("Cargando configuración...")
    logger.info("Log de ejecucion: %s", config.LOG_FILE)

    config.MET_MONTO = data["metricas"]["col_monto"]
    config.MET_NUM = data["metricas"]["col_num"]

    database_conf = data.get("database", {})
    config.DATABASE_ENABLED = bool(database_conf.get("enabled", True))
    config.DATABASE_FAIL_ON_ERROR = bool(database_conf.get("fail_on_error", False))
    config.DATABASE_HEALTH_CHECK = bool(database_conf.get("health_check", True))

    etl_conf = data.get("etl", {})
    config.ETL_MOVER_PROCESADOS = bool(etl_conf.get("mover_procesados", False))
    config.ETL_USAR_ZONA_TRABAJO = bool(etl_conf.get("usar_zona_trabajo", True))
    config.ETL_RUTA_WORK = etl_conf.get("ruta_work", "datos_work")
    config.ETL_RUTA_PROCESADOS = etl_conf.get("ruta_procesados", "datos_procesados")
    config.ETL_RUTA_ERROR = etl_conf.get("ruta_error", "datos_error")
    for etl_dir in (config.ETL_RUTA_WORK, config.ETL_RUTA_PROCESADOS, config.ETL_RUTA_ERROR):
        Path(etl_dir).mkdir(parents=True, exist_ok=True)

    pdf_conf = data.get("pdf", {})
    config.PDF_FIGURE_SCALE = float(pdf_conf.get("figure_scale", 0.78))

    retention_conf = data.get("retention", {})
    config.RETENTION_ENABLED = bool(retention_conf.get("enabled", False))
    config.RETENTION_DRY_RUN = bool(retention_conf.get("dry_run", True))
    config.RETENTION_MAX_AGE_DAYS = retention_conf.get(
        "max_age_days",
        {
            "datos_work": 7,
            "datos_error": 30,
            "datos_procesados": 90,
            "logs": 30,
            "manifests": 90,
        },
    )

    estilos = data["estilos"]
    config.COLOR_INFONAVIT = estilos["color_corporativo"]
    config.COLOR_POS = estilos["color_positivo"]
    config.COLOR_NEG = estilos["color_negativo"]
    config.COLOR_NEUTRO = estilos["color_neutro"]
    
    config.ESTADOS_MX = data["estados_mx"]


def main():
    logger.info("=== INICIANDO REPORTE ESTRATÉGICO (ORDEN PERSONALIZADO) ===")

    # 1. Configuración
    cargar_configuracion_yaml()

    # 2. ETL
    manager = etl.DataManager()
    try:
        manager.run_etl()
    except Exception as e:
        logger.error(f"Error en ETL: {e}", exc_info=True)
        return

    # 3. Sincronización PostgreSQL
    if config.DATABASE_ENABLED:
        logger.info("Sincronizando histórico consolidado con PostgreSQL...")
        input_path = Path(str(config.FILE_INPUT))
        csv_path = input_path if input_path.suffix.lower() == ".csv" else Path("SII_concentrado_v3.csv")

        db_available = True
        if config.DATABASE_HEALTH_CHECK:
            db_available, db_message = health_check()
            if db_available:
                logger.info(db_message)
            else:
                logger.error(db_message)

        migration_ok = False
        if db_available:
            migration_ok = migrate(csv_path=str(csv_path))

        if not migration_ok:
            msg = "Error en sincronización PostgreSQL."
            if config.DATABASE_FAIL_ON_ERROR:
                logger.error("%s El reporte no será generado.", msg)
                return
            logger.warning("%s Se continuará con la generación del PDF.", msg)
    else:
        logger.info("Sincronización PostgreSQL deshabilitada por configuración.")

    # 4. PDF Global
    nombre_pdf = f"{config.PDF_NAME_PREFIX}_{config.ANIO_ANALISIS}.pdf"
    ruta_pdf = config.OUTDIR / nombre_pdf
    
    with PdfPages(ruta_pdf) as pdf:
        config.PDF_REPORT = pdf
        
        # Portada
        viz.crear_portada_pdf()

        # 5. Estilos Matplotlib
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']

        logger.info("Generando visualizaciones en secuencia...")

        # =========================================================
        # SECUENCIA EXACTA SOLICITADA
        # [01, 02, 03, 11, 06, 09, 13, 08, 28, 29, 04, 19, 26, 20, 
        #  05, 15, 16, 18, 30, 23, 25, 27, 31, 32, 33, 17, 21, 
        #  34, 35, 36, 24, 22, 14, 07, 12, 10]
        # =========================================================

        # 01, 02, 03: Métricas Macro
        viz.plot_01_monto_nacional(manager.df_global)
        viz.plot_02_volumen_nacional(manager.df_global)
        viz.plot_03_ticket_nacional(manager.df_global)

        # 11: Ticket por línea (Evolución)
        viz.plot_11_ticket_real_linea(manager.df_linea_mensual)

        # 06: Crecimiento YoY (Semáforo)
        viz.plot_06_crecimiento_yoy(manager.df_global)

        # 09: Carrera Anual (Acumulados)
        anios_carrera = list(range(config.ANIO_HISTORICO_INICIO, config.ANIO_OBJETIVO + 1))
        viz.plot_09_carrera_anual(manager.df_global, anios_carrera)

        # 13: Share Stacked
        viz.plot_13_share(manager.df_raw_monto)

        # 08: Ciclos Estacionalidad
        viz.plot_08_ciclos_estacionalidad(manager.df_global)

        # 28: Face to Face (Mes vs Mes año anterior)
        viz.plot_28_face_to_face(manager.df_raw_monto, [config.ANIO_PREVIO, config.ANIO_ANALISIS])

        # 29: Volatilidad YoY
        viz.plot_29_distribucion_volatilidad_yoy(manager.df_master, config.ANIO_ANALISIS)

        # 04: Mix Productos (Barras apiladas mensual)
        viz.plot_04_mix_productos(manager.df_master, config.ANIO_ANALISIS)

        # 19: Share Lineas (Evolución % mes a mes)
        viz.plot_19_share_lineas(manager.df_master, config.ANIO_ANALISIS)

        # 26: Pareto Líneas (80/20)
        viz.plot_26_pareto_lineas(manager.df_master, config.ANIO_ANALISIS)

        # 20: Conquista Portafolio (Area chart)
        viz.plot_20_conquista_portafolio(manager.df_master, config.FECHA_INICIO_FILTROS,)
        #df_master, anio, top_n=5
        # 05: Pareto Estados (General)
        viz.plot_05_pareto_estados(manager.df_master, config.ANIO_ANALISIS)

        # 15: Top Estados (Línea Principal)
        # Nota: Usamos la línea #1 en monto para este gráfico
        top_linea_name = manager.df_master[manager.df_master["fecha"].dt.year == config.ANIO_ANALISIS]\
            .groupby("linea")["Monto"].sum().idxmax()
        viz.plot_15_top_estados(manager.df_master, top_linea_name, config.ANIO_ANALISIS)

        # 16, 18: Geografía Detalle
        viz.plot_16_top10_estados_proyeccion(manager.df_master, config.ANIO_ANALISIS)
        
        # 35: Radiografía específica de CDMX
        viz.plot_35_deep_dive_cdmx(manager.df_master, config.ANIO_ANALISIS, "Ciudad de México")
        viz.plot_18_pareto_estados_proyeccion(manager.df_master, config.ANIO_ANALISIS)

        # 30: Cierre Línea II (Vivienda vs Terreno)
        # Filtramos datos específicos para L2
        df_l2 = manager.df_master[
            (manager.df_master["Linea_Estrategica"] == "Línea II: Adquisición") &
            (manager.df_master["fecha"].dt.year == config.ANIO_ANALISIS)
        ]
        viz.plot_30_cierre_lineaII_vivienda_vs_terreno(df_l2, config.ANIO_ANALISIS)

        # 23, 25, 27: Drill-down específico Línea II - Vivienda
        # Preparamos los datos agrupados para estas gráficas
        df_l2_viv = df_l2[df_l2["Subtipo_Adquisicion"] == "Vivienda"].copy()
        if not df_l2_viv.empty:
            grp_l2 = df_l2_viv.groupby("producto", as_index=False).agg({"Monto":"sum", "Num_Creditos":"sum"})
            grp_l2 = grp_l2[grp_l2["Num_Creditos"]>0]
            grp_l2["Ticket"] = grp_l2["Monto"]/grp_l2["Num_Creditos"]
            grp_l2 = grp_l2.sort_values("Monto", ascending=False)
            
            # Llamamos a los genericos pero forzando los números solicitados
            viz.plot_generico_monto_vs_creditos(grp_l2, config.ANIO_ANALISIS, "L2 Vivienda", "23")
            viz.plot_generico_share(grp_l2, config.ANIO_ANALISIS, "L2 Vivienda", "25")
            viz.plot_generico_ticket(grp_l2, config.ANIO_ANALISIS, "L2 Vivienda", "27")

        # 31, 32, 33: Drill-down TOP LINEA #1
        # 34, 35, 36: Drill-down TOP LINEA #2
        # Obtenemos las 2 líneas más grandes
        top_2_lineas = manager.df_master[manager.df_master["fecha"].dt.year == config.ANIO_ANALISIS]\
            .groupby("linea")["Monto"].sum().nlargest(2).index.tolist()
        
        # Bucle para generar 31-33 y 34-36
        for i, linea_nom in enumerate(top_2_lineas):
            # i=0 -> grafica_base = 31 | i=1 -> grafica_base = 34
            grafica_base = 31 + (i * 3) 
            
            df_linea = manager.df_master[
                (manager.df_master["linea"] == linea_nom) & 
                (manager.df_master["fecha"].dt.year == config.ANIO_ANALISIS)
            ]
            grp = df_linea.groupby("producto", as_index=False).agg({"Monto":"sum", "Num_Creditos":"sum"})
            grp = grp[grp["Num_Creditos"]>0]
            grp["Ticket"] = grp["Monto"]/grp["Num_Creditos"]
            grp = grp.sort_values("Monto", ascending=False)

            viz.plot_generico_monto_vs_creditos(grp, config.ANIO_ANALISIS, linea_nom, str(grafica_base))
            viz.plot_generico_share(grp, config.ANIO_ANALISIS, linea_nom, str(grafica_base + 1))
            viz.plot_generico_ticket(grp, config.ANIO_ANALISIS, linea_nom, str(grafica_base + 2))

        # 17: Scatter Línea III
        viz.plot_17_scatter_estado_ticket_proyeccion(manager.df_master, config.ANIO_ANALISIS)

        # 21: Elasticidad Precio vs Volumen
        viz.plot_21_elasticidad_ticket_vs_volumen(manager.df_master, anio_objetivo=config.ANIO_OBJETIVO, meses_hasta=None, top_n=10, min_creditos=500)

        # 24: YoY por Línea (Horizontal Divergente)
        viz.plot_24_yoy_por_linea(manager.df_master, config.ANIO_ANALISIS)

        # 22: Scorecard Ejecutivo (Variaciones acumuladas)
        viz.plot_22_reporte_ejecutivo(manager.df_master, config.ANIO_ANALISIS)

        # 14: Matriz Estratégica Full
        viz.plot_14_matriz_estrategica_full(manager.df_master, config.ANIO_ANALISIS)

        # 07: Matriz BCG (Burbujas)
        viz.plot_07_matriz_bcg(manager.df_master, config.ANIO_ANALISIS)

        viz.plot_40_cagr_productos(manager.df_master, config.ANIO_OBJETIVO, periodo=3)

        viz.plot_41_matriz_crecimiento_estados(manager.df_master, config.ANIO_OBJETIVO, periodo=3)

        # 12: Análisis Forense (Solo si hay culpable)
        if manager.culpable_linea:
            viz.plot_12_analysis_forense(manager.df_linea_mensual)

        # 10: Heatmap Ticket MoM
        viz.plot_10_heatmap_ticket_mom(manager.df_master)
        viz.plot_10b_heatmap_ticket_nivel(manager.df_master)

        logger.info(f"=== REPORTE COMPLETADO ===")
        logger.info(f"PDF generado: {ruta_pdf}")

    apply_retention_policy()

if __name__ == "__main__":
    main()
