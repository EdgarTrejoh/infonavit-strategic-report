# Módulo 3: utils.py
import matplotlib.ticker as mtick

def safe_get(df, col):
    """
    Devuelve la serie si existe la columna, si no, None.
    """
    return df[col] if col in df.columns else None


def mm_formatter(scale=1e9, suffix="MM", decimals=2, thousands_sep=True):
    """
    Formateador para eje: Miles de Millones (MM)
    Ej: 1500000000 -> 1.50 MM
    """
    # Nota: miles separador opcional para lectura ejecutiva
    if thousands_sep:
        fmt = f"{{:,.{decimals}f}} {suffix}"
    else:
        fmt = f"{{:.{decimals}f}} {suffix}"

    def _f(x, pos=None):
        try:
            return fmt.format(x / scale)
        except Exception:
            return ""
    return mtick.FuncFormatter(_f)

def apply_axes_branding(ax, cfg):
    """
    Branding básico: grid, spines, ticks, colores de texto.
    """
    ax.grid(
        True, axis="y",
        linestyle="-", linewidth=0.6, alpha=0.8,
        color=cfg.COLOR_GRID
    )
    # Incremental: sólo grid mayor (menos ruido visual)
    ax.yaxis.grid(True, which="major")

    ax.tick_params(axis="both", labelsize=cfg.TICK_SIZE, colors=cfg.COLOR_TEXT)
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_color(cfg.COLOR_SPINES)

def style_right_axis(ax_right, cfg, line_color=None, label=None):
    """
    Aplica estilo al eje derecho (secundario).
    - label: texto del eje
    - line_color: color de la línea asociada (para que se vea legible)
    """
    # Etiqueta
    if label:
        ax_right.set_ylabel(label, fontsize=cfg.LABEL_SIZE, color=cfg.COLOR_TEXT)

    # ticks del eje derecho: opcional que “match” con la línea
    if cfg.RIGHT_AXIS_TICK_COLOR_MATCH_LINE and line_color:
        ax_right.tick_params(axis="y", colors=line_color, labelsize=cfg.TICK_SIZE)
        # Incremental opcional: si quieres que el label también “case”
        if label and getattr(cfg, "RIGHT_AXIS_LABEL_COLOR_MATCH_LINE", False):
            ax_right.yaxis.label.set_color(line_color)
    else:
        ax_right.tick_params(axis="y", colors=cfg.COLOR_TEXT, labelsize=cfg.TICK_SIZE)

    for spine in ax_right.spines.values():
        spine.set_color(cfg.COLOR_SPINES)

def set_money_axis_mm(ax_right, cfg, decimals=2):
    """
    Configura el eje derecho para mostrarse en MM.
    """
    ax_right.yaxis.set_major_formatter(
        mm_formatter(
            scale=cfg.MONEY_UNIT_SCALE,
            suffix=cfg.MONEY_UNIT_LABEL,
            decimals=decimals
        )
    )
    # Incremental: limitar ticks para lectura ejecutiva
    ax_right.yaxis.set_major_locator(mtick.MaxNLocator(nbins=6))
