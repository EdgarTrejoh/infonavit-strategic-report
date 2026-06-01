import pandas as pd
import numpy as np
import datetime
import re

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.patheffects as path_effects
import matplotlib.dates as mdates
import seaborn as sns

import config
import utils
import etl

from .helpers import *

def plot_07_matriz_bcg(df_master, anio):
    df_year = df_master[df_master["fecha"].dt.year == anio].copy()
    if df_year.empty: return

    data = df_year.groupby("linea").agg({"Monto": "sum", "Num_Creditos": "sum"}).reset_index()
    data = data[data["Num_Creditos"] > 0].copy()
    data["Ticket"] = data["Monto"] / data["Num_Creditos"]
    data = data.sort_values("Monto", ascending=False)

    diccionario_colores = {
        "Línea II: Adquisición de suelo para uso habitacional": "#6F7271",
        "Línea II: Adquisición de vivienda existente": "#691C32",
        "Línea II: Adquisición de vivienda nueva": "#BC955C",
        "Línea III: Construcción": "#DDC9A3",
        "Línea IV: Mejoramientos": "#235B4E",
        "Línea V: Pago de pasivos": "#235B4E",
        "Otros: Créditos": "#98989A",
    }
    colores = [diccionario_colores.get(x, "#7f7f7f") for x in data["linea"]]

    monto = data["Monto"].astype(float)
    size_raw = (monto / float(monto.max())).clip(0, 1) ** 0.5
    sizes = 800 + size_raw * 5200

    fig, ax = plt.subplots(figsize=(14, 9))
    ax.scatter(data["Num_Creditos"], data["Ticket"], s=sizes, c=colores, alpha=0.80, edgecolors="white", linewidth=1.5, zorder=3)
    ax.axvline(float(data["Num_Creditos"].median()), color="#999999", linestyle="--", linewidth=1, alpha=0.7, zorder=1)
    ax.axhline(float(data["Ticket"].median()), color="#999999", linestyle="--", linewidth=1, alpha=0.7, zorder=1)

    ax.text(0.98, 0.95, "ESTRELLAS", transform=ax.transAxes, ha="right", va="top", color="#235B4E", alpha=0.55, fontweight="bold")
    ax.text(0.98, 0.09, "MASIVOS", transform=ax.transAxes, ha="right", va="bottom", color="#10312B", alpha=0.55, fontweight="bold")
    ax.text(0.02, 0.95, "NICHO", transform=ax.transAxes, ha="left", va="top", color="#691C32", alpha=0.55, fontweight="bold")

    diccionario_nombres = {
        "Línea II: Adquisición de suelo para uso habitacional": "Adq. Suelo",
        "Línea II: Adquisición de vivienda existente": "Viv. Existente",
        "Línea II: Adquisición de vivienda nueva": "Viv. Nueva",
        "Línea III: Construcción": "Construcción",
        "Línea IV: Mejoramientos": "Mejoramiento",
        "Línea V: Pago de pasivos": "P.Pasivos",
        "Otros: Créditos": "Otros"
    }

    offsets = {"Viv. Existente": (18, 10), "Viv. Nueva": (-18, 12), "Mejoramientos": (10, -10)}
    
    try: peff = [path_effects.withStroke(linewidth=3, foreground="white")]
    except: peff = None

    for _, row in data.iterrows():
        nombre = diccionario_nombres.get(row["linea"], row["linea"])[:15]
        dx, dy = offsets.get(nombre, (10, 10))
        ax.annotate(nombre, xy=(row["Num_Creditos"], row["Ticket"]), xytext=(dx, dy),
                    textcoords="offset points", ha="center", va="center", fontsize=10, fontweight="bold",
                    color="#333333", path_effects=peff, arrowprops=dict(arrowstyle="-", color="#666666", lw=0.6), zorder=4)

    ax.set_title(f"Matriz Estratégica: Volumen vs Ticket Promedio ({anio})", 
        loc="left", 
        fontweight="bold", 
        fontsize=15, 
        color="#333333", 
        pad=10
        )
    ax.set_xlabel("Volumen (# Créditos)", fontsize=12)
    ax.set_ylabel("Ticket Promedio ($)", fontsize=12)
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax.grid(True, linestyle="--", alpha=0.25, color="gray")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.figtext(0.01, 0.01, "Nota: El tamaño de la burbuja representa el Monto Total colocado.", fontsize=9, color="gray", style="italic")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    savefig(f"07_matriz_bcg_{anio}.png")

def plot_10_heatmap_ticket_mom(df_master):
    # CORRECCIÓN: config.ANIO_PREVIO
    df_heat = df_master[df_master["fecha"] >= f"{config.ANIO_PREVIO}-01-01"].copy()
    if df_heat.empty: return

    df_heat["periodo"] = df_heat["fecha"].dt.to_period("M")
    g = df_heat.groupby(["linea", "periodo"], as_index=False).agg(Monto=("Monto", "sum"), Num_Creditos=("Num_Creditos", "sum"))
    g["Ticket"] = np.where(g["Num_Creditos"] > 0, g["Monto"] / g["Num_Creditos"], np.nan)
    pivot_mom = g.pivot(index="linea", columns="periodo", values="Ticket").sort_index(axis=1).pct_change(axis=1) * 100

    values = pivot_mom.to_numpy().astype(float)
    if np.all(np.isnan(values)): return
    vmax = np.nanpercentile(np.abs(values[np.isfinite(values)]), 95)
    
    fig, ax = plt.subplots(figsize=(16, 8))
    cmap = plt.cm.RdYlGn.copy()
    cmap.set_bad(color="#f2f2f2")
    im = ax.imshow(values, aspect="auto", interpolation="nearest", cmap=cmap, vmin=-vmax, vmax=vmax)

    y_labels = list(pivot_mom.index)
    x_labels = [str(p) for p in pivot_mom.columns]
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels, fontsize=12)
    ax.set_xticks(range(len(x_labels)))
    n = max(1, len(x_labels) // 12)
    ax.set_xticklabels([lab if (i % n == 0) else "" for i, lab in enumerate(x_labels)], rotation=90, fontsize=10)
    
    ax.set_title("Mapa de Calor: Variación del Ticket vs Mes Previo (MoM %)", loc="left", color="#333333", fontweight="bold", fontsize=15)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Variación % MoM")
    cbar.ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    savefig("10_heatmap_ticket_mom.png")

def plot_10b_heatmap_ticket_nivel(df_master):
    # CORRECCIÓN: config.ANIO_PREVIO
    df_heat = df_master[df_master["fecha"] >= f"{config.ANIO_PREVIO}-01-01"].copy()
    if df_heat.empty: return

    df_heat["periodo"] = df_heat["fecha"].dt.to_period("M")
    g = df_heat.groupby(["linea", "periodo"], as_index=False).agg(Monto=("Monto", "sum"), Num_Creditos=("Num_Creditos", "sum"))
    g["Ticket_M"] = np.where(g["Num_Creditos"] > 0, (g["Monto"] / g["Num_Creditos"]) / 1_000_000, np.nan)
    pivot = g.pivot(index="linea", columns="periodo", values="Ticket_M").sort_index(axis=1)

    values = pivot.to_numpy().astype(float)
    if np.all(np.isnan(values)): return
    vmin, vmax = np.nanpercentile(values[np.isfinite(values)], [5, 95])

    fig, ax = plt.subplots(figsize=(16, 8))
    cmap = plt.cm.magma_r.copy()
    cmap.set_bad(color="#f2f2f2")
    im = ax.imshow(values, aspect="auto", interpolation="nearest", cmap=cmap, vmin=vmin, vmax=vmax)

    y_labels = list(pivot.index)
    x_labels = [str(p) for p in pivot.columns]
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels, fontsize=12)
    ax.set_xticks(range(len(x_labels)))
    n = max(1, len(x_labels) // 12)
    ax.set_xticklabels([lab if (i % n == 0) else "" for i, lab in enumerate(x_labels)], rotation=90, fontsize=10)

    ax.set_title("Mapa de Calor: Ticket Promedio por Producto (Millones MXN)", loc="left", color="#333333", fontweight="bold", fontsize=15)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Millones MXN")
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    savefig("10b_heatmap_ticket_nivel.png")

def plot_12_analysis_forense(df_linea):
    
    # --------------------------------------------------
    # 1) Detectar al ticket máximo en últimos 6 meses
    # --------------------------------------------------
    fecha_corte = df_linea["fecha"].max() - pd.DateOffset(months=6)
    df_recent = df_linea[df_linea["fecha"] >= fecha_corte].copy()
    if df_recent.empty: return

    # Identificamos la línea con el ticket más alto reciente
    culpable = df_recent.loc[df_recent["Ticket_Promedio"].idxmax()]["linea"]

    # --------------------------------------------------
    # 2) Filtrar datos de esa línea específica
    # --------------------------------------------------
    df_sospechoso = df_linea[
        (df_linea["linea"] == culpable) & 
        (df_linea["fecha"] >= config.FECHA_INICIO_FILTROS)
    ].copy()

    if df_sospechoso.empty: return

    # --------------------------------------------------
    # 3) Configuración de Ejes
    # --------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(14, 8))
    ax2 = ax1.twinx() # Eje secundario para el Ticket

    # --- EJE 1: Volumen (Barras de fondo) ---
    color_vol = "#cfd8dc" # Gris azulado suave
    ax1.bar(
        df_sospechoso["fecha"], 
        df_sospechoso["Num_Creditos"], 
        color=color_vol, 
        alpha=0.6, # Un poco más transparente para no robar atención
        width=20, 
        label="Volumen (#)"
    )
    ax1.set_ylabel("Volumen (#)", fontsize=12, color="#546e7a")
    ax1.yaxis.set_major_formatter(mtick.StrMethodFormatter('{x:,.0f}'))

    # --- EJE 2: Ticket Promedio (Línea Principal) ---
    color_ticket = config.COLOR_INFONAVIT # Vino corporativo
    ax2.plot(
        df_sospechoso["fecha"], 
        df_sospechoso["Ticket_Promedio"], 
        color=color_ticket, 
        linewidth=3.5, 
        marker="o",
        markersize=6,
        label="Ticket Promedio ($)"
    )
    ax2.set_ylabel("Ticket Promedio ($)", fontsize=12, color=color_ticket)
    ax2.yaxis.set_major_formatter(formatter_human)

    # Margen extra arriba para que quepa la etiqueta del máximo
    ymax = df_sospechoso["Ticket_Promedio"].max() * 1.15
    ymin = df_sospechoso["Ticket_Promedio"].min() * 0.90
    ax2.set_ylim(ymin, ymax)
    ax2.grid(False) # Apagamos grid del eje 2 para limpieza

    # --------------------------------------------------
    # 4) Títulos y Formatos
    # --------------------------------------------------
    nombre_limpio = culpable.split(".")[0] if ":" in culpable else culpable
    fig.suptitle(f"Análisis {nombre_limpio}", x=0.06, ha="left", fontsize=16, fontweight="bold", color="#333333")
    
    # Eje X en español (Helper propio para evitar problemas de idioma en servidor)
    meses_es = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    def fmt_mes_custom(x, pos=None):
        dt = mdates.num2date(x)
        return f"{meses_es[dt.month-1]}\n{str(dt.year)[-2:]}" # Ene\n24

    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3)) # Cada trimestres para no saturar
    ax1.xaxis.set_major_formatter(mtick.FuncFormatter(fmt_mes_custom))
    
    # Leyenda unificada
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False)

    # --------------------------------------------------
    # 9) ANOTACIÓN DEL MÁXIMO 
    # --------------------------------------------------
    # Encontrar el punto exacto
    idx_max = df_sospechoso["Ticket_Promedio"].idxmax()
    val_max = df_sospechoso.loc[idx_max, "Ticket_Promedio"]
    fecha_max = df_sospechoso.loc[idx_max, "fecha"]

    # Crear el texto (usamos human_format para que salga "909k" o "1.2MM")
    texto_etiqueta = f"Máximo: {human_format(val_max)}"

    # Añadir la anotación
    ax2.annotate(
        texto_etiqueta,
        xy=(fecha_max, val_max),
        xytext=(0, 15), # 15 puntos hacia arriba
        textcoords="offset points",
        ha="center", 
        va="bottom",
        fontsize=10, 
        fontweight="bold",
        color=color_ticket,
        # Caja blanca para que se lea bien sobre las barras o líneas
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color_ticket, alpha=0.9),
        # Flecha apuntando al punto
        arrowprops=dict(arrowstyle="->", color=color_ticket, linewidth=1.5)
    )

    # --------------------------------------------------
    # Limpieza Final
    # --------------------------------------------------
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False) # Ocultamos borde izquierdo del eje derecho

    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color='gray', style='italic')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    savefig("12_analysis_forense.png")

def plot_14_matriz_estrategica_full(df_master, anio):
    """
    14. Matriz Estratégica de Cartera (Año) - VERSIÓN IMPACTO
    Mejoras:
    - Colores corporativos por línea.
    - Nombres cortos para limpieza visual.
    - Etiquetas de cuadrantes (Estrellas, Masivos, Nicho).
    - Ajuste manual de etiquetas para evitar superposiciones.
    """
    # 1. Preparación de Datos
    df_anio = df_master[df_master["fecha"].dt.year == anio].copy()
    if df_anio.empty: return

    data = (
        df_anio.groupby("linea")
        .agg(Monto=("Monto", "sum"), Num_Creditos=("Num_Creditos", "sum"))
        .reset_index()
    )
    data = data[data["Num_Creditos"] > 0].copy()
    data["Ticket_Promedio"] = data["Monto"] / data["Num_Creditos"]

    # 2. Branding (Colores y Nombres Cortos)
    # Definimos explícitamente para asegurar consistencia
    config_visual = {
        "Línea II: Adquisición de vivienda existente":   {"color": "#691C32", "label": "Viv. Existente"}, # Vino
        "Línea II: Adquisición de vivienda nueva":       {"color": "#BC955C", "label": "Viv. Nueva"},     # Dorado
        "Línea IV: Mejoramientos":                       {"color": "#235B4E", "label": "Mejora"},   # Verde
        "Línea III: Construcción":                       {"color": "#10312B", "label": "Construcción"},    # Verde Oscuro
        "Línea V: Pago de pasivos":                      {"color": "#6F7271", "label": "P. Pasivos"},   # Gris
        "Línea II: Adquisición de suelo para uso habitacional": {"color": "#8D6E63", "label": "Adq. Suelo"},
        "Otros: Créditos":                               {"color": "#98989A", "label": "Otros"},
        "Otros: Créditos por emergencia":                {"color": "#D0D0D0", "label": "Emergencia"}
    }

    # Asignar color y label al dataframe
    data["color"] = data["linea"].map(lambda x: config_visual.get(x, {}).get("color", "#7f7f7f"))
    data["label"] = data["linea"].map(lambda x: config_visual.get(x, {}).get("label", x[:10]))

    # 3. Escala de Burbujas
    # Normalizamos para que la más grande tenga un tamaño fijo razonable
    max_area = 6000
    monto_vals = data["Monto"].values.astype(float)
    sizes = (monto_vals / monto_vals.max()) * max_area
    # Asegurar un tamaño mínimo para que se vean las pequeñas
    sizes = np.maximum(sizes, 150)

    # 4. Definición de Cuadrantes (Medianas)
    avg_vol = data["Num_Creditos"].median()
    avg_ticket = data["Ticket_Promedio"].median()

    # 5. Plot
    fig, ax = plt.subplots(figsize=(16, 10))

    # Scatter
    ax.scatter(
        data["Num_Creditos"],
        data["Ticket_Promedio"],
        s=sizes,
        c=data["color"],
        alpha=0.75,         # Transparencia para ver superposiciones
        edgecolors="white", # Borde blanco para definición
        linewidth=1.5,
        zorder=3
    )

    # Líneas de cuadrantes
    ax.axvline(avg_vol, color="gray", linestyle="--", alpha=0.4, zorder=1)
    ax.axhline(avg_ticket, color="gray", linestyle="--", alpha=0.4, zorder=1)

    # 6. Etiquetas de Fondo (Zonas Estratégicas)
    # Usamos coordenadas relativas (transform=ax.transAxes)
    props_font = dict(fontsize=16, fontweight="bold", alpha=0.15, zorder=0)
    
    # Cuadrante 1 (Der-Arr): Alto Vol, Alto Ticket
    ax.text(0.95, 0.95, "ESTRELLAS\n(Alto Valor)", transform=ax.transAxes, ha="right", va="top", color="#BC955C", **props_font)
    
    # Cuadrante 2 (Der-Abajo): Alto Vol, Bajo Ticket
    ax.text(0.95, 0.15, "MASIVOS\n(Volumen)", transform=ax.transAxes, ha="right", va="bottom", color="#235B4E", **props_font)
    
    # Cuadrante 3 (Izq-Arr): Bajo Vol, Alto Ticket
    ax.text(0.05, 0.95, "NICHO\n(Selectos)", transform=ax.transAxes, ha="left", va="top", color="#691C32", **props_font)

    # 7. Etiquetado Inteligente (Smart Labeling Manual)
    # Definimos offsets manuales para los casos conocidos que se enciman
    # (dx, dy) en puntos
    offsets_manuales = {
        "Viv. Nueva": (-40, 20),      # Mover a la izquierda arriba
        "Viv. Existente": (40, -10),  # Mover a la derecha abajo
        "Mejora": (0, -35),     # Debajo de la burbuja
        "Consgtrucción": (0, 35)        # Arriba de la burbuja
    }

    import matplotlib.patheffects as path_effects
    peff = [path_effects.withStroke(linewidth=3, foreground="white")]

    for _, row in data.iterrows():
        lbl = row["label"]
        x, y = row["Num_Creditos"], row["Ticket_Promedio"]
        
        # Obtener offset manual o calcular automático básico
        if lbl in offsets_manuales:
            dx, dy = offsets_manuales[lbl]
        else:
            # Lógica automática simple: alejarse del centro
            dx = 20 if x > avg_vol else -20
            dy = 20 if y > avg_ticket else -20

        ax.annotate(
            lbl,
            xy=(x, y),
            xytext=(dx, dy),
            textcoords="offset points",
            ha="center", va="center",
            fontsize=10, fontweight="bold", color="#333333",
            path_effects=peff,
            arrowprops=dict(arrowstyle="-", color="gray", alpha=0.5),
            zorder=5
        )

    # 8. Estilo Final
    ax.set_title(f"Matriz Estratégica de Productos ({anio})", loc="left", color="#333333", fontsize=15, fontweight="bold", pad=10)
    
    ax.set_xlabel("Volumen (Número de Créditos)", fontsize=12)
    ax.set_ylabel("Valor (Ticket Promedio $)", fontsize=12)
    
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    ax.yaxis.set_major_formatter(formatter_human)

    # Expandir márgenes un 10% para que quepan las burbujas grandes
    ax.margins(0.15)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#dddddd")
    ax.spines["bottom"].set_color("#dddddd")
    ax.grid(True, linestyle="--", alpha=0.35, color="gray")

    plt.figtext(0.01, 0.01, "Nota: El tamaño de la burbuja representa el Monto Total ($).", fontsize=9, color="gray", style="italic")

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    savefig("14_matriz_estrategica_bubble.png")

def plot_21_elasticidad_ticket_vs_volumen(df_master, anio_objetivo, meses_hasta=None, top_n=10, min_creditos=100):
    """
    Matriz de Elasticidad: Ticket Promedio vs Volumen.
    AJUSTE: Implementación de nombres cortos y colores homologados.
    """
    # 1. Preparación de Datos
    df = df_master[df_master["fecha"].dt.year == anio_objetivo].copy()
    
    grp = df.groupby("linea").agg(
        Monto=("Monto", "sum"),
        Num_Creditos=("Num_Creditos", "sum")
    ).reset_index()
    
    grp = grp[grp["Num_Creditos"] > min_creditos].copy()
    if grp.empty: return

    grp["Ticket"] = grp["Monto"] / grp["Num_Creditos"]

    # 2. Diccionario de Configuración Visual (Homologado con plot_14)
    config_visual = {
        "Línea II: Adquisición de vivienda existente":   {"color": "#691C32", "label": "Viv. Existente"},
        "Línea II: Adquisición de vivienda nueva":       {"color": "#BC955C", "label": "Viv. Nueva"},
        "Línea IV: Mejoramientos":                       {"color": "#235B4E", "label": "Mejora"},
        "Línea III: Construcción":                       {"color": "#10312B", "label": "Construcción"},
        "Línea V: Pago de pasivos":                      {"color": "#6F7271", "label": "P. Pasivos"},
        "Línea II: Adquisición de suelo para uso habitacional": {"color": "#8D6E63", "label": "Adq. Suelo"},
        "Otros: Créditos":                               {"color": "#98989A", "label": "Otros"}
    }

    # Asignar propiedades visuales
    grp["color"] = grp["linea"].map(lambda x: config_visual.get(x, {}).get("color", "#7f7f7f"))
    grp["label_corto"] = grp["linea"].map(lambda x: config_visual.get(x, {}).get("label", x[:15]))

    # 3. Estadísticas para Cuadrantes
    avg_ticket = grp["Ticket"].median()
    avg_vol = grp["Num_Creditos"].median()

    # 4. Gráfico
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Escala de burbujas (normalizada)
    s_factor = 2500 * (grp["Monto"] / grp["Monto"].max())
    s_factor = np.maximum(s_factor, 200) # Tamaño mínimo
    
    ax.scatter(
        grp["Num_Creditos"], 
        grp["Ticket"], 
        s=s_factor, 
        c=grp["color"], 
        alpha=0.7, 
        edgecolors="white", 
        linewidth=1.5,
        zorder=3
    )

    # Cuadrantes
    ax.axhline(avg_ticket, color='gray', linestyle='--', alpha=0.4, zorder=1)
    ax.axvline(avg_vol, color='gray', linestyle='--', alpha=0.4, zorder=1)

    # 5. Etiquetado Inteligente
    import matplotlib.patheffects as path_effects
    peff = [path_effects.withStroke(linewidth=3, foreground="white")]

    for _, row in grp.iterrows():
        # Desplazamiento simple para evitar que el texto esté justo encima del centro de la burbuja
        ax.annotate(
            row["label_corto"],
            xy=(row["Num_Creditos"], row["Ticket"]),
            xytext=(10, 10),
            textcoords="offset points",
            fontsize=10,
            fontweight='bold',
            color="#333333",
            path_effects=peff,
            zorder=4
        )

    # 6. Estilo y Formato
    ax.set_title(f"Matriz de Elasticidad: Precio vs Volumen ({anio_objetivo})", loc='left', fontweight="bold", fontsize=15, color="#333333", pad=20)
    ax.set_ylabel("Ticket Promedio ($)", fontsize=12)
    ax.set_xlabel("Volumen de Créditos (#)", fontsize=12)
    
    ax.yaxis.set_major_formatter(formatter_human)
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter('{x:,.0f}'))

    # Limpieza
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, linestyle='--', alpha=0.3, color='gray', zorder=0)

    # Nota al pie
    plt.figtext(0.01, 0.01, "Nota: El tamaño de la burbuja representa el Monto Total Colocado ($). | Fuente: Sistema de Información INFONAVIT", fontsize=9, color='gray', style='italic')

    plt.tight_layout()
    savefig("21_elasticidad_precio_volumen.png")

def plot_22_reporte_ejecutivo(df_master, anio):
    """
    22. Reporte Ejecutivo de Desempeño (Dashboard de Semáforos)
    Transforma datos complejos en una tabla visual de fácil lectura.
    """
    # 1. Preparación de Datos
    anios = [anio, anio - 1]
    df = df_master[df_master["fecha"].dt.year.isin(anios)].copy()
    
    # Agrupar por Línea (Nombres cortos)
    mapa_corto = {
        "Línea II: Adquisición de vivienda existente": "L2 Existente",
        "Línea II: Adquisición de vivienda nueva": "L2 Nueva",
        "Línea IV: Mejoramientos": "L4 Mejoras",
        "Línea III: Construcción": "L3 Const.",
        "Línea V: Pago de pasivos": "L5 Pasivos"
    }
    df["Producto"] = df["linea"].map(lambda x: mapa_corto.get(x, "Otros"))
    
    resumen = df.groupby([df["fecha"].dt.year, "Producto"])["Monto"].sum().unstack(level=0).fillna(0)
    resumen.columns = ["Previo", "Actual"]
    
    # Cálculos clave
    resumen["Var_Abs"] = resumen["Actual"] - resumen["Previo"]
    resumen["Var_Pct"] = (resumen["Actual"] / resumen["Previo"] - 1) * 100
    resumen["Share"] = (resumen["Actual"] / resumen["Actual"].sum()) * 100
    resumen = resumen.sort_values("Actual", ascending=False)

    # 2. Configuración del Gráfico (Tipo Tabla Visual)
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_axis_off() # No queremos ejes, queremos una tabla limpia

    # Encabezados
    cols = ["Producto", "Monto Actual", "Crecimiento YoY", "Share %"]
    col_x = [0.1, 0.4, 0.65, 0.85]
    
    # Dibujar encabezados
    for i, col in enumerate(cols):
        ax.text(col_x[i], 0.9, col, fontweight="bold", fontsize=13, color="#333333", ha="center")
    
    ax.axhline(0.87, color="#691C32", linewidth=2, xmin=0.05, xmax=0.95)

    # 3. Dibujar Filas
    for i, (idx, row) in enumerate(resumen.iterrows()):
        y_pos = 0.75 - (i * 0.12)
        
        # Nombre Producto
        ax.text(col_x[0], y_pos, idx, fontsize=12, fontweight="bold", ha="center")
        
        # Monto Actual (Formateado)
        ax.text(col_x[1], y_pos, f"${human_format(row['Actual'])}", fontsize=12, ha="center")
        
        # Crecimiento YoY (Con Semáforo)
        color_var = config.COLOR_POS if row["Var_Pct"] >= 0 else config.COLOR_NEG
        triangulo = "▲" if row["Var_Pct"] >= 0 else "▼"
        ax.text(col_x[2], y_pos, f"{triangulo} {row['Var_Pct']:+.1f}%", 
                fontsize=12, fontweight="bold", color=color_var, ha="center",
                bbox=dict(boxstyle="round,pad=0.3", fc=color_var, ec="none", alpha=0.1))
        
        # Share % (Barra de progreso visual)
        share_val = row["Share"]
        ax.text(col_x[3], y_pos, f"{share_val:.1f}%", fontsize=12, ha="center")
        # Mini barra de share debajo del texto
        ax.add_patch(plt.Rectangle((col_x[3]-0.05, y_pos-0.03), 0.1 * (share_val/100), 0.01, color="#BC955C"))

    # 4. Título y Notas
    plt.suptitle(f"Resumen Ejecutido de Colocación ({anio})", fontsize=15, fontweight="bold", y=0.98)
    plt.figtext(0.5, 0.05, f"Total Colocado: ${human_format(resumen['Actual'].sum())} | Variación Total: {((resumen['Actual'].sum()/resumen['Previo'].sum())-1)*100:+.1f}%", 
                ha="center", fontsize=12, fontweight="bold", bbox=dict(boxstyle="round,pad=0.5", fc="#f5f5f5", ec="#dddddd"))

    plt.tight_layout()
    savefig("22_reporte_ejecutivo.png")

def plot_40_cagr_productos(df_master, anio_fin, periodo=3):
    """
    40. CAGR por Producto - VERSIÓN LIMPIA (Sin Otros/Emergencia)
    Filtra productos con poco historial o ruido estadístico.
    """
    anio_ini = anio_fin - periodo
    df = df_master[df_master["fecha"].dt.year.isin([anio_ini, anio_fin])].copy()
    
    mapa_corto = {
        "Línea II: Adquisición de vivienda existente": "L2 Existente",
        "Línea II: Adquisición de vivienda nueva": "L2 Nueva",
        "Línea IV: Mejoramientos": "L4 Mejoras",
        "Línea III: Construcción": "L3 Const.",
        "Línea V: Pago de pasivos": "L5 Pasivos"
    }
    df["Producto"] = df["linea"].map(lambda x: mapa_corto.get(x, None))
    
    # ELIMINAR RUIDO: Quitamos los que no mapeamos (Otros/Emergencia/Suelo nuevo)
    df = df.dropna(subset=["Producto"])
    
    data = df.groupby([df["fecha"].dt.year, "Producto"])["Monto"].sum().unstack()
    if anio_ini not in data.index or anio_fin not in data.index: return

    # Cálculo CAGR
    cagr = ((data.loc[anio_fin] / data.loc[anio_ini]) ** (1/periodo)) - 1
    cagr = (cagr * 100).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Colores corporativos aplicados al CAGR
    mapa_colores = {
        "L2 Existente": "#691C32", "L2 Nueva": "#BC955C", "L4 Mejoras": "#235B4E",
        "L3 Const.": "#10312B", "L5 Pasivos": "#6F7271"
    }
    colores = [mapa_colores.get(prod, "#333333") for prod in cagr.index]
    
    bars = ax.barh(cagr.index, cagr.values, color=colores, alpha=0.9)
    
    # LÍNEA DE BENCHMARK (Ejemplo: Inflación o Meta del 5%)
    benchmark = 5.0 
    ax.axvline(benchmark, color='#d32f2f', linestyle='--', alpha=0.6, label=f"Benchmark ({benchmark}%)")
    ax.axvline(0, color='black', linewidth=1)

    for bar in bars:
        w = bar.get_width()
        ax.annotate(f"{w:+.1f}%", xy=(w, bar.get_y() + bar.get_height()/2),
                    xytext=(5 if w>0 else -5, 0), textcoords="offset points",
                    ha='left' if w>0 else 'right', va='center', fontweight='bold', fontsize=11)

    ax.set_title(f"CAGR por Línea de Negocio ({anio_ini}-{anio_fin})", loc="left", fontsize=15, fontweight="bold")
    ax.set_xlabel("Tasa de Crecimiento Anual Compuesta (%)", fontweight="bold", color="gray")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.legend(loc="lower right", frameon=False)
    
    plt.figtext(0.01, 0.01, f"Nota: Se excluyen productos con historial menor a {periodo} años para evitar ruido estadístico.", 
                fontsize=9, color="gray", style="italic")
    
    plt.tight_layout()
    savefig("40_cagr_productos.png")

def plot_41_matriz_crecimiento_estados(df_master, anio_fin, periodo=3):
    """
    41. Matriz de Oportunidad Estatal (CAGR vs Monto).
    AJUSTES: Colores corporativos, limpieza de etiquetas encimadas y diseño ejecutivo.
    """
    anio_ini = anio_fin - periodo
    df_periodo = df_master[df_master["fecha"].dt.year.isin([anio_ini, anio_fin])].copy()
    
    stats = df_periodo.groupby([df_periodo["fecha"].dt.year, "nombre_estado"])["Monto"].sum().unstack(level=0)
    stats.columns = ["Vi", "Vf"]
    stats = stats.dropna()

    stats["CAGR"] = (((stats["Vf"] / stats["Vi"]) ** (1/periodo)) - 1) * 100
    stats["Monto_Actual"] = stats["Vf"]
    
    # Filtro de ruido para evitar distorsiones visuales
    stats = stats[stats["CAGR"] < 100]

    fig, ax = plt.subplots(figsize=(14, 10))
    
    # --- PALETA CORPORATIVA ---
    # Usamos un mapa de colores que va de Gris (estable) a Vino (crecimiento explosivo)
    from matplotlib.colors import LinearSegmentedColormap
    colors = ["#D0D0D0", "#BC955C", "#691C32"] # Gris -> Dorado -> Vino
    n_bins = 100
    cmap_infonavit = LinearSegmentedColormap.from_list("infonavit_cagr", colors, N=n_bins)

    # Burbujas escaladas por monto actual
    max_monto = stats["Monto_Actual"].max()
    sizes = (stats["Monto_Actual"] / max_monto) * 8000
    sizes = np.maximum(sizes, 200) # Tamaño mínimo para visibilidad

    scatter = ax.scatter(
        stats["CAGR"], stats["Monto_Actual"], 
        s=sizes, 
        c=stats["CAGR"], 
        cmap=cmap_infonavit, 
        alpha=0.75, 
        edgecolors="white", 
        linewidth=1.5,
        zorder=3
    )

    # --- LÍNEAS DE REFERENCIA (Medianas) ---
    med_cagr = stats["CAGR"].median()
    med_monto = stats["Monto_Actual"].median()
    ax.axvline(med_cagr, color="#999999", linestyle="--", alpha=0.6, lw=1.5, zorder=1)
    ax.axhline(med_monto, color="#999999", linestyle="--", alpha=0.6, lw=1.5, zorder=1)

    # --- ETIQUETADO INTELIGENTE (Smart Labeling) ---
    import matplotlib.patheffects as path_effects
    peff = [path_effects.withStroke(linewidth=3, foreground="white")]
    
    # Ordenar para etiquetar prioritarios (más grandes o más crecimiento)
    top_monto = stats.nlargest(10, "Monto_Actual").index
    top_growth = stats.nlargest(5, "CAGR").index
    interes = top_monto.union(top_growth)

    for state in interes:
        row = stats.loc[state]
        # Pequeño ajuste manual para estados específicos que suelen chocar
        offset_y = 15 if row["Monto_Actual"] > med_monto else -15
        
        ax.annotate(
            state, 
            xy=(row["CAGR"], row["Monto_Actual"]),
            xytext=(0, offset_y),
            textcoords="offset points",
            ha='center', va='center',
            fontsize=10, fontweight='bold',
            color="#333333",
            path_effects=peff,
            zorder=5
        )

    # --- FORMATOS Y TÍTULOS ---
    ax.set_title(f"MATRIZ DE POSICIONAMIENTO ESTATAL ({anio_ini}-{anio_fin})", 
                 loc="left", fontsize=15, fontweight="bold", color="#333333", pad=30)
    
    ax.set_xlabel(f"Tasa de Crecimiento Anual Compuesta (CAGR %)", fontsize=12, fontweight="bold", labelpad=15)
    ax.set_ylabel("Monto Colocado Anual ($)", fontsize=12, fontweight="bold", labelpad=15)
    
    ax.yaxis.set_major_formatter(formatter_human)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))

    # Etiquetas de Cuadrantes (Zonas Estratégicas)
    props = dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.1, edgecolor='none')
    ax.text(0.95, 0.95, "ESTRELLAS\n(Crecimiento y Escala)", transform=ax.transAxes, ha="right", va="top", color="#691C32", fontsize=14, fontweight="bold", alpha=0.3)
    ax.text(0.05, 0.95, "MADUROS\n(Volumen Estable)", transform=ax.transAxes, ha="left", va="top", color="#6F7271", fontsize=14, fontweight="bold", alpha=0.3)

    # Limpieza
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, linestyle='--', alpha=0.2, color='gray')

    plt.figtext(0.01, 0.01, f"Nota: Tamaño de burbuja proporcional al monto actual. | Mediana CAGR: {med_cagr:.1f}%", 
                fontsize=9, color="gray", style="italic")

    plt.tight_layout()
    savefig("41_matriz_cagr_estados.png")

def plot_99_resumen_ejecutivo(df_master, df_global, anio_objetivo):
    last_date = df_global.index.max()
    kpi_monto = df_global.loc[last_date, "Monto"]
    kpi_num = df_global.loc[last_date, "Num_Creditos"]
    
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111); ax.axis("off")
    ax.text(0.02, 0.94, "RESUMEN EJECUTIVO", fontsize=22, fontweight="bold", color="#691C32")
    ax.text(0.04, 0.74, f"• Monto: {human_format(kpi_monto)}", fontsize=13)
    ax.text(0.04, 0.70, f"• Volumen: {kpi_num:,.0f}", fontsize=13)
    
    if getattr(config, "PDF_REPORT", None): config.PDF_REPORT.savefig(fig)
    plt.close()
    savefig("99_resumen_ejecutivo.png")


