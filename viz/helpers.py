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


def _smart_label_positioner(ax, final_points, min_distance=2.0):
    """Ajusta posiciones verticales de etiquetas para evitar superposiciones."""
    final_points.sort(key=lambda x: x[0])
    positions = [p[0] for p in final_points]

    changed = True
    iterations = 0
    max_iterations = 50

    while changed and iterations < max_iterations:
        changed = False
        iterations += 1
        for i in range(len(positions) - 1):
            dist = positions[i + 1] - positions[i]
            if dist < min_distance:
                overlap = min_distance - dist
                positions[i] -= overlap / 2
                positions[i + 1] += overlap / 2
                changed = True

    for i, (original_y, color, text_str, x_pos) in enumerate(final_points):
        new_y = positions[i]
        ax.text(
            x_pos, new_y, f"  {text_str}",
            color=color, fontweight="bold", fontsize=11, va="center"
        )
        if abs(new_y - original_y) > 0.5:
            ax.plot(
                [x_pos, x_pos], [original_y, new_y],
                color=color, linewidth=0.8, linestyle=":", alpha=0.6
            )


def _smart_scatter_labeling(ax, data, x_col, y_col, label_col, color_col, x_mean, y_mean, manual_offsets=None):
    """Versión V3: incluye soporte para ajustes manuales específicos."""
    df_sorted = data.sort_values(y_col, ascending=False).copy()
    placed_boxes = []
    y_span = data[y_col].max() - data[y_col].min()
    min_dist_y = y_span * 0.12 if y_span else 1.0

    for _, row in df_sorted.iterrows():
        x, y = row[x_col], row[y_col]
        label = row[label_col]
        color = row[color_col]

        # 0) Excepciones manuales
        if manual_offsets and label in manual_offsets:
            dx, dy = manual_offsets[label]
            bbox_props = dict(boxstyle="round,pad=0.3", fc="white", ec=color, alpha=0.85, lw=1.5)
            ax.annotate(
                label, xy=(x, y), xytext=(dx, dy),
                textcoords="offset points",
                ha="left" if dx > 0 else "right",
                va="bottom" if dy > 0 else "top",
                fontsize=9, fontweight="bold", color="#333333",
                bbox=bbox_props,
                arrowprops=dict(arrowstyle="-", color=color, lw=1.5, alpha=0.6),
                zorder=12
            )
            placed_boxes.append((x, y + (dy / 50 * y_span * 0.05 if y_span else 0)))
            continue

        # A) Cuadrantes automáticos
        offset_base = 40
        dx = offset_base if x >= x_mean else -offset_base
        dy = offset_base if y >= y_mean else -offset_base

        # B) Colisiones
        proposed_y = y
        adjustment_count = 0
        for (px, py) in placed_boxes:
            dist_x_visual = abs(x - px)
            dist_y_visual = abs(proposed_y - py)
            if dist_x_visual < (data[x_col].max() * 0.15 if data[x_col].max() else 1.0) and dist_y_visual < min_dist_y:
                proposed_y = py - min_dist_y
                adjustment_count += 1
        placed_boxes.append((x, proposed_y))

        # C) Dibujar
        bbox_props = dict(boxstyle="round,pad=0.3", fc="white", ec=color, alpha=0.85, lw=1.5)
        if abs(proposed_y - y) > (min_dist_y * 0.1) or adjustment_count > 0:
            ax.annotate(
                label, xy=(x, y),
                xytext=(x + (dx / 50 * (data[x_col].max() * 0.05 if data[x_col].max() else 1.0)), proposed_y),
                textcoords="data",
                ha="left" if dx > 0 else "right", va="center",
                fontsize=9, fontweight="bold", color="#333333",
                bbox=bbox_props,
                arrowprops=dict(arrowstyle="-|>", color=color, shrinkA=5, shrinkB=5, lw=1.5),
                zorder=10
            )
        else:
            ax.annotate(
                label, xy=(x, y), xytext=(dx, dy),
                textcoords="offset points",
                ha="left" if dx > 0 else "right", va="bottom" if dy > 0 else "top",
                fontsize=9, fontweight="bold", color="#333333",
                bbox=bbox_props,
                arrowprops=dict(arrowstyle="-", color=color, lw=1, alpha=0.6),
                zorder=10
            )

# =====================================================================
# IO / FORMATTERS
# =====================================================================
def savefig(name: str):
    """Guarda la figura actual como PNG y la agrega al PDF global."""
    # Asegurarse de usar config.OUTDIR
    fp = config.OUTDIR / name
    plt.tight_layout()
    plt.savefig(fp, dpi=300,bbox_inches="tight", pad_inches=0.3)
    print(f"PNG Generado: {name}")

    if getattr(config, "PDF_REPORT", None) is not None:
        config.PDF_REPORT.savefig(bbox_inches="tight")
        print("   └── Agregado al Reporte PDF")
    plt.close()

def human_format(x, pos=None):
    x = float(x) if x is not None else 0.0
    if x >= 1e12: return f"{x*1e-12:,.1f}B"
    if x >= 1e9: return f"{x*1e-9:,.1f}MM"
    if x >= 1e6: return f"{x*1e-6:,.1f}M"
    if x >= 1e3: return f"{x*1e-3:,.0f}k"
    return f"{x:,.0f}"

formatter_human = mtick.FuncFormatter(human_format)

def calcular_crecimiento_yoy(df_global, metrica="Monto"):
    df = df_global.copy()
    df["mes"] = df.index.month
    df["anio"] = df.index.year
    pivot = df.pivot_table(index="mes", columns="anio", values=metrica)
    
    cols = pivot.columns.sort_values()
    df_yoy = pd.DataFrame(index=pivot.index)
    for i in range(1, len(cols)):
        year_curr = cols[i]
        year_prev = cols[i - 1]
        col_name = f"{year_curr} vs {year_prev}"
        df_yoy[col_name] = ((pivot[year_curr] - pivot[year_prev]) / pivot[year_prev]) * 100
    return df_yoy

# =====================================================================
# HELPERS “MAESTROS”
# =====================================================================
def _helper_doble_eje_barras(df, x_col, y1_col, y2_col, titulo, archivo_salida,
                             color1=None, color2="#10312B", label1="Monto ($)", label2="# Créditos"):
    # Asignación de color corporativo por defecto
    if color1 is None:
        color1 = config.COLOR_INFONAVIT
        
    if df.empty:
        print(f"⚠️ Dataframe vacío para: {titulo}")
        return

    # Aumentamos el tamaño de la figura para que respire
    fig, ax1 = plt.subplots(figsize=(16, 9))
    indices = np.arange(len(df))
    width = 0.35

    # --- EJE 1: MONTO (Barras Izquierda) ---
    bars1 = ax1.bar(indices - width / 2, df[y1_col], width, color=color1, label=label1, alpha=0.9)
    ax1.set_ylabel(label1, color=color1, fontweight="bold", fontsize=14, labelpad=15)
    ax1.yaxis.set_major_formatter(formatter_human)
    
    # Ajuste de escala para que las etiquetas no toquen el borde superior
    ax1.set_ylim(top=df[y1_col].max() * 1.25)

    # --- EJE 2: VOLUMEN (Barras Derecha) ---
    ax2 = ax1.twinx()
    bars2 = ax2.bar(indices + width / 2, df[y2_col], width, color=color2, label=label2, alpha=0.9)
    ax2.set_ylabel(label2, color=color2, fontweight="bold", fontsize=14, labelpad=15)
    ax2.yaxis.set_major_formatter(mtick.StrMethodFormatter("{x:,.0f}"))
    
    # Ajuste de escala eje derecho
    ax2.set_ylim(top=df[y2_col].max() * 1.25)
    ax2.grid(False) # Quitamos el grid del segundo eje para evitar cruces de líneas

    # --- ETIQUETADO DIRECTO CON HALO ---
    import matplotlib.patheffects as path_effects
    peff = [path_effects.withStroke(linewidth=3, foreground="white")]

    def etiquetar(barras, ax, es_dinero, color):
        for bar in barras:
            h = bar.get_height()
            txt = f"${human_format(h)}" if es_dinero else f"{h:,.0f}"
            ax.annotate(txt, xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 8),
                        textcoords="offset points", ha="center", va="bottom",
                        fontsize=11, fontweight="bold", color=color, path_effects=peff)

    etiquetar(bars1, ax1, True, color1)
    etiquetar(bars2, ax2, False, color2)

    # --- FORMATO DE EJES Y TÍTULO ---
    ax1.set_xticks(indices)
    rot = 15 if len(df) > 4 else 0
    ax1.set_xticklabels(df[x_col], fontweight="bold", rotation=rot, fontsize=12)
    
    # Título con estilo de dashboard (Grande y a la izquierda)
    ax1.set_title(titulo, loc="left", color="#333333", fontsize=18, fontweight="bold", pad=25)

    # Limpieza visual de recuadros
    for ax in [ax1, ax2]:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)

    # Grid horizontal sutil solo en el eje principal
    ax1.grid(axis="y", linestyle="--", alpha=0.3, color="gray")

    # Fuente al pie
    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", 
                fontsize=10, color="gray", style="italic")

    plt.tight_layout(rect=[0, 0.03, 1, 0.98])
    savefig(archivo_salida)

def _helper_share_horizontal(df, y_col, col_monto, col_num, titulo, archivo_salida):
    """
    Helper para gráficas comparativas de Share (Monto vs Volumen).
    Ajustes: Homologación de colores, limpieza de grid y etiquetas de impacto.
    """
    if df.empty: return
    
    local_df = df.copy()
    # Cálculo de participación porcentual
    local_df["Share_Monto"] = local_df[col_monto] / local_df[col_monto].sum() * 100
    local_df["Share_Num"] = local_df[col_num] / local_df[col_num].sum() * 100
    local_df = local_df.sort_values(col_monto, ascending=True)

    # Configuración de la figura
    fig, axes = plt.subplots(1, 2, figsize=(16, 9), sharey=True)
    
    # Paleta Corporativa
    color_monto = config.COLOR_INFONAVIT # Vino
    color_volumen = "#10312B"            # Verde Institucional

    # --- PANEL 1: Share por Monto (%) ---
    bars1 = axes[0].barh(local_df[y_col], local_df["Share_Monto"], color=color_monto, alpha=0.9)
    axes[0].set_title("Share por Monto (%)", fontweight="bold", fontsize=14, color=color_monto, pad=15)
    axes[0].xaxis.set_major_formatter(mtick.PercentFormatter())
    
    # Espacio para etiquetas
    axes[0].set_xlim(right=local_df["Share_Monto"].max() * 1.25)
    
    for bar in bars1:
        w = bar.get_width()
        axes[0].text(w, bar.get_y() + bar.get_height() / 2, f" {w:.1f}%",
                     va="center", fontweight="bold", color=color_monto, fontsize=11)

    # --- PANEL 2: Share por # Créditos (%) ---
    bars2 = axes[1].barh(local_df[y_col], local_df["Share_Num"], color=color_volumen, alpha=0.9)
    axes[1].set_title("Share por # Créditos (%)", fontweight="bold", fontsize=14, color=color_volumen, pad=15)
    axes[1].xaxis.set_major_formatter(mtick.PercentFormatter())
    
    # Espacio para etiquetas
    axes[1].set_xlim(right=local_df["Share_Num"].max() * 1.25)
    
    for bar in bars2:
        w = bar.get_width()
        axes[1].text(w, bar.get_y() + bar.get_height() / 2, f" {w:.1f}%",
                     va="center", fontweight="bold", color=color_volumen, fontsize=11)

    # --- ESTILO GLOBAL ---
    fig.suptitle(titulo, fontsize=18, fontweight="bold", color="#333333", x=0.5, y=0.98)
    
    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color("#dddddd")
        ax.grid(axis="x", linestyle="--", alpha=0.3)
        # Etiquetas de categorías en negrita
        ax.tick_params(axis='y', labelsize=11)
        for label in ax.get_yticklabels():
            label.set_fontweight("bold")

    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", 
                fontsize=10, color="gray", style="italic")

    plt.tight_layout(rect=[0, 0.05, 1, 0.93])
    savefig(archivo_salida)

def _helper_barra_simple_ticket(df, x_col, y_col, titulo, archivo_salida, color_default="#BC955C"):
    """
    Helper para Ticket Promedio con colores homologados y diseño ejecutivo.
    """
    if df.empty: return
    
    # Diccionario maestro de colores para homologación
    colores_productos = {
        "Crédito Tradicional": "#691C32",  # Vino
        "Cofinavit": "#BC955C",           # Dorado
        "Infonavit Total": "#235B4E",     # Verde
        "Apoyo Infonavit": "#6F7271",     # Gris
        "Mejoravit": "#10312B"            # Verde Oscuro
    }

    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Asignación de colores por barra
    colores_barras = [colores_productos.get(x, color_default) for x in df[x_col]]
    
    bars = ax.bar(df[x_col], df[y_col], color=colores_barras, alpha=0.9, edgecolor="white")
    
    # Título Estilo Dashboard
    ax.set_title(titulo, loc="left", color="#333333", fontsize=18, fontweight="bold", pad=25)
    
    # Eje Y: Tamaño y Formato
    ax.set_ylabel("Ticket Promedio ($)", fontsize=14, fontweight="bold", labelpad=15)
    ax.yaxis.set_major_formatter(formatter_human)
    
    # Etiquetas Eje X
    ax.tick_params(axis='x', labelsize=12)
    for label in ax.get_xticklabels():
        label.set_fontweight("bold")

    # --- ETIQUETADO DIRECTO CON HALO ---
    import matplotlib.patheffects as path_effects
    peff = [path_effects.withStroke(linewidth=3, foreground="white")]

    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h, 
                    f"${human_format(h)}", 
                    ha="center", va="bottom", 
                    fontweight="bold", fontsize=12,
                    path_effects=peff)

    # Limpieza visual
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#dddddd")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    
    # Margen para etiquetas
    ax.set_ylim(top=df[y_col].max() * 1.2)

    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", 
                fontsize=10, color="gray", style="italic")
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    savefig(archivo_salida)

# =====================================================================
# PLOTS (1..)
# =====================================================================

__all__ = ['_smart_label_positioner', '_smart_scatter_labeling', 'savefig', 'human_format', 'formatter_human', 'calcular_crecimiento_yoy', '_helper_doble_eje_barras', '_helper_share_horizontal', '_helper_barra_simple_ticket']
