"""
ETL de archivos SII INFONAVIT.

Convierte archivos Excel SII a un CSV consolidado usado por el pipeline de
analisis y visualizaciones.
"""

import hashlib
import json
import logging
import os
import re
import shutil
from datetime import datetime

import pandas as pd

import config

logger = logging.getLogger(__name__)

ESTADOS_MX = {
    "Aguascalientes": 1,
    "Baja California": 2,
    "Baja California Sur": 3,
    "Campeche": 4,
    "Coahuila": 5,
    "Colima": 6,
    "Chiapas": 7,
    "Chihuahua": 8,
    "Ciudad de Mexico": 9,
    "Ciudad de México": 9,
    "Durango": 10,
    "Guanajuato": 11,
    "Guerrero": 12,
    "Hidalgo": 13,
    "Jalisco": 14,
    "Estado de Mexico": 15,
    "Estado de México": 15,
    "Michoacan": 16,
    "Michoacán": 16,
    "Morelos": 17,
    "Nayarit": 18,
    "Nuevo Leon": 19,
    "Nuevo León": 19,
    "Oaxaca": 20,
    "Puebla": 21,
    "Queretaro": 22,
    "Querétaro": 22,
    "Quintana Roo": 23,
    "San Luis Potosi": 24,
    "San Luis Potosí": 24,
    "Sinaloa": 25,
    "Sonora": 26,
    "Tabasco": 27,
    "Tamaulipas": 28,
    "Tlaxcala": 29,
    "Veracruz": 30,
    "Yucatan": 31,
    "Yucatán": 31,
    "Zacatecas": 32,
}

MAPA_LIMPIEZA_DEFAULT = {
    "CDMX": "Ciudad de México",
    "Ciudad de Mexico": "Ciudad de México",
    "Mexico": "Estado de México",
    "México": "Estado de México",
    "Edo. de Mexico": "Estado de México",
    "Edo. de México": "Estado de México",
    "Distrito Federal": "Ciudad de México",
    "Estado de Mexico": "Estado de México",
}

MESES_MAP = {
    "Enero": 1,
    "Febrero": 2,
    "Marzo": 3,
    "Abril": 4,
    "Mayo": 5,
    "Junio": 6,
    "Julio": 7,
    "Agosto": 8,
    "Septiembre": 9,
    "Octubre": 10,
    "Noviembre": 11,
    "Diciembre": 12,
}


def normalizar_estado(nombre):
    """Limpia el nombre del estado y aplica sinonimos conocidos."""
    if pd.isna(nombre):
        return None
    nombre_limpio = str(nombre).strip()
    mapa_limpieza = getattr(config, "ESTADO_ALIASES", None) or MAPA_LIMPIEZA_DEFAULT
    return mapa_limpieza.get(nombre_limpio, nombre_limpio)


def generar_id_reporte(row):
    """Crea una llave unica para PostgreSQL."""
    cadena = f"{row['anio']}_{row['mes']}_{row['estado']}_{row['linea']}_{row['producto']}_{row['metrica']}"
    return hashlib.md5(cadena.encode()).hexdigest()


def _validar_archivo_excel_sii(ruta_archivo):
    nombre_archivo = os.path.basename(ruta_archivo)
    anio_match = re.search(r"SII_(\d{4})", nombre_archivo)
    if not anio_match:
        raise ValueError(
            f"No se pudo detectar el anio en el nombre del archivo '{nombre_archivo}'. "
            "Usa el patron SII_YYYY."
        )

    if not nombre_archivo.lower().endswith((".xlsx", ".xls")):
        raise ValueError(f"El archivo '{nombre_archivo}' no es .xls o .xlsx.")

    return int(anio_match.group(1))


def procesar_archivo_sii(ruta_archivo):
    anio = _validar_archivo_excel_sii(ruta_archivo)

    df_raw = pd.read_excel(ruta_archivo, header=None)
    if df_raw.shape[0] < 4 or df_raw.shape[1] < 4:
        raise ValueError("El archivo Excel no tiene la estructura minima esperada.")

    header_rows = df_raw.iloc[0:3].copy()
    header_rows.iloc[0] = header_rows.iloc[0].ffill()
    header_rows.iloc[1] = header_rows.iloc[1].ffill()

    data = df_raw.iloc[3:].copy()
    data[0] = data[0].ffill().apply(normalizar_estado)

    registros_largos = []

    for col_idx in range(3, df_raw.shape[1]):
        linea = header_rows.iloc[0, col_idx]
        producto = header_rows.iloc[1, col_idx]
        metrica = header_rows.iloc[2, col_idx]

        if "Totales" in str(linea) or pd.isna(metrica):
            continue

        temp_df = data[[0, 1, col_idx]].copy()
        temp_df.columns = ["estado_nombre", "mes_nombre", "valor"]
        temp_df["linea"] = linea
        temp_df["producto"] = producto
        temp_df["metrica"] = metrica
        registros_largos.append(temp_df)

    if not registros_largos:
        raise ValueError("No se encontraron columnas de metricas procesables en el Excel.")

    df_final = pd.concat(registros_largos, ignore_index=True)
    df_final["anio"] = anio
    df_final["estado"] = df_final["estado_nombre"].map(ESTADOS_MX)
    df_final["mes"] = df_final["mes_nombre"].map(MESES_MAP)
    df_final["periodicidad"] = "mensual"
    df_final["fuente"] = "INFONAVIT_SII"
    df_final["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df_final = df_final.dropna(subset=["estado", "mes", "valor"])
    df_final["valor"] = pd.to_numeric(df_final["valor"], errors="coerce").fillna(0)
    df_final["id_reporte"] = df_final.apply(generar_id_reporte, axis=1)

    cols_orden = [
        "id_reporte",
        "anio",
        "estado",
        "mes",
        "linea",
        "producto",
        "metrica",
        "valor",
        "periodicidad",
        "fuente",
        "timestamp",
    ]
    return df_final[cols_orden]


def _crear_manifest(run_id):
    started_at = datetime.now().isoformat(timespec="seconds")
    return {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": None,
        "files": [],
    }


def _guardar_manifest(manifest):
    runs_dir = os.path.join("logs", "runs")
    os.makedirs(runs_dir, exist_ok=True)
    manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
    path_manifest = os.path.join(runs_dir, f"run_{manifest['run_id']}.json")
    with open(path_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    logger.info("Manifest ETL generado: %s", path_manifest)
    return path_manifest


def _registrar_manifest(manifest, source_file, work_file, status, message="", error_type=None, destination=None):
    manifest["files"].append(
        {
            "source_file": source_file,
            "work_file": work_file,
            "status": status,
            "message": message,
            "error_type": error_type,
            "destination": destination,
        }
    )


def _copiar_archivo_operativo(ruta_origen, carpeta_destino, run_id):
    os.makedirs(carpeta_destino, exist_ok=True)
    base = os.path.basename(ruta_origen)
    stem, ext = os.path.splitext(base)
    destino = os.path.join(carpeta_destino, f"{stem}_{run_id}{ext}")
    shutil.copy2(ruta_origen, destino)
    return destino


def procesar_archivo_sii_operativo(
    ruta_archivo,
    run_id,
    manifest,
    usar_zona_trabajo=True,
    ruta_work="datos_work",
    ruta_procesados="datos_procesados",
    ruta_error="datos_error",
    copiar_procesados=False,
):
    source_file = os.path.abspath(ruta_archivo)
    work_file = None

    try:
        if usar_zona_trabajo:
            work_file = _copiar_archivo_operativo(source_file, ruta_work, run_id)
            logger.info("Copia de trabajo creada: %s", work_file)
            ruta_proceso = work_file
        else:
            ruta_proceso = source_file

        df_temp = procesar_archivo_sii(ruta_proceso)

        destination = None
        if copiar_procesados:
            destination = _copiar_archivo_operativo(source_file, ruta_procesados, run_id)
            logger.info("Copia de archivo procesado creada: %s", destination)

        _registrar_manifest(
            manifest,
            source_file=source_file,
            work_file=work_file,
            status="ok",
            message="Archivo procesado correctamente.",
            destination=destination,
        )
        return df_temp
    except Exception as e:
        destination = None
        try:
            ruta_error_origen = work_file if work_file else source_file
            destination = _copiar_archivo_operativo(ruta_error_origen, ruta_error, run_id)
            logger.info("Copia de archivo con error creada: %s", destination)
        except Exception as copy_error:
            logger.exception("No se pudo copiar archivo con error: %s", copy_error)

        _registrar_manifest(
            manifest,
            source_file=source_file,
            work_file=work_file,
            status="error",
            message=str(e),
            error_type=type(e).__name__,
            destination=destination,
        )
        logger.exception("Error procesando %s: %s", source_file, e)
        return None


def ejecutar_concentrado(
    path_origen,
    archivo_salida="SII_concentrado_v3.csv",
    mover_procesados=False,
    usar_zona_trabajo=True,
    ruta_work="datos_work",
    ruta_procesados="datos_procesados",
    ruta_error="datos_error",
):
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest = _crear_manifest(run_id)
    os.makedirs(ruta_work, exist_ok=True)
    os.makedirs(ruta_procesados, exist_ok=True)
    os.makedirs(ruta_error, exist_ok=True)
    os.makedirs(os.path.join("logs", "runs"), exist_ok=True)

    archivos = [
        f
        for f in os.listdir(path_origen)
        if f.lower().endswith((".xlsx", ".xls")) and not f.startswith("~$")
    ]
    archivos_csv = [f for f in os.listdir(path_origen) if f.lower().endswith(".csv")]

    if not archivos:
        logger.warning("No se encontraron archivos .xls o .xlsx en la carpeta de entrada: %s", path_origen)
        if archivos_csv:
            logger.warning(
                "Se encontraron CSVs en la carpeta (%s), pero no se procesan automaticamente "
                "cuando archivo_entrada apunta a una carpeta. Configura archivo_entrada con "
                "la ruta exacta del CSV si deseas usarlo directamente.",
                ", ".join(archivos_csv),
            )
            for csv_file in archivos_csv:
                _registrar_manifest(
                    manifest,
                    source_file=os.path.abspath(os.path.join(path_origen, csv_file)),
                    work_file=None,
                    status="skipped",
                    message="CSV detectado en carpeta; no se procesa automaticamente como entrada de carpeta.",
                )

    if os.path.exists(archivo_salida):
        historico = pd.read_csv(archivo_salida)
        periodos_procesados = historico[["anio", "mes"]].drop_duplicates().assign(_periodo_procesado=True)
    else:
        historico = pd.DataFrame()
        periodos_procesados = pd.DataFrame(columns=["anio", "mes", "_periodo_procesado"])

    bloques_nuevos = []
    archivos_exitosos = []

    for f in archivos:
        ruta_completa = os.path.join(path_origen, f)
        logger.info("Procesando: %s", f)

        df_temp = procesar_archivo_sii_operativo(
            ruta_completa,
            run_id=run_id,
            manifest=manifest,
            usar_zona_trabajo=usar_zona_trabajo,
            ruta_work=ruta_work,
            ruta_procesados=ruta_procesados,
            ruta_error=ruta_error,
            copiar_procesados=mover_procesados,
        )
        if df_temp is None:
            continue

        df_nuevo = df_temp.merge(periodos_procesados, on=["anio", "mes"], how="left")
        df_nuevo = df_nuevo[df_nuevo["_periodo_procesado"].isna()].drop(columns=["_periodo_procesado"])

        if not df_nuevo.empty:
            bloques_nuevos.append(df_nuevo)
            logger.info("-> %s registros nuevos detectados.", len(df_nuevo))
        else:
            logger.info("-> Sin informacion nueva.")

        archivos_exitosos.append(f)

    if bloques_nuevos:
        final = pd.concat([historico] + bloques_nuevos, ignore_index=True)
        final.to_csv(archivo_salida, index=False, encoding="utf-8-sig")
        logger.info("Archivo '%s' actualizado exitosamente.", archivo_salida)
    else:
        logger.info("No hubo datos nuevos para agregar.")

    if not mover_procesados:
        if archivos_exitosos:
            logger.info("Movimiento de archivos procesados deshabilitado por configuracion.")
        _guardar_manifest(manifest)
        return

    _guardar_manifest(manifest)


def ejecutar_archivo_excel(
    ruta_archivo,
    mover_procesados=False,
    usar_zona_trabajo=True,
    ruta_work="datos_work",
    ruta_procesados="datos_procesados",
    ruta_error="datos_error",
):
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest = _crear_manifest(run_id)
    os.makedirs(ruta_work, exist_ok=True)
    os.makedirs(ruta_procesados, exist_ok=True)
    os.makedirs(ruta_error, exist_ok=True)
    os.makedirs(os.path.join("logs", "runs"), exist_ok=True)

    df_temp = procesar_archivo_sii_operativo(
        ruta_archivo,
        run_id=run_id,
        manifest=manifest,
        usar_zona_trabajo=usar_zona_trabajo,
        ruta_work=ruta_work,
        ruta_procesados=ruta_procesados,
        ruta_error=ruta_error,
        copiar_procesados=mover_procesados,
    )
    _guardar_manifest(manifest)
    if df_temp is None:
        raise ValueError(f"No se pudo procesar el archivo Excel: {ruta_archivo}")
    return df_temp


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    carpeta_archivos = "./datos_entrada"
    archivo_salida = "SII_concentrado_v3.csv"

    logger.info("Iniciando proceso de consolidacion...")
    ejecutar_concentrado(carpeta_archivos, archivo_salida)
    logger.info("Proceso terminado.")
