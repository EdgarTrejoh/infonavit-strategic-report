from dataclasses import dataclass
from pathlib import Path
import yaml

with open("config.yaml", "r", encoding="utf-8") as f:
    conf_data = yaml.safe_load(f)

# Esto es vital para que el ETL asigne bien los IDs
ESTADOS_MX = conf_data.get("estados_mx", {})

# =============================================================================
# VARIABLES GLOBALES (Placeholders)
# Se definen aquí para evitar errores de 'AttributeError' cuando viz.py
# se importa antes de que main.py cargue el YAML.
# =============================================================================

# 1. Rutas y Archivos (Valores por defecto)
FILE_INPUT = "SII_concentrado_v3.csv"
OUTDIR = Path("salidas_viz_final")
PDF_NAME_PREFIX = "Reporte"
PDF_REPORT = None  # Aquí se guardará el objeto PDFPages
PDF_FIGURE_SCALE = 0.78
LOG_FILE = None

# 2. Configuración de Tiempo (Valores por defecto)
ANIO_ANALISIS = 2024
ANIO_OBJETIVO = 2025
ANIO_PREVIO = 2023
ANIO_HISTORICO_INICIO = 2022
FECHA_INICIO_ANIO_ANALISIS = "2024-01-01"
FECHA_INICIO_FILTROS = "2022-01-01"

# 3. Métricas
MET_MONTO = "Monto de crédito Infonavit"
MET_NUM = "Número de créditos formalizados"

# 3.1 Base de datos
DATABASE_ENABLED = True
DATABASE_FAIL_ON_ERROR = False
DATABASE_HEALTH_CHECK = True

# 3.2 ETL e insumos
ETL_MOVER_PROCESADOS = False
ETL_USAR_ZONA_TRABAJO = True
ETL_RUTA_WORK = "datos_work"
ETL_RUTA_PROCESADOS = "datos_procesados"
ETL_RUTA_ERROR = "datos_error"

# 3.3 Retencion/limpieza operativa
RETENTION_ENABLED = False
RETENTION_DRY_RUN = True
RETENTION_MAX_AGE_DAYS = {
    "datos_work": 7,
    "datos_error": 30,
    "datos_procesados": 90,
    "logs": 30,
    "manifests": 90,
}

# 4. Colores y Estilos (Mapeo doble para compatibilidad)
# Definimos tanto MAYÚSCULAS (estándar Python) como minúsculas (según tu error)
COLOR_INFONAVIT = "#691C32"  # Vino default
color_corporativo = COLOR_INFONAVIT  # Alias para evitar tu error de viz.py

COLOR_POS = "#235B4E"
COLOR_NEG = "#9F2241"
COLOR_NEUTRO = "#6F7271"

# 5. Diccionarios
ESTADOS_MX = {}  # Se llenará con el YAML

# =============================================================================
# CLASE DE CONFIGURACIÓN VISUAL (ESTÁTICA)
# =============================================================================
@dataclass(frozen=True)
class VizConfig:
    # -------------------------
    # Unidades / formato
    # -------------------------
    MONEY_UNIT_LABEL: str = "MM"
    MONEY_UNIT_SCALE: float = 1e9

    # -------------------------
    # Estilo general
    # -------------------------
    FIGSIZE_DEFAULT: tuple = (14, 8)
    DPI: int = 160

    # -------------------------
    # Colores (branding)
    # -------------------------
    # Usamos las variables globales definidas arriba
    COLOR_BARS: str = "#2E86AB"
    COLOR_LINE_RIGHT: str = "#4A4A4A"
    COLOR_GRID: str = "#E6E6E6"
    COLOR_TEXT: str = "#222222"
    COLOR_SPINES: str = "#D0D0D0"
    
    # Variables que utils.py buscaba y no encontraba
    RIGHT_AXIS_TICK_COLOR_MATCH_LINE: bool = True
    RIGHT_AXIS_LABEL_COLOR_MATCH_LINE: bool = True

    # -------------------------
    # Tipografía / tamaños
    # -------------------------
    TITLE_SIZE: int = 16
    LABEL_SIZE: int = 12
    TICK_SIZE: int = 10
