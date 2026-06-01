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

def plot_01_monto_nacional(df_global):
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(df_global.index, df_global["Monto"], color="#691C32", linewidth=2.5)
    ax.fill_between(df_global.index, df_global["Monto"], color="#691C32", alpha=0.09)
    ax.set_title("Evolución mensual del Monto de crédito otorgado ($)", loc="left", fontweight="bold", fontsize=15, color="#333333", pad=10)
    ax.set_ylabel("Cifras en miles de Millones de Pesos", fontsize=12)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35, color="gray")
    ax.grid(False, axis="x")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#dddddd")
    ax.spines["bottom"].set_color("#dddddd")
    ax.yaxis.set_major_formatter(formatter_human)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fecha_max = df_global["Monto"].idxmax()
    monto_max = float(df_global["Monto"].max())
    ax.set_ylim(bottom=0, top=monto_max * 1.15)
    
    x_min, x_max = ax.get_xlim()
    x_pos = mdates.date2num(fecha_max)
    is_near_right = x_pos > (x_min + 0.75 * (x_max - x_min))
    xytext = (-40, 25) if is_near_right else (40, 25)
    ha = "right" if is_near_right else "left"

    ax.annotate(f"Máximo histórico: {monto_max / 1_000_000_000:.1f}", xy=(fecha_max, monto_max),
                xytext=xytext, textcoords="offset points", ha=ha,
                arrowprops=dict(arrowstyle="->", color="black", connectionstyle="arc3,rad=.2"),
                fontsize=10, fontweight="bold", color="#691C32")
    plt.figtext(0.01, 0.005, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", 
                fontsize=9, color="gray", style="italic", ha="left", va="bottom")
    
    fig.tight_layout(rect=[0, 0.08, 1, 0.98])
    savefig("01_monto_nacional.png")

def plot_02_volumen_nacional(df_global):
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(df_global.index, df_global["Num_Creditos"], color="#10312B", linewidth=2.5)
    ax.fill_between(df_global.index, df_global["Num_Creditos"], color="#235B4E", alpha=0.09)
    ax.set_title("Evolución mensual del numero de créditos otorgados", loc="left", fontweight="bold", fontsize=15, color="#333333", pad=10)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35, color="gray")
    ax.grid(False, axis="x")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#dddddd")
    ax.spines["bottom"].set_color("#dddddd")
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    y_max = float(df_global["Num_Creditos"].max())
    y_min = float(df_global["Num_Creditos"].min())
    ax.set_ylim(bottom=max(0, y_min * 0.85), top=y_max * 1.15)

    fecha_min = df_global["Num_Creditos"].idxmin()
    x_min, x_max = ax.get_xlim()
    x_pos = mdates.date2num(fecha_min)
    is_near_right = x_pos > (x_min + 0.75 * (x_max - x_min))
    xytext = (-40, 40) if is_near_right else (40, 40)
    ha = "right" if is_near_right else "left"

    ax.annotate(f"Mínimo histórico \n(post-2020): {y_min:,.0f}", xy=(fecha_min, y_min),
                xytext=xytext, textcoords="offset points", ha=ha,
                arrowprops=dict(arrowstyle="->", color="black", connectionstyle="arc3,rad=.2"),
                fontsize=10, fontweight="bold", color="#10312B")
    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    savefig("02_volumen_nacional.png")

def plot_03_ticket_nacional(df_global):
    # CORRECCIÓN: Usar config.FECHA_INICIO_FILTROS
    df_zoom = df_global[df_global.index >= config.FECHA_INICIO_FILTROS]

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(df_zoom.index, df_zoom["Ticket_Promedio"], color="#BC955C", linewidth=3)
    ax.fill_between(df_zoom.index, df_zoom["Ticket_Promedio"], color="#DDC9A3", alpha=0.09)
    ax.set_title("Evolución del Ticket Promedio ($ corrientes)", loc="left", fontweight="bold", fontsize=15, color="#333333", pad=10)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35, color="gray")
    ax.grid(False, axis="x")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#dddddd")
    ax.spines["bottom"].set_color("#dddddd")
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax.xaxis.set_major_locator(mdates.YearLocator(1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    fecha_max = df_zoom["Ticket_Promedio"].idxmax()
    valor_max = float(df_zoom["Ticket_Promedio"].max())
    valor_min = float(df_zoom["Ticket_Promedio"].min())
    ax.set_ylim(bottom=valor_min * 0.95, top=valor_max * 1.20)

    x_min, x_max = ax.get_xlim()
    x_pos = mdates.date2num(fecha_max)
    is_near_right = x_pos > (x_min + 0.75 * (x_max - x_min))
    xytext = (-40, 20) if is_near_right else (40, 20)
    ha = "right" if is_near_right else "left"

    ax.annotate(f"Máximo: ${valor_max:,.0f}", xy=(fecha_max, valor_max),
                xytext=xytext, textcoords="offset points", ha=ha,
                arrowprops=dict(arrowstyle="->", color="black", connectionstyle="arc3,rad=.2"),
                fontsize=10, fontweight="bold", color="#BC955C")
    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    savefig("03_ticket_nacional.png")

def plot_06_crecimiento_yoy(df_global):
    df_yoy = calcular_crecimiento_yoy(df_global, metrica="Monto")
    if df_yoy.shape[1] == 0: return
    col_plot = df_yoy.columns[-1]
    data_plot = df_yoy[col_plot].dropna()
    if data_plot.empty: return

    # CORRECCIÓN: Usar config.COLOR_POS/NEG
    colores = [config.COLOR_POS if x >= 0 else config.COLOR_NEG for x in data_plot]

    fig, ax = plt.subplots(figsize=(14, 6.5))
    bars = ax.bar(data_plot.index, data_plot, color=colores, width=0.75, alpha=0.90)
    ax.set_title(f"Indicador de Variación: {col_plot} (%)", loc="left", fontweight="bold", fontsize=15, color="#333333", pad=10)
    ax.set_ylabel("Variación % vs Año Anterior", fontsize=12)
    ax.axhline(0, color="black", linewidth=1)
    
    mapa_meses = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}
    ax.set_xticks(list(data_plot.index))
    ax.set_xticklabels([mapa_meses.get(m, str(m)) for m in data_plot.index], fontsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.30, color="gray")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)

    y_min, y_max = float(min(0, data_plot.min())), float(max(0, data_plot.max()))
    y_range = max(1e-6, y_max - y_min)
    pad = 0.03 * y_range

    try:
        peff = [path_effects.withStroke(linewidth=3, foreground="white")]
    except:
        peff = None

    for bar in bars:
        h = bar.get_height()
        va = "bottom" if h >= 0 else "top"
        y = h + pad if h >= 0 else h - pad
        ax.text(bar.get_x() + bar.get_width() / 2, y, f"{h:+.1f}%",
                ha="center", va=va, fontsize=9, fontweight="bold", color="#333333", path_effects=peff)

    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    savefig("06_crecimiento_yoy.png")

def plot_08_ciclos_estacionalidad(df_global):
    df = df_global.copy()
    df["mes"] = df.index.month
    df["anio"] = df.index.year
    pivot = df.pivot_table(index="mes", columns="anio", values="Monto")
    pivot = pivot[pivot.columns[-3:]]

    mapa_colores = {
        config.ANIO_PREVIO: "#9e9e9e",
        config.ANIO_ANALISIS: config.COLOR_INFONAVIT,
        config.ANIO_OBJETIVO: config.COLOR_POS
    }
    colores_plot = [mapa_colores.get(col, config.COLOR_NEUTRO) for col in pivot.columns]

    fig, ax = plt.subplots(figsize=(14, 8))
    pivot.plot(ax=ax, linewidth=3.5, marker="o", markersize=9, color=colores_plot)

    if config.ANIO_ANALISIS in pivot.columns:
        base_idx = list(pivot.columns).index(config.ANIO_ANALISIS)
        ax.lines[base_idx].set_linewidth(4.5)
        ax.lines[base_idx].set_zorder(5)

    ax.set_title("Ciclos de Negocio: Comparativo Mes a Mes", loc="left", fontweight="bold", fontsize=15, color="#333333", pad=10)
    ax.yaxis.set_major_formatter(formatter_human)
    ax.set_ylabel("Cifras en miles de Millones de Pesos", fontsize=12)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'], fontsize=12)
    ax.set_xlabel("")
    ax.legend(title="Año", title_fontsize=12, fontsize=12, loc="upper left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, linestyle="--", alpha=0.4, color="gray")
    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    savefig("08_ciclos_estacionalidad.png")

def plot_09_carrera_anual(df_global, anios_interes):
   
    # 1) Preparación de datos
    df_race = df_global.copy()
    df_race["mes"] = df_race.index.month
    df_race["anio"] = df_race.index.year

    # Filtrar años
    df_race = df_race[df_race["anio"].isin(anios_interes)].copy()
    if df_race.empty: return

    # Acumulado anual
    df_race["Acumulado_Anual"] = df_race.groupby("anio")["Monto"].cumsum()
    pivot = df_race.pivot_table(index="mes", columns="anio", values="Acumulado_Anual", aggfunc="last")
    pivot = pivot.reindex(range(1, 13))
    pivot = pivot[sorted(pivot.columns)] # Ordenar años ascendente

    # 2) Configuración de Colores
    mapa_colores = {
        config.ANIO_OBJETIVO: getattr(config, "COLOR_POS", "#235B4E"),        # Verde (Futuro/Meta)
        config.ANIO_ANALISIS: getattr(config, "COLOR_INFONAVIT", "#691C32"),  # Vino (Actual)
        config.ANIO_PREVIO: "#757575",                                        # Gris Medio (Previo)
        config.ANIO_PREVIO - 1: "#bdbdbd"                                     # Gris Claro
    }
    colores_plot = [mapa_colores.get(col, "#333333") for col in pivot.columns]

    # 3) Plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Dibujamos las líneas
    pivot.plot(
        ax=ax,
        linewidth=3,
        marker='o',
        markersize=6,
        color=colores_plot
    )

    # 4) Resaltado y Etiquetas Directas (EL IMPACTO)
    cols = list(pivot.columns)
    
    # Importar efectos para texto legible
    import matplotlib.patheffects as path_effects
    peff = [path_effects.withStroke(linewidth=3, foreground="white")]

    for anio in cols:
        # Obtener la serie limpia (sin NaNs al final si el año no ha terminado)
        serie = pivot[anio].dropna()
        if serie.empty: continue
        
        # Datos del último punto
        ultimo_mes = serie.index[-1]
        ultimo_valor = serie.iloc[-1]
        
        # Color correspondiente
        idx_col = cols.index(anio)
        color_linea = colores_plot[idx_col]
        
        # Grosor dinámico: Año actual y objetivo más gruesos
        lw = 4.5 if anio in [config.ANIO_ANALISIS, config.ANIO_OBJETIVO] else 3.0
        alpha = 1.0 if anio in [config.ANIO_ANALISIS, config.ANIO_OBJETIVO] else 0.7
        
        ax.lines[idx_col].set_linewidth(lw)
        ax.lines[idx_col].set_alpha(alpha)
        
        # Marcador final más grande
        ax.plot(ultimo_mes, ultimo_valor, marker='o', markersize=10, color=color_linea, markeredgecolor='white', markeredgewidth=1.5)

        # ETIQUETA DIRECTA: "2024: $150MM"
        # Ajustamos posición para que no se encimen
        offset_y = 0
        if anio == config.ANIO_PREVIO: offset_y = -10 # Bajar un poco la del año pasado si están cerca
        
        ax.annotate(
            f"{anio}\n{human_format(ultimo_valor)}",
            xy=(ultimo_mes, ultimo_valor),
            xytext=(10, offset_y), # A la derecha del punto
            textcoords="offset points",
            va="center",
            fontsize=10,
            fontweight="bold",
            color=color_linea,
            path_effects=peff
        )

    # 5) Textos y Ejes (Tus correcciones)
    ax.set_title("Colocación Acumulada Anual ($)", loc='left', color='#333333', fontweight='bold', fontsize=15, pad=10)

    # EJE Y: Etiqueta explicita solicitada
    ax.set_ylabel("Cifras en miles de Millones de Pesos", fontsize=12)
    ax.yaxis.set_major_formatter(formatter_human)

    # EJE X: Sin etiqueta "mes" y formato limpio
    ax.set_xlabel("") 
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'], fontsize=11)
    
    # Expandir un poco el eje X a la derecha para que quepan las etiquetas nuevas
    ax.set_xlim(0.8, 13.2) 

    # 6) Limpieza y Leyenda
    # Quitamos la leyenda tradicional si usamos etiquetas directas, 
    # PERO la dejamos minimalista por si acaso se enciman las líneas al principio.
    ax.legend(title="Año", title_fontsize=12, fontsize=12, loc="upper left")

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#dddddd')
    ax.spines['bottom'].set_color('#dddddd')
    ax.grid(True, linestyle='--', alpha=0.4, color='gray')

    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color='gray', style='italic')
    
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    savefig("09_carrera_acumulada.png")

def plot_28_face_to_face(df_raw_monto, anios):
    """
    28. Face to Face: Comparativo Mensual - VERSIÓN CON DELTAS
    Mejoras:
    - Cálculo y visualización de variación porcentual (YoY) por mes.
    - Etiquetado directo del monto actual.
    - Estilo jerárquico (Gris suave para año previo, Vino para actual).
    """
    anio_prev, anio_curr = anios[0], anios[1]
    
    # 1. Preparación de Datos
    df = df_raw_monto.copy()
    if not np.issubdtype(df["fecha"].dtype, np.datetime64): 
        df["fecha"] = pd.to_datetime(df["fecha"])
    
    df = df[df["fecha"].dt.year.isin(anios)]
    
    # Determinar columna de valor
    col_valor = "valor" if "valor" in df.columns else "Monto"
    
    # Pivot: Mes vs Año
    pivot = df.pivot_table(index=df["fecha"].dt.month, columns=df["fecha"].dt.year, values=col_valor, aggfunc="sum").fillna(0)
    pivot = pivot.reindex(range(1, 13), fill_value=0)
    
    # Asegurar columnas
    if anio_prev not in pivot.columns: pivot[anio_prev] = 0
    if anio_curr not in pivot.columns: pivot[anio_curr] = 0

    # 2. Configuración del Plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    indices = np.arange(12)
    width = 0.38
    
    # Colores: 2023 (Gris Claro, contexto) vs 2024 (Vino, protagonista)
    color_prev = "#CFD8DC" # Gris azulado muy suave
    color_curr = config.COLOR_INFONAVIT 

    # Barras
    bars_prev = ax.bar(indices - width/2, pivot[anio_prev], width, label=str(anio_prev), color=color_prev)
    bars_curr = ax.bar(indices + width/2, pivot[anio_curr], width, label=str(anio_curr), color=color_curr)

    # 3. Lógica de "Deltas" (Variaciones)
    for i in indices:
        val_prev = pivot.loc[i + 1, anio_prev]
        val_curr = pivot.loc[i + 1, anio_curr]
        
        # a) Etiqueta de Valor 2024 (Solo si hay dato)
        if val_curr > 0:
            ax.annotate(
                f"${human_format(val_curr)}",
                xy=(indices[i] + width/2, val_curr),
                xytext=(0, 5), textcoords="offset points",
                ha='center', va='bottom',
                fontsize=10, fontweight='bold', color=color_curr
            )

        # b) Badge de Variación % (El Insight)
        # Solo calculamos si el año previo tuvo dato para evitar división por cero
        if val_prev > 0 and val_curr > 0:
            var_pct = ((val_curr / val_prev) - 1) * 100
            
            # Determinar color del semáforo
            color_delta = config.COLOR_POS if var_pct >= 0 else config.COLOR_NEG
            signo = "+" if var_pct >= 0 else ""
            
            # Altura para el badge (un poco más arriba de la barra más alta de las dos)
            max_h = max(val_prev, val_curr)
            
            ax.annotate(
                f"{signo}{var_pct:.0f}%",
                xy=(indices[i], max_h),
                xytext=(0, 20), # Flotando arriba
                textcoords="offset points",
                ha='center', va='bottom',
                fontsize=9, fontweight='bold', color=color_delta,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=color_delta, alpha=0.8)
            )

    # 4. Estilo Final
    ax.set_ylabel("Monto Colocado ($)", fontsize=12, fontweight="bold", color=config.COLOR_NEUTRO)
    ax.yaxis.set_major_formatter(formatter_human)
    
    ax.set_xticks(indices)
    ax.set_xticklabels(["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"], fontsize=11)
    
    # Margen superior extra para los badges
    max_global = pivot.max().max()
    ax.set_ylim(top=max_global * 1.25)

    ax.set_title(f"Face to Face: {anio_prev} vs {anio_curr} (Variación %)", loc="left", fontsize=16, fontweight="bold", color="#333333")
    
    # Leyenda limpia
    ax.legend(frameon=False, loc="upper left", ncol=2)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, axis='y', linestyle='--', alpha=0.3)

    plt.tight_layout()
    savefig("28_face_to_face.png")

def plot_29_distribucion_volatilidad_yoy(df_master, anio_fin):
    """
    29. Distribución de Volatilidad (Boxplot YoY) 
    FIX: Se añade 'hue' y 'legend=False' para evitar errores de mapeo en Seaborn.
    """
    # 1. Preparación de Datos
    anio_inicio = anio_fin - 2
    df = df_master[df_master["fecha"].dt.year >= anio_inicio].copy()
    
    mapa_corto = {
        "Línea II: Adquisición de vivienda existente": "L2 Existente",
        "Línea II: Adquisición de vivienda nueva": "L2 Nueva",
        "Línea IV: Mejoramientos": "L4 Mejoras",
        "Línea III: Construcción": "L3 Const.",
        "Línea V: Pago de pasivos": "L5 Pasivos",
        "Otros: Créditos": "Otros",
        "Otros: Créditos por emergencia": "Emergencia"
    }
    df["nombre_visual"] = df["linea"].map(lambda x: mapa_corto.get(x, x.split(":")[0]))

    grp = df.groupby(["fecha", "nombre_visual"])["Monto"].sum().unstack(level=1).fillna(0)
    df_yoy = (grp.pct_change(periods=12) * 100).replace([np.inf, -np.inf], np.nan)

    mask_fecha = df_yoy.index.year == anio_fin
    df_plot = df_yoy[mask_fecha].melt(var_name="producto", value_name="Crecimiento_YoY").dropna()
    df_plot = df_plot[df_plot["Crecimiento_YoY"].between(-105, 305)]

    if df_plot.empty: return

    orden = df_plot.groupby("producto")["Crecimiento_YoY"].median().sort_values(ascending=False).index

    # 2. Paleta con Fallback (Si no existe el nombre, usa gris)
    paleta_base = {
        "L2 Existente": "#691C32", "L2 Nueva": "#BC955C", "L4 Mejoras": "#235B4E",
        "L3 Const.": "#10312B", "L5 Pasivos": "#6F7271", "Emergencia": "#D0D0D0", "Otros": "#98989A"
    }
    
    # Aseguramos que CADA producto en el DF tenga un color en el diccionario para evitar el ValueError
    paleta_final = {prod: paleta_base.get(prod, "#7f7f7f") for prod in df_plot["producto"].unique()}

    # 3. Plot
    fig, ax = plt.subplots(figsize=(14, 9))

    # --- CAMBIO CLAVE: Se agrega hue=... y legend=False ---
    sns.boxplot(
        data=df_plot, 
        x="Crecimiento_YoY", 
        y="producto", 
        order=orden,
        hue="producto",       # Obligatorio en versiones recientes de Seaborn para usar palette
        palette=paleta_final,
        ax=ax,
        width=0.6,
        showfliers=False, 
        legend=False,         # Quita la leyenda redundante que genera el 'hue'
        boxprops=dict(alpha=0.8, edgecolor='white', linewidth=1)
    )
    
    sns.stripplot(
        data=df_plot,
        x="Crecimiento_YoY",
        y="producto",
        order=orden,
        color="#333333",
        alpha=0.3,
        size=5,
        ax=ax,
        jitter=True
    )

    # 4. Etiquetas y Estilo
    ax.axvline(0, color='black', linestyle='--', linewidth=1.5, alpha=0.8)

    medianas = df_plot.groupby("producto")["Crecimiento_YoY"].median()
    import matplotlib.patheffects as path_effects
    
    for i, prod in enumerate(orden):
        val = medianas[prod]
        color_prod = paleta_final.get(prod, "#333333")
        
        ax.text(
            val, i - 0.38, 
            f"Mediana: {val:+.1f}%",
            ha='center', va='center',
            fontsize=10, fontweight='bold', color=color_prod,
            path_effects=[path_effects.withStroke(linewidth=3, foreground="white")]
        )

    ax.set_title(f"Volatilidad y Estabilidad de Crecimiento ({anio_fin})", loc="left", fontsize=16, fontweight="bold", color="#333333", pad=20)
    ax.set_xlabel("Variación Anual de Monto Colocado (%)", fontweight="bold", color="gray")
    ax.set_ylabel("")
    
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, axis='x', linestyle='--', alpha=0.4, color='gray')

    plt.figtext(0.01, 0.01, "Nota: Cada punto es un mes. La caja muestra el rango de variación típica.", fontsize=9, color="gray", style="italic")

    plt.tight_layout()
    savefig(f"29_distribucion_volatilidad_yoy.png")

def crear_portada_pdf():
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111); ax.axis("off")
    ax.text(0.5, 0.7, "REPORTE ESTRATÉGICO", ha="center", fontsize=30, fontweight="bold", color=config.COLOR_INFONAVIT)
    ax.text(0.5, 0.5, f"INFONAVIT {config.ANIO_PREVIO}-{config.ANIO_OBJETIVO}", ha="center", fontsize=18)
    if getattr(config, "PDF_REPORT", None): config.PDF_REPORT.savefig(fig)
    plt.close()