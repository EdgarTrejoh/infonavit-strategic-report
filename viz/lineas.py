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

def plot_04_mix_productos(df_master, anio):
    df_yr = df_master[df_master["fecha"].dt.year == anio].copy()
    top = df_yr.groupby("linea")["Monto"].sum().nlargest(5).index.tolist()
    df_yr["linea_viz"] = df_yr["linea"].where(df_yr["linea"].isin(top), "OTROS")
    df_yr["mes"] = df_yr["fecha"].dt.month
    pivot = df_yr.pivot_table(index="mes", columns="linea_viz", values="Monto", aggfunc="sum").fillna(0)
    pivot = pivot.reindex(range(1, 13), fill_value=0)

    diccionario_colores = {
        "Línea II: Adquisición de suelo para uso habitacional": "#6F7271",
        "Línea II: Adquisición de vivienda existente": "#691C32",
        "Línea II: Adquisición de vivienda nueva": "#BC955C",
        "Línea III: Construcción": "#DDC9A3",
        "Línea IV: Mejoramientos": "#235B4E",
        "OTROS": "#98989A",
    }
    colores_asignados = [diccionario_colores.get(col, "#000000") for col in pivot.columns]
    
    fig, ax = plt.subplots(figsize=(14, 8))
    pivot.plot(kind="bar", stacked=True, color=colores_asignados, width=0.8, ax=ax)
    ax.set_title(f"Mezcla de Productos {anio} (Composición Mensual)", loc="left", fontweight="bold", fontsize=15, color="#333333", pad=10)
    ax.set_ylabel("Cifras en miles de Millones de Pesos", fontsize=12)
    ax.set_xlabel("")
    ax.grid(True, axis="y", linestyle="--", alpha=0.35, color="gray")
    ax.grid(False, axis="x")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#dddddd")
    ax.spines["bottom"].set_color("#dddddd")
    
    ax.set_xticklabels(["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"], rotation=0, fontsize=13)
    ax.yaxis.set_major_formatter(formatter_human)
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=10, frameon=False)
    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")
    fig.tight_layout(rect=[0, 0.03, 0.82, 1])
    savefig(f"04_mix_productos_{anio}.png")

def plot_11_ticket_real_linea(df_linea):
    # CORRECCIÓN: config.FECHA_INICIO_FILTROS
    df_plot = df_linea[df_linea["fecha"] >= config.FECHA_INICIO_FILTROS].copy()
    top_lines = df_plot.groupby("linea")["Monto_Total"].sum().nlargest(5).index.tolist()
    df_plot = df_plot[df_plot["linea"].isin(top_lines)]
    if df_plot.empty: return

    linea_lider = df_plot.groupby("linea")["Ticket_Promedio"].mean().idxmax()
    fig, ax = plt.subplots(figsize=(14, 8))
    sns.lineplot(data=df_plot, x="fecha", y="Ticket_Promedio", hue="linea", linewidth=3.2, marker="o", markersize=7, palette="tab10", ax=ax)

    for line in ax.lines:
        if line.get_label() == linea_lider:
            line.set_linewidth(4.5)
            line.set_alpha(1.0)
        else:
            line.set_alpha(0.45)

    fig.suptitle("Evolución del Ticket Promedio por Línea (Top 5)", x=0.06, ha="left", fontsize=15, fontweight="bold", color="#333333")
    ax.yaxis.set_major_formatter(formatter_human)
    
    # Eje X en español (Helper propio para evitar problemas de idioma en servidor)
    meses_es = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    def fmt_mes_custom(x, pos=None):
        dt = mdates.num2date(x)
        return f"{meses_es[dt.month-1]}\n{str(dt.year)[-2:]}" # Ene\n24

    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3)) # Cada trimestres para no saturar
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(fmt_mes_custom))
    
    #ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    #ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.set_ylabel("Ticket Promedio ($)", fontsize=12)
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, linestyle="--", alpha=0.35, color="gray")

    max_row = df_plot.loc[df_plot["Ticket_Promedio"].idxmax()]
    ax.annotate(f"Récord: {human_format(max_row.Ticket_Promedio)}\n{max_row.linea.split(':')[0]}",
                xy=(max_row.fecha, max_row.Ticket_Promedio), xytext=(0, 42), textcoords="offset points", ha="center",
                arrowprops=dict(facecolor=config.COLOR_INFONAVIT, width=2.5, headwidth=10),
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=config.COLOR_INFONAVIT, alpha=0.95),
                fontsize=10, fontweight="bold", color=config.COLOR_INFONAVIT)

    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color='gray', style='italic')

    plt.tight_layout(rect=[0, 0.03, 0.86, 0.88])
    savefig("11_ticket_real_por_linea.png")

def plot_13_share(df_raw_monto):
    
    # 1) Preparación de datos
    df = df_raw_monto[df_raw_monto["fecha"] >= config.FECHA_INICIO_FILTROS].copy()
    
    # Pivot: Mes vs Línea
    # Nota: Asegúrate que la columna de valor sea 'valor' o 'Monto' según tu ETL
    col_valor = "valor" if "valor" in df.columns else "Monto"
    pivot = df.pivot_table(index="fecha", columns="linea", values=col_valor, aggfunc="sum").fillna(0).sort_index()
    
    if pivot.empty: return

    # --- RECOMENDACIÓN DE IMPACTO: SUAVIZADO ---
    # Aplicamos media móvil de 3 meses para que la gráfica se vea más "orgánica" y menos "nerviosa"
    pivot_smooth = pivot.rolling(window=3, min_periods=1).mean()

    # Ordenar columnas: Las de mayor volumen total van abajo (para dar base sólida al gráfico)
    orden_cols = pivot_smooth.sum().sort_values(ascending=False).index.tolist()
    pivot_smooth = pivot_smooth[orden_cols]

    # 2) Mapeo de Colores Corporativos y Nombres Cortos
    # Ajusta los nombres exactos según vengan en tu CSV
    mapa_visual = {
        "Línea II: Adquisición de vivienda existente":              {"color": "#691C32", "label": "LII - Viv. Existente"}, # Vino
        "Línea II: Adquisición de vivienda nueva":                  {"color": "#BC955C", "label": "LII - Viv. Nueva"},     # Dorado
        "Línea II: Adquisición de suelo para uso habitacional":     {"color": "#10312B", "label": "LII - Adq. Suelo"},   # Verde Inst.
        "Línea IV: Mejoramientos":                                  {"color": "#DDC9A3", "label": "LIV - Mejora"},   # Verde Inst.
        "Línea III: Construcción":                                  {"color": "#235B4E", "label": "LIII - Construcción"}, # Verde Oscuro
        "Línea V: Pago de pasivos":                                 {"color": "#6F7271", "label": "LV - P. Pasivos"},   # Gris
        "Otros: Créditos por emergencia":                           {"color": "#98989A", "label": "Otros"},   # Gris Claro
        "Otros: Créditos":                                          {"color": "#D0D0D0", "label": "Otros"}         # Gris Muy Claro
    }

    # Generamos listas alineadas con el orden de las columnas
    colores_plot = []
    labels_plot = []
    
    for col in pivot_smooth.columns:
        # Busca el nombre completo o usa defaults si no encuentra match exacto
        info = mapa_visual.get(col, {"color": "#333333", "label": col[:15]})
        colores_plot.append(info["color"])
        labels_plot.append(info["label"])

    # 3) Plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    ax.stackplot(
        pivot_smooth.index, 
        pivot_smooth.T.values, 
        labels=labels_plot, 
        colors=colores_plot,
        alpha=0.90 # Un poco sólido para que los colores resalten
    )

    # Bordes blancos finos entre capas para definición
    for collection in ax.collections:
        collection.set_edgecolor("white")
        collection.set_linewidth(0.5)

    # 4) Estilo y Formato
    ax.set_title("Evolución de la Colocación por Línea", loc="left", color="#333333", fontsize=15, fontweight="bold", pad=10)
    
    # Eje Y limpio
    ax.set_ylabel("Cifras en miles de Millones de Pesos", fontsize=12)
    ax.yaxis.set_major_formatter(formatter_human)
    ax.set_ylim(bottom=0)

    # Eje X en español (Helper propio para evitar problemas de idioma en servidor)
    meses_es = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    def fmt_mes_custom(x, pos=None):
        dt = mdates.num2date(x)
        return f"{meses_es[dt.month-1]}\n{str(dt.year)[-2:]}" # Ene\n24

    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3)) # Cada trimestres para no saturar
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(fmt_mes_custom))
    
    # Leyenda compacta a la derecha (fuera del área gráfica)
    # Invertimos el orden de handles/labels en la leyenda para que coincida visualmente con el apilado (el de arriba en la lista es el de arriba en la gráfica)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], bbox_to_anchor=(1.01, 0.5), loc="center left", fontsize=11, frameon=False, title="Línea - Producto")

    # Limpieza
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#dddddd")
    ax.spines["bottom"].set_color("#dddddd")
    ax.grid(True, linestyle="--", alpha=0.4, color="gray", axis="y")

    plt.figtext(0.01, 0.01, "Nota: Se aplica suavizado de 3 meses para visualizar tendencia. | Fuente: Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")
    
    plt.tight_layout(rect=[0, 0.02, 0.85, 1]) # Margen derecho extra para la leyenda
    savefig("13_share_evolucion.png")

def plot_19_share_lineas(df_master, anio, top_n=5):
    """
    19. Evolución de Participación de Mercado (Share) - VERSIÓN DIRECT LABELING
    Mejoras:
    - Etiquetas directas al final de la línea (Nombre + %).
    - Paleta corporativa.
    - Línea líder más gruesa.
    """
    # 1. Preparación de Datos
    df = df_master[df_master["fecha"].dt.year == anio].copy()
    if df.empty: return

    # Pivot: Mes vs Línea (Monto)
    pivot = df.pivot_table(index="fecha", columns="linea", values="Monto", aggfunc="sum").fillna(0)
    
    # Calcular Share (%)
    share = pivot.div(pivot.sum(axis=1), axis=0) * 100
    
    # Filtrar Top N líneas (por promedio anual)
    top_cols = share.mean().sort_values(ascending=False).head(top_n).index
    share_plot = share[top_cols]

    # 2. Configuración Visual (Colores y Nombres)
    mapa_visual = {
        "Línea II: Adquisición de vivienda existente":          {"color": "#691C32", "label": "Viv. Existente"}, # Vino
        "Línea II: Adquisición de vivienda nueva":              {"color": "#BC955C", "label": "Viv. Nueva"},     # Dorado
        "Línea II: Adquisición de suelo para uso habitacional": {"color": "#8D6E63", "label": "Adq. Suelo"},
        "Línea IV: Mejoramientos":                              {"color": "#235B4E", "label": "Mejora"},   # Verde
        "Línea III: Construcción":                              {"color": "#10312B", "label": "Construcción."},    # Verde Oscuro
        "Línea V: Pago de pasivos":                             {"color": "#6F7271", "label": "P. Pasivos"},   # Gris
        "Otros: Créditos":                                      {"color": "#98989A", "label": "Otros"}
    }

    # 3. Plot
    fig, ax = plt.subplots(figsize=(14, 8))

    # Identificar cuál es la línea líder al final del periodo para destacarla
    last_values = share_plot.iloc[-1]
    lider_name = last_values.idxmax()

    # Iterar sobre las columnas para graficar
    for col in share_plot.columns:
        # Obtener estilos
        estilo = mapa_visual.get(col, {"color": "#757575", "label": col[:10]})
        color = estilo["color"]
        label_corto = estilo["label"]
        
        # Datos de la serie
        serie = share_plot[col]
        
        # Destacar líder
        es_lider = (col == lider_name)
        lw = 4.5 if es_lider else 3.0
        alpha = 1.0 if es_lider else 0.75
        
        # Graficar línea
        ax.plot(
            serie.index, 
            serie, 
            color=color, 
            linewidth=lw, 
            alpha=alpha,
            marker='o',       # Marcadores en todos los puntos
            markersize=6,
            markevery=1       # En cada mes
        )

        # --- ETIQUETADO DIRECTO AL FINAL (La mejora solicitada) ---
        ultimo_valor = serie.iloc[-1]
        ultimo_fecha = serie.index[-1]

        # Texto: "L2 Nueva: 45.2%"
        texto_label = f"{label_corto}\n{ultimo_valor:.1f}%"
        
        # Ajuste de posición para que no se pegue al punto
        ax.annotate(
            texto_label,
            xy=(ultimo_fecha, ultimo_valor),
            xytext=(10, 0), # 10 puntos a la derecha
            textcoords="offset points",
            va="center", ha="left",
            color=color, fontweight="bold", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.6) # Fondo semi-transparente por si cruza líneas
        )
        
        # Marcador final más grande para anclar la vista
        ax.plot(ultimo_fecha, ultimo_valor, marker='o', markersize=9, color=color, markeredgecolor='white', markeredgewidth=1.5)

    # 4. Estilo Final
    ax.set_title(f"Evolución del % de Participación por Producto \nMonto de crédito otorgado - {anio}", loc='left', color='#333333', fontsize=15, fontweight="bold", pad=10)
    
    # Eje Y en porcentaje
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    
    # Eje X formateado a meses
    # Eje X en español (Helper propio para evitar problemas de idioma en servidor)
    meses_es = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    def fmt_mes_custom(x, pos=None):
        dt = mdates.num2date(x)
        return f"{meses_es[dt.month-1]}\n{str(dt.year)[-2:]}" # Ene\n24

    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1)) # Cada trimestres para no saturar
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(fmt_mes_custom))
    
    # Margen derecho extra para que quepan las etiquetas de texto
    # (Esto es clave: extendemos el límite x un 15% más allá de la última fecha)
    ax.set_xlim(right=share_plot.index.max() + pd.Timedelta(days=45))

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#dddddd')
    ax.spines['bottom'].set_color('#dddddd')
    
    ax.grid(True, axis='y', linestyle='--', alpha=0.4, color='gray')
    ax.grid(False, axis='x') # Quitamos grid vertical para limpieza

    # Nota al pie
    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")
    plt.tight_layout(rect=[0, 0.03, 1, 1])

    savefig("19_share_lineas_evolucion.png")

def plot_20_conquista_portafolio(df_master, desde, top_n=8, smooth=3):
    """
    20. Evolución de la Colocación: Combinación Línea-Producto.
    Muestra la verdadera mezcla del portafolio segmentando el Crédito Tradicional.
    """
    df = df_master[df_master["fecha"] >= desde].copy()
    if df.empty: return

    # --- PASO 1: INGENIERÍA DE CATEGORÍAS ---
    def segmentar_mezcla(row):
        linea = str(row['linea']).lower()
        prod = str(row['producto']).lower()
        
        # Segmentación del Tradicional (El gigante)
        if "tradicional" in prod:
            if "nueva" in linea: return "Trad - Viv. Nueva"
            if "existente" in linea: return "Trad - Viv. Existente"
            if "construcción" in linea: return "Trad - Construcción"
            if "suelo" in linea: return "Trad - Suelo"
            return "Trad - Otros"
        
        # Simplificación de los demás
        if "cofinavit" in prod: return "Cofinavit (Mix)"
        if "total" in prod: return "Infonavit Total"
        if "mejoravit" in prod: return "Mejoravit"
        if "segundo" in prod: return "2do Crédito"
        
        return "Otros"

    df["Mezcla_Categoría"] = df.apply(segmentar_mezcla, axis=1)

    # --- PASO 2: PIVOT Y SUAVIZADO ---
    pivot = df.pivot_table(index="fecha", columns="Mezcla_Categoría", values="Monto", aggfunc="sum").fillna(0)
    
    # Ordenar columnas: Los Tradicionales abajo para dar base, el resto arriba
    # Esto mantiene la "montaña" visual pero ya segmentada
    orden_manual = [
        "Trad - Viv. Existente", "Trad - Viv. Nueva", "Trad - Construcción", "Trad - Suelo", 
        "Trad - Otros", "Cofinavit (Mix)", "Infonavit Total", "Mejoravit", "2do Crédito", "Otros"
    ]
    columnas_finales = [c for c in orden_manual if c in pivot.columns]
    pivot = pivot[columnas_finales]
    
    if smooth > 1:
        pivot = pivot.rolling(window=smooth, min_periods=1).mean()

    # --- PASO 3: PALETA DE COLORES POR FAMILIAS ---
    # Usamos gradientes para que se entienda que pertenecen al mismo grupo
    mapa_colores = {
        "Trad - Viv. Existente": "#4a1222", # Vino Muy Oscuro
        "Trad - Viv. Nueva":     "#691C32", # Vino Corporativo
        "Trad - Construcción":   "#8e2b46", # Vino Claro
        "Trad - Suelo":          "#a65268", # Rosáceo Institucional
        "Trad - Otros":          "#c28091", # Rosáceo Pálido
        "Cofinavit (Mix)":       "#BC955C", # Dorado
        "Infonavit Total":       "#DDC9A3", # Dorado Claro
        "Mejoravit":             "#235B4E", # Verde
        "2do Crédito":           "#6F7271", # Gris
        "Otros":                 "#D0D0D0"  # Gris Claro
    }
    colores_plot = [mapa_colores.get(c, "#333333") for c in pivot.columns]

    # --- PASO 4: PLOT ---
    fig, ax = plt.subplots(figsize=(15, 9))
    
    # Graficar Áreas
    ax.stackplot(pivot.index, pivot.T.values, labels=pivot.columns, colors=colores_plot, alpha=0.85)

    # --- AJUSTE: EJE Y ---
    ax.set_ylabel("Cifras en miles de Millones de Pesos", fontsize=12, fontweight="bold", color="gray")
    ax.yaxis.set_major_formatter(formatter_human)

    # --- AJUSTE: EJE X EN ESPAÑOL ---
    meses_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    def date_formatter_es(x, pos):
        dt = mdates.num2date(x)
        # Retorna: Ene 22, Abr 22, etc.
        return f"{meses_es[dt.month-1]} {str(dt.year)[-2:]}"

    ax.xaxis.set_major_formatter(mtick.FuncFormatter(date_formatter_es))
    # Forzamos que muestre marcas cada 3 o 6 meses para que no se sature
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6)) 

    # --- RESTO DEL ESTILO ---
    ax.set_title(f"Composición del portafolio: Mezcla Línea-Producto ", 
                 loc='left', fontweight="bold", fontsize=15, color="#333333", pad=20)
    
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], bbox_to_anchor=(1.02, 0.5), loc='center left', frameon=False)

    # Nota al pie
    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", fontsize=9, color="gray", style="italic")
    #plt.tight_layout(rect=[0, 0.03, 1, 1])

    plt.tight_layout(rect=[0, 0.03, 0.85, 1])
    savefig("20_conquista_portafolio_final.png")

def plot_24_yoy_por_linea(df_master, anio):
    """
    24. Variación Anual (YoY) por Línea.
    CIRUGÍA: 
    - Eliminación de outlier 'Emergencia'.
    - Homologación de colores corporativos.
    - Mejora de espaciado en etiquetas.
    """
    # 1. Preparación de Datos y Filtro de Años comparables
    anio_previo = anio - 1
    meses_actuales = sorted(
        df_master.loc[df_master["fecha"].dt.year == anio, "fecha"].dt.month.unique()
    )
    if not meses_actuales:
        return

    mes_corte = int(max(meses_actuales))
    meses_comparables = list(range(1, mes_corte + 1))
    df = df_master[
        (df_master["fecha"].dt.year.isin([anio_previo, anio]))
        & (df_master["fecha"].dt.month.isin(meses_comparables))
    ].copy()
    
    # Mapeo de Nombres Cortos (Mismo diccionario de plot_14 y plot_21)
    mapa_corto = {
        "Línea II: Adquisición de vivienda existente": "L2 Existente",
        "Línea II: Adquisición de vivienda nueva": "L2 Nueva",
        "Línea II: Adquisición de suelo para uso habitacional": "L2 Suelo",
        "Línea IV: Mejoramientos": "L4 Mejoras",
        "Línea III: Construcción": "L3 Const.",
        "Línea V: Pago de pasivos": "L5 Pasivos",
        "Otros: Créditos": "Otros"
    }
    
    # Aplicar nombres y FILTRAR OUTLIERS
    df["nombre_visual"] = df["linea"].map(lambda x: mapa_corto.get(x, "Eliminar"))
    df = df[df["nombre_visual"] != "Eliminar"].copy() # Aquí eliminamos 'Emergencia' y otros no mapeados

    # 2. Agrupación y Cálculo de Variación
    grp = df.groupby([df["fecha"].dt.year, "nombre_visual"])["Monto"].sum().unstack(level=0).fillna(0)
    if anio_previo not in grp.columns:
        grp[anio_previo] = 0
    if anio not in grp.columns:
        grp[anio] = 0
    grp = grp.rename(columns={anio_previo: "Prev", anio: "Curr"})
    grp = grp[["Prev", "Curr"]]
    
    # Solo líneas con datos en ambos años para evitar infinitos
    grp = grp[grp["Prev"] > 0].copy()
    grp["YoY"] = ((grp["Curr"] / grp["Prev"]) - 1) * 100
    grp = grp.sort_values("YoY", ascending=True) 

    # 3. Paleta Homologada (Vino, Dorado, Verde, Gris)
    mapa_colores = {
        "L2 Viv. Existente": "#691C32", # Vino
        "L2 Viv. Nueva":     "#BC955C", # Dorado
        "L4 Mejoras":   "#235B4E", # Verde
        "L3 Const.":    "#10312B", # Verde Oscuro
        "L5 Pasivos":   "#6F7271", # Gris
        "L2 Adq. Suelo":     "#8D6E63", # Café
        "Otros":        "#98989A"
    }
    colores = [mapa_colores.get(idx, "#333333") for idx in grp.index]

    # 4. Plot
    fig, ax = plt.subplots(figsize=(14, 10))
    bars = ax.barh(grp.index, grp["YoY"], color=colores, alpha=0.9, height=0.7)
    
    # Línea de origen
    ax.axvline(0, color='black', linewidth=0.8, alpha=0.5)

    # 5. Etiquetas de Impacto (Porcentaje + Monto)
    for bar, (idx, row) in zip(bars, grp.iterrows()):
        valor_pct = row["YoY"]
        monto_actual = row["Curr"]
        
        # Posicionamiento dinámico de la etiqueta
        if valor_pct >= 0:
            x_label = bar.get_width() + 2
            ha = 'left'
            label_color = "#333333"
        elif valor_pct <= -35:
            x_label = bar.get_width() + 3
            ha = 'left'
            label_color = "white"
        else:
            x_label = bar.get_width() - 2
            ha = 'right'
            label_color = "#333333"
        
        etiqueta = f"+{valor_pct:.1f}%  ({human_format(monto_actual)})" if valor_pct >= 0 else f"{valor_pct:.1f}%  ({human_format(monto_actual)})"
        
        ax.text(
            x_label, 
            bar.get_y() + bar.get_height()/2, 
            etiqueta,
            va='center', ha=ha, 
            fontsize=11, fontweight='bold', color=label_color
        )

    # 6. Estética Final
    ax.set_title(f"Variación Anual (YoY) por Línea: {anio}", loc='left', fontsize=18, fontweight="bold", color="#333333", pad=20)
    meses_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    ventana_label = f"{meses_es[0]}-{meses_es[mes_corte - 1]}"
    ax.set_xlabel("Crecimiento vs Año Anterior (%) - YTD comparable", fontweight="bold", color="gray", fontsize=12)
    
    # Formato de porcentaje en eje X
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    
    # Ajustar límites para que quepan etiquetas positivas y negativas
    min_yoy = grp["YoY"].min()
    max_yoy = grp["YoY"].max()
    ax.set_xlim(left=min(min_yoy * 1.15, -10), right=max(max_yoy * 1.25, 10))

    # Limpieza de spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color("#dddddd")
    ax.spines['bottom'].set_color("#dddddd")
    
    ax.grid(True, axis='x', linestyle='--', alpha=0.4, color='gray', zorder=0)

    plt.figtext(0.01, 0.01, f"Nota: Comparación YTD comparable {ventana_label} {anio} vs {ventana_label} {anio_previo}. El valor entre paréntesis indica el Monto Colocado en el año actual. | Se excluyen líneas de emergencia por distorsión de escala.", 
                fontsize=9, color="gray", style="italic")
    
    plt.tight_layout()
    savefig("24_yoy_por_linea.png")

def plot_26_pareto_lineas(df_master, anio):
    """
    26. Pareto Líneas (80/20) - VERSIÓN IMPACTO
    Mejoras:
    - Colores consistentes con otras gráficas (L4 Verde, L2 Vino).
    - Etiquetas de valor ($) y porcentaje (%) directas.
    - Señalización clara de la concentración.
    """
    # 1. Preparación de Datos
    df = df_master[df_master["fecha"].dt.year == anio].copy()
    if df.empty: return

    # Agrupamos por nombre corto de Línea (Broad Category)
    # Limpieza: "Línea II: ..." -> "Línea II"
    df["nombre_corto"] = df["linea"].astype(str).apply(lambda x: x.split(":")[0].strip())
    
    grp = df.groupby("nombre_corto", as_index=False)["Monto"].sum().sort_values("Monto", ascending=False)
    grp = grp.reset_index(drop=True)

    grp["Acumulado"] = grp["Monto"].cumsum()
    grp["Porcentaje_Acum"] = 100 * grp["Acumulado"] / grp["Monto"].sum()

    # 2. Configuración de Colores (Mapeo Broad)
    # Asignamos colores según la línea general para mantener consistencia
    mapa_colores = {
        "Línea II":  "#691C32", # Vino (Dominante)
        "Línea IV":  "#235B4E", # Verde (Mejoras)
        "Línea III": "#10312B", # Verde Oscuro (Construcción)
        "Línea V":   "#6F7271", # Gris (Pasivos)
        "Otros":     "#98989A"  # Gris Claro
    }
    colores = [mapa_colores.get(x, "#555555") for x in grp["nombre_corto"]]

    # 3. Plot
    fig, ax1 = plt.subplots(figsize=(14, 8))

    # --- EJE 1: Barras (Monto) ---
    bars = ax1.bar(
        grp["nombre_corto"], 
        grp["Monto"], 
        color=colores, 
        alpha=0.95,
        width=0.75
    )

    # Etiquetas de Valor ($) sobre las barras
    for bar in bars:
        height = bar.get_height()
        ax1.annotate(
            f"${human_format(height)}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 5), textcoords="offset points",
            ha='center', va='bottom',
            fontsize=11, fontweight='bold', color="#333333"
        )

    ax1.set_ylabel("Monto Colocado ($)", fontsize=12, fontweight="bold", color=config.COLOR_NEUTRO)
    ax1.yaxis.set_major_formatter(formatter_human)
    # Margen superior extra para la línea
    ax1.set_ylim(top=grp["Monto"].max() * 1.2)

    # --- EJE 2: Línea (Acumulado) ---
    ax2 = ax1.twinx()
    color_linea = "#263238" # Gris oscuro
    
    ax2.plot(
        grp.index, 
        grp["Porcentaje_Acum"], 
        color=color_linea, 
        marker="o", 
        linewidth=2.5, 
        markersize=8,
        label="% Acumulado"
    )

    # Etiquetas de % en la línea (Solo las relevantes para no saturar)
    for i, pct in enumerate(grp["Porcentaje_Acum"]):
        # Etiquetamos el primero, el que cruza el 80% y el último
        es_cruce = (pct >= 80) and (grp.iloc[i-1]["Porcentaje_Acum"] < 80 if i > 0 else True)
        if i == 0 or es_cruce or i == len(grp)-1:
            ax2.annotate(
                f"{pct:.0f}%",
                xy=(i, pct),
                xytext=(0, -15), textcoords="offset points",
                ha='center', va='top',
                fontsize=10, fontweight='bold', color=color_linea,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7)
            )

    ax2.set_ylabel("% Acumulado", fontsize=12, fontweight="bold", color=color_linea)
    ax2.set_ylim(0, 110)
    
    # Línea de referencia 80%
    ax2.axhline(80, color="#d67e27", linestyle="--", linewidth=1.5)
    ax2.text(len(grp)-0.5, 80, " 80%", va="center", ha="left", color="#d67e27", fontweight="bold")

    # 4. Insight Automático
    # Detectar cuántas líneas hacen el 80%
    idx_80 = grp[grp["Porcentaje_Acum"] >= 79.9].first_valid_index()
    num_lineas = idx_80 + 1
    pct_lider = grp.iloc[0]["Porcentaje_Acum"]
    nombre_lider = grp.iloc[0]["nombre_corto"]

    texto_insight = f"Alta Concentración:\n{nombre_lider} representa el {pct_lider:.0f}% del total."
    
    # Colocar insight en el espacio vacío del gráfico
    ax1.text(
        0.5, 0.6, texto_insight, 
        transform=ax1.transAxes, 
        ha="left", va="center",
        fontsize=12, color="#555555",
        bbox=dict(boxstyle="round,pad=0.5", fc="#f5f5f5", ec="#dddddd")
    )

    # 5. Estilo Final
    ax1.set_title(f"Pareto por Líneas de Negocio ({anio})", loc="left", fontsize=16, fontweight="bold", color="#333333")
    
    ax1.spines['top'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax1.grid(False, axis='x')
    
    plt.tight_layout()
    savefig("26_pareto_lineas.png")

def plot_30_cierre_lineaII_vivienda_vs_terreno(df_l2, anio):
    """
    30. Cierre Línea II: Vivienda vs Terreno.
    MEJORA: Paleta de colores llamativa y diferenciada por producto.
    """
    fig, axes = plt.subplots(1, 2, figsize=(18, 9)) 
    subtipos = ["Vivienda", "Terreno"]
    
    # Diccionario de colores para consistencia visual
    colores_productos = {
        "Crédito Tradicional": "#691C32",  # Vino
        "Cofinavit": "#BC955C",           # Dorado
        "Infonavit Total": "#235B4E",      # Verde
        "Apoyo Infonavit": "#6F7271"       # Gris
    }

    import matplotlib.patheffects as path_effects
    peff = [path_effects.withStroke(linewidth=3, foreground="white")]

    for ax, subtipo in zip(axes, subtipos):
        df_plot = df_l2[df_l2["Subtipo_Adquisicion"] == subtipo].copy()
        if df_plot.empty:
            ax.set_axis_off()
            continue
        
        grp = df_plot.groupby("producto")["Monto"].sum().reset_index()
        
        # Asignar colores basados en el nombre del producto
        colores_barras = [colores_productos.get(p, "#98989A") for p in grp["producto"]]
            
        bars = ax.bar(grp["producto"], grp["Monto"], color=colores_barras, alpha=0.9, edgecolor="white", linewidth=1)
        
        # Etiquetado
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.annotate(
                    f"${human_format(h)}",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 10),
                    textcoords="offset points",
                    ha="center", va="bottom",
                    fontsize=12, fontweight="bold", 
                    color="#333333", # Texto oscuro para que resalte con el halo blanco
                    path_effects=peff
                )
        
        # Estética de paneles
        ax.set_title(f"Segmento: {subtipo}", fontweight="bold", fontsize=15, color="#555555", pad=20)
        ax.yaxis.set_major_formatter(formatter_human)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.2)
        ax.set_ylim(top=grp["Monto"].max() * 1.2)

    # Título Principal
    fig.suptitle(f"Análisis Línea II: Adquisición de Vivienda - Terreno ({anio})", 
                 x=0.04, y=0.98, ha='left', fontweight="bold", fontsize=20, color="#333333")

    plt.figtext(0.01, 0.01, "Fuente: Elaboración propia con datos del Sistema de Información INFONAVIT", 
                fontsize=10, color='gray', style='italic')

    plt.tight_layout(rect=[0, 0.05, 1, 0.92])
    savefig("30_cierre_lineaII_vivienda_vs_terreno.png")

def plot_generico_monto_vs_creditos(grp, anio, linea_nombre, num_grafica=None):
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "", linea_nombre.replace(":", "").replace(" ", "_"))
    _helper_doble_eje_barras(grp, "producto", "Monto", "Num_Creditos", f"{linea_nombre} ({anio})", f"{num_grafica}_{safe}.png")

def plot_generico_share(grp, anio, linea_nombre, num_grafica=None):
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "", linea_nombre.replace(":", "").replace(" ", "_"))
    _helper_share_horizontal(grp, "producto", "Monto", "Num_Creditos", f" {linea_nombre} Share ({anio})", f"{num_grafica}_{safe}.png")

def plot_generico_ticket(grp, anio, linea_nombre, num_grafica=None):
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "", linea_nombre.replace(":", "").replace(" ", "_"))
    _helper_barra_simple_ticket(grp, "producto", "Ticket", f"{linea_nombre} Ticket ({anio})", f"{num_grafica}_{safe}.png")
