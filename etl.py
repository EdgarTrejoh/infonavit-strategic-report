#====================
# MÓDULO 04 — etl.py
#====================

from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd
import numpy as np
import config

# ✅ IMPORTA TU ETL EXCEL→CSV (ajusta el nombre del archivo si aplica)
# Opción A (recomendado): sii_excel_etl.py
from sii_excel_etl import procesar_archivo_sii, ejecutar_concentrado
# Opción B: si tu archivo se llama infonavit_etl.py
# from infonavit_etl import procesar_archivo_sii, ejecutar_concentrado

logger = logging.getLogger(__name__)

class DataManager:

    def __init__(self):
        """Inicializa el gestor de datos vacío."""
        self.df_raw_monto = None
        self.df_raw_num = None

        # DataFrames procesados principales
        self.df_master = None
        self.df_global = None

        # Derivados comunes
        self.df_linea_mensual = None
        self.df_analisis_global = None

        # Variables de análisis
        self.culpable_linea = None
        self.culpable_ticket_val = 0.0

    def run_etl(self):
        """Ejecuta todo el flujo de carga y transformación una sola vez."""
        logger.info("Ejecutando ETL (Extracción, Transformación y Carga)...")

        # 1. Carga
        self._cargar_datos()

        # 2. Transformación Maestra
        self.df_master = self._crear_master_dataset()

        # 3. Derivados Globales
        self.df_global = self._preparar_global_mensual()
        self.df_linea_mensual = self._preparar_df_linea_mensual()
        self.df_analisis_global = self._preparar_analisis_global()

        # 4. Análisis preliminar (Detectives)
        self._detectar_culpable()  # ✅ FIX: antes estaba cortado

        logger.info("ETL completado exitosamente.")

    # --------------------------------------------------
    # MÉTODOS INTERNOS (Privados)
    # --------------------------------------------------

    def _resolver_fuente_input(self) -> str:
        """
        Resuelve config.FILE_INPUT.
        Si es Excel o carpeta → genera/actualiza CSV consolidado y regresa la ruta del CSV.
        Si ya es CSV → regresa la misma ruta.
        """
        input_path = str(config.FILE_INPUT)
        p = Path(input_path)

        # Si ya es CSV, directo
        if p.is_file() and p.suffix.lower() == ".csv":
            return input_path

        # CSV consolidado por default (si no existe, lo creamos)
        # Puedes cambiarlo luego a una ruta en config.yaml si quieres.
        csv_out = Path("SII_concentrado_v3.csv")

        # Caso: carpeta con Excels
        if p.is_dir():
            logger.info("Input detectado como carpeta: %s", p)
            ejecutar_concentrado(str(p), archivo_salida=str(csv_out))
            if not csv_out.exists():
                raise FileNotFoundError(f"No se generó el CSV consolidado: {csv_out}")
            return str(csv_out)

        # Caso: Excel individual
        if p.is_file() and p.suffix.lower() in (".xlsx", ".xls"):
            logger.info("Input detectado como Excel: %s", p)

            df_nuevo = procesar_archivo_sii(str(p))

            # Si ya existe consolidado, anexamos y deduplicamos por id_reporte
            if csv_out.exists():
                historico = pd.read_csv(csv_out)
                df_out = pd.concat([historico, df_nuevo], ignore_index=True)
                if "id_reporte" in df_out.columns:
                    df_out = df_out.drop_duplicates(subset=["id_reporte"], keep="last")
            else:
                df_out = df_nuevo

            df_out.to_csv(csv_out, index=False, encoding="utf-8-sig")
            logger.info("CSV consolidado actualizado: %s", csv_out)

            return str(csv_out)

        # Si llega aquí, no soportado
        raise ValueError(
            "FILE_INPUT no soportado. Usa ruta a .csv, .xlsx/.xls o carpeta con Excels."
        )

    def _cargar_datos(self):
        # ✅ 0) Resolver fuente: CSV directo o generado desde Excel/carpeta
        csv_path = self._resolver_fuente_input()

        logger.info("Cargando insumo CSV: %s", csv_path)
        df = pd.read_csv(csv_path)

        required = {"estado", "anio", "mes", "metrica", "valor", "linea", "producto"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Faltan columnas requeridas en el CSV: {sorted(missing)}")

        # Tipos
        df["anio"] = pd.to_numeric(df["anio"], errors="coerce").fillna(0).astype(int)
        df["mes"] = pd.to_numeric(df["mes"], errors="coerce").fillna(0).astype(int)
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

        # Filtrado mínimo
        df = df[(df["anio"] > 0) & (df["mes"] > 0)].copy()

        # Fecha mensual (primer día del mes)
        df["fecha"] = pd.to_datetime(dict(year=df["anio"], month=df["mes"], day=1))

        # Estado -> nombre
        # Nota: mantener "Desconocido" pero empujarlo al final con prefijo.
        # IMPORTANTE: aquí config.ESTADOS_MX debe ser mapping {id:int -> "Nombre"}.
        df["nombre_estado"] = df["estado"].map(config.ESTADOS_MX).fillna("ZZ Desconocido")  # ✅ FIX paréntesis

        # Separación por métrica
        self.df_raw_monto = df[df["metrica"] == config.MET_MONTO].copy()
        self.df_raw_num = df[df["metrica"] == config.MET_NUM].copy()

        logger.info("Filas monto: %s | Filas num: %s", len(self.df_raw_monto), len(self.df_raw_num))

    def _crear_master_dataset(self):
        grp_cols = [pd.Grouper(key="fecha", freq="MS"), "linea", "nombre_estado", "producto"]

        m_agg = (
            self.df_raw_monto.groupby(grp_cols)["valor"]
            .sum()
            .reset_index()
            .rename(columns={"valor": "Monto"})
        )

        n_agg = (
            self.df_raw_num.groupby(grp_cols)["valor"]
            .sum()
            .reset_index()
            .rename(columns={"valor": "Num_Creditos"})
        )

        df_master = pd.merge(
            m_agg, n_agg, on=["fecha", "linea", "nombre_estado", "producto"], how="outer"
        ).fillna(0)

        # Ticket promedio
        df_master["Ticket_Promedio"] = np.where(
            df_master["Num_Creditos"] > 0,
            df_master["Monto"] / df_master["Num_Creditos"],
            0,
        )

        # Mapeos (vectorizados para escalar)
        linea_str = df_master["linea"].astype(str)

        conds = [
            linea_str.str.contains("Línea III", na=False),
            linea_str.str.contains("Línea II", na=False),
            linea_str.str.contains("Línea IV", na=False),
        ]

        choices = [
            "Línea III: Construcción",
            "Línea II: Adquisición",
            "Línea IV: Mejoramientos",
        ]

        df_master["Linea_Estrategica"] = np.select(conds, choices, default="OTROS")

        # Subtipo adquisición
        is_l2 = df_master["Linea_Estrategica"] == "Línea II: Adquisición"
        linea_lower = linea_str.str.lower()
        subtipo = np.select(
            [
                is_l2 & (linea_lower.str.contains("terreno", na=False) | linea_lower.str.contains("suelo", na=False)),
                is_l2 & (linea_lower.str.contains("vivienda", na=False)),
                is_l2,
            ],
            ["Terreno", "Vivienda", "Vivienda"],
            default=None,
        )
        df_master["Subtipo_Adquisicion"] = subtipo

        return df_master

    def _preparar_global_mensual(self):
        g = self.df_master.groupby("fecha").agg({"Monto": "sum", "Num_Creditos": "sum"}).copy()
        g["Ticket_Promedio"] = np.where(
            g["Num_Creditos"] > 0, g["Monto"] / g["Num_Creditos"], 0
        )
        return g

    def _preparar_df_linea_mensual(self):
        g = (
            self.df_master.groupby(["fecha", "linea"], as_index=False)
            .agg({"Monto": "sum", "Num_Creditos": "sum"})
        )
        g = g.rename(columns={"Monto": "Monto_Total"})
        g = g[g["Num_Creditos"] > 0].copy()
        g["Ticket_Promedio"] = g["Monto_Total"] / g["Num_Creditos"]
        return g

    def _preparar_analisis_global(self):
        df = self.df_global.copy()
        df = df.rename(columns={"Monto": "Monto_Total"})
        return df

    def _detectar_culpable(self):
        """Busca internamente al culpable y guarda el resultado en atributos de la clase."""
        df_recent = self.df_master[self.df_master["fecha"] >= config.FECHA_INICIO_ANIO_ANALISIS].copy()
        if df_recent.empty:
            return

        lineas = df_recent.groupby("linea").agg({"Monto": "sum", "Num_Creditos": "sum"})
        lineas = lineas[lineas["Num_Creditos"] > 0].copy()

        if not lineas.empty:
            lineas["Ticket"] = lineas["Monto"] / lineas["Num_Creditos"]
            self.culpable_linea = lineas["Ticket"].idxmax()
            self.culpable_ticket_val = float(lineas["Ticket"].max())

    # --------------------------------------------------
    # MÉTODOS PÚBLICOS (Helpers para las gráficas)
    # --------------------------------------------------

    def get_lineaII_vivienda_terreno(self, anio):
        """Filtra Linea II para vivienda vs terreno en un año específico."""
        df = self.df_master[
            (self.df_master["Linea_Estrategica"] == "Línea II: Adquisición")
            & (self.df_master["Subtipo_Adquisicion"].notna())
            & (self.df_master["fecha"].dt.year == anio)
        ].copy()

        out = (
            df.groupby(["Subtipo_Adquisicion", "producto"], as_index=False)
            .agg(Monto=("Monto", "sum"), Num_Creditos=("Num_Creditos", "sum"))
        )

        out = out[out["Num_Creditos"] > 0].copy()
        out["Ticket"] = out["Monto"] / out["Num_Creditos"]
        return out

    def get_linea_generica(self, anio, nombre_linea_estrategica):
        """Obtiene datos agrupados para cualquier línea estratégica."""
        df = self.df_master[
            (self.df_master["Linea_Estrategica"] == nombre_linea_estrategica)
            & (self.df_master["fecha"].dt.year == anio)
        ].copy()

        if df.empty:
            return pd.DataFrame()

        grp = (
            df.groupby("producto", as_index=False)
            .agg(Monto=("Monto", "sum"), Num_Creditos=("Num_Creditos", "sum"))
        )

        grp = grp[grp["Num_Creditos"] > 0].copy()
        grp["Ticket"] = grp["Monto"] / grp["Num_Creditos"]
        grp = grp.sort_values("Monto", ascending=False)
        return grp

    def get_lineaII_por_subtipo(self, anio, subtipo="Vivienda"):
        df = self.df_master[
            (self.df_master["Linea_Estrategica"] == "Línea II: Adquisición")
            & (self.df_master["Subtipo_Adquisicion"] == subtipo)
            & (self.df_master["fecha"].dt.year == anio)
        ].copy()

        grp = (
            df.groupby("producto", as_index=False)
            .agg(Monto=("Monto", "sum"), Num_Creditos=("Num_Creditos", "sum"))
        )

        grp = grp[grp["Num_Creditos"] > 0].copy()
        grp["Ticket"] = grp["Monto"] / grp["Num_Creditos"]
        return grp
