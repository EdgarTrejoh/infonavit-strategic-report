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

def plot_05_pareto_estados(df_master, anio):
    df_year = df_master[df_master["fecha"].dt.year == anio].copy()
    if df_year.empty:
        print(f"⚠️ No hay datos para {anio}.")
        return

    estados = df_year.groupby("nombre_estado")["Monto"].sum().sort_values(ascending=False)
    pareto_df = pd.DataFrame({"Monto": estados})
    pareto_df["Acumulado_Pct"] = pareto_df["Monto"].cumsum() / pareto_df["Monto"].sum() * 100

    idx_80 = pareto_df["Acumulado_Pct"].ge(80).idxmax()
    n_estados_80 = pareto_df.index.get_loc(idx_80) + 1
    pct_80 = float(pareto_df.loc[idx_80, "Acumulado_Pct"])

    fig, ax1 = plt.subplots(figsize=(14, 8))
    ax1.bar(pareto_df.index, pareto_df["Monto"], color="#691C32", alpha=0.90)
    ax1.set_ylabel("Cifras en miles de Millones de Pesos", fontsize=12)
    ax1.yaxis.set_major_formatter(formatter_human)
    ax1.tick_params(axis="x", labelrotation=45, labelsize=9)
    for label in ax1.get_xticklabels(): label.set_ha("right")

    ax2 = ax1.twinx()
    ax2.plot(pareto_df.index, pareto_df["Acumulado_Pct"], color="#BC955C", marker="o", linewidth=2, ms=5)
    ax2.set_ylabel("% Acumulado", fontsize=11, color="#555555")
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax2.set_ylim(0, 110)
    ax2.axhline(80, color="#333333", linestyle="--", linewidth=1, alpha=0.6)
    ax1.axvline(n_estados_80 - 1, color="#DDC9A3", linestyle="--", linewidth=2, alpha=0.9)

    ax2.text(0.98, 0.74, f"Corte 80%: {n_estados_80} estados\n({idx_80}, {pct_80:.1f}%)",
             transform=ax2.transAxes, ha="right", va="center", fontsize=9, fontweight="bold",
             color="#333333", bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#dddddd", alpha=0.9))

    ax1.grid(axis="y", linestyle="--", alpha=0.30, color="gray")
    ax1.set_title(f"¿Qué estados generan el 80%? (acumulado en {anio})", loc="left", fontweight="bold", fontsize=15, color="#333333", pad=10)
    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    savefig(f"05_pareto_estados_{anio}.png")

def plot_15_top_estados(df_master, nombre_linea, anio):
    """
    15. Top 10 Estados por Monto - Línea seleccionada
    MEJORAS:
    - Etiquetas de valor sobre cada barra (Direct Labeling).
    - Resaltado sutil del Estado #1 (Líder).
    - Ejes y títulos más limpios.
    """
    if not nombre_linea: return
    
    # 1. Filtro de Datos
    df = df_master[
        (df_master["fecha"].dt.year == anio) & 
        (df_master["linea"] == nombre_linea)
    ].copy()

    if df.empty: return

    # 2. Agrupación y Top 10
    top_estados = (
        df.groupby("nombre_estado")["Monto"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    # 3. Configuración del Plot
    fig, ax = plt.subplots(figsize=(14, 8))

    # --- ESTRATEGIA VISUAL: Highlight al Líder ---
    # El #1 va en un Vino profundo ("#4a1222"), el resto en el Vino corporativo estándar
    colores = [config.COLOR_INFONAVIT] * len(top_estados)
    colores[0] = "#4a1222" # Highlight sutil

    # Convertimos a Miles de Millones para graficar barras manejables
    top_plot_vals = top_estados / 1e9

    bars = ax.bar(
        top_plot_vals.index, 
        top_plot_vals.values, 
        color=colores,
        width=0.75,
        alpha=0.95
    )

    # 4. Etiquetas de Valor (LO QUE FALTABA)
    for bar in bars:
        height = bar.get_height()
        # Valor real para la etiqueta (recuperamos escala completa para el formateador)
        valor_real = height * 1e9 
        
        ax.annotate(
            f"${human_format(valor_real)}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 5), # 5 puntos arriba de la barra
            textcoords="offset points",
            ha="center", 
            va="bottom",
            fontsize=11, 
            fontweight="bold",
            color="#333333"
        )

    # 5. Estilo Final
    # Limpiamos nombre de línea (quitamos lo que está antes de los dos puntos si es muy largo)
    nombre_limpio = nombre_linea.split(".")[0] if ":" in nombre_linea else nombre_linea
    
    ax.set_title(f"Top 10 Estados: {nombre_limpio} ({anio})", loc="left", fontsize=15, fontweight="bold", color="#333333", pad=15)
    
    # Eje Y más claro
    ax.set_ylabel("Monto Colocado (miles de Millones de Pesos)", fontsize=12)
    
    # Margen superior extra (15%) para que quepan las etiquetas nuevas
    ax.set_ylim(top=top_plot_vals.max() * 1.15)

    # Limpieza visual
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#dddddd")
    ax.spines["bottom"].set_color("#dddddd")
    
    ax.grid(True, axis="y", linestyle="--", alpha=0.4, color="gray")
    
    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    
    # Guardado seguro
    safe_name = "15_top_estados_" + "".join([c if c.isalnum() else "_" for c in nombre_limpio.lower()]) + f"_{anio}.png"
    savefig(safe_name)

def plot_16_top10_estados_proyeccion(df_master, anio):
    """
    16. Top 10 Estados – Volumen vs Monto
    CORRECCIÓN: Se usa ax.annotate en lugar de ax.text para soportar xytext.
    """
    # 1. Preparación de Datos
    df = df_master[df_master["fecha"].dt.year == anio].copy()
    if df.empty: return

    grp = (
        df.groupby("nombre_estado", as_index=False)
        .agg({"Num_Creditos": "sum", "Monto": "sum"})
        .sort_values("Num_Creditos", ascending=False)
        .head(10)
    )
    
    # Calcular Ticket para el insight
    grp["Ticket"] = grp["Monto"] / grp["Num_Creditos"]

    # 2. Configuración del Plot
    fig, ax1 = plt.subplots(figsize=(14, 8))

    # --- EJE 1: VOLUMEN (BARRAS) ---
    bars = ax1.bar(
        grp["nombre_estado"], 
        grp["Num_Creditos"], 
        color=config.COLOR_INFONAVIT, 
        alpha=0.90, 
        label="Créditos (#)"
    )

    # Etiquetas de Créditos (Dentro de la barra)
    # Aquí usamos ax.text porque NO necesitamos offset
    for bar in bars:
        height = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width()/2, 
            height/2, 
            f"{height/1000:.0f}k", 
            ha='center', va='center', 
            color='white', fontweight='bold', fontsize=10,
            path_effects=[path_effects.withStroke(linewidth=2, foreground=config.COLOR_INFONAVIT)]
        )

    ax1.set_ylabel("Créditos Formalizados (#)", fontsize=12)
    ax1.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    
    # --- EJE 2: MONTO (LÍNEA) ---
    ax2 = ax1.twinx()
    color_linea = '#D4AF37' 
    
    ax2.plot(
        grp["nombre_estado"], 
        grp["Monto"], 
        color=color_linea, 
        linewidth=3, 
        linestyle="-", 
        marker="o", 
        markersize=9,
        markeredgecolor="white",
        markeredgewidth=1.5,
        label="Monto ($)"
    )

    # Etiquetas de Monto (Encima del punto)
    # CORRECCIÓN AQUÍ: Usamos annotate en lugar de text
    for i, txt in enumerate(grp["Monto"]):
        ax2.annotate(
            human_format(txt),            # Texto
            xy=(i, txt),                  # Coordenada del punto (x, y)
            xytext=(0, 10),               # Offset (10 puntos arriba)
            textcoords='offset points',
            ha='center', va='bottom', 
            color=color_linea, fontweight='bold', fontsize=10,
            path_effects=[path_effects.withStroke(linewidth=3, foreground="white")]
        )

    ax2.set_ylabel("Monto Colocado (miles de Millones de Pesos)", fontsize=12, color=color_linea)
    ax2.yaxis.set_major_formatter(formatter_human)
    ax2.grid(False)
    ax2.set_ylim(top=grp["Monto"].max() * 1.25)

    # --- INSIGHT AUTOMÁTICO ---
    idx_max_ticket = grp["Ticket"].idxmax()
    state_max = grp.loc[idx_max_ticket, "nombre_estado"]
    val_ticket = grp.loc[idx_max_ticket, "Ticket"]
    
    pos_x = list(grp["nombre_estado"]).index(state_max)
    pos_y = grp.loc[idx_max_ticket, "Monto"]

    ax2.annotate(
        f"Mayor Ticket Promedio:\n${val_ticket/1000:.0f}k ({state_max})",
        xy=(pos_x, pos_y),
        xytext=(0, 45), textcoords="offset points",
        ha="center", 
        bbox=dict(boxstyle="round,pad=0.4", fc="#FFF8E1", ec=color_linea),
        arrowprops=dict(arrowstyle="->", color=color_linea, linewidth=1.5),
        fontsize=9, color="#5D4037", fontweight="bold"
    )

    # 3. Estilo y Limpieza
    ax1.set_title(f"Top 10 Estados – Volumen vs Monto ({anio})", loc="left", color="#333333", fontsize=15, fontweight="bold", pad=10)
    
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1+h2, l1+l2, loc="upper right", frameon=False)

    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax2.spines["left"].set_visible(False)

    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")

    plt.tight_layout(rect=[0, 0.03, 1, 1])

    savefig("16_top10_proyeccion.png")

def plot_17_scatter_estado_ticket_proyeccion(df_master, anio):
    df = df_master[(df_master["linea"] == "Línea III: Construcción") & (df_master["fecha"].dt.year == anio)].copy()
    if df.empty: return

    g = df.groupby("nombre_estado", as_index=False).agg(Monto=("Monto", "sum"), Num_Creditos=("Num_Creditos", "sum"))
    g = g[g["Num_Creditos"] > 0]
    g["Ticket"] = g["Monto"] / g["Num_Creditos"]

    fig, ax = plt.subplots(figsize=(14, 9))
    sizes = (g["Monto"] / g["Monto"].max()) * 14000

    ax.scatter(
        g["Num_Creditos"],
        g["Ticket"],
        s=sizes,
        alpha=0.7,
        edgecolors="white",
        color="#9F2241",
        linewidth=1.5
    )

    # Etiquetas
    for _, r in g.iterrows():
        ax.text(
            r["Num_Creditos"],
            r["Ticket"],
            r["nombre_estado"],
            fontsize=9,
            ha="center",
            va="center",
            path_effects=[path_effects.withStroke(linewidth=3, foreground="white")]
        )

    # Título principal y ejes
    ax.set_title(f"Línea III: Construcción ({anio})\nEstados: Volumen vs Ticket", loc="left", fontweight="bold", fontsize=15, color="#333333", pad=10)
    ax.set_xlabel("Número de Créditos (#)", fontsize=12)
    ax.set_ylabel("Ticket Promedio (Millones de Pesos)", fontsize=12)
    
    # Formatos
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    ax.yaxis.set_major_formatter(formatter_human)
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.set_axisbelow(True)

    # Nota al pie
    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")
    plt.tight_layout(rect=[0, 0.03, 1, 1])

    savefig("17_lineaIII_proyeccion_scatter_estado_ticket.png")

def plot_18_pareto_estados_proyeccion(df_master, anio):
    """
    18. Concentración Geográfica (Pareto)
    MEJORA: Identificación visual exacta del punto de corte del 80%.
    """
    # 1. Preparación de Datos
    df = df_master[df_master["fecha"].dt.year == anio].copy()
    if df.empty: return

    # Agrupar, ordenar y calcular acumulados
    grp = df.groupby("nombre_estado", as_index=False)["Monto"].sum().sort_values("Monto", ascending=False)
    
    # IMPORTANTE: Resetear índice para trabajar con coordenadas numéricas (0, 1, 2...)
    grp = grp.reset_index(drop=True)
    
    grp["Acumulado"] = grp["Monto"].cumsum()
    grp["Porcentaje_Acum"] = 100 * grp["Acumulado"] / grp["Monto"].sum()

    # 2. Configuración del Plot
    fig, ax1 = plt.subplots(figsize=(14, 8))

    # --- EJE 1: Barras (Monto Individual) ---
    ax1.bar(grp.index, grp["Monto"], color=config.COLOR_INFONAVIT, alpha=0.95, label="Monto Individual")
    ax1.set_ylabel("Monto Colocado ($)", fontsize=12, color=config.COLOR_INFONAVIT)
    ax1.yaxis.set_major_formatter(formatter_human)
    
    # Etiquetas eje X (Estados) - Rotadas para lectura
    ax1.set_xticks(grp.index)
    ax1.set_xticklabels(grp["nombre_estado"], rotation=45, fontsize=9, ha="right")

    # --- EJE 2: Línea (% Acumulado) ---
    ax2 = ax1.twinx()
    color_linea = "#263238" # Gris oscuro casi negro
    
    ax2.plot(
        grp.index, 
        grp["Porcentaje_Acum"], 
        color=color_linea, 
        marker="o", 
        linewidth=2, 
        markersize=5,
        label="% Acumulado"
    )
    
    ax2.set_ylabel("% Acumulado", fontsize=12, color=color_linea)
    ax2.set_ylim(0, 105) # Margen arriba del 100%
    
    # Línea de referencia del 80%
    ax2.axhline(80, color="#d32f2f", linestyle="--", linewidth=1.5, alpha=0.7)

    # 3. ANOTACIÓN DEL CORTE 80%
    # Buscamos el primer índice donde el acumulado supera o iguala el 80%
    # Usamos 79.9 para asegurar que atrapamos el cruce exacto
    corte_row = grp[grp["Porcentaje_Acum"] >= 79.9].iloc[0]
    idx_corte = corte_row.name # Índice numérico (0, 1, 2...)
    pct_real = corte_row["Porcentaje_Acum"]
    num_estados = idx_corte + 1 # +1 porque el índice empieza en 0

    # a) Línea vertical guía (baja desde el punto hasta el estado)
    ax1.axvline(idx_corte, color="#d32f2f", linestyle=":", alpha=0.6)

    # b) La Anotación (Caja con flecha)
    ax2.annotate(
        f"Corte 80%:\nTop {num_estados} Estados",
        xy=(idx_corte, pct_real),
        xytext=(40, -40), # Desplazado a la derecha y abajo para no tapar la curva
        textcoords="offset points",
        ha="left", va="top",
        bbox=dict(boxstyle="round,pad=0.4", fc="#FFF3E0", ec="#d32f2f", alpha=1.0),
        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2", color="#d32f2f", linewidth=1.5),
        fontsize=10, fontweight="bold", color="#BF360C"
    )

    # 4. Estilo Final
    ax1.set_title(f"Concentración Geográfica (Pareto) - {anio}", loc='left', color='#333333', fontsize=15, fontweight="bold", pad=10)
    
    ax1.spines['top'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    
    ax1.grid(True, axis='y', linestyle='--', alpha=0.3)
    ax2.grid(False) # Grid solo en barras para no ensuciar

    # Nota al pie
    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")
    plt.tight_layout(rect=[0, 0.03, 1, 1])

    savefig("18_pareto_estados_proyeccion.png")

def plot_35_deep_dive_cdmx(df_master, anio, estado="Ciudad de México"):
    """
    35. Radiografía Estatal (Butterfly Chart) - VERSIÓN HEADERS AL PIE
    Ajustes: Encabezados en la base, KPI centralizado y alineación de "mariposa".
    """
    df = df_master[
        (df_master["fecha"].dt.year == anio) & 
        (df_master["nombre_estado"] == estado)
    ].copy()
    
    if df.empty: return

    # Mapeo de nombres cortos
    mapa_corto = {
        "Adquisición de vivienda existente": "Viv. Existente",
        "Adquisición de vivienda nueva": "Viv. Nueva",
        "Adquisición de suelo para uso habitacional": "Suelo",
        "Mejoramientos": "Mejoras",
        "Construcción": "Construcción",
        "Pago de pasivos": "Pasivos"
    }

    df["nombre_base"] = df["linea"].apply(lambda x: x.split(":")[1].strip() if ":" in x else x)
    df["nombre_visual"] = df["nombre_base"].map(lambda x: mapa_corto.get(x, x))
    
    grp = df.groupby("nombre_visual", as_index=False).agg({"Num_Creditos": "sum", "Monto": "sum"})
    grp = grp.sort_values("Monto", ascending=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 10), sharey=True)
    plt.subplots_adjust(wspace=0.15) 
    bar_height = 0.6 

    col_vol = "#235B4E" # Verde
    col_monto = config.COLOR_INFONAVIT # Vino

    # --- LADO IZQUIERDO: VOLUMEN ---
    bars1 = ax1.barh(grp.index, grp["Num_Creditos"], color=col_vol, alpha=0.9, height=bar_height)
    ax1.set_xlim(right=grp["Num_Creditos"].max() * 1.4)
    ax1.invert_xaxis()
    
    # Header en la parte inferior (X-Axis Label)
    ax1.set_xlabel("VOLUMEN (# CRÉDITOS)", fontweight='bold', color=col_vol, fontsize=13, labelpad=15)
    
    for bar in bars1:
        w = bar.get_width()
        if w > 0:
            ax1.annotate(f"{w:,.0f}", xy=(w, bar.get_y() + bar.get_height()/2),
                         xytext=(-12, 0), textcoords="offset points",
                         ha='right', va='center', fontweight='bold', color=col_vol, fontsize=12)

    # --- LADO DERECHO: MONTO ---
    bars2 = ax2.barh(grp.index, grp["Monto"], color=col_monto, alpha=0.9, height=bar_height)
    ax2.set_xlim(right=grp["Monto"].max() * 1.4)
    
    # Header en la parte inferior (X-Axis Label)
    ax2.set_xlabel("MONTO COLOCADO ($)", fontweight='bold', color=col_monto, fontsize=13, labelpad=15)
    
    for bar in bars2:
        w = bar.get_width()
        if w > 0:
            ax2.annotate(f"${human_format(w)}", xy=(w, bar.get_y() + bar.get_height()/2),
                         xytext=(12, 0), textcoords="offset points",
                         ha='left', va='center', fontweight='bold', color=col_monto, fontsize=12)

    # --- EJE CENTRAL ---
    for i, linea in zip(grp.index, grp["nombre_visual"]):
        ax2.text(-0.075, i, linea, ha='center', va='center', fontsize=11, fontweight='bold', 
                 color='#444444', transform=ax2.get_yaxis_transform(),
                 bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#e0e0e0", alpha=1, zorder=10))

    # --- TÍTULO Y KPI ---
    ticket_global = grp["Monto"].sum() / grp["Num_Creditos"].sum()
    fig.suptitle(f"35. RADIOGRAFÍA: {estado.upper()} ({anio})", x=0.5, y=0.97, fontsize=20, fontweight='bold')
    
    fig.text(0.5, 0.91, f" TICKET PROMEDIO GLOBAL: ${ticket_global:,.0f} ", 
             ha='center', fontsize=14, color='white', fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.4", fc="#6F7271", ec="none"))

    # Limpiar ejes para look "Dashboard"
    for ax in [ax1, ax2]:
        ax.set_yticks([])
        ax.set_xticks([]) # Opcional: esconder ticks numéricos para limpieza total
        for spine in ax.spines.values(): spine.set_visible(False)

    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con información del Sistema de Información Infonavit", 
                fontsize=9, color="gray", style="italic")

    plt.tight_layout(rect=[0, 0.05, 1, 0.90])
    
    safe_state = estado.replace(" ", "_")
    savefig(f"35_radiografia_{safe_state}.png")

